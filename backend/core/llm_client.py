"""LLM client — delegates prompt building and response parsing to each cancer module."""
from __future__ import annotations

import base64
from pathlib import Path
from typing import Optional, Union, TYPE_CHECKING

from loguru import logger
from openai import AsyncOpenAI

from config import settings
from core.segmentation import SegmentationResult
from models.schemas import DiagnosticReport

if TYPE_CHECKING:
    from core.modules.base import DiagnosisModule


class LLMClient:
    def __init__(self) -> None:
        self._client = AsyncOpenAI(
            base_url=f"{settings.ollama_base_url}/v1",
            api_key="ollama",
        )

    async def analyze(
        self,
        montage_path: Union[Path, list[Path]],
        seg: SegmentationResult,
        modality: str,
        rag_context: str = "",
        radiomics_summary: str = "",
        patient_info: Optional[dict] = None,
        module: Optional["DiagnosisModule"] = None,
        model: Optional[str] = None,
        applied_preprocessing: Optional[list[str]] = None,
    ) -> DiagnosticReport:
        if module is None:
            from core.modules.liver import LiverModule
            module = LiverModule()

        model_tag = model or settings.llm_model
        # Accept a single image or several (skin can submit multiple lesion views).
        paths = montage_path if isinstance(montage_path, list) else [montage_path]
        paths = [p for p in paths if p is not None]
        logger.info(
            f"Calling LLM ({model_tag}) for cancer_type={module.cancer_type} "
            f"with {len(paths)} image(s) …"
        )

        image_blocks = []
        for p in paths:
            with open(p, "rb") as fh:
                b64 = base64.b64encode(fh.read()).decode()
            image_blocks.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/png;base64,{b64}", "detail": "high"},
            })

        system_msg = module.system_prompt()
        user_prompt = module.build_prompt(seg, modality, rag_context, radiomics_summary, patient_info)

        # State exactly which enhancement steps actually ran (or that none did), so the
        # prompt never claims preprocessing the user toggled off. Caller passes None to
        # opt out of this note entirely (e.g. volumetric pipelines).
        if applied_preprocessing is not None:
            if applied_preprocessing:
                user_prompt += ("\n\nIMAGE PREPROCESSING (applied before you see the image): "
                                + ", ".join(applied_preprocessing) + ".")
            else:
                user_prompt += ("\n\nIMAGE PREPROCESSING: none — you are viewing the original, "
                                "unenhanced image(s).")

        response = await self._client.chat.completions.create(
            model=model_tag,
            messages=[
                {"role": "system", "content": system_msg},
                {"role": "user", "content": [*image_blocks, {"type": "text", "text": user_prompt}]},
            ],
            temperature=0.05,
            max_tokens=2048,
        )

        raw = response.choices[0].message.content or ""
        logger.info(f"LLM returned {len(raw)} chars")
        return module.parse_report(raw, modality, bool(rag_context), radiomics_summary)


llm_client = LLMClient()
