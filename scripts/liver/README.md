# Liver scripts

Project-level scripts for the **liver / HCC (CT)** module. Run from the **repo
root** with the backend virtualenv. The validation flow needs the backend API
running (`Launch.bat` / `start_backend.ps1`).

| File | Purpose |
|------|---------|
| `batch_validate.py` | Upload every HCC-TACE-Seg case to the running API, wait for analysis, write results to `validation_results.csv`. |
| `summarize_results.py` | Summarise `validation_results.csv` into accuracy / agreement metrics. |
| `validation_results.csv` | Output of the last batch run (data artifact). |

## batch_validate.py
Expects the dataset at `Datasets/HCC-TACE-Seg/hcc_tace_seg/` and the API at
`http://localhost:8000`.

```powershell
# 1) start the backend first (separate terminal)
#    Launch.bat   (or)   .\start_backend.ps1
# 2) then, from repo root:
backend\.venv\Scripts\python.exe scripts\liver\batch_validate.py
```
Writes `scripts/liver/validation_results.csv`.

## summarize_results.py
```powershell
backend\.venv\Scripts\python.exe scripts\liver\summarize_results.py
# or point at a specific CSV:
backend\.venv\Scripts\python.exe scripts\liver\summarize_results.py --csv scripts\liver\validation_results.csv
```
