"""Breast cancer module — BI-RADS (ACR 2013) / mammography + ultrasound."""
from __future__ import annotations

import json as _json
from typing import Optional

from loguru import logger

from core.modules.base import (
    DIFFERENTIAL_INSTRUCTIONS, DIFFERENTIAL_JSON, DiagnosisModule, coerce_json, parse_differential,
)
from models.schemas import DiagnosticReport, LesionFinding

_SYSTEM = """You are an expert breast radiologist specializing in breast cancer detection using mammography, ultrasound, and MRI.
You apply ACR BI-RADS 5th edition (2013) criteria and follow NCCN Breast Cancer Screening and ACR Practice Parameters.

ACR BI-RADS Assessment Categories:
• 0   Incomplete — additional imaging needed
• 1   Negative — no significant finding; routine screening
• 2   Benign — definitely benign finding; routine screening
• 3   Probably benign — ≤2% malignancy risk; 6-month follow-up
• 4A  Low suspicion — >2% but ≤10%; tissue diagnosis
• 4B  Moderate suspicion — >10% but ≤50%; tissue diagnosis
• 4C  High suspicion — >50% but <95%; tissue diagnosis
• 5   Highly suggestive of malignancy — ≥95% probability; tissue diagnosis / surgical consult
• 6   Biopsy-proven malignancy — staging

Key mammographic features suggesting malignancy:
Masses: irregular shape, spiculated margin, high density
Calcifications: pleomorphic/fine linear/fine linear branching distribution; segmental/linear/grouped
Asymmetries: developing asymmetry, focal asymmetry with associated findings
Architectural distortion

Ultrasound features:
Suspicious: irregular shape, non-parallel orientation (taller-than-wide), angular/spiculated/microlobulated margin,
heterogeneous echo texture, posterior acoustic shadowing, calcifications, duct extension/branch pattern,
thickened Cooper's ligaments, lymph node changes

Always respond with valid JSON only — no markdown, no prose outside the JSON object."""


class BreastModule(DiagnosisModule):
    cancer_type = "breast"
    display_name = "Breast (BI-RADS)"
    pipeline = "image"

    def rag_query(self, seg, modality: str) -> str:
        return f"breast cancer {modality} BI-RADS mammography diagnosis guidelines"

    def system_prompt(self) -> str:
        return _SYSTEM

    def build_prompt(self, seg, modality: str, rag_context: str, radiomics_summary: str, patient_info: Optional[dict]) -> str:
        rag_txt = f"\nRELEVANT GUIDELINE EXCERPTS:\n{rag_context}\n" if rag_context else ""
        pt_txt = f"\nCLINICAL CONTEXT:\n{_json.dumps(patient_info, indent=2)}\n" if patient_info else ""
        feat_txt = f"\nQUANTITATIVE IMAGE ANALYSIS:\n{radiomics_summary}\n" if radiomics_summary else ""

        return f"""Analyse the attached breast imaging and provide a structured BI-RADS assessment.
The image has been preprocessed with CLAHE contrast enhancement to accentuate masses, calcifications and architectural distortion.

MODALITY: {modality or 'Mammography / Ultrasound'}
{pt_txt}{feat_txt}{rag_txt}
{DIFFERENTIAL_INSTRUCTIONS}

Return ONLY valid JSON with this exact structure:
{{
  "overall_impression": "1-2 sentence summary",
  "lesions": [
    {{
      "lesion_id": "M1",
      "location_segment": "Right breast upper outer quadrant, 10 o'clock, 5cm from nipple",
      "size_mm": 15.0,
      "score_system": "BI-RADS",
      "score": "4B",
      "major_features": ["Irregular spiculated mass", "High density"],
      "ancillary_features": ["Architectural distortion", "Skin thickening"],
      "reasoning": "Detailed reasoning citing BI-RADS criteria"
    }}
  ],
{DIFFERENTIAL_JSON}
  "staging": "Clinical stage II (cT2N0M0 pending nodal assessment) if malignancy confirmed",
  "recommendations": [
    "Ultrasound-guided core needle biopsy",
    "Axillary ultrasound for nodal staging",
    "MRI breast for surgical planning if biopsy confirms malignancy"
  ],
  "guideline_citations": ["ACR BI-RADS 5th Edition 2013", "NCCN Breast Cancer Screening v1.2024"]
}}"""

    def parse_report(self, raw: str, modality: str, rag_used: bool, radiomics_summary: str) -> DiagnosticReport:
        data = coerce_json(raw)
        if data is None:
            logger.error("Could not parse breast LLM output as JSON")
            return DiagnosticReport(study_id="", modality=modality, cancer_type="breast",
                                    overall_impression="Analysis complete — see raw output.",
                                    raw_llm_output=raw, rag_context_used=rag_used,
                                    radiomics_summary=radiomics_summary)

        lesions = [
            LesionFinding(
                lesion_id=item.get("lesion_id", "M?"),
                location_segment=item.get("location_segment"),
                size_mm=item.get("size_mm"),
                score_system=item.get("score_system", "BI-RADS"),
                score=item.get("score"),
                major_features=item.get("major_features", []),
                ancillary_features=item.get("ancillary_features", []),
                reasoning=item.get("reasoning"),
            )
            for item in data.get("lesions", [])
        ]
        diff_assessment, differential = parse_differential(data)
        return DiagnosticReport(
            study_id="", modality=modality or "Mammography", cancer_type="breast",
            overall_impression=data.get("overall_impression", ""),
            lesions=lesions,
            differential_diagnosis=differential,
            differential_assessment=diff_assessment,
            staging=data.get("staging"),
            recommendations=data.get("recommendations", []),
            guideline_citations=data.get("guideline_citations", []),
            raw_llm_output=raw, rag_context_used=rag_used,
        )
