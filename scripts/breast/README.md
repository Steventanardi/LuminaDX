# Breast scripts

Project-level scripts for the **breast / mammography (DBT)** module. Run from the
**repo root** with the backend virtualenv.

| Script | Purpose |
|--------|---------|
| `download_dbt_breast.py` | Sort the Breast-Cancer-Screening-DBT (Duke DBT, 2024) **test split** into LuminaDx's breast reference folders. |

## download_dbt_breast.py

Uses the dataset's own label + file-path CSVs to copy images into
`backend/data/reference/breast/<Healthy|Non-Healthy>/`. The test split is chosen
deliberately: it has exactly 30 Cancer + 298 Normal patients, so you get all 30
cancers plus a balanced set of normals from one consistent source.

```powershell
# from repo root — see --help for the exact CSV / image-root flags
backend\.venv\Scripts\python.exe scripts\breast\download_dbt_breast.py --help
```

> You must download the Duke DBT dataset first (TCIA). See `dataset.md` /
> `README.md` for the link and the expected on-disk layout.
