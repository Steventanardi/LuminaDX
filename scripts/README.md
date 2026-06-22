# `scripts/` — project-level scripts, by cancer

Run these from the **repo root** with the backend virtualenv
(`backend\.venv\Scripts\python.exe`). Each subfolder has its own README with
exact commands and flags.

| Folder | Cancer | Contents |
|--------|--------|----------|
| [`skin/`](skin/README.md) | Skin / melanoma | `train_skin_classifier.py` (HAM10000 ResNet50 trainer) |
| [`breast/`](breast/README.md) | Breast / DBT | `download_dbt_breast.py` (Duke DBT → reference folders) |
| [`liver/`](liver/README.md) | Liver / HCC | `batch_validate.py`, `summarize_results.py`, `validation_results.csv` |
| [`shared/`](shared/README.md) | All / infra | `setup.ps1`, `seed_admin.py`, `verify_deidentification.py`, `run_totalseg.py`, `ingest_guidelines.py` (legacy) |

Backend-only eval/ingestion scripts live under
[`backend/scripts/`](../backend/scripts/README.md) (run from `backend/`).
