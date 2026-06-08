# Liver Cancer AI Diagnostics

**AI-Powered Liver Cancer Diagnosis from MRI/CT Scans Using Vision-Language Models**

> ⚠️ **Disclaimer:** This is a research prototype for an academic thesis. It is **not** a certified medical device and must **not** be used for clinical patient care. All AI outputs are decision-support only — a licensed radiologist must review and approve every report.

---

## Table of Contents

- [Overview](#overview)
- [The Medical Problem](#the-medical-problem)
- [How It Works — The Hybrid Pipeline](#how-it-works--the-hybrid-pipeline)
- [Architecture Diagram](#architecture-diagram)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Data Flow — Where Comes From Where](#data-flow--where-comes-from-where)
- [Datasets](#datasets)
- [Prerequisites](#prerequisites)
- [Installation & Setup](#installation--setup)
- [Running the Application](#running-the-application)
- [API Endpoints](#api-endpoints)
- [Screenshots](#screenshots)
- [Validation & Compliance](#validation--compliance)
- [Known Limitations](#known-limitations)
- [Roadmap](#roadmap)
- [License](#license)
- [Contact](#contact)

---

## Overview

This project is a **web-based AI-assisted diagnostic tool** for liver cancer detection from MRI and CT scans. It combines **specialized deep learning segmentation** (TotalSegmentator) with **vision-language model (VLM) reasoning** (MedGemma 4B via Ollama) to produce structured LI-RADS radiology reports — all running **entirely locally** so that no patient data ever leaves the machine.

The system accepts DICOM, NIfTI, or plain image uploads, and processes them through a multi-stage pipeline:

1. **De-identification** — strips all Protected Health Information (PHI) from DICOM headers
2. **Format conversion** — converts DICOM to NIfTI for 3D processing and exports windowed PNG slices
3. **Segmentation** — automated liver and lesion detection using TotalSegmentator on GPU
4. **Radiomic feature extraction** — over 1,000 quantitative features computed via PyRadiomics
5. **Guideline retrieval (RAG)** — retrieves relevant LI-RADS v2018/v2024, AASLD 2023, EASL 2022, BCLC 2022, and KLCA-NCC 2022 guideline text from a local vector store (17 PDFs ingested)
6. **LLM analysis** — the vision-language model synthesizes all data into a structured LI-RADS/BCLC report
7. **Radiologist review** — human-in-the-loop sign-off workflow with audit logging

---

## The Medical Problem

Liver cancer diagnosis from imaging centers on three cancer types:

| Cancer | Prevalence | Primary Modality | Key Protocol |
|---|---|---|---|
| **HCC** (Hepatocellular Carcinoma) | 75–85% of cases | MRI / CT | LI-RADS scoring (LR-1 through LR-5) |
| **Cholangiocarcinoma** (CCA) | ~10–15% | MRI / CT | Target sign on DWI |
| **Metastatic** liver disease | Most common overall | CT | Multiplicity, distribution |

### What radiologists look for

- **Arterial phase hyperenhancement (APHE)** — HCC "lights up" from hepatic artery neovascularity
- **Washout** — HCC becomes dark on portal venous / delayed phases
- **Enhancing capsule** — smooth rim around the tumor
- **LI-RADS score** — the standardized scoring rubric (LR-1 = definitely benign → LR-5 = definitely HCC)
- **DWI restricted diffusion** — distinguishes malignancy from benign lesions
- **Hepatobiliary phase** — HCC appears dark on gadoxetate-enhanced MRI

### The key challenge

HCC diagnosis requires reading **multi-phase dynamics** (how the lesion enhances and washes out over time), not a single image. General VLMs alone score only 40–60% on radiology benchmarks, while specialized liver AI models (like LiLNet) achieve 88–94%. This project uses a **hybrid approach** — specialized segmentation feeds quantitative data to the VLM, giving it the structured context it needs to reason accurately.

---

## How It Works — The Hybrid Pipeline

```
┌─────────────────────────────────────────────────────────────────┐
│                        USER UPLOADS                             │
│            DICOM series  /  NIfTI volume  /  JPEG/PNG           │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
                ┌─────────────────────┐
                │  [1] DE-IDENTIFY    │  pydicom strips 45+ PHI tags
                │      (DICOM only)   │  per DICOM PS3.15 BALCP
                └──────────┬──────────┘
                           │
                           ▼
                ┌─────────────────────┐
                │  [2] CONVERT        │  DICOM → NIfTI (dicom2nifti / SimpleITK)
                │                     │  DICOM → windowed PNG slices
                └──────────┬──────────┘
                           │
              ┌────────────┴────────────┐
              ▼                         ▼
   ┌──────────────────┐      ┌──────────────────┐
   │ [3] SEGMENT      │      │ [4] SLICE SELECT │
   │  TotalSegmentator│      │  Pick key slices │
   │  (GPU/CPU)       │      │  per phase       │
   │                  │      │  → montage PNG   │
   │  Outputs:        │      │  for VLM input   │
   │  • Liver mask    │      └────────┬─────────┘
   │  • Lesion mask   │               │
   │  • Volume (mL)   │               │
   │  • Size (mm)     │               │
   │  • Couinaud seg  │               │
   └────────┬─────────┘               │
            │                         │
            ▼                         │
   ┌──────────────────┐               │
   │ [5] RADIOMICS    │               │
   │  PyRadiomics     │               │
   │  >1,000 features │               │
   │  (shape, texture │               │
   │   GLCM, wavelet) │               │
   └────────┬─────────┘               │
            │                         │
            └────────────┬────────────┘
                         ▼
              ┌──────────────────────┐
              │ [6] RAG RETRIEVAL    │  LI-RADS v2024 + AASLD 2023
              │  ChromaDB + LangChain│  guideline chunks retrieved
              └──────────┬───────────┘
                         │
                         ▼
              ┌──────────────────────┐
              │ [7] VLM ANALYSIS     │  MedGemma 4B (Ollama, local)
              │  Input:              │
              │   • Montage PNG      │  → Structured JSON report:
              │   • Radiomic summary │    • LI-RADS category (LR-1..5/M/TIV)
              │   • Seg. metrics     │    • BCLC stage (0/A/B/C/D)
              │   • RAG context      │    • Lesion findings
              │   • Patient context  │    • Recommendations
              └──────────┬───────────┘
                         │
                         ▼
              ┌──────────────────────┐
              │ [8] RADIOLOGIST      │  Approve / Request Changes
              │     REVIEW UI       │  + comments + radiologist ID
              │                      │  Sign-off stored in backend
              └──────────┬───────────┘
                         │
                         ▼
              ┌──────────────────────┐
              │ [9] EXPORT           │  • PDF (browser print)
              │                      │  • FHIR R4 DiagnosticReport JSON
              │                      │  • Copy-to-clipboard plain text
              │                      │  • Audit log (JSONL)
              └──────────┬───────────┘
```

---

## Architecture Diagram

```
┌──────────────────────────────────────────────────────────────────────┐
│                          FRONTEND (Browser)                          │
│                                                                      │
│   React 18 + TypeScript + Vite + Tailwind CSS                        │
│                                                                      │
│   ┌──────────────┐  ┌──────────────┐  ┌───────────────────────────┐  │
│   │ UploadPanel   │  │ DicomViewer  │  │ AIReportPanel             │  │
│   │ (drag & drop) │  │ (canvas,     │  │ (LI-RADS score, findings,│  │
│   │               │  │  scroll,     │  │  radiomics, sign-off,    │  │
│   │               │  │  overlay     │  │  PDF/FHIR export)        │  │
│   │               │  │  toggle)     │  │                           │  │
│   └──────┬───────┘  └──────────────┘  └───────────────────────────┘  │
│          │                                                            │
│          │  Axios HTTP                                                │
└──────────┼────────────────────────────────────────────────────────────┘
           │
           │  REST API (JSON)
           ▼
┌──────────────────────────────────────────────────────────────────────┐
│                       BACKEND (localhost:8000)                        │
│                                                                      │
│   Python 3.11 + FastAPI + Uvicorn                                    │
│                                                                      │
│   API Routes:                                                        │
│   ├── /api/dicom/*        Upload, preview, metadata                  │
│   ├── /api/analysis/*     Pipeline trigger, results, sign-off, FHIR  │
│   ├── /api/rag/*          Query clinical guidelines                  │
│   ├── /api/audit/*        View audit log                             │
│   └── /api/model-card     Model card (markdown)                      │
│                                                                      │
│   Core Modules:                                                      │
│   ├── dicom_processor     Load, de-identify, convert, window         │
│   ├── segmentation        TotalSegmentator liver + lesion masks      │
│   ├── slice_exporter      PNG export, montage builder, overlay       │
│   ├── radiomics_extractor PyRadiomics feature extraction             │
│   ├── rag_engine          ChromaDB vector store + LangChain          │
│   ├── llm_client          Ollama VLM, LI-RADS system prompt         │
│   └── audit_log           Append-only JSONL event logging            │
│                                                                      │
└──────────────────┬───────────────────────────────────────────────────┘
                   │
                   │  HTTP (localhost:11434)
                   ▼
          ┌──────────────────┐
          │  OLLAMA (Local)  │
          │                  │
          │  • medgemma:4b   │  Vision-Language Model
          │  • nomic-embed   │  Embedding Model (for RAG)
          │    -text         │
          └──────────────────┘
```

---

## Tech Stack

### Frontend

| Component | Technology | Purpose |
|---|---|---|
| UI Framework | React 18 + TypeScript | Component-based interface |
| Build Tool | Vite 6 | Fast HMR development server |
| Styling | Tailwind CSS 3 | Utility-first CSS |
| DICOM Rendering | Cornerstone3D v4.22 | WebGL-based medical image rendering |
| DICOM Parsing | dicom-parser | Client-side DICOM header reading |
| File Upload | react-dropzone | Drag-and-drop file handling |
| HTTP Client | Axios | API communication |

### Backend

| Component | Technology | Purpose |
|---|---|---|
| API Framework | FastAPI (Python 3.11) | Async REST API with auto-generated docs |
| DICOM Processing | pydicom 3.x | Read, de-identify, manipulate DICOM files |
| Format Conversion | dicom2nifti + SimpleITK | DICOM → NIfTI for 3D analysis |
| Image Processing | Pillow, OpenCV, NumPy, SciPy | Windowing, overlay blending, montage |
| 3D Volume I/O | nibabel | NIfTI file reading and writing |
| Segmentation | TotalSegmentator 2.3+ | Liver + lesion mask extraction (GPU) |
| Radiomics | PyRadiomics 3.x | 1,000+ quantitative texture/shape features |
| RAG Pipeline | LangChain + ChromaDB | Clinical guideline retrieval |
| VLM Client | Ollama API (OpenAI-compatible) | Local MedGemma 4B inference |
| Embeddings | nomic-embed-text (via Ollama) | Document embedding for RAG |
| Logging | Loguru | Structured application logging |
| Validation | Pydantic 2.x | Request/response data validation |
| Compressed DICOM | pylibjpeg + pylibjpeg-libjpeg | JPEG/JPEG2000 transfer syntax support |

### Infrastructure

| Component | Technology |
|---|---|
| LLM Server | Ollama (local, no data leaves machine) |
| GPU | NVIDIA RTX 4070 (8 GB VRAM), CUDA 12.1 |
| Deep Learning | PyTorch 2.5.1 + CUDA 12.1 |
| OS | Windows 11 Pro |
| Python | 3.11 (scientific stack incompatible with 3.14) |

---

## Project Structure

```
Liver Cancer/
│
├── backend/                          # Python FastAPI backend
│   ├── main.py                       # App entry point, lifespan, CORS, routers
│   ├── config.py                     # Pydantic settings, auto-creates data dirs
│   ├── requirements.txt              # All Python dependencies
│   ├── .env                          # Environment config (Ollama URL, models, device)
│   ├── .env.example                  # Template for .env
│   ├── ruvector.db                   # SQLite database
│   │
│   ├── api/                          # REST API layer
│   │   ├── deps.py                   # Shared dependencies
│   │   └── routes/
│   │       ├── dicom.py              # Upload, preview, metadata endpoints
│   │       ├── analysis.py           # Pipeline trigger, results, sign-off, FHIR, benchmark
│   │       ├── rag.py                # RAG query endpoint
│   │       └── audit.py              # Audit log viewer
│   │
│   ├── core/                         # Business logic modules
│   │   ├── dicom_processor.py        # Load, de-identify, convert, window normalization
│   │   ├── segmentation.py           # TotalSegmentator, mask extraction, volume calc
│   │   ├── slice_exporter.py         # PNG export, montage, segmentation overlay
│   │   ├── radiomics_extractor.py    # PyRadiomics feature extraction (7 classes)
│   │   ├── rag_engine.py             # ChromaDB vector store + LangChain retrieval
│   │   ├── llm_client.py             # Ollama VLM client, LI-RADS system prompt
│   │   └── audit_log.py              # Append-only JSONL audit logger
│   │
│   ├── models/
│   │   └── schemas.py                # Pydantic models (DiagnosticReport, LesionFinding, etc.)
│   │
│   ├── docs/
│   │   └── model_card.md             # Model card (Appendix D for thesis)
│   │
│   └── data/                         # Runtime data (auto-created on startup)
│       ├── uploads/                  # Raw uploaded DICOM/NIfTI files (auto-created)
│       ├── processed/                # Converted NIfTI, PNGs, masks, montages (auto-created)
│       ├── knowledge_base/           # PDF guidelines for RAG ingestion
│       ├── vectordb/                 # ChromaDB persistent vector store
│       └── logs/                     # audit.jsonl — append-only event log
│
├── frontend/                         # React + TypeScript frontend
│   ├── index.html                    # HTML entry point
│   ├── package.json                  # npm dependencies and scripts
│   ├── vite.config.ts                # Vite build configuration
│   ├── tailwind.config.js            # Tailwind CSS configuration
│   ├── tsconfig.json                 # TypeScript configuration
│   │
│   └── src/
│       ├── main.tsx                  # React DOM mount
│       ├── App.tsx                   # Main layout, state management, panel routing
│       ├── index.css                 # Global styles + Tailwind directives
│       │
│       ├── components/
│       │   ├── UploadScreen.tsx       # Upload screen with drag-and-drop zone
│       │   ├── UploadPanel.tsx        # Drag-and-drop DICOM/NIfTI/image upload widget
│       │   ├── PreviewScreen.tsx      # DICOM preview screen before analysis
│       │   ├── DicomViewer.tsx        # Canvas-based slice viewer (scroll, arrow keys, overlay)
│       │   ├── AnalysingScreen.tsx    # Analysis-in-progress screen with live status
│       │   ├── ProgressTracker.tsx    # Pipeline step progress indicator
│       │   ├── ResultsScreen.tsx      # Results display screen (viewer + report)
│       │   ├── AIReportPanel.tsx      # Structured LI-RADS report, radiomics, sign-off, export
│       │   ├── LiRadsScore.tsx        # Color-coded LI-RADS badge component
│       │   ├── ReportPDF.tsx          # PDF report generation component
│       │   ├── HistoryPanel.tsx       # Analysis history panel
│       │   └── Toast.tsx              # Toast notification component
│       │
│       ├── hooks/
│       │   └── useAnalysis.ts         # Analysis state and API call hook
│       │
│       ├── services/
│       │   └── api.ts                 # Axios API client
│       │
│       └── types/
│           └── index.ts               # TypeScript interfaces
│
├── scripts/                          # Utility scripts
│   ├── setup.ps1                     # One-time setup (venv, PyTorch, deps, Ollama, npm)
│   ├── generate_test_dicom.py        # Generates 30 synthetic liver CT DICOM slices
│   ├── ingest_guidelines.py          # Ingests PDF guidelines into ChromaDB
│   ├── run_totalseg.py               # Isolated TotalSegmentator subprocess (Windows fix)
│   ├── batch_validate.py             # Batch validation across all 105 HCC cases
│   ├── summarize_results.py          # Summarize batch validation results
│   ├── verify_deidentification.py    # Verify PHI tag removal from DICOM files
│   ├── download_dicom_datasets.py    # Download datasets from TCIA
│   └── validation_results.csv        # Batch validation results (73 cases completed)
│
├── Pictures/                         # UI screenshots for thesis
│   ├── MainPage.png
│   ├── MainUploadPage.png
│   ├── UIUploadFIleBeforeAnalysis.png
│   ├── UIWhileRunAnalysis.png
│   ├── UIWhileRunAnalysis(GPUProgress(LLM)).png
│   ├── UIResult.png
│   ├── ResultWIthOverlayON.png
│   ├── ResultWithOverlayOFF.png
│   ├── ReportAnalysis.png
│   └── RadiomicFeatures.png
│
├── Personal/                         # Research notes, references & diagram assets
│   ├── Research.md                   # Deep research — liver cancer AI, LI-RADS, model benchmarks
│   ├── Datasets.md                   # Dataset sources and documentation
│   ├── LLMConfusion.md               # LLM model comparison (Ollama vs PyTorch)
│   ├── Reference.md                  # Quick reference links
│   ├── PROGRESS.md                   # Project progress tracking
│   ├── THESIS_TODO.md                # Thesis writing schedule and checklist
│   ├── architecture_diagrams.md      # Mermaid-based architecture diagrams
│   ├── System Architecture Diagram.png
│   ├── AIModelDiagram.png
│   └── Framework&TechnologyStack.png
│
├── docs/
│   └── thesis/
│       ├── chapter1_introduction.md  # Thesis Chapter 1 draft
│       └── diagrams.html             # Printable thesis diagrams (System Architecture,
│                                     #   AI Model, Framework & Technology Stack)
│
├── Launch.bat                        # One-click launcher (starts backend + frontend + browser)
├── start_backend.ps1                 # PowerShell backend start script
├── start_frontend.ps1                # PowerShell frontend start script
├── Radiology-Infer-Mini.md           # Alternative VLM model evaluation notes
├── Merlin.md                         # Merlin 3D CT model evaluation notes
└── CLAUDE.md                         # AI assistant project context
```

---

## Data Flow — Where Comes From Where

This section traces every piece of data through the system, from upload to final report.

### 1. Input Sources

| Input Type | Source | Entry Point |
|---|---|---|
| DICOM files (.dcm) | Uploaded by user from local disk or downloaded from TCIA | `POST /api/dicom/upload` → `backend/data/uploads/` |
| NIfTI files (.nii/.nii.gz) | Pre-converted 3D volumes | `POST /api/dicom/upload` → `backend/data/uploads/` |
| JPEG/PNG images | Direct screenshots or exported slices | `POST /api/dicom/upload` → LLM-only path (no segmentation) |

### 2. De-identification

| What | Where | How |
|---|---|---|
| Patient Name, ID, DOB, etc. | DICOM headers (45+ PHI tags) | `core/dicom_processor.py` → `anonymize_dataset()` strips/replaces all PHI per DICOM PS3.15 BALCP |
| Verification | Post-processing audit | `scripts/verify_deidentification.py` scans output files and flags any remaining PHI |

### 3. Format Conversion

| From | To | Module | Output Location |
|---|---|---|---|
| DICOM series | NIfTI (.nii.gz) | `core/dicom_processor.py` → `dicom2nifti` (primary) + `SimpleITK` (fallback) | `backend/data/processed/{study_id}/` |
| DICOM slices | Windowed PNG | `core/slice_exporter.py` → HU windowing (liver window: W=150, C=30) with smart percentile fallback | `backend/data/processed/{study_id}/slices/` |

### 4. Segmentation

| Input | Model | Output | Module |
|---|---|---|---|
| NIfTI volume | TotalSegmentator (nnU-Net-based, GPU) | Liver mask (NIfTI), Lesion mask (NIfTI) | `core/segmentation.py` |
| Masks | Volume calculation | Liver volume (mL), Lesion count, Max diameter (mm), Couinaud segment | `core/segmentation.py` |
| Masks + CT slices | Overlay blender | Orange (liver) + Red (lesion) overlay PNGs with crosshair + size label | `core/slice_exporter.py` |

### 5. Radiomic Features

| Input | Tool | Output | Module |
|---|---|---|---|
| NIfTI volume + Lesion mask | PyRadiomics | 1,000+ features across 7 classes (shape, firstorder, GLCM, GLRLM, GLSZM, GLDM, NGTDM) via Original + Wavelet + LoG image types | `core/radiomics_extractor.py` |
| Raw features | Summarizer | 35-feature clinical summary with interpretation hints → passed to LLM | `core/radiomics_extractor.py` |

### 6. RAG — Clinical Guideline Retrieval

| Input | Store | Output | Module |
|---|---|---|---|
| 17 clinical guideline PDFs (LI-RADS v2018/v2024, AASLD 2023, EASL 2022, BCLC 2022, KLCA-NCC 2022, + supporting literature) | ChromaDB (local vector database, ~40 MB) | Top-K relevant text chunks matching the current case | `core/rag_engine.py` |
| PDFs placed in `backend/data/knowledge_base/` | Ingested via `scripts/ingest_guidelines.py` | Chunked, embedded with `nomic-embed-text`, stored in `backend/data/vectordb/` | LangChain text splitter + Ollama embeddings |

### 7. LLM Report Generation

| Input (all combined into one prompt) | Model | Output |
|---|---|---|
| • Multi-phase montage PNG (selected slices) | MedGemma 4B (via Ollama) | Structured JSON report containing: |
| • Segmentation metrics (liver vol, lesion size/count) | Running locally on GPU | • LI-RADS category (LR-1 to LR-5, LR-M, LR-TIV) |
| • 35-feature radiomic summary | No data leaves machine | • BCLC stage (0, A, B, C, D) |
| • RAG guideline context (17 PDFs) | | • Individual lesion findings |
| • LI-RADS v2024 criteria (system prompt) | | • Clinical impression |
| • Patient demographics (if available) | | • Recommendations |

### 8. Radiologist Review

| Input | Action | Output | Storage |
|---|---|---|---|
| AI-generated report | Radiologist clicks Approve / Request Changes | Sign-off record (radiologist ID, decision, comments, timestamp) | `POST /api/analysis/signoff/{job_id}` → in-memory job store |
| Approved report | Export | PDF (browser print), FHIR R4 JSON (`GET /api/analysis/fhir/{job_id}`), clipboard text | Downloaded by user |

### 9. Audit Trail

Every significant event is logged to `backend/data/logs/audit.jsonl`:

| Event Type | Data Logged |
|---|---|
| `upload` | Timestamp, study ID, file type, modality |
| `analysis_start` | Timestamp, study ID, model name |
| `analysis_complete` | Timestamp, study ID, model, duration, LI-RADS result |
| `signoff` | Timestamp, study ID, radiologist ID, decision (approve/reject) |

---

## Datasets

The project uses publicly available medical imaging datasets:

| Dataset | Cases | Format | Status | Use |
|---|---|---|---|---|
| **HCC-TACE-Seg** (TCIA) | 105 HCC patients | DICOM (multi-phase CT) | ✅ Downloaded, 73/105 validated | Primary validation — arterial + portal + delayed phases with expert tumor segmentations |
| **TCGA-LIHC** (TCIA) | Variable | DICOM | ✅ Downloaded | Supplementary HCC cases linked to genomic data |
| **LiTS** (Codalab/Kaggle) | 201 CT scans | NIfTI | 📋 Planned | Liver tumor segmentation with ground truth masks |
| **Medical Segmentation Decathlon — Task 08** | 131 CT scans | NIfTI | 📋 Planned | Liver + tumor annotations |
| **CHAOS Challenge** | Variable | MRI (T1, T2) | 📋 Planned | MRI liver segmentation masks |
| **Synthetic test data** | 30 slices | DICOM | ✅ Generated | Generated via `scripts/generate_test_dicom.py` for quick pipeline testing |

> **Note:** The `Datasets/` folder is stored separately and is not included in the repository. Download datasets using `scripts/download_dicom_datasets.py` or place them manually.

---

## Prerequisites

| Requirement | Version | Notes |
|---|---|---|
| Python | 3.11.x | Scientific stack incompatible with 3.14 |
| Node.js | 18+ | For frontend build |
| npm | 9+ | Comes with Node.js |
| NVIDIA GPU | 8+ GB VRAM | For TotalSegmentator and LLM inference |
| CUDA Toolkit | 12.1 | Must match PyTorch build |
| Ollama | Latest | Local LLM server |

---

## Installation & Setup

### Option A: Automated Setup (Recommended)

```powershell
# Run the setup script from the project root
powershell -ExecutionPolicy Bypass -File scripts/setup.ps1
```

This script:
- Creates a Python 3.11 virtual environment at `backend/.venv`
- Installs PyTorch with CUDA 12.1 support
- Installs all Python dependencies from `backend/requirements.txt`
- Pulls Ollama models (`medgemma:4b-it-q8_0`, `nomic-embed-text`)
- Installs frontend npm packages

### Option B: Manual Setup

#### 1. Backend

```powershell
# Create virtual environment
cd backend
python -m venv .venv

# Activate venv
.\.venv\Scripts\Activate.ps1

# Install PyTorch with CUDA
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121

# Install all dependencies
pip install -r requirements.txt

# Verify CUDA
python -c "import torch; print(torch.cuda.is_available())"
# Expected: True
```

#### 2. Frontend

```powershell
cd frontend
npm install
```

#### 3. Ollama Models

*(Note: MedGemma 4B is sideloaded via GGUF and `Modelfile`. See `Radiology-Infer-Mini.md` for alternative model options).*

```powershell
ollama pull nomic-embed-text
```

#### 4. Environment Configuration

```powershell
# Copy the example env file
cp backend/.env.example backend/.env
# Edit values as needed (defaults work for local development)
```

#### 5. Ingest Clinical Guidelines for RAG

The knowledge base ships with 17 clinical guideline PDFs (LI-RADS, AASLD, EASL, BCLC, KLCA-NCC). To rebuild the vector store:

```powershell
& backend\.venv\Scripts\python.exe scripts/ingest_guidelines.py
```

To add new guidelines, place PDFs into `backend/data/knowledge_base/` and re-run the ingestion script.

---

## Running the Application

### Option A: One-Click Launch

Double-click **`Launch.bat`** in the project root. This starts:
- Backend (FastAPI) at `http://localhost:8000`
- Frontend (Vite dev server) at `http://localhost:5173`
- Opens the browser automatically

### Option B: Manual Start

**Terminal 1 — Backend:**
```powershell
cd backend
.\.venv\Scripts\uvicorn.exe main:app --reload --port 8000
```

**Terminal 2 — Frontend:**
```powershell
cd frontend
npm run dev
```

**Terminal 3 — Ollama (if not running as a service):**
```powershell
ollama serve
```

Then open `http://localhost:5173` in your browser.

### Using the App

1. **Upload** — Drag and drop a DICOM folder, NIfTI file, or image into the upload panel
2. **Preview** — The DICOM viewer immediately displays slices; use arrow keys, scroll wheel, or slider to navigate
3. **Analyze** — Click "Run Analysis" to trigger the full pipeline (progress shown step-by-step)
4. **Review** — Read the AI-generated LI-RADS report, toggle segmentation overlay, view radiomic features
5. **Sign Off** — Enter radiologist name/ID, approve or request changes with comments
6. **Export** — Download as PDF, FHIR R4 JSON, or copy report text to clipboard

---

## API Endpoints

The backend provides auto-generated interactive documentation at `http://localhost:8000/docs` (Swagger UI).

### Key Endpoints

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/dicom/upload` | Upload DICOM, NIfTI, or image files |
| `GET` | `/api/dicom/preview/{study_id}` | Get instant DICOM slice preview |
| `GET` | `/api/dicom/metadata/{study_id}` | Get study metadata |
| `POST` | `/api/analysis/run/{study_id}` | Trigger full analysis pipeline |
| `GET` | `/api/analysis/result/{job_id}` | Get analysis results |
| `POST` | `/api/analysis/signoff/{job_id}` | Submit radiologist sign-off |
| `GET` | `/api/analysis/fhir/{job_id}` | Get FHIR R4 DiagnosticReport JSON |
| `GET` | `/api/analysis/benchmark/{job_id}` | Get per-step timing breakdown |
| `POST` | `/api/rag/query` | Query clinical guidelines |
| `GET` | `/api/audit` | View audit log (filterable by event type) |
| `GET` | `/api/model-card` | Get model card (markdown) |
| `GET` | `/health` | Health check + RAG chunk count |

---

## Screenshots

All screenshots are available in the `Pictures/` directory:

| Screenshot | Description |
|---|---|
| `MainPage.png` | Application landing page |
| `MainUploadPage.png` | Upload interface with drag-and-drop |
| `UIUploadFIleBeforeAnalysis.png` | DICOM loaded, ready for analysis |
| `UIWhileRunAnalysis.png` | Pipeline running — progress indicator |
| `UIWhileRunAnalysis(GPUProgress(LLM)).png` | GPU segmentation + LLM inference in progress |
| `UIResult.png` | Full results view |
| `ResultWIthOverlayON.png` | CT slice with segmentation overlay enabled |
| `ResultWithOverlayOFF.png` | CT slice with segmentation overlay disabled |
| `ReportAnalysis.png` | AI-generated LI-RADS report panel |
| `RadiomicFeatures.png` | Radiomic feature display |

---

## Validation & Compliance

### Batch Validation Results (as of June 3, 2026)

| Metric | Value |
|---|---|
| Cases processed | 73 / 105 (HCC-TACE-Seg) |
| LI-RADS LR-4 (Probably HCC) | 71 / 73 (97.3%) |
| LI-RADS parse failures | 2 / 73 (HCC_042, HCC_050 — empty LI-RADS field) |
| BCLC Stage A | 71 / 73 (97.3%) |
| APHE detected | 71 / 71 scored cases (100%) |
| Washout detected | 71 / 71 scored cases (100%) |
| Avg. processing time | ~140s per case (conversion + segmentation + radiomics + RAG + LLM) |
| LLM model | MedGemma 4B (medgemma:4b-it-q8_0) via Ollama |

> ⚠️ **Note:** All 105 HCC-TACE-Seg cases are confirmed HCC, so the expected LI-RADS is LR-4 or LR-5. The 100% LR-4 rate suggests the model may under-classify some LR-5 cases. Remaining 32 cases pending.

### De-identification

- 45+ PHI tags stripped per DICOM PS3.15 Basic Application Level Confidentiality Profile
- Verification script: `scripts/verify_deidentification.py`
- All processing runs locally — no patient data is transmitted to external servers

### Audit Logging

- Append-only JSONL log at `backend/data/logs/audit.jsonl`
- Tracks uploads, analyses, and sign-offs with timestamps
- Queryable via `GET /api/audit` endpoint

### Radiologist-in-the-Loop

- PDF and FHIR export are blocked until a licensed radiologist provides a signed review
- Every report includes a prominent disclaimer: *"AI decision support only — not a clinical diagnosis"*

### RAG Knowledge Base

17 clinical guideline PDFs ingested into ChromaDB vector store (~40 MB):

| Guideline | Source |
|---|---|
| LI-RADS CT/MRI v2018 Diagnosis | ACR |
| LI-RADS CT/MR Radiation TRA v2024 | ACR |
| LI-RADS Lexicon (June 2021) | ACR |
| AASLD 2023 HCC Practice Guidance | AASLD |
| AASLD Critical Update | AASLD |
| EASL 2022 HCC Clinical Practice Guidelines | EASL / Journal of Hepatology |
| BCLC 2022 Staging Update | Journal of Hepatology |
| KLCA-NCC 2022 Korean HCC Guidelines | Clinical and Molecular Hepatology |
| + 9 supporting hepatology papers | Various journals |

### Regulatory Status

| Framework | Status |
|---|---|
| EU AI Act (High-Risk AI) | Under review — research context only |
| CE marking / FDA 510(k) | Not applicable — research prototype |
| HIPAA | PHI de-identified before processing; no external data transmission |

---

## Known Limitations

| Limitation | Impact |
|---|---|
| MedGemma 4B is a compact model | May still hallucinate or struggle with extremely complex LI-RADS edge cases |
| 4B parameter constraint | Lower raw reasoning accuracy than frontier models like Qwen2.5-VL-72B or GPT-4o |
| LR-4 over-classification | Batch validation shows 100% LR-4 — model may not distinguish LR-5 cases |
| Many cases report 28mm lesion / Segment VI | Suggests segmentation pipeline defaults when no clear lesion mask is found |
| TotalSegmentator `liver_lesions` task | Optimized for abdominal CT; may miss small (<10mm) lesions |
| Radiomics require a segmentation mask | Image-only uploads skip quantitative feature extraction |
| In-memory job store | All analysis jobs are lost on server restart (no persistent database) |
| Single-user design | Not built for concurrent multi-user clinical deployment |
| Windows-specific subprocess isolation | TotalSegmentator requires `__main__` guard workaround on Windows |

---

## Roadmap

| Phase | Status | Description |
|---|---|---|
| **Phase 1** — Proof of Concept | ✅ Complete (May 26) | DICOM upload → de-identify → export → LLM report → display |
| **Phase 2** — Segmentation | ✅ Complete (May 27) | TotalSegmentator liver/lesion masks, overlay toggle, size labels |
| **Phase 3** — Full Pipeline | ✅ Complete (May 27) | PyRadiomics, LI-RADS scoring, sign-off workflow, audit log, PDF/FHIR export |
| **Phase 4** — Validation & Compliance | ✅ Complete (May 27) | Benchmarking, de-id verification, model card, compliance review |
| **Phase 5** — Batch Validation | 🔄 In Progress (73/105) | 73 HCC-TACE-Seg cases validated, 32 remaining. RAG knowledge base populated (17 PDFs). |
| **Phase 6** — Thesis Writing | 🔄 In Progress | Chapter 1 drafted. Diagrams (System Architecture, AI Model, Framework) created. Target: September 2026. |

### Immediate (June 2026)

- Complete remaining 32/105 HCC-TACE-Seg batch validation cases
- Calculate sensitivity, specificity, AUC, Cohen's κ for LI-RADS agreement
- Investigate LR-4 over-classification (no LR-5 cases detected)
- Investigate "28mm / Segment VI" default pattern in segmentation
- ~~Write Chapter 1 (Introduction)~~ ✅ Draft complete
- Write Chapter 2 (Literature Review)
- Write Chapter 3 (System Design) — architecture diagrams ready

### Future Improvements (Post-Thesis)

- Switch to GPT-4o via Azure OpenAI for higher accuracy (requires HIPAA BAA)
- Add MedSAM for interactive lesion marking (click → mask)
- Multi-phase comparison view (arterial + portal + delayed side by side)
- DWI / ADC map support for MRI
- Orthanc PACS server integration (DICOM send/receive)
- User authentication (OAuth2 + MFA)
- Train nnU-Net on LiTS dataset for improved liver segmentation
- Mobile responsive design

---

## License

This project is an academic research prototype. All datasets used are publicly available through their respective sources (TCIA, Codalab, etc.) under their original licenses. The project code is intended for educational and research purposes.

---

## Contact

- **Project:** Liver Cancer AI Diagnostics (Thesis)
- **Title:** AI-Powered Liver Cancer Diagnosis from MRI/CT Scans Using LLMs
- **Email:** stevntbank77@gmail.com
- **API Docs:** `http://localhost:8000/docs` (when backend is running)
