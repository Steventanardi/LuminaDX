from __future__ import annotations

import gc
import json
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Tuple

import nibabel as nib
import numpy as np
from loguru import logger

# Standalone helper script that runs TotalSegmentator with a proper __main__
# guard so nnU-Net's spawned DataLoader workers don't re-launch uvicorn on Windows
_TOTALSEG_SCRIPT = Path(__file__).parent.parent.parent / "scripts" / "run_totalseg.py"


@dataclass
class LesionInfo:
    lesion_id: str
    size_mm: float
    volume_ml: float
    centroid_voxel: List[int]
    voxel_count: int


@dataclass
class SegmentationResult:
    liver_mask: Optional[np.ndarray] = None
    tumor_mask: Optional[np.ndarray] = None
    liver_volume_ml: float = 0.0
    lesions: List[LesionInfo] = field(default_factory=list)
    affine: Optional[np.ndarray] = None
    voxel_spacing: Tuple[float, float, float] = (1.0, 1.0, 1.0)

    @property
    def has_lesions(self) -> bool:
        return len(self.lesions) > 0


def _free_gpu() -> None:
    try:
        import torch
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
    except ImportError:
        pass
    gc.collect()


def _run_totalseg(args: dict) -> None:
    cmd = [sys.executable, str(_TOTALSEG_SCRIPT), json.dumps(args)]
    logger.info(f"TotalSegmentator subprocess: task={args.get('task','total')} roi={args.get('roi_subset')}")
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.stdout:
        logger.info(f"TotalSegmentator stdout: {proc.stdout[-500:]}")
    if proc.returncode != 0:
        logger.error(f"TotalSegmentator stderr: {proc.stderr[-1000:]}")
        raise RuntimeError(f"TotalSegmentator failed (exit {proc.returncode}): {proc.stderr[-300:]}")


def run_segmentation(
    input_nifti: Path,
    output_dir: Path,
    device: str = "gpu",
) -> SegmentationResult:
    output_dir.mkdir(parents=True, exist_ok=True)
    result = SegmentationResult()

    liver_out = output_dir / "liver"
    tumor_out = output_dir / "tumor"

    try:
        logger.info("Segmenting liver (subprocess)...")
        _run_totalseg({
            "input": str(input_nifti),
            "output": str(liver_out),
            "roi_subset": ["liver"],
            "device": device,
            "fast": True,
        })

        logger.info("Segmenting liver lesions (subprocess)...")
        _run_totalseg({
            "input": str(input_nifti),
            "output": str(tumor_out),
            "task": "liver_lesions",
            "device": device,
        })

    finally:
        _free_gpu()

    # Load liver mask
    liver_path = liver_out / "liver.nii.gz"
    if liver_path.exists():
        img = nib.load(str(liver_path))
        result.liver_mask = img.get_fdata().astype(np.uint8)
        result.affine = img.affine
        zooms = img.header.get_zooms()
        result.voxel_spacing = (float(zooms[0]), float(zooms[1]), float(zooms[2]))
        voxel_ml = np.prod(result.voxel_spacing) / 1000.0
        result.liver_volume_ml = float(np.sum(result.liver_mask)) * voxel_ml
        logger.info(f"Liver volume: {result.liver_volume_ml:.0f} mL")
    else:
        logger.warning("Liver mask not found — segmentation may have failed")

    # Load tumor mask (TotalSegmentator uses different filenames)
    for candidate in ["liver_lesions.nii.gz", "liver_tumor.nii.gz", "liver_tumour.nii.gz", "hepatic_tumor.nii.gz"]:
        p = tumor_out / candidate
        if p.exists():
            t_img = nib.load(str(p))
            result.tumor_mask = t_img.get_fdata().astype(np.uint8)
            if result.voxel_spacing == (1.0, 1.0, 1.0):
                zooms = t_img.header.get_zooms()
                result.voxel_spacing = (float(zooms[0]), float(zooms[1]), float(zooms[2]))
            result.lesions = _extract_lesions(result.tumor_mask, result.voxel_spacing)
            logger.info(f"Found {len(result.lesions)} lesion(s)")
            break

    return result


def _extract_lesions(mask: np.ndarray, spacing: Tuple[float, float, float]) -> List[LesionInfo]:
    from scipy import ndimage

    labeled, n = ndimage.label(mask)
    voxel_ml = np.prod(spacing) / 1000.0
    lesions = []

    for i in range(1, n + 1):
        comp = labeled == i
        count = int(np.sum(comp))
        if count < 8:
            continue

        idx = np.where(comp)
        dims = [
            (int(idx[ax].max()) - int(idx[ax].min()) + 1) * spacing[ax]
            for ax in range(3)
        ]
        centroid = [int(np.mean(idx[ax])) for ax in range(3)]

        lesions.append(
            LesionInfo(
                lesion_id=f"L{i}",
                size_mm=round(max(dims), 1),
                volume_ml=round(count * voxel_ml, 3),
                centroid_voxel=centroid,
                voxel_count=count,
            )
        )

    lesions.sort(key=lambda x: x.size_mm, reverse=True)
    return lesions
