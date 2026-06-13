from __future__ import annotations

import asyncio
import base64
import json
import shutil
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from loguru import logger

from api.deps import assert_modify, assert_view, can_view, get_current_user
from config import settings
from core import store
from core.audit_log import log_analysis_complete, log_analysis_start, log_signoff
from core.database import User
from core.dicom_processor import convert_to_nifti, extract_study_info, load_series_map
from core.image_preprocess import preprocess_dermoscopy, preprocess_mammography, compute_mammographic_density
from core.llm_client import llm_client
from core.modules import registry
from core import model_catalog, feature_catalog
from core import cnn_features, knn_classifier
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


def _run_cnn_backbones(job: AnalysisJob, image_path: Path, proc_dir: Path, feat_set: set[str]) -> str:
    """Run any selected CNN backbones on an image; return a combined summary string.

    Each backbone writes an activation-heatmap overlay to proc_dir. Failures are
    logged and skipped — they never block the diagnosis.
    """
    tags = feature_catalog.cnn_backbones_in(feat_set)
    if not tags:
        return ""
    summaries: list[str] = []
    for tag in tags:
        _step(job, AnalysisStatus.EXTRACTING, 45, f"Extracting {tag.replace('cnn_', '').upper()} features …")
        try:
            heat = proc_dir / f"{tag}_heatmap.png"
            cf = cnn_features.extract_cnn_features(tag, image_path, heat, device=settings.device)
            if cf is not None:
                summaries.append(cf.summary())
        except Exception as exc:
            logger.warning(f"CNN backbone {tag} failed: {exc}")
    return "\n\n".join(summaries)


def _run_knn(job: AnalysisJob, cancer_type: str, image_path: Path, feat_set: set[str]) -> str:
    """Run the KNN classifier if selected; return a summary (or an unavailable note)."""
    if "knn_classifier" not in feat_set:
        return ""
    backbone = feature_catalog.knn_backbone_for(feat_set)
    _step(job, AnalysisStatus.EXTRACTING, 50, "Classifying with KNN …")
    try:
        res = knn_classifier.classify(cancer_type, image_path, backbone=backbone, device=settings.device)
    except Exception as exc:
        logger.warning(f"KNN classification failed: {exc}")
        return ""
    if res is not None:
        return res.summary()
    st = knn_classifier.status(cancer_type)
    return (
        "KNN classifier requested but no usable labelled reference set was found "
        f"(have {st['n_reference']} image(s) across {len(st['classes'])} class(es) at "
        f"{st['reference_dir']}). Add labelled images under "
        f"data/reference/{cancer_type}/<label>/ (≥2 classes) to enable KNN predictions."
    )


async def _pipeline(
    job: AnalysisJob,
    study_dir: Path,
    patient_info: Optional[dict],
) -> None:
    study_id = job.study_id
    proc_dir = settings.processed_dir / study_id
    proc_dir.mkdir(parents=True, exist_ok=True)
    # Clear stale CNN heatmaps so /overlays reflects only the current run.
    for old in proc_dir.glob("*_heatmap.png"):
        old.unlink(missing_ok=True)

    meta_path = study_dir / "_meta.json"
    meta = json.loads(meta_path.read_text()) if meta_path.exists() else {"type": "dicom"}
    upload_type = meta.get("type", "dicom")
    cancer_type = meta.get("cancer_type", "liver")
    module = registry.get(cancer_type)
    model_tag = job.model or model_catalog.default_for(cancer_type)
    feat_set = set(job.features) if job.features else feature_catalog.resolve(cancer_type, None)

    log_analysis_start(job.job_id, study_id, model_tag)
    t0 = time.monotonic()

    try:
        if upload_type == "image":
            await _run_image_pipeline(job, study_dir, meta, proc_dir, patient_info, module, model_tag, feat_set)
        else:
            await _run_volumetric_pipeline(job, study_dir, meta, proc_dir, upload_type, patient_info, module, model_tag, feat_set)
        log_analysis_complete(job.job_id, study_id, model_tag, time.monotonic() - t0, "complete")

    except Exception as exc:
        logger.exception(f"Pipeline error: {exc}")
        job.status = AnalysisStatus.FAILED
        job.progress = 0
        job.current_step = "Failed"
        job.error = str(exc)
        store.save_job(job)
        log_analysis_complete(job.job_id, study_id, model_tag, time.monotonic() - t0, "failed")


async def _run_image_pipeline(
    job: AnalysisJob,
    study_dir: Path,
    meta: dict,
    proc_dir: Path,
    patient_info: Optional[dict],
    module,
    model_tag: str,
    feat_set: set[str],
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
    # raw_b64 keeps the originals; slices_b64 may get its first frame swapped for
    # the enhanced image so the split view shows enhanced (top) vs original (bottom).
    raw_b64 = list(slices_b64)
    store.save_slices(job.job_id, slices_b64, raw_b64)

    modality = meta.get("modality", "CT")
    seg = SegmentationResult()
    montage = image_files[0]
    radiomics_summary = ""

    # Skin: dermoscopy enhancement (colour constancy → hair removal → CLAHE)
    # plus quantitative ABCD features — each step user-selectable.
    if module.cancer_type == "skin" and (
        feat_set & {"color_constancy", "hair_removal", "clahe", "dermoscopy_abcd"}
    ):
        _step(job, AnalysisStatus.PROCESSING, 35, "Enhancing dermoscopy image …")
        enhanced_path = proc_dir / "skin_enhanced.png"
        try:
            feats = preprocess_dermoscopy(
                montage, enhanced_path,
                color_constancy="color_constancy" in feat_set,
                hair_removal="hair_removal" in feat_set,
                clahe="clahe" in feat_set,
                compute_abcd="dermoscopy_abcd" in feat_set,
            )
            if enhanced_path.exists():
                montage = enhanced_path
                slices_b64[0] = base64.b64encode(enhanced_path.read_bytes()).decode()
                store.save_slices(job.job_id, slices_b64, raw_b64)
            if feats is not None:
                radiomics_summary = feats.summary()
        except Exception as exc:  # never let preprocessing block diagnosis
            logger.warning(f"Dermoscopy preprocessing failed, using raw image: {exc}")

    # Breast: CLAHE enhancement + mammographic density (computed on the original).
    elif module.cancer_type == "breast" and (feat_set & {"clahe", "breast_density"}):
        if "clahe" in feat_set:
            _step(job, AnalysisStatus.PROCESSING, 35, "Enhancing mammography image (CLAHE) …")
            enhanced_path = proc_dir / "breast_enhanced.png"
            try:
                if preprocess_mammography(montage, enhanced_path) and enhanced_path.exists():
                    montage = enhanced_path
                    slices_b64[0] = base64.b64encode(enhanced_path.read_bytes()).decode()
                    store.save_slices(job.job_id, slices_b64, raw_b64)
            except Exception as exc:  # never let preprocessing block diagnosis
                logger.warning(f"Mammography preprocessing failed, using raw image: {exc}")
        # Density uses the ORIGINAL image (image_files[0]), unaffected by CLAHE above.
        if "breast_density" in feat_set:
            _step(job, AnalysisStatus.EXTRACTING, 45, "Estimating mammographic density …")
            try:
                mf = compute_mammographic_density(image_files[0])
                if mf is not None:
                    radiomics_summary = mf.summary()
            except Exception as exc:
                logger.warning(f"Mammographic density failed: {exc}")

    # CNN backbone deep features (VGG16/19, ResNet50) — run on the (enhanced) image.
    cnn_summary = _run_cnn_backbones(job, montage, proc_dir, feat_set)
    if cnn_summary:
        radiomics_summary = (radiomics_summary + "\n\n" + cnn_summary).strip()

    # KNN classifier over CNN embeddings (needs a labelled reference set).
    knn_summary = _run_knn(job, module.cancer_type, montage, feat_set)
    if knn_summary:
        radiomics_summary = (radiomics_summary + "\n\n" + knn_summary).strip()

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
        radiomics_summary=radiomics_summary,
        patient_info=patient_info,
        module=module,
        model=model_tag,
    )
    t["llm_s"] = round(time.monotonic() - t0, 2)
    report.study_id = study_id
    report.cancer_type = module.cancer_type
    report.model = model_tag
    if radiomics_summary:
        report.radiomics_summary = radiomics_summary

    job.status = AnalysisStatus.COMPLETE
    job.progress = 100
    job.current_step = "Analysis complete"
    job.completed_at = datetime.now(timezone.utc)
    job.report = report
    job.timings = t
    store.save_job(job)
    logger.info(f"Image pipeline complete for study {study_id} (model={model_tag})")


async def _run_volumetric_pipeline(
    job: AnalysisJob,
    study_dir: Path,
    meta: dict,
    proc_dir: Path,
    upload_type: str,
    patient_info: Optional[dict],
    module,
    model_tag: str,
    feat_set: set[str],
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

    rad_summary = ""
    if "radiomics" in feat_set:
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

    # CNN backbone deep features (VGG16/19, ResNet50) — run on the montage image.
    cnn_summary = _run_cnn_backbones(job, montage, proc_dir, feat_set)
    if cnn_summary:
        rad_summary = (rad_summary + "\n\n" + cnn_summary).strip()

    # KNN classifier over CNN embeddings (needs a labelled reference set).
    knn_summary = _run_knn(job, module.cancer_type, montage, feat_set)
    if knn_summary:
        rad_summary = (rad_summary + "\n\n" + knn_summary).strip()

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
        model=model_tag,
    )
    t["llm_s"] = round(time.monotonic() - t0, 2)
    report.study_id = study_id
    report.cancer_type = module.cancer_type
    report.model = model_tag
    if rad_summary:
        report.radiomics_summary = rad_summary

    job.status = AnalysisStatus.COMPLETE
    job.progress = 100
    job.current_step = "Analysis complete"
    job.completed_at = datetime.now(timezone.utc)
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

@router.get("/models")
async def list_models(current_user: User = Depends(get_current_user)):
    """Per-cancer LLM catalog (default + selectable options) for the model picker."""
    return model_catalog.catalog()


@router.get("/features")
async def list_features(current_user: User = Depends(get_current_user)):
    """Per-cancer feature/extractor catalog (defaults + options) for the feature picker."""
    return feature_catalog.catalog()


@router.get("/knn/status/{cancer_type}")
async def knn_status(cancer_type: str, current_user: User = Depends(get_current_user)):
    """Labelled-reference-set status for the KNN classifier."""
    return knn_classifier.status(cancer_type)


@router.post("/knn/build/{cancer_type}")
async def knn_build(
    cancer_type: str,
    backbone: str = "cnn_resnet50",
    current_user: User = Depends(get_current_user),
):
    """(Re)build the KNN reference index for a cancer from its labelled images."""
    if not cnn_features.is_backbone(backbone):
        raise HTTPException(400, f"Unknown backbone: {backbone}")
    n = knn_classifier.build_index(cancer_type, backbone, device=settings.device)
    return {"cancer": cancer_type, "backbone": backbone, "indexed": n,
            "status": knn_classifier.status(cancer_type)}


@router.post("/start/{study_id}", response_model=AnalysisJob)
async def start_analysis(
    study_id: str,
    background_tasks: BackgroundTasks,
    patient_context: Optional[PatientContext] = None,
    model: Optional[str] = None,
    features: Optional[List[str]] = Query(None),
    current_user: User = Depends(get_current_user),
):
    study_dir = settings.uploads_dir / study_id
    if not study_dir.exists():
        raise HTTPException(404, "Study not found — upload files first")

    meta_path = study_dir / "_meta.json"
    meta = json.loads(meta_path.read_text()) if meta_path.exists() else {}
    cancer_type = meta.get("cancer_type", "liver")
    # For a comparison feature, silently running a different model than the one
    # requested would be misleading — reject unknown tags outright.
    if model and not model_catalog.is_allowed(model):
        raise HTTPException(400, f"Unknown model: {model}")
    model_tag = model_catalog.resolve(cancer_type, model)
    # Resolve selected features against what's applicable for this cancer
    # (unknown/inapplicable keys are dropped; None → cancer defaults).
    feature_set = sorted(feature_catalog.resolve(cancer_type, features))

    job = AnalysisJob(
        job_id=str(uuid.uuid4()),
        study_id=study_id,
        cancer_type=cancer_type,
        model=model_tag,
        features=feature_set,
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


@router.get("/overlays/{job_id}")
async def get_overlays(job_id: str, current_user: User = Depends(get_current_user)):
    """CNN activation-heatmap overlays (Grad-CAM-style) saved during analysis."""
    job = _get_owned_job(job_id, current_user)
    proc_dir = settings.processed_dir / job.study_id
    overlays = []
    if proc_dir.exists():
        for f in sorted(proc_dir.glob("*_heatmap.png")):
            tag = f.stem.replace("_heatmap", "")
            label = f"{tag.replace('cnn_', '').upper()} attention"
            overlays.append({
                "key": tag,
                "label": label,
                "image": base64.b64encode(f.read_bytes()).decode(),
            })
    return {"overlays": overlays}


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
