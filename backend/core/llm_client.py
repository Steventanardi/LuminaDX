from __future__ import annotations

import base64
import json
from pathlib import Path
from typing import Optional

from loguru import logger
from openai import AsyncOpenAI

from config import settings
from core.segmentation import SegmentationResult
from models.schemas import DiagnosticReport, LesionFinding, LiRadsCategory

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

_LIRADS_MAP = {
    "LR-1": LiRadsCategory.LR_1,
    "LR-2": LiRadsCategory.LR_2,
    "LR-3": LiRadsCategory.LR_3,
    "LR-4": LiRadsCategory.LR_4,
    "LR-5": LiRadsCategory.LR_5,
    "LR-M": LiRadsCategory.LR_M,
    "LR-TIV": LiRadsCategory.LR_TIV,
}


def _build_prompt(
    seg: SegmentationResult,
    modality: str,
    rag_context: str,
    radiomics_summary: str,
    patient_info: Optional[dict],
) -> str:
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
  "differential_diagnosis": ["HCC (most likely)", "Dysplastic nodule"],
  "bclc_stage": "BCLC-A",
  "vascular_involvement": "No portal vein tumour thrombus",
  "recommendations": ["Multidisciplinary tumour board review", "AFP / AFP-L3 serology"],
  "guideline_citations": ["LI-RADS v2024 Section 4.2", "AASLD 2023 HCC Guidance §5.1"]
}}"""


class LLMClient:
    def __init__(self) -> None:
        self._client = AsyncOpenAI(
            base_url=f"{settings.ollama_base_url}/v1",
            api_key="ollama",
        )

    async def analyze(
        self,
        montage_path: Path,
        seg: SegmentationResult,
        modality: str,
        rag_context: str = "",
        radiomics_summary: str = "",
        patient_info: Optional[dict] = None,
    ) -> DiagnosticReport:
        logger.info(f"Calling LLM ({settings.llm_model}) …")

        with open(montage_path, "rb") as fh:
            b64 = base64.b64encode(fh.read()).decode()

        prompt = _build_prompt(seg, modality, rag_context, radiomics_summary, patient_info)

        response = await self._client.chat.completions.create(
            model=settings.llm_model,
            messages=[
                {"role": "system", "content": _SYSTEM},
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{b64}",
                                "detail": "high",
                            },
                        },
                        {"type": "text", "text": prompt},
                    ],
                },
            ],
            temperature=0.05,
            max_tokens=2048,
        )

        raw = response.choices[0].message.content or ""
        logger.info(f"LLM returned {len(raw)} chars")
        return self._parse(raw, modality, bool(rag_context), radiomics_summary)

    def _parse(
        self,
        raw: str,
        modality: str,
        rag_used: bool,
        radiomics_summary: str,
    ) -> DiagnosticReport:
        json_str = raw.strip()
        # Strip markdown code fences if present
        for fence in ("```json", "```"):
            if json_str.startswith(fence):
                json_str = json_str[len(fence):]
                if "```" in json_str:
                    json_str = json_str[: json_str.index("```")]
                break

        try:
            data = json.loads(json_str)
        except json.JSONDecodeError:
            # Last resort: find the outermost {...}
            try:
                s, e = raw.index("{"), raw.rindex("}") + 1
                data = json.loads(raw[s:e])
            except Exception:
                logger.error("Could not parse LLM output as JSON")
                return DiagnosticReport(
                    study_id="",
                    modality=modality,
                    overall_impression="Analysis complete — see raw output.",
                    raw_llm_output=raw,
                    rag_context_used=rag_used,
                    radiomics_summary=radiomics_summary,
                )

        lesions: list[LesionFinding] = []
        for item in data.get("lesions", []):
            cat = _LIRADS_MAP.get(item.get("lirads_category", ""), LiRadsCategory.INDETERMINATE)
            lesions.append(
                LesionFinding(
                    lesion_id=item.get("lesion_id", "L?"),
                    location_segment=item.get("location_segment"),
                    size_mm=item.get("size_mm"),
                    lirads_category=cat,
                    aphe_present=item.get("aphe_present"),
                    washout_present=item.get("washout_present"),
                    capsule_present=item.get("capsule_present"),
                    diffusion_restriction=item.get("diffusion_restriction"),
                    major_features=item.get("major_features", []),
                    ancillary_features=item.get("ancillary_features", []),
                    reasoning=item.get("reasoning"),
                )
            )

        return DiagnosticReport(
            study_id="",
            modality=modality,
            overall_impression=data.get("overall_impression", ""),
            lesions=lesions,
            differential_diagnosis=data.get("differential_diagnosis", []),
            bclc_stage=data.get("bclc_stage"),
            vascular_involvement=data.get("vascular_involvement"),
            recommendations=data.get("recommendations", []),
            guideline_citations=data.get("guideline_citations", []),
            raw_llm_output=raw,
            rag_context_used=rag_used,
            radiomics_summary=radiomics_summary,
        )


llm_client = LLMClient()
