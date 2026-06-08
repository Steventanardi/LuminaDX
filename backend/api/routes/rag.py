from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException

from api.deps import verify_api_key
from config import settings
from core.rag_engine import rag_engine
from models.schemas import RagQueryRequest

router = APIRouter()


@router.post("/ingest")
async def ingest(background_tasks: BackgroundTasks, _: None = Depends(verify_api_key)):
    pdfs = list(settings.knowledge_base_dir.glob("*.pdf"))
    if not pdfs:
        raise HTTPException(
            400,
            f"No PDFs in {settings.knowledge_base_dir}. "
            "Download guidelines (LI-RADS, AASLD, ESMO, NCCN) and place them there.",
        )
    background_tasks.add_task(rag_engine.ingest_knowledge_base)
    return {"message": f"Ingestion started for {len(pdfs)} PDF(s)"}


@router.post("/query")
async def query(req: RagQueryRequest):
    ctx = await rag_engine.retrieve(req.query, req.n_results)
    return {"query": req.query, "context": ctx, "found": bool(ctx)}


@router.get("/status")
async def status():
    return {
        "ready": rag_engine.ready,
        "chunks": rag_engine.chunk_count,
        "pdf_count": len(list(settings.knowledge_base_dir.glob("*.pdf"))),
        "knowledge_base_dir": str(settings.knowledge_base_dir),
    }
