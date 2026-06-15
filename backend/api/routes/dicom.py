from __future__ import annotations

import base64
import io
import json
import re
import shutil
import uuid
from pathlib import Path
from typing import List, Optional

import nibabel as nib
import numpy as np
import pydicom
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel
from fastapi.responses import FileResponse
from loguru import logger
from PIL import Image

from api.deps import assert_modify, assert_view, can_view, get_current_user
from config import settings
from core.audit_log import log_upload
from core.database import User
from core.dicom_processor import anonymize_dataset, extract_study_info, load_series_map
from models.schemas import DicomStudy, Modality, SeriesInfo, UploadResponse

router = APIRouter()

_studies: dict[str, DicomStudy] = {}

_IMAGE_EXTS = {".jpg", ".jpeg", ".png"}

def _detect_type(filenames: list[str]) -> str:
    """Return 'nifti', 'image', or 'dicom' based on file extensions."""
    lower = [n.lower() for n in filenames if n]
    if any(n.endswith(".nii.gz") or n.endswith(".nii") for n in lower):
        return "nifti"
    if any(Path(n).suffix in _IMAGE_EXTS for n in lower):
        return "image"
    return "dicom"


@router.post("/upload", response_model=UploadResponse)
async def upload_files(
    files: List[UploadFile] = File(...),
    cancer_type: str = "liver",
    current_user: User = Depends(get_current_user),
):
    if not files:
        raise HTTPException(400, "No files provided")

    upload_type = _detect_type([f.filename or "" for f in files])
    study_id = str(uuid.uuid4())
    study_dir = settings.uploads_dir / study_id
    study_dir.mkdir(parents=True, exist_ok=True)

    dept = current_user.department
    if upload_type == "nifti":
        return await _handle_nifti(files, study_id, study_dir, cancer_type, current_user.id, dept)
    if upload_type == "image":
        return await _handle_images(files, study_id, study_dir, cancer_type, current_user.id, dept)
    return await _handle_dicom(files, study_id, study_dir, cancer_type, current_user.id, dept)


async def _handle_nifti(
    files: List[UploadFile], study_id: str, study_dir: Path,
    cancer_type: str = "liver", owner_user_id: str = "", _dept: Optional[str] = None,
) -> UploadResponse:
    saved: list[str] = []
    for f in files:
        name = Path(f.filename or "volume.nii.gz").name
        dest = study_dir / name
        dest.write_bytes(await f.read())
        saved.append(name)
        logger.info(f"Saved NIfTI: {name}")

    modality = "CT"
    for name in saved:
        nl = name.lower()
        if "mri" in nl or "mr_" in nl or "t1" in nl or "t2" in nl:
            modality = "MRI"
            break

    series = [SeriesInfo(series_uid="nifti-0", description="NIfTI Volume", phase="arterial", num_slices=1)]

    meta = {"type": "nifti", "modality": modality, "nifti_files": saved, "cancer_type": cancer_type}
    (study_dir / "_meta.json").write_text(json.dumps(meta))

    study = DicomStudy(id=study_id, modality=Modality(modality), num_files=len(saved), series=series,
                       cancer_type=cancer_type, owner_user_id=owner_user_id, owner_department=_dept)
    _studies[study_id] = study
    logger.info(f"NIfTI study {study_id}: {len(saved)} file(s), cancer_type={cancer_type}")
    log_upload(study_id, "nifti", len(saved), modality)
    return UploadResponse(
        study_id=study_id, num_files=len(saved), modality=modality, series=series,
        message=f"Uploaded {len(saved)} NIfTI file(s) — full segmentation pipeline",
    )


async def _handle_images(
    files: List[UploadFile], study_id: str, study_dir: Path,
    cancer_type: str = "liver", owner_user_id: str = "", _dept: Optional[str] = None,
) -> UploadResponse:
    saved: list[str] = []
    for i, f in enumerate(files):
        name = Path(f.filename or f"image_{i:04d}.jpg").name
        dest = study_dir / name
        dest.write_bytes(await f.read())
        saved.append(name)

    # Assign a sensible default modality per cancer type for image uploads
    _modality_defaults = {"skin": "Dermoscopy", "breast": "Mammography", "lung": "CT", "colorectal": "CT"}
    modality = _modality_defaults.get(cancer_type, "Photo")

    series = [SeriesInfo(series_uid="img-0", description="Image Upload", phase=None, num_slices=len(saved))]
    meta = {"type": "image", "modality": modality, "image_files": saved, "cancer_type": cancer_type}
    (study_dir / "_meta.json").write_text(json.dumps(meta))

    study = DicomStudy(id=study_id, modality=None, num_files=len(saved), series=series,
                       cancer_type=cancer_type, owner_user_id=owner_user_id, owner_department=_dept)
    _studies[study_id] = study
    logger.info(f"Image study {study_id}: {len(saved)} image(s), cancer_type={cancer_type}")
    log_upload(study_id, "image", len(saved), modality)
    return UploadResponse(
        study_id=study_id, num_files=len(saved), modality=modality, series=series,
        message=f"Uploaded {len(saved)} image(s) — LLM-only analysis (~30 s)",
    )


async def _handle_dicom(
    files: List[UploadFile], study_id: str, study_dir: Path,
    cancer_type: str = "liver", owner_user_id: str = "", _dept: Optional[str] = None,
) -> UploadResponse:
    saved = 0
    for f in files:
        name = Path(f.filename or f"slice_{saved:04d}.dcm").name
        dest = study_dir / name
        content = await f.read()
        dest.write_bytes(content)

        # Parse first. A file that isn't valid DICOM is simply discarded (it can
        # never reach the pipeline), so it is not a PHI risk.
        try:
            ds = pydicom.dcmread(str(dest), force=True)
        except Exception as exc:
            logger.debug(f"Not a DICOM file, discarding {name}: {exc}")
            dest.unlink(missing_ok=True)
            continue

        # Fail closed: if a real DICOM cannot be de-identified, delete it and
        # reject the upload rather than silently keeping PHI on disk.
        try:
            ds = anonymize_dataset(ds)
            ds.save_as(str(dest))
        except Exception as exc:
            dest.unlink(missing_ok=True)
            logger.error(f"De-identification failed for {name}: {exc}")
            raise HTTPException(
                422,
                f"De-identification failed for '{name}'; upload rejected to prevent PHI leakage.",
            )
        saved += 1

    if saved == 0:
        raise HTTPException(400, "No valid DICOM files found in upload")

    series_map = load_series_map(study_dir)
    info = extract_study_info(series_map)
    modality_enum = info["modality"]
    modality = modality_enum.value if modality_enum else None
    series: List[SeriesInfo] = info["series"]

    meta = {"type": "dicom", "modality": modality, "cancer_type": cancer_type}
    (study_dir / "_meta.json").write_text(json.dumps(meta))

    study = DicomStudy(id=study_id, modality=modality_enum, num_files=saved, series=series,
                       cancer_type=cancer_type, owner_user_id=owner_user_id, owner_department=_dept)
    _studies[study_id] = study
    logger.info(f"DICOM study {study_id}: {saved} files, modality={modality}, cancer_type={cancer_type}")
    log_upload(study_id, "dicom", saved, modality)
    return UploadResponse(
        study_id=study_id, num_files=saved, modality=modality, series=series,
        message=f"Uploaded {saved} DICOM files ({len(series)} series detected)",
    )


@router.get("/studies", response_model=List[DicomStudy])
async def list_studies(current_user: User = Depends(get_current_user)):
    return [s for s in _studies.values() if can_view(s.owner_user_id, s.owner_department, current_user)]


@router.get("/studies/{study_id}", response_model=DicomStudy)
async def get_study(study_id: str, current_user: User = Depends(get_current_user)):
    s = _studies.get(study_id)
    if not s:
        raise HTTPException(404, "Study not found")
    assert_view(s.owner_user_id, s.owner_department, current_user)
    return s


@router.delete("/studies/{study_id}")
async def delete_study(study_id: str, current_user: User = Depends(get_current_user)):
    s = _studies.get(study_id)
    if not s:
        raise HTTPException(404, "Study not found")
    assert_view(s.owner_user_id, s.owner_department, current_user)
    assert_modify(s.owner_user_id, current_user)
    for d in (settings.uploads_dir / study_id, settings.processed_dir / study_id):
        if d.exists():
            shutil.rmtree(d)
    _studies.pop(study_id, None)
    return {"message": f"Study {study_id} deleted"}


@router.get("/files/{study_id}")
async def list_files(study_id: str, current_user: User = Depends(get_current_user)):
    s = _studies.get(study_id)
    if not s or s.owner_user_id != current_user.id:
        raise HTTPException(404, "Study not found")
    d = settings.uploads_dir / study_id
    files = sorted(f.name for f in d.iterdir() if f.is_file())
    return {"study_id": study_id, "files": files, "count": len(files)}


@router.get("/serve/{study_id}/{filename}")
async def serve_file(study_id: str, filename: str, current_user: User = Depends(get_current_user)):
    s = _studies.get(study_id)
    if not s or s.owner_user_id != current_user.id:
        raise HTTPException(404, "File not found")
    path = settings.uploads_dir / study_id / Path(filename).name
    if not path.exists():
        raise HTTPException(404, "File not found")
    return FileResponse(str(path), media_type="application/dicom")


def _to_jpeg_b64(gray: np.ndarray) -> str:
    img = Image.fromarray(np.rot90(gray).astype(np.uint8), "L").resize((512, 512), Image.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=82)
    return base64.b64encode(buf.getvalue()).decode()


def _auto_window(arr: np.ndarray) -> np.ndarray:
    """Percentile-based windowing — works on any pixel range (raw, HU, MRI)."""
    lo, hi = np.percentile(arr, 1.0), np.percentile(arr, 99.0)
    if hi <= lo:
        hi = lo + 1.0
    return ((np.clip(arr, lo, hi) - lo) / (hi - lo) * 255).astype(np.uint8)


class _UpdateCancerType(BaseModel):
    cancer_type: str


@router.patch("/studies/{study_id}/cancer-type")
async def update_study_cancer_type(
    study_id: str,
    body: _UpdateCancerType,
    current_user: User = Depends(get_current_user),
):
    """Update the cancer type stored in study metadata (allows post-upload correction)."""
    s = _studies.get(study_id)
    if not s:
        raise HTTPException(404, "Study not found")
    assert_modify(s.owner_user_id, current_user)

    study_dir = settings.uploads_dir / study_id
    meta_path = study_dir / "_meta.json"
    meta = json.loads(meta_path.read_text()) if meta_path.exists() else {}
    meta["cancer_type"] = body.cancer_type
    meta_path.write_text(json.dumps(meta))
    s.cancer_type = body.cancer_type
    logger.info(f"Study {study_id[:8]} cancer_type updated to {body.cancer_type} by {current_user.email}")
    return {"study_id": study_id, "cancer_type": body.cancer_type}


@router.get("/preview/{study_id}")
def preview_slices(study_id: str, n: int = 24, current_user: User = Depends(get_current_user)):
    """Return raw (no-overlay) preview slices immediately after upload."""
    study_dir = settings.uploads_dir / study_id
    if not study_dir.exists():
        raise HTTPException(404, "Study not found")

    meta_path = study_dir / "_meta.json"
    meta = json.loads(meta_path.read_text()) if meta_path.exists() else {"type": "dicom"}
    upload_type = meta.get("type", "dicom")
    modality = meta.get("modality", "CT")

    slices: list[str] = []

    if upload_type == "image":
        image_files = sorted(
            f for f in study_dir.iterdir()
            if f.suffix.lower() in _IMAGE_EXTS and f.name != "_meta.json"
        )[:n]
        for f in image_files:
            slices.append(base64.b64encode(f.read_bytes()).decode())

    elif upload_type == "nifti":
        nifti_files = meta.get("nifti_files", [])
        src = study_dir / nifti_files[0] if nifti_files else None
        if not src or not src.exists():
            candidates = sorted(study_dir.glob("*.nii.gz")) + sorted(study_dir.glob("*.nii"))
            src = candidates[0] if candidates else None
        if src and src.exists():
            vol = nib.load(str(src)).get_fdata()
            total = vol.shape[2]
            for z in np.linspace(0, total - 1, num=min(n, total), dtype=int):
                slices.append(_to_jpeg_b64(_auto_window(vol[:, :, int(z)])))

    else:  # DICOM
        dcm_files = sorted(study_dir.glob("*.dcm")) + sorted(study_dir.glob("*.DCM"))
        if not dcm_files:
            dcm_files = sorted(f for f in study_dir.iterdir()
                               if f.suffix.lower() == ".dcm" and f.name != "_meta.json")

        # Sort by InstanceNumber; fall back to filename so scrambled de-id studies stay ordered
        def _sort_key(p: Path):
            try:
                ds = pydicom.dcmread(str(p), stop_before_pixels=True, force=True)
                n = int(getattr(ds, "InstanceNumber", 0) or 0)
                return (n if n > 0 else 10_000_000, p.stem)
            except Exception:
                return (10_000_000, p.stem)

        dcm_files.sort(key=_sort_key)
        step = max(1, len(dcm_files) // n)
        selected = dcm_files[::step][:n]

        for p in selected:
            try:
                ds = pydicom.dcmread(str(p), force=True)
                arr = ds.pixel_array.astype(float)
                slope = float(getattr(ds, "RescaleSlope", 1) or 1)
                intercept = float(getattr(ds, "RescaleIntercept", 0) or 0)
                arr = arr * slope + intercept
                slices.append(_to_jpeg_b64(_auto_window(arr)))
            except Exception as exc:
                logger.warning(f"Preview skip {p.name}: {exc}")

    logger.info(f"Preview for {study_id}: {len(slices)} slices (type={upload_type})")
    return {"slices": slices, "count": len(slices)}
