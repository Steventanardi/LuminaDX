from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    app_name: str = "LuminaDx — Multi-Cancer AI Diagnostics"
    debug: bool = False

    base_dir: Path = Path(__file__).parent
    uploads_dir: Path = base_dir / "data" / "uploads"
    processed_dir: Path = base_dir / "data" / "processed"
    knowledge_base_dir: Path = base_dir / "data" / "knowledge_base"
    vectordb_dir: Path = base_dir / "data" / "vectordb"
    logs_dir: Path = base_dir / "data" / "logs"
    # KNN classifier: labeled reference images live under reference_dir/<cancer>/<label>/;
    # built embedding indices are cached under knn_index_dir.
    reference_dir: Path = base_dir / "data" / "reference"
    knn_index_dir: Path = base_dir / "data" / "knn_index"
    # Trained model checkpoints (e.g. HAM10000 skin classifier).
    weights_dir: Path = base_dir / "data" / "weights"

    ollama_base_url: str = "http://localhost:11434"
    llm_model: str = "medgemma:4b-it-q8_0"
    embed_model: str = "nomic-embed-text"

    rag_chunk_size: int = 500
    rag_chunk_overlap: int = 50
    rag_top_k: int = 5
    # Max chunks embedded per Ollama request during ingestion. Large PDFs in one
    # batch OOM-crash the embed runner, so cap it.
    embed_batch_size: int = 64

    # When False, extract Original-image features only (fast). Wavelet/LoG add
    # ~1,000 features that are NOT used in the LLM summary, so they are off by
    # default — enable only if you need the full feature set for analysis.
    radiomics_extended: bool = False

    device: str = "gpu"
    api_key: str = ""  # legacy; replaced by JWT auth

    # Auth
    auth_secret_key: str = "change-me-in-production-use-AUTH_SECRET_KEY-env-var"
    auth_token_expire_hours: int = 24
    cookie_secure: bool = False  # set True when serving over HTTPS

    model_config = {"env_file": ".env"}


settings = Settings()

if not settings.debug and settings.auth_secret_key.startswith("change-me"):
    raise RuntimeError(
        "AUTH_SECRET_KEY is still the insecure default — set it in backend/.env "
        "(generate one with: python -c \"import secrets; print(secrets.token_urlsafe(48))\")"
    )

for _d in [
    settings.uploads_dir,
    settings.processed_dir,
    settings.knowledge_base_dir,
    settings.vectordb_dir,
    settings.logs_dir,
    settings.reference_dir,
    settings.knn_index_dir,
    settings.weights_dir,
]:
    _d.mkdir(parents=True, exist_ok=True)
