"""
Run once to load medical guidelines into the RAG vector store.

Place these PDFs in backend/data/knowledge_base/ before running:
  1. LI-RADS 2024 CT/MRI  →  https://www.acr.org/Clinical-Resources/Reporting-and-Data-Systems/LI-RADS
  2. AASLD HCC Guidance    →  https://www.aasld.org/liver-disease-guidelines
  3. ESMO Liver Guidelines →  https://www.esmo.org/guidelines/gastrointestinal-cancers
  4. NCCN Hepatobiliary    →  https://www.nccn.org/guidelines  (free registration)
  5. BCLC Staging          →  Search "BCLC 2022 update" on pubmed/EASL

Usage:
  cd scripts
  python ingest_guidelines.py
"""
import sys
import asyncio
import warnings
from pathlib import Path

warnings.filterwarnings("ignore", message="Advanced encoding.*not implemented")
warnings.filterwarnings("ignore", category=DeprecationWarning, module="asyncio")

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))

from config import settings
from core.rag_engine import rag_engine


async def main() -> None:
    kb = settings.knowledge_base_dir
    pdfs = list(kb.glob("*.pdf"))

    if not pdfs:
        print(f"\nNo PDFs found in: {kb}\n")
        print("Download and save the following guidelines as PDFs there:")
        print("  • ACR LI-RADS v2024 CT/MRI document")
        print("  • AASLD HCC Practice Guidance (2023)")
        print("  • ESMO Hepatobiliary Cancer Guidelines")
        print("  • NCCN Hepatobiliary Cancers (free account required)")
        print("  • BCLC 2022 update (Reig et al., Journal of Hepatology)")
        return

    print(f"\nFound {len(pdfs)} PDF(s):")
    for p in pdfs:
        print(f"  {p.name}  ({p.stat().st_size // 1024} KB)")

    await rag_engine.initialize()
    print("\nIngesting…")
    n = await rag_engine.ingest_knowledge_base()
    print(f"\nDone — {n} chunks stored in {settings.vectordb_dir}")


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
