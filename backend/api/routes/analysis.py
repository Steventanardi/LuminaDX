from __future__ import annotations

import asyncio
import base64
import json
import shutil
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from loguru import logger

from api.deps import verify_api_key
from config import settings
from core.audit_log import log_analysis_complete, log_analysis_start, log_signoff
from core.dicom_processor import convert_to_nifti, extract_study_info, load_series_map
from core.llm_client import llm_client
from core.rag_engine import rag_engine
from core.radiomics_extractor import extract, summarize
from core.segmentation import SegmentationResult, run_segmentation
from core.slice_exporter import create_montage, export_overlay_slices_b64
from models.schemas import AnalysisJob, AnalysisStatus, DiagnosticReport, PatientContext, SeriesInfo, SignOff, SignOffRequest

router = APIRouter()

_jobs: Dict[str, AnalysisJob] = {}
_slices: Dict[str, List[str]] = {}      # job_id → overlaid slices
_raw_slices: Dict[str, List[str]] = {}  # job_id → raw slices (no mask)


def _step(job: AnalysisJob, status: AnalysisStatus, pct: int, msg: str) -> None:
    job.status = status
    job.progress = pct
    job.current_step = msg
    logger.info(f"[{job.job_id[:8]}] {pct:3d}%  {msg}")


async def _pipeline(
    job: AnalysisJob,
    study_dir: Path,
    patient_info: Optional[dict],
) -> None:
    study_id = job.study_id
    proc_dir = settings.processed_dir / study_id
    proc_dir.mkdir(parents=True, exist_ok=True)

    meta_path = study_dir / "_meta.json"
    meta = json.loads(meta_path.read_text()) if meta_path.exists() else {"type": "dicom"}
    upload_type = meta.get("type", "dicom")

    log_analysis_start(job.job_id, study_id, settings.llm_model)
    t0 = time.monotonic()

    try:
        if upload_type == "image":
            await _run_image_pipeline(job, study_dir, meta, proc_dir, patient_info)
        else:
            await _run_volumetric_pipeline(job, study_dir, meta, proc_dir, upload_type, patient_info)
        log_analysis_complete(job.job_id, study_id, settings.llm_model, time.monotonic() - t0, "complete")

    except Exception as exc:
        logger.exception(f"Pipeline error: {exc}")
        job.status = AnalysisStatus.FAILED
        job.progress = 0
        job.current_step = "Failed"
        job.error = str(exc)
        log_analysis_complete(job.job_id, study_id, settings.llm_model, time.monotonic() - t0, "failed")


async def _run_image_pipeline(
    job: AnalysisJob,
    study_dir: Path,
    meta: dict,
    proc_dir: Path,
    patient_info: Optional[dict],
) -> None:
    study_id = job.study_id
    t = {}

    _step(job, AnalysisStatus.PROCESSING, 10, "Loading image files …")
    image_names = meta.get("image_files", [])
    image_files = [study_dir / n for n in image_names if (study_dir / n).exists()]
    if not image_files:
        image_files = sorted(
            f for f in study_dir.iterdir()
            if f.suffix.lower() in (".jpg", ".jpeg", ".png")
        )
    if not image_files:
        raise RuntimeError("No image files found in study directory")

    # Encode images for frontend viewer (no segmentation → raw == overlaid)
    slices_b64: list[str] = []
    for img_path in image_files[:24]:
        slices_b64.append(base64.b64encode(img_path.read_bytes()).decode())
    _slices[job.job_id] = slices_b64
    _raw_slices[job.job_id] = slices_b64

    modality = meta.get("modality", "CT")
    seg = SegmentationResult()
    montage = image_files[0]

    _step(job, AnalysisStatus.ANALYZING, 60, "Retrieving guidelines (RAG) …")
    t0 = time.monotonic()
    rag_ctx = await rag_engine.retrieve(f"liver imaging {modality} LI-RADS HCC assessment")
    t["rag_s"] = round(time.monotonic() - t0, 2)

    _step(job, AnalysisStatus.ANALYZING, 80, "Running LLM analysis …")
    t0 = time.monotonic()
    report: DiagnosticReport = await llm_client.analyze(
        montage_path=montage,
        seg=seg,
        modality=modality,
        rag_context=rag_ctx,
        radiomics_summary="",
        patient_info=patient_info,
    )
    t["llm_s"] = round(time.monotonic() - t0, 2)
    report.study_id = study_id

    job.status = AnalysisStatus.COMPLETE
    job.progress = 100
    job.current_step = "Analysis complete"
    job.completed_at = datetime.utcnow()
    job.report = report
    job.timings = t
    logger.info(f"Image pipeline complete for study {study_id}")


async def _run_volumetric_pipeline(
    job: AnalysisJob,
    study_dir: Path,
    meta: dict,
    proc_dir: Path,
    upload_type: str,
    patient_info: Optional[dict],
) -> None:
    study_id = job.study_id
    t: dict[str, float] = {}

    # ── Step 1 — detect modality & locate NIfTI ──────────────────────────────
    if upload_type == "nifti":
        _step(job, AnalysisStatus.PROCESSING, 5, "Reading NIfTI metadata …")
        modality = meta.get("modality", "CT")
        nifti_files = meta.get("nifti_files", [])
        src_paths = [study_dir / fn for fn in nifti_files if (study_dir / fn).exists()]
        if not src_paths:
            src_paths = sorted(study_dir.glob("*.nii.gz")) + sorted(study_dir.glob("*.nii"))
        if not src_paths:
            raise RuntimeError("No NIfTI files found in study directory")

        _step(job, AnalysisStatus.PROCESSING, 12, "Preparing NIfTI volume …")
        nifti_dir = proc_dir / "nifti"
        nifti_dir.mkdir(parents=True, exist_ok=True)
        for p in src_paths:
            shutil.copy2(p, nifti_dir / p.name)
        nifti_paths = [nifti_dir / p.name for p in src_paths]
        series_list = [SeriesInfo(series_uid="nifti-0", description="NIfTI Volume", phase="arterial", num_slices=1)]
        phase_labels = ["arterial"]
        t["conversion_s"] = 0.0
    else:
        # DICOM
        _step(job, AnalysisStatus.PROCESSING, 5, "Reading DICOM metadata …")
        series_map = load_series_map(study_dir)
        info = extract_study_info(series_map)
        modality_enum = info["modality"]
        modality = modality_enum.value if modality_enum else "CT"
        series_list = info["series"]
        phase_labels = [s.phase or s.description for s in series_list]

        _step(job, AnalysisStatus.PROCESSING, 12, "Converting DICOM → NIfTI …")
        t0 = time.monotonic()
        nifti_dir = proc_dir / "nifti"
        nifti_paths = convert_to_nifti(study_dir, nifti_dir)
        t["conversion_s"] = round(time.monotonic() - t0, 2)
        if not nifti_paths:
            raise RuntimeError("DICOM→NIfTI conversion produced no output")

    primary = nifti_paths[0]

    # ── Step 3 — Segmentation ─────────────────────────────────────────────────
    _step(job, AnalysisStatus.SEGMENTING, 22, "Segmenting liver & tumours (GPU) …")
    seg_dir = proc_dir / "seg"
    t0 = time.monotonic()
    seg: SegmentationResult = await asyncio.get_event_loop().run_in_executor(
        None, run_segmentation, primary, seg_dir, settings.device,
    )
    t["segmentation_s"] = round(time.monotonic() - t0, 2)

    # ── Step 4 — Overlay slices for frontend ─────────────────────────────────
    _step(job, AnalysisStatus.PROCESSING, 52, "Rendering overlay slices …")
    t0 = time.monotonic()
    slices_b64 = export_overlay_slices_b64(primary, seg, modality, n_slices=24, apply_overlay=True)
    raw_b64 = export_overlay_slices_b64(primary, seg, modality, n_slices=24, apply_overlay=False)
    _slices[job.job_id] = slices_b64
    _raw_slices[job.job_id] = raw_b64
    t["overlay_s"] = round(time.monotonic() - t0, 2)

    # ── Step 5 — Montage for LLM ──────────────────────────────────────────────
    _step(job, AnalysisStatus.PROCESSING, 60, "Building diagnostic montage …")
    montage = create_montage(nifti_paths, seg, proc_dir, modality, phase_labels)

    # ── Step 6 — Radiomics ────────────────────────────────────────────────────
    _step(job, AnalysisStatus.EXTRACTING, 68, "Extracting radiomic features …")
    tumor_mask_path: Optional[Path] = None
    for candidate in ("liver_lesions.nii.gz", "liver_tumor.nii.gz", "liver_tumour.nii.gz"):
        p = seg_dir / "tumor" / candidate
        if p.exists():
            tumor_mask_path = p
            break
    t0 = time.monotonic()
    features = extract(primary, tumor_mask_path)
    t["radiomics_s"] = round(time.monotonic() - t0, 2)
    rad_summary = summarize(features)

    # ── Step 7 — RAG ─────────────────────────────────────────────────────────
    _step(job, AnalysisStatus.ANALYZING, 76, "Retrieving guidelines (RAG) …")
    rag_query = (
        f"{seg.lesions[0].size_mm:.0f}mm liver lesion {modality} LI-RADS assessment"
        if seg.lesions
        else f"liver imaging {modality} LI-RADS HCC assessment"
    )
    t0 = time.monotonic()
    rag_ctx = await rag_engine.retrieve(rag_query)
    t["rag_s"] = round(time.monotonic() - t0, 2)

    # ── Step 8 — LLM ─────────────────────────────────────────────────────────
    _step(job, AnalysisStatus.ANALYZING, 84, "Running LLM analysis …")
    t0 = time.monotonic()
    report: DiagnosticReport = await llm_client.analyze(
        montage_path=montage,
        seg=seg,
        modality=modality,
        rag_context=rag_ctx,
        radiomics_summary=rad_summary,
        patient_info=patient_info,
    )
    t["llm_s"] = round(time.monotonic() - t0, 2)
    report.study_id = study_id

    job.status = AnalysisStatus.COMPLETE
    job.progress = 100
    job.current_step = "Analysis complete"
    job.completed_at = datetime.utcnow()
    job.report = report
    job.timings = t
    logger.info(
        f"Pipeline complete for study {study_id} — "
        + ", ".join(f"{k}={v}s" for k, v in t.items())
    )


@router.post("/start/{study_id}", response_model=AnalysisJob)
async def start_analysis(
    study_id: str,
    background_tasks: BackgroundTasks,
    patient_context: Optional[PatientContext] = None,
    _: None = Depends(verify_api_key),
):
    study_dir = settings.uploads_dir / study_id
    if not study_dir.exists():
        raise HTTPException(404, "Study not found — upload files first")

    job = AnalysisJob(job_id=str(uuid.uuid4()), study_id=study_id)
    _jobs[job.job_id] = job

    pt_dict = patient_context.model_dump() if patient_context else None
    background_tasks.add_task(_pipeline, job, study_dir, pt_dict)
    return job


@router.get("/status/{job_id}", response_model=AnalysisJob)
async def job_status(job_id: str):
    job = _jobs.get(job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    return job


@router.get("/history")
async def list_jobs():
    """Return all in-session analysis jobs, newest first."""
    return sorted(
        [j.model_dump() for j in _jobs.values()],
        key=lambda j: j["created_at"],
        reverse=True,
    )


@router.get("/report/{job_id}", response_model=DiagnosticReport)
async def get_report(job_id: str):
    job = _jobs.get(job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    if job.status != AnalysisStatus.COMPLETE or not job.report:
        raise HTTPException(202, "Report not ready yet")
    return job.report


@router.get("/slices/{job_id}")
async def get_slices(job_id: str):
    if job_id not in _jobs:
        raise HTTPException(404, "Job not found")
    slices = _slices.get(job_id, [])
    raw = _raw_slices.get(job_id, [])
    return {"slices": slices, "raw_slices": raw, "count": len(slices)}


@router.post("/signoff/{job_id}", response_model=AnalysisJob)
async def sign_off(job_id: str, req: SignOffRequest):
    job = _jobs.get(job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    if job.status != AnalysisStatus.COMPLETE:
        raise HTTPException(400, "Cannot sign off an incomplete analysis")
    job.sign_off = SignOff(
        radiologist_name=req.radiologist_name,
        decision=req.decision,
        comments=req.comments,
    )
    logger.info(f"Sign-off [{job_id[:8]}] {req.decision} by {req.radiologist_name}")
    log_signoff(job_id, job.study_id, req.radiologist_name, req.decision)
    return job


@router.get("/benchmark/{job_id}")
async def get_benchmark(job_id: str):
    """Return per-step timing breakdown for a completed analysis job."""
    job = _jobs.get(job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    total = (
        (job.completed_at - job.created_at).total_seconds()
        if job.completed_at
        else None
    )
    return {
        "job_id": job_id,
        "status": job.status,
        "total_s": round(total, 2) if total is not None else None,
        "steps": job.timings,
        "created_at": job.created_at.isoformat(),
        "completed_at": job.completed_at.isoformat() if job.completed_at else None,
    }


@router.get("/fhir/{job_id}")
async def fhir_export(job_id: str):
    """Return a FHIR R4 DiagnosticReport JSON for the completed analysis."""
    job = _jobs.get(job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    if job.status != AnalysisStatus.COMPLETE or not job.report:
        raise HTTPException(400, "Analysis not complete")

    r = job.report
    status = "final" if job.sign_off else "preliminary"

    observations: list[dict] = []
    for l in r.lesions:
        obs: dict = {
            "resourceType": "Observation",
            "status": status,
            "code": {"coding": [{"system": "http://loinc.org", "code": "85319-2",
                                  "display": "LI-RADS category"}]},
            "valueCodeableConcept": {"text": l.lirads_category},
            "component": [],
        }
        if l.location_segment:
            obs["component"].append({
                "code": {"text": "Couinaud segment"},
                "valueString": l.location_segment,
            })
        if l.size_mm is not None:
            obs["component"].append({
                "code": {"coding": [{"system": "http://loinc.org", "code": "33756-8",
                                     "display": "Lesion size"}]},
                "valueQuantity": {"value": l.size_mm, "unit": "mm",
                                  "system": "http://unitsofmeasure.org", "code": "mm"},
            })
        observations.append(obs)

    fhir_report: dict = {
        "resourceType": "DiagnosticReport",
        "id": job_id,
        "meta": {"profile": ["http://hl7.org/fhir/StructureDefinition/DiagnosticReport"]},
        "status": status,
        "category": [{"coding": [{"system": "http://terminology.hl7.org/CodeSystem/v2-0074",
                                   "code": "RAD", "display": "Radiology"}]}],
        "code": {"coding": [{"system": "http://loinc.org", "code": "24606-6",
                              "display": "MR Liver"}],
                 "text": f"{r.modality} Liver — LI-RADS Assessment"},
        "subject": {"reference": f"Patient/{r.study_id[:8]}", "display": "De-identified patient"},
        "issued": r.generated_at.isoformat() + "Z",
        "conclusion": r.overall_impression,
        "result": [{"display": o["valueCodeableConcept"]["text"],
                    "type": "Observation"} for o in observations],
        "contained": observations,
        "extension": [],
    }

    if r.bclc_stage:
        fhir_report["extension"].append({
            "url": "https://example.org/fhir/StructureDefinition/bclc-stage",
            "valueString": r.bclc_stage,
        })
    if r.differential_diagnosis:
        fhir_report["extension"].append({
            "url": "https://example.org/fhir/StructureDefinition/differential-diagnosis",
            "valueString": "; ".join(r.differential_diagnosis),
        })
    if r.recommendations:
        fhir_report["extension"].append({
            "url": "https://example.org/fhir/StructureDefinition/recommendations",
            "valueString": "; ".join(r.recommendations),
        })
    if job.sign_off:
        fhir_report["extension"].append({
            "url": "https://example.org/fhir/StructureDefinition/radiologist-signoff",
            "extension": [
                {"url": "radiologist", "valueString": job.sign_off.radiologist_name},
                {"url": "decision", "valueString": job.sign_off.decision},
                {"url": "signedAt", "valueDateTime": job.sign_off.signed_at.isoformat() + "Z"},
            ],
        })

    return JSONResponse(
        content=fhir_report,
        headers={"Content-Disposition": f'attachment; filename="fhir_report_{job_id[:8]}.json"'},
    )


@router.websocket("/ws/{job_id}")
async def progress_ws(websocket: WebSocket, job_id: str):
    await websocket.accept()
    try:
        while True:
            job = _jobs.get(job_id)
            if job:
                await websocket.send_json({
                    "status": job.status,
                    "progress": job.progress,
                    "current_step": job.current_step,
                    "error": job.error,
                })
                if job.status in (AnalysisStatus.COMPLETE, AnalysisStatus.FAILED):
                    break
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        pass
    finally:
        await websocket.close()
