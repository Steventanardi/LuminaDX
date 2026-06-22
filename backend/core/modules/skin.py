"""Skin cancer module — ABCDE criteria + 7-point dermoscopy checklist.

Works with dermoscopy images or clinical photographs (JPG/PNG).
Uses the image pipeline — no volumetric segmentation required.
"""
from __future__ import annotations

import json as _json
from typing import Optional

from loguru import logger

from core.modules.base import DiagnosisModule, coerce_json, parse_differential
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
Any image preprocessing that was applied is stated at the END of this prompt — do not assume
enhancement (colour constancy, hair removal, CLAHE) that is not explicitly listed there.

IMAGE TYPE: {modality or 'Dermoscopy / Clinical photo'}
{pt_txt}{feat_txt}{rag_txt}
If more than one image is attached, assess every image; treat each as a separate
lesion/view and record which one it is in "location_segment" (e.g. "Image 2 — left
forearm"). Per-image quantitative metrics, when present, are labelled "Image N" above.
Identify and assess each visible suspicious lesion.

PRECISION REQUIREMENTS — be specific, not vague:
• Build a RANKED differential (most likely first, 2–4 candidates). For EACH candidate
  give the evidence FOR it ("supporting_features") and AGAINST it ("opposing_features").
• Cite ONLY features that are actually visible in the image or appear in the
  QUANTITATIVE IMAGE ANALYSIS above (ABCDE flags, TDS, 7-point items, measured
  asymmetry/border/colour, the trained-classifier probabilities). Do NOT invent findings.
  If there is no opposing evidence, write ["none significant"].
• Set each candidate's "likelihood" to "high" / "moderate" / "low" and keep it
  CONSISTENT with the trained HAM10000 classifier's malignancy probability when one is
  provided above: if malignancy probability ≥ 60%%, at least one malignant diagnosis
  (melanoma / BCC / SCC / actinic keratosis) must be "high"; if ≤ 20%%, malignant
  diagnoses should be "low". If the classifier and the dermoscopic features disagree,
  say so explicitly in that candidate's reasoning.
• If the trained classifier reports a SCREENING FLAG of "URGENT" (its melanoma/malignancy
  probability cleared the safety threshold), treat at least one malignant diagnosis as
  "moderate" or higher and include urgent excisional biopsy in the recommendations — even
  when a benign diagnosis is most likely. Missing a melanoma is the costly error.

Return ONLY valid JSON with the structure below. The values shown are FIELD
DESCRIPTIONS inside angle brackets, NOT a sample answer — fill EVERY field from
THIS specific image and the QUANTITATIVE IMAGE ANALYSIS above. Do NOT copy the
placeholder text, and do NOT default to melanoma: the most likely diagnosis must
follow the trained classifier's top class and the features you actually observe.
{{
  "overall_impression": "<1-2 sentences grounded in what you see in THIS image and the classifier's top class + probability>",
  "lesions": [
    {{
      "lesion_id": "L1",
      "location_segment": "<anatomical site, or 'Image N — <site>' for multiple views>",
      "size_mm": "<numeric estimate, or null if not estimable>",
      "score_system": "7-point dermoscopy",
      "score": "<e.g. 'Low risk (score 1/7)' — reflect the ACTUAL criteria count>",
      "risk_level": "<low | moderate | high>",
      "dermoscopy_score": "<integer 0-7 = number of 7-point criteria actually present>",
      "abcde": {{
        "A_asymmetry": "<true | false | null>",
        "B_border": "<true | false | null>",
        "C_color": "<true | false | null>",
        "D_diameter": "<true | false | null>",
        "E_evolution": null
      }},
      "major_features": ["<only 7-point major criteria actually visible; [] if none>"],
      "ancillary_features": ["<only minor/ancillary features actually visible; [] if none>"],
      "reasoning": "<dermoscopic reasoning citing the SPECIFIC criteria you observed and how they agree/disagree with the classifier>"
    }}
  ],
  "differential_assessment": [
    {{
      "diagnosis": "<candidate diagnosis; list 2-4, MOST LIKELY FIRST, consistent with the classifier's ranking>",
      "likelihood": "<high | moderate | low>",
      "supporting_features": ["<evidence FOR, from the image / measured metrics / classifier probabilities>"],
      "opposing_features": ["<evidence AGAINST, or 'none significant'>"]
    }}
  ],
  "staging": "<staging note if a malignancy is plausible, else null>",
  "recommendations": ["<management steps appropriate to the assessed risk level>"],
  "guideline_citations": ["<relevant guideline(s) you applied, e.g. NCCN/AAD>"]
}}"""

    def parse_report(self, raw: str, modality: str, rag_used: bool, radiomics_summary: str) -> DiagnosticReport:
        data = coerce_json(raw)
        if data is None:
            logger.error("Could not parse skin LLM output as JSON")
            return DiagnosticReport(
                study_id="", modality=modality, cancer_type="skin",
                overall_impression="Analysis complete — see raw output.",
                raw_llm_output=raw, rag_context_used=rag_used,
                radiomics_summary=radiomics_summary,
            )

        lesions: list[LesionFinding] = []
        for item in data.get("lesions", []):
            risk = item.get("risk_level", "unknown").lower()
            ds = item.get("dermoscopy_score")
            try:
                ds = int(ds) if ds is not None else None
            except (TypeError, ValueError):
                ds = None
            abcde = item.get("abcde")
            if not isinstance(abcde, dict):
                abcde = None
            lesions.append(LesionFinding(
                lesion_id=item.get("lesion_id", "L?"),
                location_segment=item.get("location_segment"),
                size_mm=item.get("size_mm"),
                score_system=item.get("score_system", "7-point dermoscopy"),
                score=item.get("score", risk),
                dermoscopy_score=ds,
                abcde=abcde,
                major_features=item.get("major_features", []),
                ancillary_features=item.get("ancillary_features", []),
                reasoning=item.get("reasoning"),
            ))

        diff_assessment, differential = parse_differential(data)

        return DiagnosticReport(
            study_id="", modality=modality or "Dermoscopy", cancer_type="skin",
            overall_impression=data.get("overall_impression", ""),
            lesions=lesions,
            differential_diagnosis=differential,
            differential_assessment=diff_assessment,
            staging=data.get("staging"),
            recommendations=data.get("recommendations", []),
            guideline_citations=data.get("guideline_citations", []),
            raw_llm_output=raw, rag_context_used=rag_used,
        )
