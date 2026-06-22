"""One-off runner to ingest guideline PDFs into the RAG vector store.

Usage (from backend/):
    python scripts/ingest_guidelines.py            # all namespaces
    python scripts/ingest_guidelines.py liver skin # selected namespaces
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from core.rag_engine import rag_engine, _COLLECTION_MAP  # noqa: E402


async def main(namespaces: list[str]) -> None:
    await rag_engine.initialize()
    grand_total = 0
    for ns in namespaces:
        n = await rag_engine.ingest_knowledge_base(ns)
        print(f"[{ns}] ingested {n} chunks")
        grand_total += n
    print(f"DONE — {grand_total} chunks across {len(namespaces)} namespace(s)")


if __name__ == "__main__":
    ns = sys.argv[1:] or list(_COLLECTION_MAP.keys())
    asyncio.run(main(ns))
