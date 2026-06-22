# Shared / infrastructure scripts

Cross-cancer setup, data-safety and runtime-helper scripts. Run from the **repo
root** (paths inside these scripts assume the repo root is the working dir).

| File | Purpose | Cancer |
|------|---------|--------|
| `setup.ps1` | One-time environment setup: venv, CUDA PyTorch, backend + frontend deps. | all |
| `seed_admin.py` | Create the initial admin account (auth). | all |
| `ingest_guidelines.py` | **Legacy** liver-only RAG ingester. Prefer the multi-namespace one at `backend/scripts/shared/ingest_guidelines.py`. | all (RAG) |
| `verify_deidentification.py` | Audit a DICOM dir for PHI leakage (DICOM PS3.15 Basic Confidentiality Profile). | all (CT/MRI) |
| `run_totalseg.py` | Subprocess wrapper that runs TotalSegmentator with a `__main__` guard. **Called automatically by `backend/core/segmentation.py`** — not usually run by hand. | liver / lung |

## setup.ps1
```powershell
# from repo root
.\scripts\shared\setup.ps1
```

## seed_admin.py
```powershell
# from repo root; override defaults via env vars
$env:ADMIN_EMAIL="you@example.com"; $env:ADMIN_PASSWORD="…"; $env:ADMIN_NAME="Dr X"
backend\.venv\Scripts\python.exe scripts\shared\seed_admin.py
```

## verify_deidentification.py
```powershell
backend\.venv\Scripts\python.exe scripts\shared\verify_deidentification.py <dicom_dir_or_file> [--verbose]
```

## run_totalseg.py
Invoked internally as:
`python scripts/shared/run_totalseg.py '<json_args>'`. The path is referenced by
`backend/core/segmentation.py` (`_TOTALSEG_SCRIPT`) — **if you move this file,
update that constant too.**

## ingest_guidelines.py (legacy)
```powershell
# place liver guideline PDFs in backend/data/knowledge_base/ first
backend\.venv\Scripts\python.exe scripts\shared\ingest_guidelines.py
```
For multi-cancer RAG ingestion use `backend/scripts/shared/ingest_guidelines.py`
(supports per-cancer namespaces).
