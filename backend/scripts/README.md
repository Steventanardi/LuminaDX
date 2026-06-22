# `backend/scripts/` — backend eval & ingestion, by cancer

Run these from the **`backend/` directory** with the backend virtualenv, so
`core`/`config` import correctly. Each subfolder has its own README.

| Folder | Cancer | Contents |
|--------|--------|----------|
| [`skin/`](skin/README.md) | Skin / melanoma | `eval_skin.py` (KNN vs trained classifier vs LLM) |
| [`shared/`](shared/README.md) | All | `eval_knn.py` (KNN evaluation), `ingest_guidelines.py` (RAG ingestion, per-cancer namespaces) |

Project-level trainers / data scripts live under [`scripts/`](../../scripts/README.md)
(run from the repo root).
