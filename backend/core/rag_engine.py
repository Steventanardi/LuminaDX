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

_COLLECTION = "liver_cancer_guidelines"


class RAGEngine:
    def __init__(self) -> None:
        self._client: chromadb.PersistentClient | None = None
        self._collection = None
        self._embeddings: OllamaEmbeddings | None = None
        self.ready = False

    async def initialize(self) -> None:
        logger.info("Initialising RAG engine …")
        self._client = chromadb.PersistentClient(
            path=str(settings.vectordb_dir),
            settings=_CS(anonymized_telemetry=False),
        )
        self._collection = self._client.get_or_create_collection(
            name=_COLLECTION,
            metadata={"hnsw:space": "cosine"},
        )
        self._embeddings = OllamaEmbeddings(
            base_url=settings.ollama_base_url,
            model=settings.embed_model,
        )
        self.ready = True
        logger.info(f"RAG ready — {self._collection.count()} chunks in store")

    async def ingest_knowledge_base(self) -> int:
        pdfs = list(settings.knowledge_base_dir.glob("*.pdf"))
        if not pdfs:
            logger.warning("No PDFs to ingest")
            return 0

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
                    {"source": pdf.name, "page": c.metadata.get("page", 0)}
                    for c in chunks
                ]
                ids = [f"{pdf.stem}__{i}" for i in range(len(chunks))]
                embeddings = await self._embed(texts)

                self._collection.upsert(
                    ids=ids,
                    embeddings=embeddings,
                    documents=texts,
                    metadatas=metas,
                )
                total += len(chunks)
                logger.info(f"Ingested {pdf.name}: {len(chunks)} chunks")
            except Exception as exc:
                logger.error(f"Failed to ingest {pdf.name}: {exc}")

        return total

    async def retrieve(self, query: str, n: int | None = None) -> str:
        if not self.ready or not self._collection:
            return ""
        count = self._collection.count()
        if count == 0:
            return ""

        k = min(n or settings.rag_top_k, count)
        try:
            q_emb = await self._embed([query])
            res = self._collection.query(
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
        return [await self._embeddings.aembed_query(t) for t in texts]

    @property
    def chunk_count(self) -> int:
        return self._collection.count() if self._collection else 0


rag_engine = RAGEngine()
