"""Colorectal cancer module — C-RADS / CT colonography + TNM staging."""
from __future__ import annotations

import json as _json
from typing import Optional

from loguru import logger

from core.modules.base import DiagnosisModule
from models.schemas import DiagnosticReport, LesionFinding

_SYSTEM = """You are an expert abdominal radiologist specializing in colorectal cancer detection using CT colonography (CTC) and CT staging.
You apply C-RADS (CT Colonography Reporting and Data System) categories and TNM staging (AJCC 8th edition).

C-RADS Assessment Categories (for polyps on CT colonography):
• C0  Inadequate study — poor bowel prep, technical issues; repeat CTC
• C1  Normal colon / benign lesion — no polyp, or hyperplastic polyp ≤5mm; routine screening
• C2  Intermediate polyp — 6-9mm polyp; 3-year follow-up CTC or colonoscopy
• C3  Polyp, possibly advanced adenoma — ≥10mm polyp; colonoscopy recommended
• C4  Colonic mass, likely malignant — colonoscopy with biopsy; surgical evaluation

TNM Colorectal Cancer Staging (AJCC 8th):
• T1  Tumour invades submucosa
• T2  Tumour invades muscularis propria
• T3  Tumour invades through muscularis propria into pericolorectal tissues
• T4a Tumour penetrates to surface of visceral peritoneum
• T4b Tumour directly invades or adherent to adjacent organs/structures
• N0  No regional lymph node metastasis
• N1  1-3 regional lymph nodes positive
• N2  ≥4 regional lymph nodes positive
• M0  No distant metastasis; M1a one site; M1b more than one site; M1c peritoneal metastasis

Key imaging features of colorectal malignancy:
Irregular mucosal mass, apple-core lesion, bowel wall thickening >3mm (asymmetric),
pericolonic fat stranding, lymphadenopathy >8mm short axis, adjacent organ invasion, liver/lung metastases.

Always respond with valid JSON only — no markdown, no prose outside the JSON object."""


class ColorectalModule(DiagnosisModule):
    cancer_type = "colorectal"
    display_name = "Colorectal (C-RADS / TNM)"
    pipeline = "volumetric"

    def rag_query(self, seg, modality: str) -> str:
        return f"colorectal cancer {modality} CT colonography C-RADS diagnosis staging guidelines"

    def system_prompt(self) -> str:
        return _SYSTEM

    def build_prompt(self, seg, modality: str, rag_context: str, radiomics_summary: str, patient_info: Optional[dict]) -> str:
        rag_txt = f"\nRELEVANT GUIDELINE EXCERPTS:\n{rag_context}\n" if rag_context else ""
        pt_txt = f"\nCLINICAL CONTEXT:\n{_json.dumps(patient_info, indent=2)}\n" if patient_info else ""

        return f"""Analyse the attached colorectal imaging and provide a structured C-RADS / staging assessment.

MODALITY: {modality}
{pt_txt}{rag_txt}
Return ONLY valid JSON with this exact structure:
{{
  "overall_impression": "1-2 sentence summary",
  "lesions": [
    {{
      "lesion_id": "P1",
      "location_segment": "Sigmoid colon",
      "size_mm": 22.0,
      "score_system": "C-RADS",
      "score": "C4",
      "major_features": ["Irregular mucosal mass", "Transmural wall thickening"],
      "ancillary_features": ["Pericolonic fat stranding", "Regional lymphadenopathy"],
      "reasoning": "Detailed reasoning citing C-RADS criteria and TNM staging"
    }}
  ],
  "differential_diagnosis": ["Colorectal adenocarcinoma (most likely)", "Diverticular phlegmon", "Lymphoma"],
  "staging": "cT3N1M0 (Stage IIIB) — tumour through muscularis propria, 2 regional nodes, no distant metastasis",
  "recommendations": [
    "Colonoscopy with biopsy for histological confirmation",
    "MRI rectum for rectal tumours (T-staging, mesorectal fascia involvement)",
    "Staging CT chest/abdomen/pelvis for distant metastasis",
    "Colorectal multidisciplinary team review"
  ],
  "guideline_citations": ["C-RADS 2005 (Zalis et al)", "AJCC Cancer Staging Manual 8th Edition", "ESMO CRC Guidelines 2023"]
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
        except Exception:
            try:
                s, e = raw.index("{"), raw.rindex("}") + 1
                data = _json.loads(raw[s:e])
            except Exception:
                logger.error("Could not parse colorectal LLM output as JSON")
                return DiagnosticReport(study_id="", modality=modality, cancer_type="colorectal",
                                        overall_impression="Analysis complete — see raw output.",
                                        raw_llm_output=raw, rag_context_used=rag_used)

        lesions = [
            LesionFinding(
                lesion_id=item.get("lesion_id", "P?"),
                location_segment=item.get("location_segment"),
                size_mm=item.get("size_mm"),
                score_system=item.get("score_system", "C-RADS"),
                score=item.get("score"),
                major_features=item.get("major_features", []),
                ancillary_features=item.get("ancillary_features", []),
                reasoning=item.get("reasoning"),
            )
            for item in data.get("lesions", [])
        ]
        return DiagnosticReport(
            study_id="", modality=modality, cancer_type="colorectal",
            overall_impression=data.get("overall_impression", ""),
            lesions=lesions,
            differential_diagnosis=data.get("differential_diagnosis", []),
            staging=data.get("staging"),
            recommendations=data.get("recommendations", []),
            guideline_citations=data.get("guideline_citations", []),
            raw_llm_output=raw, rag_context_used=rag_used,
        )
