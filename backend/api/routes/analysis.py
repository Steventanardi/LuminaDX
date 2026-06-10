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

from api.deps import assert_modify, assert_view, can_view, get_current_user
from config import settings
from core import store
from core.audit_log import log_analysis_complete, log_analysis_start, log_signoff
from core.database import User
from core.dicom_processor import convert_to_nifti, extract_study_info, load_series_map
from core.llm_client import llm_client
from core.modules import registry
from core.rag_engine import rag_engine
from core.radiomics_extractor import extract, summarize
from core.segmentation import SegmentationResult, run_segmentation
from core.slice_exporter import create_montage, export_overlay_slices_b64
from models.schemas import AnalysisJob, AnalysisStatus, DiagnosticReport, PatientContext, SeriesInfo, SignOff, SignOffRequest

router = APIRouter()

_jobs: Dict[str, AnalysisJob] = store.load_all_jobs()

_SEG_LOCK = asyncio.Semaphore(1)


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
    cancer_type = meta.get("cancer_type", "liver")
    module = registry.get(cancer_type)

    log_analysis_start(job.job_id, study_id, settings.llm_model)
    t0 = time.monotonic()

    try:
        if upload_type == "image":
            await _run_image_pipeline(job, study_dir, meta, proc_dir, patient_info, module)
        else:
            await _run_volumetric_pipeline(job, study_dir, meta, proc_dir, upload_type, patient_info, module)
        log_analysis_complete(job.job_id, study_id, settings.llm_model, time.monotonic() - t0, "complete")

    except Exception as exc:
        logger.exception(f"Pipeline error: {exc}")
        job.status = AnalysisStatus.FAILED
        job.progress = 0
        job.current_step = "Failed"
        job.error = str(exc)
        store.save_job(job)
        log_analysis_complete(job.job_id, study_id, settings.llm_model, time.monotonic() - t0, "failed")


async def _run_image_pipeline(
    job: AnalysisJob,
    study_dir: Path,
    meta: dict,
    proc_dir: Path,
    patient_info: Optional[dict],
    module,
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

    slices_b64: list[str] = []
    for img_path in image_files[:24]:
        slices_b64.append(base64.b64encode(img_path.read_bytes()).decode())
    store.save_slices(job.job_id, slices_b64, slices_b64)

    modality = meta.get("modality", "CT")
    seg = SegmentationResult()
    montage = image_files[0]

    _step(job, AnalysisStatus.ANALYZING, 60, "Retrieving guidelines (RAG) …")
    t0 = time.monotonic()
    rag_ctx = await rag_engine.retrieve(module.rag_query(seg, modality), namespace=module.rag_namespace())
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
        module=module,
    )
    t["llm_s"] = round(time.monotonic() - t0, 2)
    report.study_id = study_id
    report.cancer_type = module.cancer_type

    job.status = AnalysisStatus.COMPLETE
    job.progress = 100
    job.current_step = "Analysis complete"
    job.completed_at = datetime.utcnow()
    job.report = report
    job.timings = t
    store.save_job(job)
    logger.info(f"Image pipeline complete for study {study_id}")


async def _run_volumetric_pipeline(
    job: AnalysisJob,
    study_dir: Path,
    meta: dict,
    proc_dir: Path,
    upload_type: str,
    patient_info: Optional[dict],
    module,
) -> None:
    study_id = job.study_id
    t: dict[str, float] = {}

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

    seg_spec = module.segmentation_spec()
    _step(job, AnalysisStatus.SEGMENTING, 22, f"Segmenting {module.cancer_type} structures (GPU) …")
    seg_dir = proc_dir / "seg"
    t0 = time.monotonic()
    async with _SEG_LOCK:
        seg: SegmentationResult = await asyncio.get_event_loop().run_in_executor(
            None, run_segmentation, primary, seg_dir, settings.device, modality, seg_spec,
        )
    t["segmentation_s"] = round(time.monotonic() - t0, 2)

    _step(job, AnalysisStatus.PROCESSING, 52, "Rendering overlay slices …")
    t0 = time.monotonic()
    slices_b64 = export_overlay_slices_b64(primary, seg, modality, n_slices=24, apply_overlay=True)
    raw_b64 = export_overlay_slices_b64(primary, seg, modality, n_slices=24, apply_overlay=False)
    store.save_slices(job.job_id, slices_b64, raw_b64)
    t["overlay_s"] = round(time.monotonic() - t0, 2)

    _step(job, AnalysisStatus.PROCESSING, 60, "Building diagnostic montage …")
    montage = create_montage(nifti_paths, seg, proc_dir, modality, phase_labels)

    _step(job, AnalysisStatus.EXTRACTING, 68, "Extracting radiomic features …")
    tumor_mask_path: Optional[Path] = None
    if seg_spec:
        for candidate in seg_spec.tumor_mask_names:
            p = seg_dir / "tumor" / candidate
            if p.exists():
                tumor_mask_path = p
                break
    t0 = time.monotonic()
    features = extract(primary, tumor_mask_path, modality)
    t["radiomics_s"] = round(time.monotonic() - t0, 2)
    rad_summary = summarize(features)

    _step(job, AnalysisStatus.ANALYZING, 76, "Retrieving guidelines (RAG) …")
    t0 = time.monotonic()
    rag_ctx = await rag_engine.retrieve(module.rag_query(seg, modality), namespace=module.rag_namespace())
    t["rag_s"] = round(time.monotonic() - t0, 2)

    _step(job, AnalysisStatus.ANALYZING, 84, "Running LLM analysis …")
    t0 = time.monotonic()
    report: DiagnosticReport = await llm_client.analyze(
        montage_path=montage,
        seg=seg,
        modality=modality,
        rag_context=rag_ctx,
        radiomics_summary=rad_summary,
        patient_info=patient_info,
        module=module,
    )
    t["llm_s"] = round(time.monotonic() - t0, 2)
    report.study_id = study_id
    report.cancer_type = module.cancer_type

    job.status = AnalysisStatus.COMPLETE
    job.progress = 100
    job.current_step = "Analysis complete"
    job.completed_at = datetime.utcnow()
    job.report = report
    job.timings = t
    store.save_job(job)
    logger.info(
        f"Pipeline complete for study {study_id} ({module.cancer_type}) — "
        + ", ".join(f"{k}={v}s" for k, v in t.items())
    )


# ── Endpoint helpers ───────────────────────────────────────────────────────────

def _get_owned_job(job_id: str, user: User) -> AnalysisJob:
    """Return job if user may view it, else 404."""
    job = _jobs.get(job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    assert_view(job.owner_user_id, job.owner_department, user)
    return job


# ── Routes ─────────────────────────────────────────────────────────────────────

@router.post("/start/{study_id}", response_model=AnalysisJob)
async def start_analysis(
    study_id: str,
    background_tasks: BackgroundTasks,
    patient_context: Optional[PatientContext] = None,
    current_user: User = Depends(get_current_user),
):
    study_dir = settings.uploads_dir / study_id
    if not study_dir.exists():
        raise HTTPException(404, "Study not found — upload files first")

    meta_path = study_dir / "_meta.json"
    meta = json.loads(meta_path.read_text()) if meta_path.exists() else {}
    cancer_type = meta.get("cancer_type", "liver")

    job = AnalysisJob(
        job_id=str(uuid.uuid4()),
        study_id=study_id,
        cancer_type=cancer_type,
        owner_user_id=current_user.id,
        owner_department=current_user.department,
    )
    _jobs[job.job_id] = job
    store.save_job(job)

    pt_dict = patient_context.model_dump() if patient_context else None
    background_tasks.add_task(_pipeline, job, study_dir, pt_dict)
    return job


@router.get("/status/{job_id}", response_model=AnalysisJob)
async def job_status(job_id: str, current_user: User = Depends(get_current_user)):
    return _get_owned_job(job_id, current_user)


@router.get("/history")
async def list_jobs(current_user: User = Depends(get_current_user)):
    user_jobs = [j for j in _jobs.values() if can_view(j.owner_user_id, j.owner_department, current_user)]
    return sorted([j.model_dump() for j in user_jobs], key=lambda j: j["created_at"], reverse=True)


@router.get("/report/{job_id}", response_model=DiagnosticReport)
async def get_report(job_id: str, current_user: User = Depends(get_current_user)):
    job = _get_owned_job(job_id, current_user)
    if job.status != AnalysisStatus.COMPLETE or not job.report:
        raise HTTPException(202, "Report not ready yet")
    return job.report


@router.get("/slices/{job_id}")
async def get_slices(job_id: str, current_user: User = Depends(get_current_user)):
    _get_owned_job(job_id, current_user)
    slices, raw = store.load_slices(job_id)
    return {"slices": slices, "raw_slices": raw, "count": len(slices)}


@router.post("/signoff/{job_id}", response_model=AnalysisJob)
async def sign_off(job_id: str, req: SignOffRequest, current_user: User = Depends(get_current_user)):
    job = _get_owned_job(job_id, current_user)
    assert_modify(job.owner_user_id, current_user)
    if job.status != AnalysisStatus.COMPLETE:
        raise HTTPException(400, "Cannot sign off an incomplete analysis")
    job.sign_off = SignOff(
        radiologist_name=req.radiologist_name or current_user.full_name,
        decision=req.decision,
        comments=req.comments,
    )
    store.save_job(job)
    logger.info(f"Sign-off [{job_id[:8]}] {req.decision} by {current_user.email}")
    log_signoff(job_id, job.study_id, req.radiologist_name or current_user.full_name, req.decision)
    return job


@router.get("/benchmark/{job_id}")
async def get_benchmark(job_id: str, current_user: User = Depends(get_current_user)):
    job = _get_owned_job(job_id, current_user)
    total = (
        (job.completed_at - job.created_at).total_seconds()
        if job.completed_at else None
    )
    return {
        "job_id": job_id, "status": job.status,
        "total_s": round(total, 2) if total is not None else None,
        "steps": job.timings,
        "created_at": job.created_at.isoformat(),
        "completed_at": job.completed_at.isoformat() if job.completed_at else None,
    }


@router.get("/fhir/{job_id}")
async def fhir_export(job_id: str, current_user: User = Depends(get_current_user)):
    job = _get_owned_job(job_id, current_user)
    if job.status != AnalysisStatus.COMPLETE or not job.report:
        raise HTTPException(400, "Analysis not complete")

    r = job.report
    status = "final" if job.sign_off else "preliminary"

    observations: list[dict] = []
    for lesion in r.lesions:
        obs: dict = {
            "resourceType": "Observation",
            "status": status,
            "code": {"coding": [{"system": "http://loinc.org", "code": "85319-2",
                                  "display": f"{r.cancer_type.title()} lesion score"}]},
            "valueCodeableConcept": {"text": lesion.score or lesion.lirads_category},
            "component": [],
        }
        if lesion.location_segment:
            obs["component"].append({"code": {"text": "Location"}, "valueString": lesion.location_segment})
        if lesion.size_mm is not None:
            obs["component"].append({
                "code": {"coding": [{"system": "http://loinc.org", "code": "33756-8", "display": "Lesion size"}]},
                "valueQuantity": {"value": lesion.size_mm, "unit": "mm",
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
        "code": {"text": f"{r.modality} {r.cancer_type.title()} AI Assessment"},
        "subject": {"reference": f"Patient/{r.study_id[:8]}", "display": "De-identified patient"},
        "issued": r.generated_at.isoformat() + "Z",
        "conclusion": r.overall_impression,
        "result": [{"display": o["valueCodeableConcept"]["text"], "type": "Observation"} for o in observations],
        "contained": observations,
        "extension": [],
    }

    staging = r.staging or r.bclc_stage
    if staging:
        fhir_report["extension"].append({"url": "staging", "valueString": staging})
    if r.differential_diagnosis:
        fhir_report["extension"].append({"url": "differential-diagnosis", "valueString": "; ".join(r.differential_diagnosis)})
    if r.recommendations:
        fhir_report["extension"].append({"url": "recommendations", "valueString": "; ".join(r.recommendations)})
    if job.sign_off:
        fhir_report["extension"].append({
            "url": "radiologist-signoff",
            "extension": [
                {"url": "radiologist", "valueString": job.sign_off.radiologist_name},
                {"url": "decision", "valueString": job.sign_off.decision},
                {"url": "signedAt", "valueDateTime": job.sign_off.signed_at.isoformat() + "Z"},
            ],
        })

    return JSONResponse(
        content=fhir_report,
        headers={"Content-Disposition": f'attachment; filename="fhir_{job_id[:8]}.json"'},
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
