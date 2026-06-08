# Liver Cancer AI Diagnostics — Project Progress & Roadmap

**Last Updated:** 2026-05-26  
**Current Phase:** Phase 2 — Segmentation Overlay (Starting)

---

## Project Overview

A web-based AI-assisted diagnostic tool for liver cancer detection from MRI and CT scans.  
The tool is **clinical decision support** — not autonomous diagnosis. A licensed radiologist must review all AI outputs.

**Core pipeline:**
```
DICOM Upload → De-identification → Slice Export → Segmentation → Radiomics → LLM Report → Radiologist Review
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React + TypeScript + Vite + Tailwind CSS |
| DICOM Rendering | Cornerstone3D v4 (canvas-based viewer) |
| Backend | Python 3.11 + FastAPI + Uvicorn |
| DICOM Processing | pydicom, dicom2nifti, SimpleITK |
| Segmentation | TotalSegmentator (GPU) |
| Radiomics | PyRadiomics |
| LLM | Ollama → llama3.2-vision:11b (local, no PHI leaves machine) |
| Embeddings | nomic-embed-text (via Ollama) |
| RAG | LangChain + ChromaDB |
| GPU | NVIDIA RTX 4070 (8 GB VRAM), CUDA 13.2 |
| OS | Windows 11 Pro |

---

## What Has Been Done

### Code (Already Written — Previous Session)

#### Backend (`backend/`)
- `main.py` — FastAPI app with lifespan, CORS, router registration
- `config.py` — Pydantic settings, auto-creates data directories on startup
- `models/schemas.py` — All Pydantic models (DiagnosticReport, LesionFinding, LiRadsCategory, etc.)
- `core/dicom_processor.py` — DICOM loading, phase detection (arterial/portal/delayed/DWI/etc.), PHI anonymization, NIfTI conversion (dicom2nifti + SimpleITK fallback), liver window normalization
- `core/segmentation.py` — TotalSegmentator integration, liver + lesion mask extraction, Couinaud segment estimation, volume calculation
- `core/slice_exporter.py` — Exports windowed PNG slices per phase, builds multi-phase montage for LLM input
- `core/radiomics_extractor.py` — PyRadiomics feature extraction from lesion masks
- `core/rag_engine.py` — ChromaDB vector store, LangChain document ingestion, guideline retrieval
- `core/llm_client.py` — Ollama-backed LLM client, LI-RADS v2024 system prompt, structured JSON report parsing
- `api/routes/dicom.py` — Upload endpoint, study metadata extraction
- `api/routes/analysis.py` — Full pipeline trigger (segmentation → radiomics → LLM)
- `api/routes/rag.py` — RAG query endpoint

#### Frontend (`frontend/`)
- `src/App.tsx` — Main layout, state management
- `src/components/UploadPanel.tsx` — Drag-and-drop DICOM folder upload
- `src/components/DicomViewer.tsx` — Canvas-based slice viewer, keyboard navigation (arrow keys), slice slider
- `src/components/AIReportPanel.tsx` — Structured LI-RADS report display
- `src/components/LiRadsScore.tsx` — Color-coded LI-RADS badge component
- `src/components/ProgressTracker.tsx` — Pipeline step progress indicator
- `src/hooks/useAnalysis.ts` — Analysis state and API call hook
- `src/services/api.ts` — Axios API client
- `src/types/index.ts` — TypeScript interfaces

#### Scripts
- `scripts/setup.ps1` — One-time setup (venv, PyTorch, deps, Ollama models, npm)
- `scripts/ingest_guidelines.py` — Ingests PDF guidelines into ChromaDB RAG
- `scripts/generate_test_dicom.py` — Generates 30 synthetic liver CT DICOM slices for testing

#### Config Files
- `backend/.env` — Environment config (Ollama URL, model names, device)
- `backend/requirements.txt` — All Python dependencies
- `frontend/package.json` — All npm dependencies (Cornerstone3D v4, React, Tailwind)
- `Research.md` — Deep research on liver cancer AI, LI-RADS, model benchmarks, architecture decisions
- `Datasets.md` — Dataset sources and notes

---

### Phase 1 Complete — 2026-05-26 ✅

| Task | Status |
|---|---|
| Ollama installed + running | ✅ Done |
| llava:7b vision model pulled | ✅ Done (llama3.2-vision not available; llava:7b used) |
| nomic-embed-text pulled | ✅ Done |
| Python 3.11 venv + all packages installed | ✅ Done |
| PyTorch 2.5.1+cu121 + CUDA verified | ✅ Done (`torch.cuda.is_available()` = True) |
| Frontend npm packages installed | ✅ Done |
| Backend starts cleanly (no import errors) | ✅ Done |
| DICOM upload endpoint working | ✅ Done |
| NIfTI conversion working | ✅ Done |
| TotalSegmentator liver segmentation (GPU) | ✅ Done (subprocess isolation fix for Windows) |
| liver_lesions task working | ✅ Done (fixed wrong task name) |
| LLM analysis via llava:7b | ✅ Done |
| Structured LI-RADS JSON report generated | ✅ Done |
| Frontend displays report (LR-4, BCLC-A) | ✅ Confirmed by user |
| Full pipeline end-to-end with real DICOM | ✅ Done |

### Key Bugs Fixed (2026-05-26)
| Bug | Fix |
|---|---|
| `TotalSegmentator` not in PATH | Switched to Python API, then subprocess |
| Wrong task `liver_vessels_and_tumors` | Changed to `liver_lesions` |
| Windows nnU-Net worker crash | Isolated subprocess with `__main__` guard (`scripts/run_totalseg.py`) |
| LLM model not installed | Updated `.env` to `llava:7b` |

---

## What Needs to Be Done Next

### Immediate (Once PyTorch Download Finishes)

1. **Install PyTorch from local .whl file**
   ```powershell
   & "D:\Steven Project\Liver Cancer\backend\.venv\Scripts\pip.exe" install "C:\Users\<you>\Downloads\torch-2.5.1+cu121-cp311-cp311-win_amd64.whl"
   ```

2. **Upgrade pip in venv**
   ```powershell
   & "D:\Steven Project\Liver Cancer\backend\.venv\Scripts\python.exe" -m pip install --upgrade pip
   ```

3. **Install remaining backend packages**
   ```powershell
   & "D:\Steven Project\Liver Cancer\backend\.venv\Scripts\pip.exe" install -r "D:\Steven Project\Liver Cancer\backend\requirements.txt"
   ```

4. **Install torchvision**
   ```powershell
   & "D:\Steven Project\Liver Cancer\backend\.venv\Scripts\pip.exe" install torchvision --index-url https://download.pytorch.org/whl/cu121
   ```
   *(Small download — only ~6 MB, separate from torch)*

5. **Verify CUDA is working**
   ```powershell
   & "D:\Steven Project\Liver Cancer\backend\.venv\Scripts\python.exe" -c "import torch; print(torch.cuda.is_available())"
   ```
   Expected output: `True`

---

### Phase 1 Completion — Get the App Running

6. **Start Ollama** (if not already running)
7. **Start the backend**
   ```
   cd backend
   .\.venv\Scripts\uvicorn main:app --reload
   ```
8. **Start the frontend**
   ```
   cd frontend
   npm run dev
   ```
9. **Open browser at** `http://localhost:5173`
10. **Upload the synthetic test DICOM** from `Datasets/sample_ct/series_arterial/`
11. **Run analysis** and verify the full pipeline works end-to-end
12. **Fix any runtime errors** that appear

---

### Phase 1 Polish (After Basic Run Works)

- [ ] Test with a real DICOM CT file (download from TCIA or Kaggle "liver DICOM")
- [ ] Verify de-identification strips PHI tags correctly
- [ ] Verify slice export produces correct windowed PNGs
- [ ] Verify LLM returns structured JSON report
- [ ] Verify frontend displays report correctly
- [ ] Add loading states and error messages in UI
- [ ] Test keyboard navigation in the DICOM viewer
- [ ] Add a disclaimer banner ("AI decision support only — radiologist review required")

---

### Phase 2 — Segmentation Integration (Future)

- [ ] Test TotalSegmentator on real liver CT
- [ ] Verify liver mask overlay renders correctly in viewer
- [ ] Feed lesion size + Couinaud segment to LLM prompt
- [ ] Export segmentation as DICOM SEG format
- [ ] Display segmentation overlay on the canvas viewer

---

### Phase 3 — Full Pipeline (Future)

- [ ] PyRadiomics feature extraction from lesion ROIs
- [ ] LI-RADS scoring logic refinement in prompt
- [ ] Radiologist review + sign-off workflow in UI
- [ ] Audit logging (who ran what, when)
- [ ] FHIR DiagnosticReport output
- [ ] Load LI-RADS v2024 PDF into RAG knowledge base

---

### Phase 4 — Regulatory & Validation (Future)

- [ ] De-identified retrospective case validation
- [ ] Prominent disclaimer and radiologist-in-the-loop enforcement
- [ ] FDA pre-submission meeting (Q-Sub) if targeting US clinical use
- [ ] EU AI Act compliance review (High-Risk AI System — August 2026 deadline)
- [ ] Azure OpenAI BAA if switching to cloud LLM with real patient data

---

## Key File Locations

| Item | Path |
|---|---|
| Backend entry point | `backend/main.py` |
| Environment config | `backend/.env` |
| Python dependencies | `backend/requirements.txt` |
| Frontend entry point | `frontend/src/main.tsx` |
| Main app component | `frontend/src/App.tsx` |
| DICOM viewer component | `frontend/src/components/DicomViewer.tsx` |
| Test DICOM data | `Datasets/sample_ct/series_arterial/` |
| Start backend script | `start_backend.ps1` |
| Start frontend script | `start_frontend.ps1` |
| Setup script | `scripts/setup.ps1` |
| RAG ingestion script | `scripts/ingest_guidelines.py` |

---

## Known Issues / Decisions

| Issue | Decision |
|---|---|
| Python 3.14 incompatible with scientific stack | Using Python 3.11 venv |
| PyTorch too large for pip (2.4 GB, keeps timing out) | Downloading .whl manually via browser |
| Cornerstone3D v1 packages don't exist on npm | Upgraded to v4.22.3 |
| No real DICOM test data (TCIA requires account) | Generated 30 synthetic slices with pydicom |
| Network congestion during setup | Install PyTorch first, then everything else |
| LLM is local (Ollama) not cloud | PHI never leaves the machine — no BAA needed for dev |
