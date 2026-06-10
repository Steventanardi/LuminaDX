"""Cancer-type module registry — maps cancer_type strings to DiagnosisModule instances."""
from __future__ import annotations

from core.modules.base import DiagnosisModule
from core.modules.breast import BreastModule
from core.modules.colorectal import ColorectalModule
from core.modules.liver import LiverModule
from core.modules.lung import LungModule
from core.modules.skin import SkinModule

_REGISTRY: dict[str, DiagnosisModule] = {
    "liver":      LiverModule(),
    "skin":       SkinModule(),
    "lung":       LungModule(),
    "breast":     BreastModule(),
    "colorectal": ColorectalModule(),
}

CANCER_TYPES: list[str] = list(_REGISTRY.keys())


def get(cancer_type: str) -> DiagnosisModule:
    """Return the module for *cancer_type*, falling back to liver if unknown."""
    return _REGISTRY.get(cancer_type, _REGISTRY["liver"])
