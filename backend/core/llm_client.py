"""LLM client — delegates prompt building and response parsing to each cancer module."""
from __future__ import annotations

import base64
from pathlib import Path
from typing import Optional, TYPE_CHECKING

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
        montage_path: Path,
        seg: SegmentationResult,
        modality: str,
        rag_context: str = "",
        radiomics_summary: str = "",
        patient_info: Optional[dict] = None,
        module: Optional["DiagnosisModule"] = None,
    ) -> DiagnosticReport:
        if module is None:
            from core.modules.liver import LiverModule
            module = LiverModule()

        logger.info(f"Calling LLM ({settings.llm_model}) for cancer_type={module.cancer_type} …")

        with open(montage_path, "rb") as fh:
            b64 = base64.b64encode(fh.read()).decode()

        system_msg = module.system_prompt()
        user_prompt = module.build_prompt(seg, modality, rag_context, radiomics_summary, patient_info)

        response = await self._client.chat.completions.create(
            model=settings.llm_model,
            messages=[
                {"role": "system", "content": system_msg},
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
                        {"type": "text", "text": user_prompt},
                    ],
                },
            ],
            temperature=0.05,
            max_tokens=2048,
        )

        raw = response.choices[0].message.content or ""
        logger.info(f"LLM returned {len(raw)} chars")
        return module.parse_report(raw, modality, bool(rag_context), radiomics_summary)


llm_client = LLMClient()
