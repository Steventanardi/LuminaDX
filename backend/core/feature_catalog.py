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
    "knn_classifier":  ("KNN classifier", "classifier"),
    "skin_classifier": ("HAM10000 classifier (7-class, trained)", "classifier"),
}

# Which features are applicable to each cancer (pipeline-dependent).
_APPLICABLE: dict[str, list[str]] = {
    "skin": [
        "color_constancy", "hair_removal", "clahe", "dermoscopy_abcd",
        "cnn_vgg16", "cnn_vgg19", "cnn_resnet50", "knn_classifier", "skin_classifier",
    ],
    "breast": ["clahe", "breast_density", "cnn_vgg16", "cnn_vgg19", "cnn_resnet50", "knn_classifier"],
    "liver":      ["radiomics", "cnn_vgg16", "cnn_vgg19", "cnn_resnet50", "knn_classifier"],
    "lung":       ["radiomics", "cnn_vgg16", "cnn_vgg19", "cnn_resnet50", "knn_classifier"],
    "colorectal": ["radiomics", "cnn_vgg16", "cnn_vgg19", "cnn_resnet50", "knn_classifier"],
}

# Default ON for each cancer (the current hardcoded behaviour, CNNs off by default).
_DEFAULTS: dict[str, list[str]] = {
    "skin":   ["color_constancy", "hair_removal", "clahe", "dermoscopy_abcd", "skin_classifier"],
    "breast": ["clahe", "breast_density"],
    "liver":      ["radiomics"],
    "lung":       ["radiomics"],
    "colorectal": ["radiomics"],
}


def applicable_for(cancer_type: str) -> list[str]:
    return _APPLICABLE.get(cancer_type, ["radiomics"])


def defaults_for(cancer_type: str) -> list[str]:
    return _DEFAULTS.get(cancer_type, ["radiomics"])


def _feature_status(cancer_type: str, key: str) -> tuple[bool, str]:
    """Live availability for status-dependent features.

    Most features are always runnable (ready=True, no detail). The two
    classifiers depend on external artifacts that may be absent: KNN needs a
    labelled reference set, the HAM10000 model needs a trained checkpoint. We
    resolve those at catalog-build time so the picker shows real status instead
    of a hardcoded "(needs reference set)" label that's wrong once it's filled.
    Imports are local to avoid import-time coupling / cycles.
    """
    if key == "knn_classifier":
        from core import knn_classifier
        st = knn_classifier.status(cancer_type)
        if st["ready"]:
            return True, f"{st['n_reference']:,} reference images · {len(st['classes'])} classes"
        if st["n_reference"]:
            return False, f"only {len(st['classes'])} class(es) — needs ≥2 labelled folders"
        return False, "needs labelled reference set"
    if key == "skin_classifier":
        from core import skin_classifier
        return (True, "trained checkpoint loaded") if skin_classifier.is_available() \
            else (False, "no trained checkpoint")
    return True, ""


def options_for(cancer_type: str) -> list[dict]:
    """Selectable features for a cancer: key, label, group, default-on flag, and
    live readiness (ready + human-readable detail) for status-dependent ones."""
    defaults = set(defaults_for(cancer_type))
    out: list[dict] = []
    for key in applicable_for(cancer_type):
        label, group = _FEATURES[key]
        ready, detail = _feature_status(cancer_type, key)
        out.append({"key": key, "label": label, "group": group,
                    "default": key in defaults, "ready": ready, "detail": detail})
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


import time as _time

# Short-TTL cache: building the catalog scans the (large) KNN reference dirs for
# live readiness, so a cold call is ~0.4 s on a 9,600-image set. The picker hits
# /features on every cancer switch — cache the result briefly so repeat loads are
# instant. A newly added reference set shows up within _CATALOG_TTL seconds.
_CATALOG_CACHE: dict[str, tuple[dict, float]] = {}
_CATALOG_TTL = 20.0


def catalog() -> dict[str, dict]:
    """Full per-cancer feature catalog for the frontend (briefly cached)."""
    cached = _CATALOG_CACHE.get("v")
    now = _time.monotonic()
    if cached is not None and now - cached[1] < _CATALOG_TTL:
        return cached[0]
    data = {
        ct: {"defaults": defaults_for(ct), "options": options_for(ct)}
        for ct in _APPLICABLE
    }
    _CATALOG_CACHE["v"] = (data, now)
    return data
