"""Skin cancer module — ABCDE criteria + 7-point dermoscopy checklist.

Works with dermoscopy images or clinical photographs (JPG/PNG).
Uses the image pipeline — no volumetric segmentation required.
"""
from __future__ import annotations

import json as _json
from typing import Optional

from loguru import logger

from core.modules.base import DiagnosisModule
from models.schemas import DiagnosticReport, LesionFinding

_SYSTEM = """You are an expert dermatologist specializing in skin cancer diagnosis using dermoscopy and clinical photography.
You apply ABCDE criteria, the 7-point dermoscopy checklist, and follow NCCN 2024 and AAD guidelines for melanoma and non-melanoma skin cancer.

ABCDE Criteria:
• A (Asymmetry)  — one half does not match the other
• B (Border)     — edges are irregular, ragged, notched, or blurred
• C (Color)      — more than one shade of tan/brown/black, or patches of red, white, or blue
• D (Diameter)   — lesion >6 mm (pencil-eraser size); melanomas can be smaller
• E (Evolution)  — changing in size, shape, color, or new symptoms

7-Point Dermoscopy Checklist (Argenziano):
  Major criteria (2 pts each):
    1. Atypical pigment network (irregular, broadened meshwork)
    2. Blue-white veil (irregular blue-white diffuse pigmentation)
    3. Atypical vascular pattern (dotted, irregular vessels)
  Minor criteria (1 pt each):
    4. Irregular streaks / pseudopods
    5. Irregular dots / globules
    6. Irregular blotches (irregular black/brown/grey areas)
    7. Regression structures (white scar-like areas, blue-grey peppering)
  Score ≥ 3 → suspicious for melanoma; Score < 3 → probably benign

Risk Stratification:
• Low risk (0-2 pts)         — routine surveillance
• Intermediate risk (3-4 pts) — short-term follow-up or excision
• High risk / Suspicious (≥5 pts or any major red flag) — urgent excision

Differential diagnoses include: melanoma, basal cell carcinoma, squamous cell carcinoma,
actinic keratosis, seborrheic keratosis, dysplastic nevus, dermatofibroma, angiokeratoma.

Always respond with valid JSON only — no markdown, no prose outside the JSON object."""


class SkinModule(DiagnosisModule):
    cancer_type = "skin"
    display_name = "Skin (Melanoma / Dermoscopy)"
    pipeline = "image"

    def rag_query(self, seg, modality: str) -> str:
        return "skin cancer melanoma dermoscopy ABCDE criteria diagnosis guidelines"

    def system_prompt(self) -> str:
        return _SYSTEM

    def build_prompt(self, seg, modality: str, rag_context: str, radiomics_summary: str, patient_info: Optional[dict]) -> str:
        rag_txt = f"\nRELEVANT GUIDELINE EXCERPTS:\n{rag_context}\n" if rag_context else ""
        pt_txt = f"\nCLINICAL CONTEXT:\n{_json.dumps(patient_info, indent=2)}\n" if patient_info else ""
        feat_txt = f"\nQUANTITATIVE IMAGE ANALYSIS:\n{radiomics_summary}\n" if radiomics_summary else ""

        return f"""Analyse the attached dermatology image(s) and provide a structured skin cancer assessment.
The image has been preprocessed (colour-constancy normalisation, hair removal, CLAHE contrast enhancement).

IMAGE TYPE: {modality or 'Dermoscopy / Clinical photo'}
{pt_txt}{feat_txt}{rag_txt}
Identify and assess each visible suspicious lesion. Return ONLY valid JSON with this exact structure:
{{
  "overall_impression": "1-2 sentence summary of findings",
  "lesions": [
    {{
      "lesion_id": "L1",
      "location_segment": "anatomical location, e.g. left forearm",
      "size_mm": 8.0,
      "score_system": "7-point dermoscopy",
      "score": "High risk (score 5/7)",
      "risk_level": "high",
      "dermoscopy_score": 5,
      "abcde": {{
        "A_asymmetry": true,
        "B_border": true,
        "C_color": true,
        "D_diameter": true,
        "E_evolution": null
      }},
      "major_features": ["Blue-white veil", "Atypical pigment network"],
      "ancillary_features": ["Irregular dots/globules", "Regression structures"],
      "reasoning": "Detailed dermoscopic reasoning citing specific criteria"
    }}
  ],
  "differential_diagnosis": ["Melanoma (most likely)", "Dysplastic nevus", "Pigmented BCC"],
  "staging": "Possible pT1a (Breslow <1mm estimated) if melanoma confirmed on histology",
  "recommendations": [
    "Urgent excisional biopsy with 2mm margins",
    "Histopathological Breslow thickness measurement",
    "Sentinel lymph node biopsy if melanoma confirmed ≥0.8mm"
  ],
  "guideline_citations": ["NCCN Melanoma v3.2024", "AAD Melanoma Guidelines 2024"]
}}"""

    def parse_report(self, raw: str, modality: str, rag_used: bool, radiomics_summary: str) -> DiagnosticReport:
        json_str = raw.strip()
        for fence in ("```json", "```"):
            if json_str.startswith(fence):
                json_str = json_str[len(fence):]
                if "```" in json_str:
                    json_str = json_str[: json_str.index("```")]
                break

        try:
            data = _json.loads(json_str)
        except _json.JSONDecodeError:
            try:
                s, e = raw.index("{"), raw.rindex("}") + 1
                data = _json.loads(raw[s:e])
            except Exception:
                logger.error("Could not parse skin LLM output as JSON")
                return DiagnosticReport(
                    study_id="", modality=modality, cancer_type="skin",
                    overall_impression="Analysis complete — see raw output.",
                    raw_llm_output=raw, rag_context_used=rag_used,
                )

        lesions: list[LesionFinding] = []
        for item in data.get("lesions", []):
            risk = item.get("risk_level", "unknown").lower()
            lesions.append(LesionFinding(
                lesion_id=item.get("lesion_id", "L?"),
                location_segment=item.get("location_segment"),
                size_mm=item.get("size_mm"),
                score_system=item.get("score_system", "7-point dermoscopy"),
                score=item.get("score", risk),
                major_features=item.get("major_features", []),
                ancillary_features=item.get("ancillary_features", []),
                reasoning=item.get("reasoning"),
            ))

        return DiagnosticReport(
            study_id="", modality=modality or "Dermoscopy", cancer_type="skin",
            overall_impression=data.get("overall_impression", ""),
            lesions=lesions,
            differential_diagnosis=data.get("differential_diagnosis", []),
            staging=data.get("staging"),
            recommendations=data.get("recommendations", []),
            guideline_citations=data.get("guideline_citations", []),
            raw_llm_output=raw, rag_context_used=rag_used,
        )
