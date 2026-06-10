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


@router.get("/status")
async def status():
    total_pdfs = sum(
        len(list(settings.knowledge_base_dir.glob("**/*.pdf"))), 0
    ) if False else len(list(settings.knowledge_base_dir.glob("*.pdf"))) + sum(
        len(list(d.glob("*.pdf")))
        for d in settings.knowledge_base_dir.iterdir() if d.is_dir()
    )
    return {
        "ready": rag_engine.ready,
        "chunks": rag_engine.chunk_count,
        "pdf_count": total_pdfs,
        "knowledge_base_dir": str(settings.knowledge_base_dir),
    }
