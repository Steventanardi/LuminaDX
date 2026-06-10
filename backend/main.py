from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse
from loguru import logger
from pathlib import Path

from api.routes import analysis, audit, dicom, rag
from api.routes import auth as auth_router
from config import settings
from core.database import init_db
from core.rag_engine import rag_engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting LuminaDx multi-cancer AI diagnostics backend")
    init_db()
    await rag_engine.initialize()
    yield
    logger.info("Shutdown complete")


app = FastAPI(
    title="LuminaDx — Multi-Cancer AI Diagnostics",
    version="0.2.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router.router, prefix="/api/auth", tags=["Auth"])
app.include_router(dicom.router, prefix="/api/dicom", tags=["DICOM"])
app.include_router(analysis.router, prefix="/api/analysis", tags=["Analysis"])
app.include_router(rag.router, prefix="/api/rag", tags=["RAG"])
app.include_router(audit.router, prefix="/api/audit", tags=["Audit"])


@app.get("/health")
async def health():
    return {"status": "ok", "rag_chunks": rag_engine.chunk_count, "version": "0.2.0"}


@app.get("/api/model-card", response_class=PlainTextResponse)
async def model_card():
    """Return the model card (Appendix material for the thesis)."""
    p = Path(__file__).parent / "docs" / "model_card.md"
    if not p.exists():
        return PlainTextResponse("Model card not found.", status_code=404)
    return PlainTextResponse(p.read_text(encoding="utf-8"))
