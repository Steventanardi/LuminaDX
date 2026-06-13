from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse
from loguru import logger
from pathlib import Path
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from api.routes import analysis, audit, dicom, rag
from api.routes import auth as auth_router
from config import settings
from core import model_catalog
from core.database import init_db
from core.rate_limit import limiter
from core.rag_engine import rag_engine


async def _ollama_status() -> str:
    """'ok' if Ollama answers /api/tags, else 'unreachable'."""
    try:
        async with httpx.AsyncClient(timeout=3) as client:
            r = await client.get(f"{settings.ollama_base_url}/api/tags")
            r.raise_for_status()
        return "ok"
    except Exception:
        return "unreachable"


async def _warn_missing_models() -> None:
    """Warn for catalog models that aren't actually pulled in Ollama."""
    try:
        async with httpx.AsyncClient(timeout=3) as client:
            r = await client.get(f"{settings.ollama_base_url}/api/tags")
            r.raise_for_status()
            installed = {m["name"] for m in r.json().get("models", [])}
    except Exception:
        logger.warning(f"Ollama unreachable at {settings.ollama_base_url} — model check skipped")
        return
    for tag in model_catalog.VISION_MODELS:
        if tag not in installed:
            logger.warning(f"Catalog model '{tag}' is not installed — run: ollama pull {tag}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting LuminaDx multi-cancer AI diagnostics backend")
    init_db()
    await rag_engine.initialize()
    await _warn_missing_models()
    yield
    logger.info("Shutdown complete")


app = FastAPI(
    title="LuminaDx — Multi-Cancer AI Diagnostics",
    version="0.2.0",
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:5174", "http://localhost:3000"],
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
    return {
        "status": "ok",
        "ollama": await _ollama_status(),
        "rag_chunks": rag_engine.chunk_count,
        "version": "0.2.0",
    }


@app.get("/api/model-card", response_class=PlainTextResponse)
async def model_card():
    """Return the model card (Appendix material for the thesis)."""
    p = Path(__file__).parent / "docs" / "model_card.md"
    if not p.exists():
        return PlainTextResponse("Model card not found.", status_code=404)
    return PlainTextResponse(p.read_text(encoding="utf-8"))
