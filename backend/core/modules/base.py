"""Protocol / ABC that every cancer-type diagnosis module must implement."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from core.segmentation import SegmentationResult
    from models.schemas import DiagnosticReport


@dataclass
class SegmentationSpec:
    organ_roi: list[str]              # TotalSegmentator ROI names for organ seg
    lesion_task: Optional[str]        # named TotalSegmentator task, e.g. "liver_lesions"
    tumor_mask_names: list[str] = field(default_factory=list)  # output filenames to look for


class DiagnosisModule(ABC):
    cancer_type: str   # e.g. "liver" | "skin" | "lung" | "breast" | "colorectal"
    display_name: str  # human label
    pipeline: str      # "volumetric" | "image"

    def segmentation_spec(self) -> Optional[SegmentationSpec]:
        return None

    def rag_namespace(self) -> str:
        return self.cancer_type

    def rag_query(self, seg: SegmentationResult, modality: str) -> str:
        return f"{self.cancer_type} cancer imaging {modality} diagnosis assessment guidelines"

    @abstractmethod
    def system_prompt(self) -> str: ...

    @abstractmethod
    def build_prompt(
        self,
        seg: SegmentationResult,
        modality: str,
        rag_context: str,
        radiomics_summary: str,
        patient_info: Optional[dict],
    ) -> str: ...

    @abstractmethod
    def parse_report(
        self,
        raw: str,
        modality: str,
        rag_used: bool,
        radiomics_summary: str,
    ) -> DiagnosticReport: ...
