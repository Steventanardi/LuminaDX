from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

from loguru import logger

from config import settings

try:
    import SimpleITK as sitk
    from radiomics import featureextractor as _fe
    _AVAILABLE = True
except ImportError:
    _AVAILABLE = False
    logger.warning("PyRadiomics not available — feature extraction skipped")

# Features shown prominently in the LLM summary (key → display label)
_SUMMARY_FEATURES: dict[str, str] = {
    # Shape
    "original_shape_MeshVolume":           "Volume (mm³)",
    "original_shape_Maximum3DDiameter":    "Max Diameter (mm)",
    "original_shape_Sphericity":           "Sphericity",
    "original_shape_SurfaceVolumeRatio":   "Surface/Volume Ratio",
    "original_shape_LeastAxisLength":      "Least Axis Length (mm)",
    "original_shape_Elongation":           "Elongation",
    "original_shape_Flatness":             "Flatness",
    # First-order intensity
    "original_firstorder_Mean":            "Mean Intensity",
    "original_firstorder_Median":          "Median Intensity",
    "original_firstorder_StandardDeviation": "Intensity SD",
    "original_firstorder_Skewness":        "Intensity Skewness",
    "original_firstorder_Kurtosis":        "Intensity Kurtosis",
    "original_firstorder_Energy":          "Energy",
    "original_firstorder_Entropy":         "Intensity Entropy",
    "original_firstorder_RobustMeanAbsoluteDeviation": "Robust MAD",
    # GLCM (texture)
    "original_glcm_Contrast":             "GLCM Contrast",
    "original_glcm_Correlation":          "GLCM Correlation",
    "original_glcm_JointEnergy":          "GLCM Joint Energy",
    "original_glcm_JointEntropy":         "GLCM Joint Entropy",
    "original_glcm_Homogeneity1":         "GLCM Homogeneity",
    "original_glcm_DifferenceVariance":   "GLCM Diff Variance",
    "original_glcm_Idmn":                 "GLCM IDMN",
    # GLRLM (run-length)
    "original_glrlm_ShortRunEmphasis":    "Short Run Emphasis",
    "original_glrlm_LongRunEmphasis":     "Long Run Emphasis",
    "original_glrlm_GrayLevelNonUniformity": "GL Non-Uniformity",
    "original_glrlm_RunLengthNonUniformityNormalized": "Run Length NUN",
    # GLSZM (zone-size)
    "original_glszm_SmallAreaEmphasis":   "Small Zone Emphasis",
    "original_glszm_LargeAreaEmphasis":   "Large Zone Emphasis",
    "original_glszm_ZoneEntropy":         "Zone Entropy",
    # GLDM (dependence)
    "original_gldm_DependenceEntropy":    "Dependence Entropy",
    "original_gldm_LargeDependenceEmphasis": "Large Dep Emphasis",
    # NGTDM (neighbouring grey-tone)
    "original_ngtdm_Coarseness":          "Coarseness",
    "original_ngtdm_Contrast":            "NGTDM Contrast",
    "original_ngtdm_Complexity":          "Complexity",
    "original_ngtdm_Strength":            "Strength",
}

# Thresholds for clinical interpretation hints
def _interpret(features: Dict[str, Any]) -> list[str]:
    """Return short clinical observation strings based on feature values."""
    hints: list[str] = []
    sph = features.get("original_shape_Sphericity")
    if sph is not None:
        hints.append(
            "Regular shape (sphericity {:.2f} — consistent with HCC)".format(sph)
            if sph > 0.7
            else "Irregular/lobulated shape (sphericity {:.2f})".format(sph)
        )
    skew = features.get("original_firstorder_Skewness")
    if skew is not None:
        if skew > 1.0:
            hints.append("Positive intensity skew — heterogeneous or necrotic regions possible")
        elif skew < -1.0:
            hints.append("Negative intensity skew — hyperdense components present")
    ent = features.get("original_glcm_JointEntropy")
    if ent is not None:
        hints.append(
            "High textural entropy ({:.2f}) — heterogeneous lesion".format(ent)
            if ent > 4.0
            else "Low textural entropy ({:.2f}) — homogeneous lesion".format(ent)
        )
    coarse = features.get("original_ngtdm_Coarseness")
    if coarse is not None:
        hints.append(
            "Fine texture (coarseness {:.4f})".format(coarse)
            if coarse < 0.003
            else "Coarse texture (coarseness {:.4f})".format(coarse)
        )
    return hints


def extract(image_nifti: Path, mask_nifti: Optional[Path], modality: str = "CT") -> Dict[str, Any]:
    if not _AVAILABLE:
        return {"error": "PyRadiomics not installed"}
    if mask_nifti is None or not mask_nifti.exists():
        return {"error": "Tumor mask unavailable"}

    try:
        extractor = _fe.RadiomicsFeatureExtractor()
        extractor.disableAllFeatures()

        # Enable all seven feature classes
        for cls in ("shape", "firstorder", "glcm", "glrlm", "glszm", "gldm", "ngtdm"):
            extractor.enableFeatureClassByName(cls)

        # Original always on. Wavelet/LoG add ~1,000 features (and most of the
        # runtime) but are not used downstream — only enable when explicitly
        # requested via settings.radiomics_extended.
        extractor.enableImageTypeByName("Original")
        if settings.radiomics_extended:
            extractor.enableImageTypeByName("Wavelet")
            extractor.enableImageTypeByName("LoG", customArgs={"sigma": [1.0, 2.0, 3.0]})

        # CT HU values are already quantitative — normalizing distorts feature
        # semantics and hurts reproducibility. Normalize MRI only.
        is_mri = str(modality).upper() in ("MR", "MRI")
        extractor.settings.update({
            "binWidth": 25,
            "normalize": is_mri,
            "normalizeScale": 100,
            "resampledPixelSpacing": None,  # keep native voxel spacing
            "interpolator": sitk.sitkBSpline,
            "padDistance": 10,
        })

        image = sitk.ReadImage(str(image_nifti))
        mask = sitk.Cast(sitk.ReadImage(str(mask_nifti)), sitk.sitkInt32)

        raw = extractor.execute(image, mask)
        features = {
            k: float(v)
            for k, v in raw.items()
            if not k.startswith("diagnostics_")
        }
        logger.info(f"Extracted {len(features)} radiomic features from {mask_nifti.name}")
        return features

    except Exception as exc:
        logger.error(f"Radiomics failed: {exc}")
        return {"error": str(exc)}


def summarize(features: Dict[str, Any]) -> str:
    if "error" in features:
        return f"Feature extraction unavailable: {features['error']}"

    total = len(features)
    # Count by image type
    wavelet_n = sum(1 for k in features if k.startswith("wavelet"))
    log_n = sum(1 for k in features if k.startswith("log"))
    orig_n = total - wavelet_n - log_n

    lines = [
        f"RADIOMIC FEATURES ({total} total: {orig_n} original · {wavelet_n} wavelet · {log_n} LoG):",
        "",
    ]

    # Organised by category
    sections = {
        "Shape & Morphology": [k for k in _SUMMARY_FEATURES if "shape" in k],
        "Intensity Distribution": [k for k in _SUMMARY_FEATURES if "firstorder" in k],
        "Texture — GLCM": [k for k in _SUMMARY_FEATURES if "glcm" in k],
        "Texture — Run/Zone": [k for k in _SUMMARY_FEATURES if "glrlm" in k or "glszm" in k],
        "Texture — Dependence/NGTDM": [k for k in _SUMMARY_FEATURES if "gldm" in k or "ngtdm" in k],
    }

    for section, keys in sections.items():
        section_lines = []
        for k in keys:
            val = features.get(k)
            if val is not None:
                section_lines.append(f"  {_SUMMARY_FEATURES[k]}: {val:.4f}")
        if section_lines:
            lines.append(f"[{section}]")
            lines.extend(section_lines)
            lines.append("")

    hints = _interpret(features)
    if hints:
        lines.append("[Radiomics Interpretation]")
        for h in hints:
            lines.append(f"  • {h}")

    return "\n".join(lines)
