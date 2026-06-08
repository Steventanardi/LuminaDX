from __future__ import annotations

import base64
import io
from pathlib import Path
from typing import List, Optional, Tuple

import nibabel as nib
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from loguru import logger

from core.segmentation import SegmentationResult

_LIVER_RGBA = (255, 165, 0, 70)   # orange, semi-transparent
_TUMOR_RGBA = (220, 20, 60, 130)  # crimson, more opaque

_SLICE_SIZE = (512, 512)


def _percentile_window(arr: np.ndarray, lo_pct: float = 1.0, hi_pct: float = 99.0) -> np.ndarray:
    lo, hi = np.percentile(arr, lo_pct), np.percentile(arr, hi_pct)
    if hi <= lo:
        hi = lo + 1.0
    return ((np.clip(arr, lo, hi) - lo) / (hi - lo) * 255).astype(np.uint8)


def _hu_to_uint8(arr: np.ndarray, center: float = 50.0, width: float = 400.0) -> np.ndarray:
    """Liver-window CT → uint8. Falls back to percentile if result is too dark (e.g. synthetic data)."""
    lo, hi = center - width / 2, center + width / 2
    result = ((np.clip(arr, lo, hi) - lo) / (hi - lo) * 255).astype(np.uint8)
    # If >90% of pixels are very dark, the HU calibration is off → use percentile fallback
    if np.mean(result < 10) > 0.90:
        return _percentile_window(arr)
    return result


def _mri_to_uint8(arr: np.ndarray) -> np.ndarray:
    return _percentile_window(arr, 0.5, 99.5)


def _best_slice(tumor_mask: Optional[np.ndarray], volume: np.ndarray) -> int:
    if tumor_mask is not None and np.any(tumor_mask):
        return int(np.argmax(np.sum(tumor_mask, axis=(0, 1))))
    return volume.shape[2] // 2


def _render_slice(
    volume: np.ndarray,
    z: int,
    modality: str,
    liver_mask: Optional[np.ndarray],
    tumor_mask: Optional[np.ndarray],
    lesion_label: Optional[str] = None,
) -> Image.Image:
    raw = volume[:, :, z]
    gray = _hu_to_uint8(raw) if modality.upper() == "CT" else _mri_to_uint8(raw)
    gray = np.rot90(gray)

    img = Image.fromarray(gray, "L").convert("RGBA").resize(_SLICE_SIZE, Image.LANCZOS)

    def _overlay(mask_slice: np.ndarray, color: Tuple[int, int, int, int]) -> None:
        layer = np.rot90(mask_slice)
        alpha = Image.fromarray((layer * 255).astype(np.uint8), "L").resize(
            _SLICE_SIZE, Image.NEAREST
        )
        colored = Image.new("RGBA", _SLICE_SIZE, color)
        colored.putalpha(alpha)
        nonlocal img
        img = Image.alpha_composite(img, colored)

    if liver_mask is not None and np.any(liver_mask[:, :, z]):
        _overlay(liver_mask[:, :, z], _LIVER_RGBA)

    tumor_on_slice = tumor_mask is not None and np.any(tumor_mask[:, :, z])
    if tumor_on_slice:
        _overlay(tumor_mask[:, :, z], _TUMOR_RGBA)  # type: ignore[index]

    img = img.convert("RGB")

    # Annotate lesion centroid with a crosshair + size label
    if tumor_on_slice and lesion_label:
        t_slice = tumor_mask[:, :, z]  # type: ignore[index]
        ys, xs = np.where(t_slice > 0)
        if len(xs):
            orig_h, orig_w = t_slice.shape
            sw, sh = _SLICE_SIZE
            # After rot90: new_x = orig_h - 1 - orig_y, new_y = orig_x
            cx = int((orig_h - 1 - float(np.mean(ys))) / orig_h * sw)
            cy = int(float(np.mean(xs)) / orig_w * sh)
            r = 8
            draw = ImageDraw.Draw(img)
            draw.ellipse([(cx - r, cy - r), (cx + r, cy + r)],
                         outline=(255, 60, 60), width=2)
            draw.line([(cx - r - 4, cy), (cx + r + 4, cy)], fill=(255, 60, 60), width=1)
            draw.line([(cx, cy - r - 4), (cx, cy + r + 4)], fill=(255, 60, 60), width=1)
            txt_x = min(cx + r + 5, sw - 80)
            txt_y = max(cy - 10, 4)
            draw.rectangle([(txt_x - 2, txt_y - 2),
                             (txt_x + len(lesion_label) * 7 + 4, txt_y + 13)],
                            fill=(0, 0, 0))
            draw.text((txt_x, txt_y), lesion_label, fill=(255, 200, 0))

    return img


def _add_label(img: Image.Image, text: str) -> Image.Image:
    draw = ImageDraw.Draw(img)
    draw.rectangle([(4, 4), (min(len(text) * 9 + 8, img.width - 4), 26)], fill=(0, 0, 0, 200))
    draw.text((8, 6), text, fill=(255, 255, 0))
    return img


def create_montage(
    nifti_paths: List[Path],
    seg: SegmentationResult,
    out_dir: Path,
    modality: str,
    phase_labels: Optional[List[str]] = None,
    max_phases: int = 4,
) -> Path:
    paths = nifti_paths[:max_phases]
    labels = (phase_labels or [])[:max_phases]
    labels += [f"Phase {i + 1}" for i in range(len(labels), len(paths))]

    # Build lesion annotation label for slices (e.g. "L1: 28mm")
    lesion_label: Optional[str] = None
    if seg.lesions:
        l0 = seg.lesions[0]
        lesion_label = (
            f"{l0.lesion_id}: {l0.size_mm:.0f}mm"
            if l0.size_mm is not None
            else l0.lesion_id
        )

    frames: List[Image.Image] = []
    for path, label in zip(paths, labels):
        try:
            vol = nib.load(str(path)).get_fdata()
            z = _best_slice(seg.tumor_mask, vol)
            frame = _render_slice(vol, z, modality, seg.liver_mask, seg.tumor_mask, lesion_label)
            frame = _add_label(frame, label.upper())
            frames.append(frame)
        except Exception as exc:
            logger.warning(f"Could not render {path.name}: {exc}")

    if not frames:
        raise RuntimeError("No slices rendered for montage")

    cols = min(2, len(frames))
    rows = (len(frames) + cols - 1) // cols
    w, h = _SLICE_SIZE
    canvas = Image.new("RGB", (cols * w, rows * h), (15, 15, 15))
    for i, f in enumerate(frames):
        r, c = divmod(i, cols)
        canvas.paste(f, (c * w, r * h))

    out = out_dir / "montage.png"
    canvas.save(str(out), "PNG", optimize=True)
    logger.info(f"Montage saved: {out} ({canvas.size})")
    return out


def export_overlay_slices_b64(
    nifti_path: Path,
    seg: SegmentationResult,
    modality: str,
    n_slices: int = 24,
    apply_overlay: bool = True,
) -> List[str]:
    vol = nib.load(str(nifti_path)).get_fdata()
    total = vol.shape[2]

    if seg.tumor_mask is not None and np.any(seg.tumor_mask):
        sums = np.sum(seg.tumor_mask, axis=(0, 1))
        nz = np.where(sums > 0)[0]
        start = max(0, int(nz[0]) - 5)
        end = min(total, int(nz[-1]) + 6)
    elif seg.liver_mask is not None and np.any(seg.liver_mask):
        sums = np.sum(seg.liver_mask, axis=(0, 1))
        nz = np.where(sums > 0)[0]
        start, end = int(nz[0]), int(nz[-1]) + 1
    else:
        start, end = 0, total

    indices = np.linspace(start, end - 1, num=min(n_slices, end - start), dtype=int)
    result = []

    liver = seg.liver_mask if apply_overlay else None
    tumor = seg.tumor_mask if apply_overlay else None

    lesion_label: Optional[str] = None
    if apply_overlay and seg.lesions:
        l0 = seg.lesions[0]
        lesion_label = (
            f"{l0.lesion_id}: {l0.size_mm:.0f}mm"
            if l0.size_mm is not None
            else l0.lesion_id
        )

    for z in indices:
        img = _render_slice(vol, int(z), modality, liver, tumor, lesion_label if apply_overlay else None)
        buf = io.BytesIO()
        img.save(buf, "JPEG", quality=82)
        result.append(base64.b64encode(buf.getvalue()).decode())

    return result
