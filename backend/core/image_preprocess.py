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
    # Segmentation-quality caveats (set by the hardened segmenter)
    multi_lesion: bool = False  # a second comparable lesion was present (metrics use one)
    low_contrast: bool = False  # weak lesion/skin separation — measurements less reliable
    border_artifact: bool = False  # chosen blob touches the frame edge (possible crop/vignette)
    # Stolz ABCD Total Dermoscopy Score components
    tds_a: int = 0              # asymmetry axes (0-2)
    tds_b: int = 0              # border-segment abrupt cutoffs (0-8)
    tds_c: int = 1             # colour count (1-6)
    tds_d: int = 1             # differential structures, estimated (1-5)
    tds: float = 0.0           # TDS = 1.3·A + 0.1·B + 0.5·C + 0.5·D
    tds_category: str = ""     # benign / suspicious / melanoma-suspicious

    def summary(self) -> str:
        if not self.segmented:
            return ("Automated lesion segmentation could not confidently isolate a "
                    "single lesion (low contrast or multiple lesions); rely on visual "
                    "assessment of the enhanced image.")
        caveats = []
        if self.multi_lesion:
            caveats.append("more than one lesion of comparable size was detected — the "
                           "metrics below describe only the largest/most central one")
        if self.low_contrast:
            caveats.append("lesion-to-skin contrast is weak, so the border, asymmetry and "
                           "colour measurements are less reliable")
        if self.border_artifact:
            caveats.append("the segmented lesion touches the image edge (possible crop, "
                           "ruler or vignette) — diameter/asymmetry may be truncated")
        caveat_txt = ("  ⚠ Segmentation caveats: " + "; ".join(caveats) + ".\n") if caveats else ""
        return (
            "Computed from automated lesion segmentation on the enhanced image:\n"
            f"{caveat_txt}"
            f"  • Asymmetry: {self.asymmetry_pct:.1f}% area mismatch across principal axes "
            f"({'asymmetric' if self.asymmetry_pct >= 15 else 'fairly symmetric'})\n"
            f"  • Border irregularity index: {self.border_irregularity:.2f} "
            f"({'irregular/notched border' if self.border_irregularity >= 1.5 else 'relatively smooth border'})\n"
            f"  • Maximum diameter: {self.diameter_px:.0f} px "
            "(physical mm not available — no calibration in image)\n"
            f"  • Colour variegation: {self.color_count} distinct dominant colour cluster(s) "
            f"({'multi-coloured' if self.color_count >= 3 else 'uniform colour'})\n"
            f"  • Lesion covers {self.lesion_area_frac * 100:.0f}% of the image\n"
            "\n"
            f"Stolz ABCD Total Dermoscopy Score (TDS = 1.3·A + 0.1·B + 0.5·C + 0.5·D):\n"
            f"  • A (asymmetry): {self.tds_a}/2 axes  • B (border cutoffs): {self.tds_b}/8 "
            f" • C (colours): {self.tds_c}/6  • D (structures, estimated): {self.tds_d}/5\n"
            f"  • TDS = {self.tds:.2f}  →  {self.tds_category}\n"
            "  (TDS <4.75 benign · 4.75–5.45 suspicious · >5.45 melanoma-suspicious)\n"
            "NOTE: automated TDS estimate — A/B measured geometrically, C from colour "
            "clustering, D approximated from texture. Decision support only; it does not "
            "replace your manual dermoscopic ABCD/7-point assessment."
        )


def _fov_mask(gray: np.ndarray) -> np.ndarray:
    """Usable field-of-view: drop the near-black vignette/border ring that many
    dermoscopes leave around the image. Vignette = very dark pixels in a blob
    that touches the frame edge; without this, Otsu locks onto the black ring
    instead of the lesion. Returns 255 inside the FOV, 0 in vignette."""
    h, w = gray.shape
    _, dark = cv2.threshold(gray, 25, 255, cv2.THRESH_BINARY_INV)
    dark = cv2.morphologyEx(dark, cv2.MORPH_CLOSE,
                            cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9)))
    n, lbl, stats, _ = cv2.connectedComponentsWithStats(dark, 8)
    vignette = np.zeros((h, w), np.uint8)
    for i in range(1, n):
        x, y, bw, bh, area = stats[i]
        touches = x == 0 or y == 0 or x + bw == w or y + bh == h
        if touches and area > 0.005 * h * w:
            vignette[lbl == i] = 255
    return cv2.bitwise_not(vignette)


def _segment_lesion(img: np.ndarray) -> Optional[tuple[np.ndarray, dict]]:
    """Otsu segmentation of the (darker) lesion, hardened against vignette, ruler
    and ink artifacts, low contrast and multiple lesions.

    Returns ``(mask, info)`` where ``info`` carries quality flags
    (``multi_lesion``, ``low_contrast``, ``border_artifact``), or None when no
    lesion can be confidently isolated.
    """
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (5, 5), 0)
    h, w = gray.shape
    fov = _fov_mask(gray)

    # Threshold only over FOV pixels so the vignette can't bias Otsu's cutoff.
    fov_vals = gray[fov > 0]
    if fov_vals.size < 0.05 * h * w:
        return None
    thr, _ = cv2.threshold(fov_vals, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    lesion_vals = fov_vals[fov_vals <= thr]
    skin_vals = fov_vals[fov_vals > thr]
    if lesion_vals.size < 10 or skin_vals.size < 10:
        return None
    contrast = abs(float(lesion_vals.mean()) - float(skin_vals.mean()))
    if contrast < 6.0:  # essentially no lesion/skin separation → unusable
        return None

    mask = ((gray <= thr) & (fov > 0)).astype(np.uint8) * 255
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9))
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

    n, lbl, stats, cents = cv2.connectedComponentsWithStats(mask, 8)
    if n <= 1:
        return None
    img_area = float(h * w)
    cx0, cy0 = w / 2.0, h / 2.0
    diag = float(np.hypot(h, w))
    candidates = []
    for i in range(1, n):
        x, y, bw, bh, area = stats[i]
        frac = area / img_area
        if frac < 0.01 or frac > 0.95:
            continue
        touch = bool(x <= 1 or y <= 1 or x + bw >= w - 1 or y + bh >= h - 1)
        ccx, ccy = cents[i]
        dist = float(np.hypot(ccx - cx0, ccy - cy0)) / diag  # 0 = centred, ~0.5 = corner
        candidates.append({"id": int(i), "area": float(area), "frac": frac,
                           "dist": dist, "touch": touch})
    if not candidates:
        return None

    # Prefer large, central blobs; penalise border-touching ones (ruler/vignette
    # remnants or lesions cropped by the frame), but never discard them entirely.
    def _score(c: dict) -> float:
        return c["area"] * (1.0 - min(c["dist"], 1.0)) * (0.4 if c["touch"] else 1.0)

    candidates.sort(key=_score, reverse=True)
    best = candidates[0]
    others = [c for c in candidates[1:]
              if not c["touch"] and c["area"] >= 0.4 * best["area"]]

    clean = np.zeros((h, w), np.uint8)
    clean[lbl == best["id"]] = 255
    # Fill internal holes (inpainted hair, glare) so geometry isn't pock-marked.
    cnts, _ = cv2.findContours(clean, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not cnts:
        return None
    clean = np.zeros((h, w), np.uint8)
    cv2.drawContours(clean, [max(cnts, key=cv2.contourArea)], -1, 255, thickness=cv2.FILLED)

    info = {
        "multi_lesion": len(others) > 0,
        "low_contrast": contrast < 12.0,
        "border_artifact": best["touch"],
    }
    return clean, info


def _asymmetry_axes(mask: np.ndarray) -> tuple[float, float]:
    """Align lesion principal axis to horizontal, then compare halves on each axis.

    Returns (mismatch_horizontal_pct, mismatch_vertical_pct), each 0-100.
    """
    ys, xs = np.where(mask > 0)
    if len(xs) < 10:
        return 0.0, 0.0
    m = cv2.moments(mask, binaryImage=True)
    if m["m00"] == 0:
        return 0.0, 0.0
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
        return 0.0, 0.0
    mismatch_h = np.count_nonzero(cv2.bitwise_xor(aligned, flip_h)) / (2 * area) * 100
    mismatch_v = np.count_nonzero(cv2.bitwise_xor(aligned, flip_v)) / (2 * area) * 100
    return float(np.clip(mismatch_h, 0, 100)), float(np.clip(mismatch_v, 0, 100))


def _asymmetry(mask: np.ndarray) -> float:
    """Mean area mismatch across the two principal axes (0-100)."""
    h, v = _asymmetry_axes(mask)
    return (h + v) / 2


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
    """k-means on lesion pixels; count clusters holding >=8% of pixels.

    Deterministic: both the pixel subsample and OpenCV's k-means initialisation
    are seeded, so the same lesion yields the same colour count (and therefore
    the same TDS C score) across runs — otherwise an unseeded subsample/init can
    nudge TDS across the 4.75 benign/suspicious boundary between identical runs.
    """
    pixels = img[mask > 0].astype(np.float32)
    if len(pixels) < k:
        return 1
    # subsample for speed on large lesions (seeded for reproducibility)
    if len(pixels) > 20000:
        rng = np.random.default_rng(42)
        idx = rng.choice(len(pixels), 20000, replace=False)
        pixels = pixels[idx]
    cv2.setRNGSeed(42)
    criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 20, 1.0)
    _, labels, _ = cv2.kmeans(pixels, k, None, criteria, 3, cv2.KMEANS_PP_CENTERS)
    counts = np.bincount(labels.flatten(), minlength=k)
    return int(np.count_nonzero(counts / counts.sum() >= 0.08))


# ── Stolz TDS components ────────────────────────────────────────────────────
def _tds_a(mask: np.ndarray, axis_thresh: float = 12.0) -> int:
    """A score (0-2): number of principal axes with significant area asymmetry."""
    h, v = _asymmetry_axes(mask)
    return int(h >= axis_thresh) + int(v >= axis_thresh)


def _tds_b(img: np.ndarray, mask: np.ndarray, sharp_thresh: float = 18.0) -> int:
    """B score (0-8): pigment border divided into 8 octants; count octants whose
    pigment ends abruptly (sharp inside-vs-outside intensity step) rather than
    fading gradually."""
    m = cv2.moments(mask, binaryImage=True)
    if m["m00"] == 0:
        return 0
    cx, cy = m["m10"] / m["m00"], m["m01"] / m["m00"]

    # narrow bands just inside and just outside the lesion border
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
    inner = cv2.subtract(mask, cv2.erode(mask, k))
    outer = cv2.subtract(cv2.dilate(mask, k), mask)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY).astype(np.float32)

    octants_sharp = 0
    for i in range(8):
        a0, a1 = i * (np.pi / 4) - np.pi, (i + 1) * (np.pi / 4) - np.pi
        sharp = _octant_step(gray, inner, outer, cx, cy, a0, a1)
        if sharp >= sharp_thresh:
            octants_sharp += 1
    return int(octants_sharp)


def _octant_step(gray: np.ndarray, inner: np.ndarray, outer: np.ndarray,
                 cx: float, cy: float, a0: float, a1: float) -> float:
    """Mean inside-vs-outside intensity step for border pixels in one angular sector."""
    def sector_vals(band: np.ndarray) -> np.ndarray:
        ys, xs = np.where(band > 0)
        if len(xs) == 0:
            return np.empty(0, np.float32)
        ang = np.arctan2(ys - cy, xs - cx)
        sel = (ang >= a0) & (ang < a1)
        return gray[ys[sel], xs[sel]]

    iv, ov = sector_vals(inner), sector_vals(outer)
    if len(iv) < 5 or len(ov) < 5:
        return 0.0
    return abs(float(np.mean(iv)) - float(np.mean(ov)))


def _tds_d(img: np.ndarray, mask: np.ndarray) -> int:
    """D score (1-5): differential structures. True structure typing (network,
    globules, dots, streaks, structureless) needs dedicated detectors; here we
    approximate structural richness from intra-lesion texture energy so the LLM
    has a number — explicitly flagged as an estimate in the summary."""
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    lap = cv2.Laplacian(gray, cv2.CV_64F, ksize=3)
    vals = lap[mask > 0]
    if vals.size == 0:
        return 1
    energy = float(np.var(vals))
    # empirical bins on Laplacian variance → 1..5 structural-richness levels
    for thr, score in ((50, 1), (200, 2), (500, 3), (1200, 4)):
        if energy < thr:
            return score
    return 5


def _tds_category(tds: float) -> str:
    if tds < 4.75:
        return "benign melanocytic lesion (TDS <4.75)"
    if tds <= 5.45:
        return "suspicious — short-term follow-up or excision (TDS 4.75–5.45)"
    return "highly suspicious for melanoma (TDS >5.45)"


def _compute_features(img: np.ndarray, mask: np.ndarray,
                      info: Optional[dict] = None) -> DermFeatures:
    info = info or {}
    h, w = mask.shape
    colors = _color_count(img, mask)
    a = _tds_a(mask)
    b = _tds_b(img, mask)
    c = int(np.clip(colors, 1, 6))
    d = _tds_d(img, mask)
    tds = round(1.3 * a + 0.1 * b + 0.5 * c + 0.5 * d, 2)
    return DermFeatures(
        asymmetry_pct=_asymmetry(mask),
        border_irregularity=_border_irregularity(mask),
        diameter_px=_max_diameter(mask),
        color_count=colors,
        lesion_area_frac=float(np.count_nonzero(mask)) / float(h * w),
        segmented=True,
        multi_lesion=bool(info.get("multi_lesion", False)),
        low_contrast=bool(info.get("low_contrast", False)),
        border_artifact=bool(info.get("border_artifact", False)),
        tds_a=a, tds_b=b, tds_c=c, tds_d=d,
        tds=tds, tds_category=_tds_category(tds),
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
    seg = _segment_lesion(enhanced)
    if seg is None:
        return DermFeatures(0.0, 0.0, 0.0, 0, 0.0, segmented=False)
    mask, info = seg
    return _compute_features(enhanced, mask, info)


@dataclass
class MammoFeatures:
    breast_area_frac: float    # breast region as a fraction of the image
    percent_density: float     # fibroglandular (dense) tissue % within the breast
    birads_density: str        # ACR density category a / b / c / d
    segmented: bool
    low_contrast: bool = False  # weak breast/background separation — estimate less reliable

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
        caveat = ("  ⚠ Weak breast/background separation (low contrast or an already-"
                  "processed image) — treat the density estimate with extra caution.\n"
                  if self.low_contrast else "")
        return (
            "Computed from automated breast-region segmentation:\n"
            f"{caveat}"
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

    # Quality flag: weak breast-vs-background separation makes the estimate shaky.
    bg_vals = img[breast == 0]
    contrast = (float(breast_vals.mean()) - float(bg_vals.mean())) if bg_vals.size else 255.0

    return MammoFeatures(
        breast_area_frac=breast_px / float(h * w),
        percent_density=pct,
        birads_density=_birads_density(pct),
        segmented=True,
        low_contrast=contrast < 25.0,
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
