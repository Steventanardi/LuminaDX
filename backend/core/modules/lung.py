"""Lung cancer module — Lung-RADS v2022 / Fleischner guidelines."""
from __future__ import annotations

import json as _json
from typing import Optional

from loguru import logger

from core.modules.base import (
    DIFFERENTIAL_INSTRUCTIONS, DIFFERENTIAL_JSON, DiagnosisModule, SegmentationSpec,
    coerce_json, parse_differential,
)
from models.schemas import DiagnosticReport, LesionFinding

_SYSTEM = """You are an expert thoracic radiologist specializing in lung cancer detection using CT imaging.
You apply Lung-RADS v2022 criteria, the Fleischner Society Guidelines (2017), and follow NCCN Lung Cancer Screening guidelines.

Lung-RADS v2022 Categories (for solid and subsolid nodules on low-dose CT):
• 1   Negative — no nodules; nodule with benign features (calcified, fat, perifissural ≤10mm)
• 2   Benign appearance — solid <6mm, part-solid <6mm total, non-solid <30mm
• 3   Probably benign — solid 6-7mm, part-solid 6mm+ with solid component <6mm, new non-solid ≥30mm
       → 6-month follow-up LDCT
• 4A  Suspicious — solid 8-14mm; part-solid ≥6mm with solid component 6-7mm; new solid 4-6mm; category 3 growing
       → 3-month follow-up LDCT or PET-CT
• 4B  Very suspicious — solid ≥15mm; any nodule with spiculation; part-solid ≥6mm with solid ≥8mm
       → chest CT ± contrast, PET-CT, tissue sampling
• 4X  Category 4 + additional suspicious features (pleural effusion, adenopathy, mediastinal invasion)
       → chest CT ± contrast, PET-CT, tissue sampling

Fleischner Society (incidental nodules, low-risk patients):
• Solid <6mm     → no follow-up required
• Solid 6-8mm    → 6-12 month CT follow-up
• Solid >8mm     → 3 month CT, PET-CT, or tissue sampling
Subsolid nodules: longer follow-up intervals; consider CT at 3-6 months to assess persistence.

Always respond with valid JSON only — no markdown, no prose outside the JSON object."""


class LungModule(DiagnosisModule):
    cancer_type = "lung"
    display_name = "Lung (Lung-RADS / Nodule)"
    pipeline = "volumetric"

    def segmentation_spec(self) -> SegmentationSpec:
        return SegmentationSpec(
            organ_roi=["lung_upper_lobe_left", "lung_upper_lobe_right",
                       "lung_lower_lobe_left", "lung_lower_lobe_right"],
            lesion_task=None,
            tumor_mask_names=[],
        )

    def rag_query(self, seg, modality: str) -> str:
        return f"lung nodule {modality} Lung-RADS classification management guidelines"

    def system_prompt(self) -> str:
        return _SYSTEM

    def build_prompt(self, seg, modality: str, rag_context: str, radiomics_summary: str, patient_info: Optional[dict]) -> str:
        rag_txt = f"\nRELEVANT GUIDELINE EXCERPTS:\n{rag_context}\n" if rag_context else ""
        pt_txt = f"\nCLINICAL CONTEXT:\n{_json.dumps(patient_info, indent=2)}\n" if patient_info else ""
        feat_txt = f"\nQUANTITATIVE IMAGE ANALYSIS (use to support imaging observations):\n{radiomics_summary}\n" if radiomics_summary else ""

        return f"""Analyse the attached lung imaging and provide a structured Lung-RADS assessment.

MODALITY: {modality}
{pt_txt}{feat_txt}{rag_txt}
{DIFFERENTIAL_INSTRUCTIONS}

Return ONLY valid JSON with this exact structure:
{{
  "overall_impression": "1-2 sentence summary",
  "lesions": [
    {{
      "lesion_id": "N1",
      "location_segment": "Right upper lobe",
      "size_mm": 12.0,
      "score_system": "Lung-RADS",
      "score": "4A",
      "nodule_type": "solid",
      "major_features": ["Spiculated margin", "Upper lobe location"],
      "ancillary_features": ["Pleural tethering"],
      "reasoning": "Detailed reasoning citing Lung-RADS criteria"
    }}
  ],
{DIFFERENTIAL_JSON}
  "staging": "Clinical stage IA (cT1bN0M0) if biopsy confirms NSCLC",
  "recommendations": ["PET-CT for metabolic characterisation", "CT-guided biopsy", "Multidisciplinary thoracic oncology review"],
  "guideline_citations": ["Lung-RADS v2022", "Fleischner Society 2017 Guidelines"]
}}"""

    def parse_report(self, raw: str, modality: str, rag_used: bool, radiomics_summary: str) -> DiagnosticReport:
        data = coerce_json(raw)
        if data is None:
            logger.error("Could not parse lung LLM output as JSON")
            return DiagnosticReport(study_id="", modality=modality, cancer_type="lung",
                                    overall_impression="Analysis complete — see raw output.",
                                    raw_llm_output=raw, rag_context_used=rag_used,
                                    radiomics_summary=radiomics_summary)

        lesions = [
            LesionFinding(
                lesion_id=item.get("lesion_id", "N?"),
                location_segment=item.get("location_segment"),
                size_mm=item.get("size_mm"),
                score_system=item.get("score_system", "Lung-RADS"),
                score=item.get("score"),
                major_features=item.get("major_features", []),
                ancillary_features=item.get("ancillary_features", []),
                reasoning=item.get("reasoning"),
            )
            for item in data.get("lesions", [])
        ]
        diff_assessment, differential = parse_differential(data)
        return DiagnosticReport(
            study_id="", modality=modality, cancer_type="lung",
            overall_impression=data.get("overall_impression", ""),
            lesions=lesions,
            differential_diagnosis=differential,
            differential_assessment=diff_assessment,
            staging=data.get("staging"),
            recommendations=data.get("recommendations", []),
            guideline_citations=data.get("guideline_citations", []),
            raw_llm_output=raw, rag_context_used=rag_used,
        )
