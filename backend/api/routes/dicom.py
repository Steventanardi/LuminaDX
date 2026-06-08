from __future__ import annotations

import base64
import io
import json
import shutil
import uuid
from pathlib import Path
from typing import List

import nibabel as nib
import numpy as np
import pydicom
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from loguru import logger
from PIL import Image

from api.deps import verify_api_key
from config import settings
from core.audit_log import log_upload
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
async def upload_files(files: List[UploadFile] = File(...), _: None = Depends(verify_api_key)):
    if not files:
        raise HTTPException(400, "No files provided")

    upload_type = _detect_type([f.filename or "" for f in files])
    study_id = str(uuid.uuid4())
    study_dir = settings.uploads_dir / study_id
    study_dir.mkdir(parents=True, exist_ok=True)

    if upload_type == "nifti":
        return await _handle_nifti(files, study_id, study_dir)
    if upload_type == "image":
        return await _handle_images(files, study_id, study_dir)
    return await _handle_dicom(files, study_id, study_dir)


async def _handle_nifti(
    files: List[UploadFile], study_id: str, study_dir: Path
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
    meta = {"type": "nifti", "modality": modality, "nifti_files": saved}
    (study_dir / "_meta.json").write_text(json.dumps(meta))

    study = DicomStudy(id=study_id, modality=Modality(modality), num_files=len(saved), series=series)
    _studies[study_id] = study
    logger.info(f"NIfTI study {study_id}: {len(saved)} file(s)")
    log_upload(study_id, "nifti", len(saved), modality)
    return UploadResponse(
        study_id=study_id,
        num_files=len(saved),
        modality=modality,
        series=series,
        message=f"Uploaded {len(saved)} NIfTI file(s) — full segmentation pipeline",
    )


async def _handle_images(
    files: List[UploadFile], study_id: str, study_dir: Path
) -> UploadResponse:
    saved: list[str] = []
    for i, f in enumerate(files):
        name = Path(f.filename or f"image_{i:04d}.jpg").name
        dest = study_dir / name
        dest.write_bytes(await f.read())
        saved.append(name)

    series = [SeriesInfo(series_uid="img-0", description="Image Upload", phase=None, num_slices=len(saved))]
    meta = {"type": "image", "modality": "CT", "image_files": saved}
    (study_dir / "_meta.json").write_text(json.dumps(meta))

    study = DicomStudy(id=study_id, modality=None, num_files=len(saved), series=series)
    _studies[study_id] = study
    logger.info(f"Image study {study_id}: {len(saved)} image(s)")
    log_upload(study_id, "image", len(saved), None)
    return UploadResponse(
        study_id=study_id,
        num_files=len(saved),
        modality=None,
        series=series,
        message=f"Uploaded {len(saved)} image(s) — LLM-only analysis (~30 s)",
    )


async def _handle_dicom(
    files: List[UploadFile], study_id: str, study_dir: Path
) -> UploadResponse:
    saved = 0
    for f in files:
        name = Path(f.filename or f"slice_{saved:04d}.dcm").name
        dest = study_dir / name
        content = await f.read()
        dest.write_bytes(content)
        try:
            ds = pydicom.dcmread(str(dest), force=True)
            ds = anonymize_dataset(ds)
            ds.save_as(str(dest))
        except Exception as exc:
            logger.debug(f"Anonymise skipped for {name}: {exc}")
        saved += 1

    series_map = load_series_map(study_dir)
    info = extract_study_info(series_map)
    modality_enum = info["modality"]
    modality = modality_enum.value if modality_enum else None
    series: List[SeriesInfo] = info["series"]

    meta = {"type": "dicom", "modality": modality}
    (study_dir / "_meta.json").write_text(json.dumps(meta))

    study = DicomStudy(id=study_id, modality=modality_enum, num_files=saved, series=series)
    _studies[study_id] = study
    logger.info(f"DICOM study {study_id}: {saved} files, modality={modality}, {len(series)} series")
    log_upload(study_id, "dicom", saved, modality)
    return UploadResponse(
        study_id=study_id,
        num_files=saved,
        modality=modality,
        series=series,
        message=f"Uploaded {saved} DICOM files ({len(series)} series detected)",
    )


@router.get("/studies", response_model=List[DicomStudy])
async def list_studies():
    return list(_studies.values())


@router.get("/studies/{study_id}", response_model=DicomStudy)
async def get_study(study_id: str):
    if study_id not in _studies:
        raise HTTPException(404, "Study not found")
    return _studies[study_id]


@router.delete("/studies/{study_id}")
async def delete_study(study_id: str):
    for d in (settings.uploads_dir / study_id, settings.processed_dir / study_id):
        if d.exists():
            shutil.rmtree(d)
    _studies.pop(study_id, None)
    return {"message": f"Study {study_id} deleted"}


@router.get("/files/{study_id}")
async def list_files(study_id: str):
    d = settings.uploads_dir / study_id
    if not d.exists():
        raise HTTPException(404, "Study not found")
    files = sorted(f.name for f in d.iterdir() if f.is_file())
    return {"study_id": study_id, "files": files, "count": len(files)}


@router.get("/serve/{study_id}/{filename}")
async def serve_file(study_id: str, filename: str):
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


# Regular def → FastAPI runs in threadpool (no event-loop blocking)
@router.get("/preview/{study_id}")
def preview_slices(study_id: str, n: int = 24):
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
