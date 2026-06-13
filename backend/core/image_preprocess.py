"""Dermoscopy image preprocessing for the skin-cancer pipeline.

Enhancement chain (CPU-only, OpenCV + numpy):
    1. Color constancy  — Shades-of-Gray (Minkowski p=6) normalises camera /
       lighting colour cast, the single biggest documented lift in dermoscopy ML.
    2. Hair removal     — DullRazor (blackhat morphology + Telea inpaint).
    3. CLAHE            — contrast-limited adaptive histogram equalisation on the
       L channel (LAB) to boost pigment-network / blue-white-veil contrast.

Also derives quantitative ABCD features from an Otsu lesion segmentation so the
LLM has measured numbers (asymmetry, border irregularity, diameter, colour
variegation) to support its assessment rather than eyeballing alone.

All functions are pure and side-effect free except `preprocess_dermoscopy`,
which writes the enhanced image to disk.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import cv2
import numpy as np
from loguru import logger


# ── enhancement steps ──────────────────────────────────────────────────────
def shades_of_gray(img: np.ndarray, power: int = 6) -> np.ndarray:
    """Shades-of-Gray colour constancy (Minkowski norm)."""
    arr = img.astype(np.float32)
    means = np.power(np.mean(np.power(arr, power), axis=(0, 1)), 1.0 / power)
    gray = float(np.mean(means))
    scale = gray / (means + 1e-6)
    return np.clip(arr * scale, 0, 255).astype(np.uint8)


def remove_hair(img: np.ndarray, kernel_size: int = 17) -> np.ndarray:
    """DullRazor hair removal: blackhat to find dark thin hairs, then inpaint."""
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (kernel_size, kernel_size))
    blackhat = cv2.morphologyEx(gray, cv2.MORPH_BLACKHAT, kernel)
    _, mask = cv2.threshold(blackhat, 10, 255, cv2.THRESH_BINARY)
    mask = cv2.dilate(mask, np.ones((3, 3), np.uint8), iterations=1)
    return cv2.inpaint(img, mask, 1, cv2.INPAINT_TELEA)


def apply_clahe(img: np.ndarray, clip: float = 2.0, grid: int = 8) -> np.ndarray:
    """CLAHE on the L channel of LAB; preserves chroma (a, b)."""
    lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=clip, tileGridSize=(grid, grid))
    l = clahe.apply(l)
    return cv2.cvtColor(cv2.merge((l, a, b)), cv2.COLOR_LAB2BGR)


# ── lesion segmentation + ABCD features ────────────────────────────────────
@dataclass
class DermFeatures:
    asymmetry_pct: float        # 0-100, mean area mismatch across principal axes
    border_irregularity: float  # compactness (1.0 = perfect circle, higher = irregular)
    diameter_px: float          # max lesion diameter in pixels
    color_count: int            # distinct dominant colour clusters in the lesion
    lesion_area_frac: float     # fraction of image occupied by the lesion
    segmented: bool             # whether a lesion was confidently isolated

    def summary(self) -> str:
        if not self.segmented:
            return ("Automated lesion segmentation could not confidently isolate a "
                    "single lesion (low contrast or multiple lesions); rely on visual "
                    "assessment of the enhanced image.")
        return (
            "Computed from automated lesion segmentation on the enhanced image:\n"
            f"  • Asymmetry: {self.asymmetry_pct:.1f}% area mismatch across principal axes "
            f"({'asymmetric' if self.asymmetry_pct >= 15 else 'fairly symmetric'})\n"
            f"  • Border irregularity index: {self.border_irregularity:.2f} "
            f"({'irregular/notched border' if self.border_irregularity >= 1.5 else 'relatively smooth border'})\n"
            f"  • Maximum diameter: {self.diameter_px:.0f} px "
            "(physical mm not available — no calibration in image)\n"
            f"  • Colour variegation: {self.color_count} distinct dominant colour cluster(s) "
            f"({'multi-coloured' if self.color_count >= 3 else 'uniform colour'})\n"
            f"  • Lesion covers {self.lesion_area_frac * 100:.0f}% of the image\n"
            "NOTE: these are unvalidated automated estimates to support — not replace — "
            "your dermoscopic ABCD/7-point assessment."
        )


def _segment_lesion(img: np.ndarray) -> Optional[np.ndarray]:
    """Otsu segmentation of the (darker) lesion; returns the largest blob mask."""
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (5, 5), 0)
    _, mask = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9))
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

    cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not cnts:
        return None
    largest = max(cnts, key=cv2.contourArea)
    area = cv2.contourArea(largest)
    h, w = mask.shape
    frac = area / float(h * w)
    # Reject if the "lesion" is a tiny speck or fills almost the whole frame
    # (latter usually means vignette/border, not a lesion).
    if frac < 0.01 or frac > 0.95:
        return None
    clean = np.zeros_like(mask)
    cv2.drawContours(clean, [largest], -1, 255, thickness=cv2.FILLED)
    return clean


def _asymmetry(mask: np.ndarray) -> float:
    """Align lesion principal axis to horizontal, then compare halves."""
    ys, xs = np.where(mask > 0)
    if len(xs) < 10:
        return 0.0
    m = cv2.moments(mask, binaryImage=True)
    if m["m00"] == 0:
        return 0.0
    cx, cy = m["m10"] / m["m00"], m["m01"] / m["m00"]
    mu20, mu02, mu11 = m["mu20"] / m["m00"], m["mu02"] / m["m00"], m["mu11"] / m["m00"]
    theta = 0.5 * np.arctan2(2 * mu11, mu20 - mu02)

    h, w = mask.shape
    rot = cv2.getRotationMatrix2D((cx, cy), np.degrees(theta), 1.0)
    aligned = cv2.warpAffine(mask, rot, (w, h), flags=cv2.INTER_NEAREST)

    flip_h = cv2.flip(aligned, 1)  # left-right
    flip_v = cv2.flip(aligned, 0)  # top-bottom
    area = float(np.count_nonzero(aligned))
    if area == 0:
        return 0.0
    mismatch_h = np.count_nonzero(cv2.bitwise_xor(aligned, flip_h)) / (2 * area)
    mismatch_v = np.count_nonzero(cv2.bitwise_xor(aligned, flip_v)) / (2 * area)
    return float(np.clip((mismatch_h + mismatch_v) / 2 * 100, 0, 100))


def _border_irregularity(mask: np.ndarray) -> float:
    cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    if not cnts:
        return 0.0
    c = max(cnts, key=cv2.contourArea)
    area = cv2.contourArea(c)
    perim = cv2.arcLength(c, True)
    if area <= 0:
        return 0.0
    return float(perim ** 2 / (4 * np.pi * area))  # 1.0 = circle


def _max_diameter(mask: np.ndarray) -> float:
    cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not cnts:
        return 0.0
    (_, _), radius = cv2.minEnclosingCircle(max(cnts, key=cv2.contourArea))
    return float(radius * 2)


def _color_count(img: np.ndarray, mask: np.ndarray, k: int = 6) -> int:
    """k-means on lesion pixels; count clusters holding >=8% of pixels."""
    pixels = img[mask > 0].astype(np.float32)
    if len(pixels) < k:
        return 1
    # subsample for speed on large lesions
    if len(pixels) > 20000:
        idx = np.random.choice(len(pixels), 20000, replace=False)
        pixels = pixels[idx]
    criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 20, 1.0)
    _, labels, _ = cv2.kmeans(pixels, k, None, criteria, 3, cv2.KMEANS_PP_CENTERS)
    counts = np.bincount(labels.flatten(), minlength=k)
    return int(np.count_nonzero(counts / counts.sum() >= 0.08))


def _compute_features(img: np.ndarray, mask: np.ndarray) -> DermFeatures:
    h, w = mask.shape
    return DermFeatures(
        asymmetry_pct=_asymmetry(mask),
        border_irregularity=_border_irregularity(mask),
        diameter_px=_max_diameter(mask),
        color_count=_color_count(img, mask),
        lesion_area_frac=float(np.count_nonzero(mask)) / float(h * w),
        segmented=True,
    )


# ── orchestration ──────────────────────────────────────────────────────────
def preprocess_dermoscopy(
    src_path: Path,
    out_path: Path,
    *,
    color_constancy: bool = True,
    hair_removal: bool = True,
    clahe: bool = True,
    compute_abcd: bool = True,
) -> Optional[DermFeatures]:
    """Enhance a dermoscopy image (selected steps only) and write it to `out_path`.

    Each enhancement step is individually toggleable. Returns computed ABCD
    features when `compute_abcd` is set, else None. Also returns None if the
    source image cannot be read (caller disambiguates via out_path existence).
    """
    img = cv2.imread(str(src_path))
    if img is None:
        logger.warning(f"Dermoscopy preprocess: could not read image {src_path}")
        return None

    if color_constancy:
        img = shades_of_gray(img)
    if hair_removal:
        img = remove_hair(img)
    if clahe:
        img = apply_clahe(img)
    enhanced = img
    out_path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(out_path), enhanced)

    if not compute_abcd:
        return None
    mask = _segment_lesion(enhanced)
    if mask is None:
        return DermFeatures(0.0, 0.0, 0.0, 0, 0.0, segmented=False)
    return _compute_features(enhanced, mask)


@dataclass
class MammoFeatures:
    breast_area_frac: float    # breast region as a fraction of the image
    percent_density: float     # fibroglandular (dense) tissue % within the breast
    birads_density: str        # ACR density category a / b / c / d
    segmented: bool

    def summary(self) -> str:
        if not self.segmented:
            return ("Automated breast-region segmentation could not isolate the "
                    "breast from the background; rely on visual density assessment.")
        cat = {
            "a": "almost entirely fatty",
            "b": "scattered fibroglandular density",
            "c": "heterogeneously dense",
            "d": "extremely dense",
        }.get(self.birads_density, "")
        return (
            "Computed from automated breast-region segmentation:\n"
            f"  • Mammographic percent density: {self.percent_density:.0f}% "
            f"(fibroglandular vs total breast area)\n"
            f"  • Estimated ACR breast density: category {self.birads_density.upper()} ({cat})\n"
            f"  • Breast occupies {self.breast_area_frac * 100:.0f}% of the image\n"
            "NOTE: unvalidated automated estimate of mammographic density (denser "
            "breasts lower sensitivity and modestly raise risk). Supports — does not "
            "replace — the radiologist's ACR density assessment."
        )


def _birads_density(pct: float) -> str:
    if pct < 25:
        return "a"
    if pct < 50:
        return "b"
    if pct < 75:
        return "c"
    return "d"


def compute_mammographic_density(src_path: Path) -> Optional[MammoFeatures]:
    """Estimate mammographic (fibroglandular) percent density and ACR category.

    Breast region = largest bright blob over the black background (Otsu); dense
    tissue = the brighter fraction within the breast (second Otsu). Computed on
    original intensities (not CLAHE-enhanced). Returns None if the image is
    unreadable. Skin-style: an estimate to support, not replace, the radiologist.
    """
    img = cv2.imread(str(src_path), cv2.IMREAD_GRAYSCALE)
    if img is None:
        logger.warning(f"Mammographic density: could not read image {src_path}")
        return None

    blur = cv2.GaussianBlur(img, (5, 5), 0)
    # breast vs background
    _, breast_mask = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (15, 15))
    breast_mask = cv2.morphologyEx(breast_mask, cv2.MORPH_OPEN, kernel)
    cnts, _ = cv2.findContours(breast_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not cnts:
        return MammoFeatures(0.0, 0.0, "a", segmented=False)
    largest = max(cnts, key=cv2.contourArea)
    breast = np.zeros_like(breast_mask)
    cv2.drawContours(breast, [largest], -1, 255, thickness=cv2.FILLED)

    breast_px = int(np.count_nonzero(breast))
    h, w = img.shape
    if breast_px < 0.02 * h * w:
        return MammoFeatures(0.0, 0.0, "a", segmented=False)

    # dense tissue = brighter fraction within the breast region
    breast_vals = img[breast > 0]
    thr, _ = cv2.threshold(breast_vals, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    dense_px = int(np.count_nonzero((img > thr) & (breast > 0)))
    pct = dense_px / breast_px * 100.0

    return MammoFeatures(
        breast_area_frac=breast_px / float(h * w),
        percent_density=pct,
        birads_density=_birads_density(pct),
        segmented=True,
    )


def preprocess_mammography(src_path: Path, out_path: Path) -> bool:
    """CLAHE contrast enhancement for mammography / breast images.

    Mammograms are grayscale; CLAHE on the luminance channel is the standard
    enhancement to bring out masses, calcifications and architectural distortion.
    Hair removal and colour constancy (dermoscopy-specific) are intentionally
    skipped. Returns True if an enhanced image was written.
    """
    img = cv2.imread(str(src_path))
    if img is None:
        logger.warning(f"Mammography preprocess: could not read image {src_path}")
        return False
    enhanced = apply_clahe(img, clip=2.0, grid=8)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(out_path), enhanced)
    return True
