from __future__ import annotations

from pathlib import Path
from typing import List

import chromadb
from chromadb.config import Settings as _CS
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader
from langchain_ollama import OllamaEmbeddings
from loguru import logger

from config import settings

_DEFAULT_COLLECTION = "liver_cancer_guidelines"
_COLLECTION_MAP = {
    "liver":      "liver_cancer_guidelines",
    "skin":       "skin_cancer_guidelines",
    "lung":       "lung_cancer_guidelines",
    "breast":     "breast_cancer_guidelines",
    "colorectal": "colorectal_cancer_guidelines",
}


class RAGEngine:
    def __init__(self) -> None:
        self._client: chromadb.PersistentClient | None = None
        self._collections: dict = {}
        self._embeddings: OllamaEmbeddings | None = None
        self.ready = False

    def _get_collection(self, namespace: str = "liver"):
        name = _COLLECTION_MAP.get(namespace, _DEFAULT_COLLECTION)
        if name not in self._collections:
            self._collections[name] = self._client.get_or_create_collection(
                name=name, metadata={"hnsw:space": "cosine"},
            )
        return self._collections[name]

    async def initialize(self) -> None:
        logger.info("Initialising RAG engine …")
        self._client = chromadb.PersistentClient(
            path=str(settings.vectordb_dir),
            settings=_CS(anonymized_telemetry=False),
        )
        # Pre-load the default liver collection so chunk_count reflects it
        self._get_collection("liver")
        self._embeddings = OllamaEmbeddings(
            base_url=settings.ollama_base_url,
            model=settings.embed_model,
        )
        self.ready = True
        logger.info(f"RAG ready — {self.chunk_count} liver-guideline chunks in store")

    async def ingest_knowledge_base(self, namespace: str = "liver") -> int:
        kb_dir = settings.knowledge_base_dir
        # Cancer-specific subfolder takes priority; fall back to root for liver
        sub = kb_dir / namespace
        pdf_dir = sub if sub.exists() else (kb_dir if namespace == "liver" else None)
        if pdf_dir is None:
            logger.warning(f"No knowledge base dir for namespace={namespace}")
            return 0

        pdfs = list(pdf_dir.glob("*.pdf"))
        if not pdfs:
            logger.warning(f"No PDFs to ingest (namespace={namespace}, dir={pdf_dir})")
            return 0

        collection = self._get_collection(namespace)
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=settings.rag_chunk_size,
            chunk_overlap=settings.rag_chunk_overlap,
            separators=["\n\n", "\n", ". ", " ", ""],
        )

        total = 0
        for pdf in pdfs:
            try:
                docs = PyPDFLoader(str(pdf)).load()
                chunks = splitter.split_documents(docs)
                texts = [c.page_content for c in chunks]
                metas = [
                    {"source": pdf.name, "page": c.metadata.get("page", 0), "cancer_type": namespace}
                    for c in chunks
                ]
                ids = [f"{namespace}__{pdf.stem}__{i}" for i in range(len(chunks))]
                embeddings = await self._embed(texts)
                collection.upsert(ids=ids, embeddings=embeddings, documents=texts, metadatas=metas)
                total += len(chunks)
                logger.info(f"Ingested {pdf.name} [{namespace}]: {len(chunks)} chunks")
            except Exception as exc:
                logger.error(f"Failed to ingest {pdf.name}: {exc}")

        return total

    async def retrieve(self, query: str, n: int | None = None, namespace: str = "liver") -> str:
        if not self.ready:
            return ""
        collection = self._get_collection(namespace)
        count = collection.count()
        if count == 0:
            return ""

        k = min(n or settings.rag_top_k, count)
        try:
            q_emb = await self._embed([query])
            res = collection.query(
                query_embeddings=q_emb,
                n_results=k,
                include=["documents", "metadatas", "distances"],
            )
            parts: List[str] = []
            for doc, meta, dist in zip(
                res["documents"][0], res["metadatas"][0], res["distances"][0]
            ):
                if (1 - dist) > 0.25:
                    src = meta.get("source", "?")
                    pg = meta.get("page", 0) + 1
                    parts.append(f"[{src} — p.{pg}]\n{doc}")
            return "\n\n---\n\n".join(parts)
        except Exception as exc:
            logger.error(f"RAG retrieval error: {exc}")
            return ""

    async def _embed(self, texts: List[str]) -> List[List[float]]:
        # Embed in capped batches. Sending every chunk of a large guideline PDF
        # in a single request OOM-crashes the Ollama embed runner (the runner
        # subprocess dies and its port starts refusing connections), so cap the
        # batch size and issue sequential requests instead.
        batch = settings.embed_batch_size
        if len(texts) <= batch:
            return await self._embeddings.aembed_documents(texts)
        out: List[List[float]] = []
        for i in range(0, len(texts), batch):
            out.extend(await self._embeddings.aembed_documents(texts[i : i + batch]))
        return out

    @property
    def chunk_count(self) -> int:
        col = self._collections.get(_DEFAULT_COLLECTION)
        return col.count() if col else 0


rag_engine = RAGEngine()
