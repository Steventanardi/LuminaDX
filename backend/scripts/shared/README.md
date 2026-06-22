# Shared eval / ingestion scripts (backend)

Cross-cancer backend scripts. Run from the **`backend/` directory** with the
backend virtualenv so `core`/`config` import.

| Script | Purpose | Cancer |
|--------|---------|--------|
| `eval_knn.py` | Evaluate the KNN classifier against a held-out labelled test set (accuracy, confusion matrix, per-class P/R/F1). | any |
| `ingest_guidelines.py` | Ingest guideline PDFs into the RAG vector store, with per-cancer namespaces. | all (RAG) |

## eval_knn.py
The test set must **not** overlap the reference set
(`backend/data/reference/<cancer>/`) or accuracy is inflated by leakage.

```powershell
# from backend/
.venv\Scripts\python.exe scripts\shared\eval_knn.py --cancer skin `
    --test-dir "C:\path\to\test" --backbone cnn_resnet50 --k 5
```

## ingest_guidelines.py
Place guideline PDFs under `backend/data/knowledge_base/<namespace>/` first.

```powershell
# from backend/
.venv\Scripts\python.exe scripts\shared\ingest_guidelines.py            # all namespaces
.venv\Scripts\python.exe scripts\shared\ingest_guidelines.py liver skin # selected namespaces
```
