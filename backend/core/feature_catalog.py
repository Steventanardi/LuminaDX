"""Per-cancer feature / extractor catalog.

Lets the user choose which feature-extraction and preprocessing steps run for a
given diagnosis, alongside the LLM picker (see model_catalog.py). Mirrors that
module's shape so the frontend can consume both the same way.

Feature keys fall into three groups:
  • preprocessing  — image enhancement applied before the LLM sees the image
  • extractor      — quantitative feature computation summarised into the prompt
  • cnn            — ImageNet-pretrained backbone deep features + heatmap overlay
"""
from __future__ import annotations

# key → (human label, group). Order here is the display order.
_FEATURES: dict[str, tuple[str, str]] = {
    # ── preprocessing ──────────────────────────────────────────────
    "color_constancy": ("Colour constancy (Shades-of-Gray)", "preprocessing"),
    "hair_removal":    ("Hair removal (DullRazor)",          "preprocessing"),
    "clahe":           ("CLAHE contrast enhancement",        "preprocessing"),
    # ── quantitative extractors ────────────────────────────────────
    "dermoscopy_abcd": ("Dermoscopy ABCD metrics",           "extractor"),
    "breast_density":  ("Mammographic density (ACR a–d)",    "extractor"),
    "radiomics":       ("Radiomic features (PyRadiomics)",   "extractor"),
    # ── CNN backbones ──────────────────────────────────────────────
    "cnn_vgg16":       ("VGG16 deep features",               "cnn"),
    "cnn_vgg19":       ("VGG19 deep features",               "cnn"),
    "cnn_resnet50":    ("ResNet50 deep features",            "cnn"),
    # ── classifier ─────────────────────────────────────────────────
    "knn_classifier":  ("KNN classifier (needs reference set)", "classifier"),
}

# Which features are applicable to each cancer (pipeline-dependent).
_APPLICABLE: dict[str, list[str]] = {
    "skin": [
        "color_constancy", "hair_removal", "clahe", "dermoscopy_abcd",
        "cnn_vgg16", "cnn_vgg19", "cnn_resnet50", "knn_classifier",
    ],
    "breast": ["clahe", "breast_density", "cnn_vgg16", "cnn_vgg19", "cnn_resnet50", "knn_classifier"],
    "liver":      ["radiomics", "cnn_vgg16", "cnn_vgg19", "cnn_resnet50", "knn_classifier"],
    "lung":       ["radiomics", "cnn_vgg16", "cnn_vgg19", "cnn_resnet50", "knn_classifier"],
    "colorectal": ["radiomics", "cnn_vgg16", "cnn_vgg19", "cnn_resnet50", "knn_classifier"],
}

# Default ON for each cancer (the current hardcoded behaviour, CNNs off by default).
_DEFAULTS: dict[str, list[str]] = {
    "skin":   ["color_constancy", "hair_removal", "clahe", "dermoscopy_abcd"],
    "breast": ["clahe", "breast_density"],
    "liver":      ["radiomics"],
    "lung":       ["radiomics"],
    "colorectal": ["radiomics"],
}


def applicable_for(cancer_type: str) -> list[str]:
    return _APPLICABLE.get(cancer_type, ["radiomics"])


def defaults_for(cancer_type: str) -> list[str]:
    return _DEFAULTS.get(cancer_type, ["radiomics"])


def options_for(cancer_type: str) -> list[dict[str, str]]:
    """Selectable features for a cancer: key, label, group, default-on flag."""
    defaults = set(defaults_for(cancer_type))
    out: list[dict[str, str]] = []
    for key in applicable_for(cancer_type):
        label, group = _FEATURES[key]
        out.append({"key": key, "label": label, "group": group,
                    "default": key in defaults})
    return out


def resolve(cancer_type: str, requested: list[str] | None) -> set[str]:
    """Pick the feature set to actually run: valid requested features, else defaults."""
    applicable = set(applicable_for(cancer_type))
    if requested is None:
        return set(defaults_for(cancer_type))
    return {f for f in requested if f in applicable}


def cnn_backbones_in(features: set[str]) -> list[str]:
    """Subset of selected features that are CNN backbones, in catalog order."""
    return [k for k, (_, g) in _FEATURES.items() if g == "cnn" and k in features]


def knn_backbone_for(features: set[str], default: str = "cnn_resnet50") -> str:
    """Backbone the KNN classifier should embed with.

    Uses the user's selected CNN backbone when exactly one is chosen, else the
    default (ResNet50 — most balanced for an 8 GB GPU).
    """
    chosen = cnn_backbones_in(features)
    return chosen[0] if len(chosen) == 1 else default


def catalog() -> dict[str, dict]:
    """Full per-cancer feature catalog for the frontend."""
    return {
        ct: {"defaults": defaults_for(ct), "options": options_for(ct)}
        for ct in _APPLICABLE
    }
