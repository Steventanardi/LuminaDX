"""Per-cancer LLM catalog — the default model each cancer uses, plus the set of
locally-available vision models that can be selected for comparison.

All models here must be pulled in Ollama (`ollama list`). Keep this list in sync
with what is actually installed; the frontend reads it via /api/analysis/models.
"""
from __future__ import annotations

# Vision-capable models confirmed available on the 8 GB laptop set.
# Each entry: tag → short human label shown in the UI dropdown.
VISION_MODELS: dict[str, str] = {
    "medgemma:4b-it-q8_0": "MedGemma 4B (medical)",
    "minicpm-v:8b":        "MiniCPM-V 8B",
    "qwen2.5vl:7b":        "Qwen2.5-VL 7B",
    "llava:7b":            "LLaVA 7B",
}

# Per-cancer recommended default. Every option in VISION_MODELS is selectable for
# comparison, but this is what runs unless the user overrides it.
_DEFAULTS: dict[str, str] = {
    "liver":      "medgemma:4b-it-q8_0",
    "lung":       "qwen2.5vl:7b",
    "skin":       "minicpm-v:8b",
    "breast":     "minicpm-v:8b",
    "colorectal": "qwen2.5vl:7b",
}

_FALLBACK_DEFAULT = "medgemma:4b-it-q8_0"


def default_for(cancer_type: str) -> str:
    return _DEFAULTS.get(cancer_type, _FALLBACK_DEFAULT)


def options_for(cancer_type: str) -> list[dict[str, str]]:
    """Selectable models for a cancer — all vision models, default first."""
    default = default_for(cancer_type)
    tags = [default] + [t for t in VISION_MODELS if t != default]
    return [{"tag": t, "label": VISION_MODELS[t]} for t in tags]


def is_allowed(model: str) -> bool:
    return model in VISION_MODELS


def resolve(cancer_type: str, requested: str | None) -> str:
    """Pick the model to actually run: a valid request wins, else the cancer default."""
    if requested and is_allowed(requested):
        return requested
    return default_for(cancer_type)


def catalog() -> dict[str, dict]:
    """Full per-cancer catalog for the frontend."""
    return {
        ct: {"default": default_for(ct), "options": options_for(ct)}
        for ct in _DEFAULTS
    }
