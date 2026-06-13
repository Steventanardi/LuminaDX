# Skin Cancer RAG Setup

## 1. Where to put the file for RAG to ingest

The RAG knowledge base holds **guideline PDFs**, organized per-cancer in subfolders.
For skin, drop your PDFs here:

```
D:\Steven Project\LuminaDx\backend\data\knowledge_base\skin\
```

How it works (`backend/core/rag_engine.py`):

- Each cancer type has its own Chroma collection — skin → `skin_cancer_guidelines`.
- For any non-liver type, the engine looks **only** in the `<namespace>/` subfolder.
  Liver is the exception — it reads the `knowledge_base/` root directly (that's why all
  current liver PDFs sit at the root).
- It loads every `*.pdf` in the folder, splits into chunks, embeds with Ollama
  `nomic-embed-text`, and upserts.
- Format must be **PDF** (uses `PyPDFLoader`).

### Trigger ingestion

After adding PDFs, call the RAG ingest endpoint with the skin namespace
(requires login — it's auth-protected):

```
POST /api/rag/ingest?namespace=skin
```

Example:

```powershell
curl -X POST "http://localhost:8000/api/rag/ingest?namespace=skin" -b cookies.txt
```

Check progress with `GET /api/rag/status`. If the folder is empty it returns a 400
telling you to add PDFs first.

## 2. Where to find the dataset (2021–2026)

The RAG store holds **clinical guideline documents**, not image training data.
The skin module (`skin.py`) cites **NCCN 2024** and **AAD** guidelines. So for the
knowledge base you want recent skin-cancer guideline PDFs.

### Guideline PDFs (for RAG knowledge base)

| Source | What | Where |
|---|---|---|
| **NCCN Guidelines** | Melanoma: Cutaneous, Basal Cell, Squamous Cell (updated yearly, v2024/2025) | nccn.org — free account required |
| **AAD** | Melanoma management guidelines | aad.org / *J Am Acad Dermatol* |
| **ESMO** | Cutaneous Melanoma Clinical Practice Guideline (2023 update) | esmo.org/guidelines |
| **EADO/EADV** | European melanoma & keratinocyte carcinoma guidelines | onlinelibrary / journal PDFs |
| **NICE** | Melanoma assessment & management (NG14) | nice.org.uk |

### Image datasets (for training/testing the vision model — NOT for RAG)

Standard public dermoscopy sets — these are images and do **not** go in `knowledge_base/`:

- **ISIC Archive** (isic-archive.com) — largest, ongoing 2016–2024
- **HAM10000**
- **BCN20000**
- **ISIC 2024 Challenge** data
