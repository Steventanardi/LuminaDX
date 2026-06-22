from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from typing import Optional

from api.deps import get_current_user
from config import settings
from core.database import User
from core.rag_engine import rag_engine
from models.schemas import RagQueryRequest

router = APIRouter()


@router.post("/ingest")
async def ingest(
    background_tasks: BackgroundTasks,
    namespace: Optional[str] = "liver",
    current_user: User = Depends(get_current_user),
):
    kb_dir = settings.knowledge_base_dir
    sub = kb_dir / namespace if namespace != "liver" else kb_dir
    pdfs = list(sub.glob("*.pdf")) if sub.exists() else []
    if not pdfs:
        raise HTTPException(
            400,
            f"No PDFs for namespace='{namespace}' in {sub}. "
            "Place guideline PDFs there first.",
        )
    background_tasks.add_task(rag_engine.ingest_knowledge_base, namespace)
    return {"message": f"Ingestion started for {len(pdfs)} PDF(s) [namespace={namespace}]"}


@router.post("/query")
async def query(req: RagQueryRequest, current_user: User = Depends(get_current_user)):
    ctx = await rag_engine.retrieve(req.query, req.n_results)
    return {"query": req.query, "context": ctx, "found": bool(ctx)}


# Display order + label for each cancer's guideline collection. Liver lives in
# the knowledge-base root; the others in same-named subfolders.
_CANCER_NS = [
    ("liver", "Liver"),
    ("skin", "Skin"),
    ("lung", "Lung"),
    ("breast", "Breast"),
    ("colorectal", "Colorectal"),
]


@router.get("/status")
async def status():
    # Per-cancer breakdown: PDFs on disk + chunks actually indexed in the vector
    # store, so the header badge can show which cancer has how many guidelines
    # (and flag PDFs that are present but not yet ingested).
    kb = settings.knowledge_base_dir
    by_cancer = []
    total_pdfs = 0
    total_chunks = 0
    for ns, label in _CANCER_NS:
        # Same resolution as ingest: prefer the cancer subfolder; liver may also
        # live in the knowledge-base root (legacy layout) — fall back to it.
        sub = kb / ns
        d = sub if sub.exists() else (kb if ns == "liver" else None)
        pdfs = sorted(p.name for p in d.glob("*.pdf")) if d and d.exists() else []
        chunks = rag_engine.chunk_count_for(ns)
        total_pdfs += len(pdfs)
        total_chunks += chunks
        by_cancer.append({
            "cancer": ns,
            "label": label,
            "pdf_count": len(pdfs),
            "chunks": chunks,
            "indexed": chunks > 0,
            "pdfs": pdfs,
        })
    return {
        "ready": rag_engine.ready,
        "chunks": total_chunks,
        "pdf_count": total_pdfs,
        "by_cancer": by_cancer,
        "knowledge_base_dir": str(settings.knowledge_base_dir),
    }
