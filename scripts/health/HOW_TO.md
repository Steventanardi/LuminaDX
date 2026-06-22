# LuminaDx Health Check

A one-command checker (and auto-fixer) that verifies the **backend (FastAPI)** and
**frontend (Vite/React)** are wired up correctly and actually run.

Script: [`health_check.ps1`](./health_check.ps1)

---

## Quick start

Open **PowerShell** in the project root (`D:\Steven Project\LuminaDx`) and run:

```powershell
# Check only - reports problems, changes nothing
.\scripts\health\health_check.ps1

# Auto-fix - repairs what it safely can
.\scripts\health\health_check.ps1 -Fix
```

> If you get *"running scripts is disabled on this system"*, allow local scripts once:
> ```powershell
> Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
> ```
> Or run a single invocation without changing policy:
> ```powershell
> powershell -ExecutionPolicy Bypass -File .\scripts\health\health_check.ps1
> ```

---

## What it checks

| # | Check | Auto-fix with `-Fix`? |
|---|-------|:--:|
| 1 | **Tooling** - `node`, `npm`, Python launcher on PATH | no (install manually) |
| 2 | **Junk files** - stray 0-byte files from botched shell redirects | yes (deletes them) |
| 3 | **Backend venv + deps** - `backend\.venv` + core packages import | yes (creates venv, `pip install -r requirements.txt`) |
| 4 | **`backend\.env`** - exists and `AUTH_SECRET_KEY` is not the insecure default | yes (creates `.env`, generates a secure secret) |
| 5 | **Frontend deps** - `frontend\node_modules` present | yes (`npm install`) |
| 6 | **Backend import + tests** - `main:app` imports, `pytest` passes | no (reports failures) |
| 7 | **AI model picker + feature/extraction selection** - the two catalogs that drive the per-diagnosis pickers are valid and the frontend still consumes them | no (reports failures) |
| 8 | **Frontend typecheck / build** - `tsc --noEmit` (and `npm run build` with `-Build`) | no (reports failures) |
| 9 | **Ollama** - reachable at `localhost:11434`, required models pulled | yes (`ollama pull` missing models) |

### What step 7 checks (the easily-forgotten part)

The **AI Model Pick** dropdown and the **Features & Extraction** checkboxes are core to the
app, so they get their own validation. Step 7 verifies:

- **Model catalog** (`backend/core/model_catalog.py`): every per-cancer default LLM is a real
  `VISION_MODELS` entry, `options_for()` lists the default first, and the catalog covers every
  cancer in the module registry.
- **Feature catalog** (`backend/core/feature_catalog.py`): every applicable feature key exists,
  every default-on feature is applicable, `resolve()` falls back to defaults and drops unknown
  keys, and every CNN feature (VGG16/19, ResNet50) maps to a real `cnn_features` backbone.
- **Frontend wiring**: `api.ts` calls `/analysis/models` + `/analysis/features`, the
  `ModelCatalog`/`FeatureCatalog` types exist, and `WorkflowPanel.tsx` still renders the model
  dropdown + feature checkboxes (`selectedModel` / `selectedFeatures`).
- **Skin classifier calibration** (advisory): reports whether the HAM10000 checkpoint carries
  `temperature` / `malignancy_threshold` / `melanoma_threshold`. Missing = a WARN telling you to
  run `scripts/skin/calibrate_skin.py` (the app still works on safe defaults).

If you add a new cancer, model, or feature/extractor, this step fails fast when something is
left half-wired.

Exit code is **0** when all critical checks pass, **1** if any failed — so it works in CI too.

---

## Options (flags)

| Flag | Effect |
|------|--------|
| `-Fix` | Apply auto-fixes (create venv, install deps, npm install, generate `.env` secret, delete junk, pull models). |
| `-SkipTests` | Skip pytest **and** the frontend typecheck — fast smoke check. |
| `-Build` | Also run the frontend production build (`npm run build`). |
| `-SkipOllama` | Skip the Ollama reachability / model checks. |

### Common combinations

```powershell
# Fast smoke check (no tests, no Ollama)
.\scripts\health\health_check.ps1 -SkipTests -SkipOllama

# Full repair pass, including a production build
.\scripts\health\health_check.ps1 -Fix -Build

# First-time setup on a fresh clone (build venv + install everything)
.\scripts\health\health_check.ps1 -Fix
```

---

## Reading the output

Each line is tagged:

- `[ OK   ]` — passed
- `[ FIXED]` — a problem was found and auto-repaired (only with `-Fix`)
- `[ WARN ]` — non-critical (e.g. Ollama down, a check skipped); does **not** fail the run
- `[ FAIL ]` — critical problem; makes the run exit `1`

The **Summary** block at the end tallies Passed / Fixed / Warnings / Failed and lists any
failures. If you ran check-only and something failed, re-run with `-Fix`.

Example of a healthy run:

```
=== Summary ===
  Passed: 10   Fixed: 0   Warnings: 1   Failed: 0

All critical checks passed.
```

---

## Notes

- The script clears `PYTHONPATH` / `VIRTUAL_ENV` before calling the venv Python, matching
  `start_backend.ps1`, so the bundled virtualenv is always used.
- It never deletes a stray file that has content — only **known 0-byte** artifacts.
- It never prints or commits secrets; the generated `AUTH_SECRET_KEY` is written straight to
  `backend\.env` (which is git-ignored).
- Requires **PowerShell 5.1+** (built into Windows 11).

## After a clean check, start the app

```powershell
# from the project root
.\Launch.bat
# or separately:
.\start_backend.ps1     # http://localhost:8000
.\start_frontend.ps1    # http://localhost:5173
```
