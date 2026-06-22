"""Liver cancer (HCC) module — LI-RADS v2024 / BCLC.

Extracts the logic that was previously hardcoded in core/llm_client.py
into the DiagnosisModule protocol so the pipeline is cancer-type-agnostic.
"""
from __future__ import annotations

import json
from typing import Optional

from core.modules.base import (
    DIFFERENTIAL_INSTRUCTIONS, DIFFERENTIAL_JSON, DiagnosisModule, SegmentationSpec,
    coerce_json, parse_differential,
)
from models.schemas import DiagnosticReport, LesionFinding, LiRadsCategory

_LIRADS_MAP = {
    "LR-1":          LiRadsCategory.LR_1,
    "LR-2":          LiRadsCategory.LR_2,
    "LR-3":          LiRadsCategory.LR_3,
    "LR-4":          LiRadsCategory.LR_4,
    "LR-5":          LiRadsCategory.LR_5,
    "LR-M":          LiRadsCategory.LR_M,
    "LR-TIV":        LiRadsCategory.LR_TIV,
}

_SYSTEM = """You are an expert hepatic radiologist with deep expertise in liver cancer diagnosis using CT and MRI.
You apply LI-RADS v2024 criteria precisely and follow AASLD 2023 and ESMO clinical guidelines.

LI-RADS v2024 Category Reference (HCC on CT/MRI):
• LR-1   Definitely benign — cyst, haemangioma, focal fat deposition
• LR-2   Probably benign — nodule <10 mm with no major features
• LR-3   Intermediate — ≥10 mm with ≤1 major feature, or <10 mm with major feature
• LR-4   Probably HCC — ≥10 mm APHE + one of {washout, capsule, threshold growth ≥50% in 6 months}
• LR-5   Definitely HCC — ≥20 mm APHE + {washout or capsule}; OR ≥10 mm with APHE + washout + capsule
• LR-M   Probably/definitely malignant, NOT HCC-specific — spiculated margin, targetoid enhancement,
          rim APHE, marked DWI restriction, necrosis, heterogeneous; consider CCA or metastasis
• LR-TIV Tumour in vein — definite or probable soft tissue in portal/hepatic vein matching liver lesion

Major features: APHE (arterial phase hyperenhancement), washout appearance, enhancing capsule.
Ancillary features favoring HCC: T2 mild hyperintensity, mosaic architecture, fat in mass, blood products,
hepatobiliary phase (HBP) hypointensity, DWI restricted diffusion, mild-moderate T2 signal.

BCLC Staging Guide (assign based on lesion count, size, vascular invasion, performance status):
• BCLC-0  Single ≤2 cm, PS 0, preserved liver function
• BCLC-A  Single any size OR ≤3 nodules ≤3 cm each, PS 0, Child-Pugh A/B
• BCLC-B  Multinodular (>3 or >3 cm), no vascular invasion/extrahepatic spread, PS 0-1
• BCLC-C  Vascular invasion (portal vein tumour thrombus) or extrahepatic spread, PS 1-2
• BCLC-D  Severe liver dysfunction or PS 3-4
If patient context is unavailable, assign based solely on imaging findings (size, count, vascular invasion).

For MRI: assess DWI restricted diffusion, hepatobiliary phase hypointensity (HBP), T2 signal intensity.
When quantitative radiomics are provided, use shape features (sphericity, diameter) to support morphologic
observations, and texture features (entropy, contrast, coarseness) to comment on lesion heterogeneity.
Reference specific radiomics values in the reasoning field where they support the imaging diagnosis.
Always respond with valid JSON only — no markdown, no prose outside the JSON object."""


class LiverModule(DiagnosisModule):
    cancer_type = "liver"
    display_name = "Liver (HCC / LI-RADS)"
    pipeline = "volumetric"

    def segmentation_spec(self) -> SegmentationSpec:
        return SegmentationSpec(
            organ_roi=["liver"],
            lesion_task="liver_lesions",
            tumor_mask_names=[
                "liver_lesions.nii.gz", "liver_tumor.nii.gz",
                "liver_tumour.nii.gz", "hepatic_tumor.nii.gz",
            ],
        )

    def rag_query(self, seg, modality: str) -> str:
        if seg.lesions:
            return f"{seg.lesions[0].size_mm:.0f}mm liver lesion {modality} LI-RADS assessment"
        return f"liver imaging {modality} LI-RADS HCC assessment"

    def system_prompt(self) -> str:
        return _SYSTEM

    def build_prompt(self, seg, modality, rag_context, radiomics_summary, patient_info) -> str:
        lesion_txt = "\n".join(
            f"  • {l.lesion_id}: {l.size_mm} mm max diameter, {l.volume_ml:.2f} mL"
            for l in seg.lesions
        ) or "  No discrete lesions detected by automated segmentation (review images carefully)"

        rag_txt = f"\nRELEVANT GUIDELINE EXCERPTS:\n{rag_context}\n" if rag_context else ""
        pt_txt = f"\nCLINICAL CONTEXT:\n{json.dumps(patient_info, indent=2)}\n" if patient_info else ""
        rad_available = radiomics_summary and not radiomics_summary.startswith("Feature extraction unavailable")
        rad_txt = (
            f"\nQUANTITATIVE RADIOMICS (use to support imaging observations):\n{radiomics_summary}\n"
            if rad_available else ""
        )

        return f"""Analyse the attached multi-phase liver imaging montage and provide a structured diagnostic report.

MODALITY: {modality}
LIVER VOLUME: {seg.liver_volume_ml:.0f} mL
{pt_txt}
AUTOMATED SEGMENTATION:
{lesion_txt}
{rad_txt}{rag_txt}
{DIFFERENTIAL_INSTRUCTIONS}

Return ONLY valid JSON with this exact structure:
{{
  "overall_impression": "1-2 sentence summary",
  "lesions": [
    {{
      "lesion_id": "L1",
      "location_segment": "Segment VI",
      "size_mm": 28.0,
      "lirads_category": "LR-4",
      "aphe_present": true,
      "washout_present": true,
      "capsule_present": false,
      "diffusion_restriction": null,
      "major_features": ["Arterial phase hyperenhancement", "Washout appearance"],
      "ancillary_features": [],
      "reasoning": "Concise rationale citing specific LI-RADS criteria"
    }}
  ],
{DIFFERENTIAL_JSON}
  "bclc_stage": "BCLC-A",
  "vascular_involvement": "No portal vein tumour thrombus",
  "recommendations": ["Multidisciplinary tumour board review", "AFP / AFP-L3 serology"],
  "guideline_citations": ["LI-RADS v2024 Section 4.2", "AASLD 2023 HCC Guidance §5.1"]
}}"""

    def parse_report(self, raw: str, modality: str, rag_used: bool, radiomics_summary: str) -> DiagnosticReport:
        from loguru import logger

        data = coerce_json(raw)
        if data is None:
            logger.error("Could not parse LLM output as JSON")
            return DiagnosticReport(
                study_id="", modality=modality, cancer_type="liver",
                overall_impression="Analysis complete — see raw output.",
                raw_llm_output=raw, rag_context_used=rag_used,
                radiomics_summary=radiomics_summary,
            )

        lesions: list[LesionFinding] = []
        for item in data.get("lesions", []):
            cat = _LIRADS_MAP.get(item.get("lirads_category", ""), LiRadsCategory.INDETERMINATE)
            lesions.append(LesionFinding(
                lesion_id=item.get("lesion_id", "L?"),
                location_segment=item.get("location_segment"),
                size_mm=item.get("size_mm"),
                lirads_category=cat,
                score_system="LI-RADS",
                score=item.get("lirads_category", "Indeterminate"),
                aphe_present=item.get("aphe_present"),
                washout_present=item.get("washout_present"),
                capsule_present=item.get("capsule_present"),
                diffusion_restriction=item.get("diffusion_restriction"),
                major_features=item.get("major_features", []),
                ancillary_features=item.get("ancillary_features", []),
                reasoning=item.get("reasoning"),
            ))

        diff_assessment, differential = parse_differential(data)
        return DiagnosticReport(
            study_id="", modality=modality, cancer_type="liver",
            overall_impression=data.get("overall_impression", ""),
            lesions=lesions,
            differential_diagnosis=differential,
            differential_assessment=diff_assessment,
            bclc_stage=data.get("bclc_stage"),
            vascular_involvement=data.get("vascular_involvement"),
            recommendations=data.get("recommendations", []),
            guideline_citations=data.get("guideline_citations", []),
            raw_llm_output=raw, rag_context_used=rag_used,
            radiomics_summary=radiomics_summary,
        )
