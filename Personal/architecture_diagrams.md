# Liver Cancer AI Diagnostics — Architecture Diagrams

> These diagrams document the complete system architecture, AI model pipeline, and technology framework for the **Liver Cancer AI Diagnostics** thesis project. All diagrams are rendered using Mermaid and are suitable for embedding in thesis chapters.

---

## 1. System Architecture Diagram

This diagram shows the **three-tier architecture**: browser-based frontend, Python FastAPI backend with core processing modules, and local AI inference services. All components run on a single machine — no patient data ever leaves the host.

```mermaid
graph TB
    subgraph BROWSER["🖥️ Frontend — Browser (localhost:5173)"]
        direction TB
        UI["React 18 + TypeScript + Vite 6"]
        
        subgraph SCREENS["UI Screens"]
            direction LR
            US["UploadScreen<br/>Drag & Drop"]
            PS["PreviewScreen<br/>DICOM Viewer"]
            AS["AnalysingScreen<br/>Progress Tracker"]
            RS["ResultsScreen<br/>Report + Overlay"]
        end

        subgraph COMPONENTS["UI Components"]
            direction LR
            UP["UploadPanel"]
            DV["DicomViewer<br/>(Canvas-based)"]
            ARP["AIReportPanel<br/>LI-RADS + BCLC"]
            LRS["LiRadsScore<br/>Badge"]
            PT["ProgressTracker"]
            HP["HistoryPanel"]
            RP["ReportPDF<br/>Export"]
            TOAST["Toast<br/>Notifications"]
        end

        subgraph FE_SERVICES["Services & Hooks"]
            API_SVC["api.ts<br/>(Axios HTTP Client)"]
            HOOK["useAnalysis<br/>Hook"]
        end
    end

    subgraph BACKEND["⚙️ Backend — FastAPI (localhost:8000)"]
        direction TB
        MAIN["main.py<br/>App Entry + CORS + Lifespan"]

        subgraph API_LAYER["API Layer (REST + WebSocket)"]
            direction LR
            R_DICOM["/api/dicom/*<br/>Upload, Preview,<br/>Metadata, Files"]
            R_ANALYSIS["/api/analysis/*<br/>Start, Status, Report,<br/>Slices, Sign-off,<br/>FHIR, Benchmark"]
            R_RAG["/api/rag/*<br/>Query, Ingest,<br/>Status"]
            R_AUDIT["/api/audit<br/>Event Viewer"]
            R_HEALTH["/health<br/>Health Check"]
            R_MODEL["/api/model-card<br/>Appendix D"]
            WS["/api/analysis/ws<br/>WebSocket Progress"]
        end

        subgraph CORE["Core Processing Modules"]
            direction TB
            DP["dicom_processor.py<br/>• Load DICOM series<br/>• De-identify PHI (45+ tags)<br/>• DICOM → NIfTI conversion<br/>• HU windowing"]
            SEG["segmentation.py<br/>• TotalSegmentator subprocess<br/>• Liver + lesion masks<br/>• Volume calculation<br/>• Lesion extraction (scipy)"]
            SE["slice_exporter.py<br/>• PNG rendering (HU/MRI)<br/>• Overlay blending<br/>• Montage builder<br/>• Crosshair annotation"]
            RE["radiomics_extractor.py<br/>• PyRadiomics (7 classes)<br/>• 1,000+ features<br/>• Clinical interpretation<br/>• 35-feature summary"]
            RAG["rag_engine.py<br/>• ChromaDB vector store<br/>• PDF ingestion (LangChain)<br/>• Cosine similarity retrieval<br/>• Top-K context"]
            LLM["llm_client.py<br/>• OpenAI-compatible client<br/>• LI-RADS v2024 system prompt<br/>• Multi-modal (image+text)<br/>• JSON response parsing"]
            AUDIT["audit_log.py<br/>• Append-only JSONL<br/>• Thread-safe writes<br/>• Upload/Analysis/Sign-off"]
        end

        subgraph MODELS["Data Models"]
            SCHEMAS["schemas.py (Pydantic 2.x)<br/>DicomStudy, DiagnosticReport,<br/>LesionFinding, LiRadsCategory,<br/>AnalysisJob, SignOff,<br/>PatientContext, FHIR export"]
        end

        CONFIG["config.py<br/>Pydantic Settings<br/>(.env file)"]
    end

    subgraph AI_SERVICES["🤖 AI Services (Local)"]
        direction LR
        subgraph OLLAMA["Ollama Server (localhost:11434)"]
            MEDGEMMA["MedGemma 4B<br/>(medgemma:4b-it-q8_0)<br/>Vision-Language Model"]
            NOMIC["nomic-embed-text<br/>Embedding Model<br/>(768-dim vectors)"]
        end
        TOTALSEG["TotalSegmentator 2.3+<br/>(nnU-Net backbone)<br/>Subprocess with<br/>__main__ guard"]
    end

    subgraph DATA_STORES["💾 Data Stores (Local Filesystem)"]
        direction LR
        UPLOADS["data/uploads/<br/>Raw DICOM/NIfTI"]
        PROCESSED["data/processed/<br/>NIfTI, masks,<br/>PNGs, montages"]
        KB["data/knowledge_base/<br/>17 clinical PDFs"]
        VDB["data/vectordb/<br/>ChromaDB (~40 MB)"]
        LOGS["data/logs/<br/>audit.jsonl"]
        RUVECTOR["ruvector.db<br/>(SQLite)"]
    end

    %% Frontend → Backend
    API_SVC -->|"HTTP REST (JSON)<br/>Axios"| MAIN
    HOOK -->|"WebSocket<br/>Progress updates"| WS

    %% Backend internal
    MAIN --> R_DICOM & R_ANALYSIS & R_RAG & R_AUDIT & R_HEALTH & R_MODEL
    R_DICOM --> DP
    R_ANALYSIS --> DP & SEG & SE & RE & RAG & LLM & AUDIT
    R_RAG --> RAG
    R_AUDIT --> AUDIT
    R_ANALYSIS --> SCHEMAS

    %% Core → AI Services
    SEG -->|"subprocess<br/>(sys.executable)"| TOTALSEG
    LLM -->|"HTTP POST<br/>/v1/chat/completions"| MEDGEMMA
    RAG -->|"HTTP POST<br/>/api/embed"| NOMIC

    %% Core → Data
    DP --> UPLOADS & PROCESSED
    SEG --> PROCESSED
    SE --> PROCESSED
    RAG --> KB & VDB
    AUDIT --> LOGS

    %% Styling
    classDef frontend fill:#1a1a2e,stroke:#e94560,color:#eee
    classDef backend fill:#0f3460,stroke:#16213e,color:#eee
    classDef ai fill:#533483,stroke:#e94560,color:#eee
    classDef data fill:#1a1a2e,stroke:#0f3460,color:#ccc

    class BROWSER frontend
    class BACKEND backend
    class AI_SERVICES ai
    class DATA_STORES data
```

---

## 2. AI Model Diagram

This diagram traces the **end-to-end AI/ML pipeline** — from raw medical image upload through every processing stage to the final structured diagnostic report with radiologist sign-off.

```mermaid
flowchart TD
    subgraph INPUT["📁 INPUT"]
        direction LR
        DICOM["DICOM Series<br/>(multi-phase CT/MRI)"]
        NIFTI["NIfTI Volume<br/>(.nii.gz)"]
        IMG["JPEG / PNG<br/>(direct image)"]
    end

    subgraph STAGE1["Stage 1 — De-identification"]
        DEID["PHI Removal<br/>(pydicom)<br/>━━━━━━━━━━━━<br/>• 45+ PHI tags stripped<br/>• DICOM PS3.15 BALCP<br/>• Patient ID → ANON_XXXX<br/>• Name → ANONYMIZED"]
    end

    subgraph STAGE2["Stage 2 — Format Conversion"]
        CONV["DICOM → NIfTI<br/>━━━━━━━━━━━━<br/>Primary: dicom2nifti<br/>Fallback: SimpleITK<br/>• Compression + Reorient"]
        PHASE["Phase Detection<br/>━━━━━━━━━━━━<br/>• SeriesDescription parsing<br/>• Keyword matching<br/>• Priority: Arterial → Portal<br/>  → Delayed → Non-contrast"]
        WINDOW["HU Windowing<br/>━━━━━━━━━━━━<br/>CT: C=50, W=400<br/>MRI: Percentile 0.5–99.5<br/>Fallback: Smart percentile"]
    end

    subgraph STAGE3["Stage 3 — Segmentation (GPU)"]
        direction TB
        TS_LIVER["TotalSegmentator<br/>Task: total<br/>ROI: liver<br/>━━━━━━━━━━━━<br/>• nnU-Net backbone<br/>• Fast mode enabled<br/>• Output: liver.nii.gz"]
        TS_TUMOR["TotalSegmentator<br/>Task: liver_lesions<br/>━━━━━━━━━━━━<br/>• Dedicated lesion model<br/>• Output: liver_lesions.nii.gz"]
        EXTRACT["Lesion Extraction<br/>(scipy.ndimage.label)<br/>━━━━━━━━━━━━<br/>• Connected components<br/>• Min 8 voxels<br/>• Max diameter (mm)<br/>• Volume (mL)<br/>• Centroid coordinates"]
        VOL["Volume Calculation<br/>━━━━━━━━━━━━<br/>• Voxel spacing from NIfTI header<br/>• Liver volume (mL)<br/>• Lesion volume (mL)"]
    end

    subgraph STAGE4["Stage 4 — Slice Processing"]
        RENDER["Slice Rendering<br/>━━━━━━━━━━━━<br/>• Best slice selection<br/>  (max tumor area)<br/>• HU / MRI normalization<br/>• 512×512 resize"]
        OVERLAY["Overlay Blending<br/>━━━━━━━━━━━━<br/>• Liver: Orange (α=70)<br/>• Tumor: Crimson (α=130)<br/>• Crosshair + size label"]
        MONTAGE["Montage Builder<br/>━━━━━━━━━━━━<br/>• Up to 4 phases<br/>• 2-column grid layout<br/>• Phase labels (ARTERIAL,<br/>  PORTAL VENOUS, etc.)"]
    end

    subgraph STAGE5["Stage 5 — Radiomics"]
        PYRAD["PyRadiomics 3.x<br/>━━━━━━━━━━━━<br/>Image Types: Original + Wavelet + LoG<br/>σ = [1.0, 2.0, 3.0]<br/><br/>7 Feature Classes:<br/>① Shape (volume, diameter, sphericity)<br/>② First-order (mean, entropy, skewness)<br/>③ GLCM (contrast, correlation, energy)<br/>④ GLRLM (short/long run emphasis)<br/>⑤ GLSZM (zone entropy)<br/>⑥ GLDM (dependence entropy)<br/>⑦ NGTDM (coarseness, contrast)"]
        SUMMARY["35-Feature Clinical Summary<br/>━━━━━━━━━━━━<br/>• Organized by category<br/>• Interpretation hints:<br/>  – Sphericity → shape regularity<br/>  – Skewness → necrosis indicator<br/>  – Entropy → heterogeneity<br/>  – Coarseness → texture grade"]
    end

    subgraph STAGE6["Stage 6 — RAG Retrieval"]
        EMBED["Query Embedding<br/>(nomic-embed-text)<br/>━━━━━━━━━━━━<br/>• 768-dim vector<br/>• via Ollama API"]
        CHROMA["ChromaDB Vector Search<br/>━━━━━━━━━━━━<br/>• Cosine similarity<br/>• Top-5 chunks<br/>• Threshold: >0.25 similarity"]
        GUIDELINES["17 Clinical Guideline PDFs<br/>━━━━━━━━━━━━<br/>• LI-RADS v2018 / v2024<br/>• AASLD 2023<br/>• EASL 2022<br/>• BCLC 2022<br/>• KLCA-NCC 2022<br/>• 9 supporting papers<br/><br/>Ingestion: LangChain<br/>RecursiveTextSplitter<br/>(500 chars, 50 overlap)"]
    end

    subgraph STAGE7["Stage 7 — VLM Analysis"]
        PROMPT["Prompt Assembly<br/>━━━━━━━━━━━━<br/>Inputs combined:<br/>① Montage PNG (base64)<br/>② Segmentation metrics<br/>③ Radiomic summary (35 features)<br/>④ RAG guideline excerpts<br/>⑤ Patient context (optional)<br/>⑥ LI-RADS v2024 system prompt"]
        VLM["MedGemma 4B<br/>(medgemma:4b-it-q8_0)<br/>━━━━━━━━━━━━<br/>• Google medical VLM<br/>• Q8_0 quantization<br/>• Temperature: 0.05<br/>• Max tokens: 2048<br/>• Multi-modal (image + text)<br/>• Local via Ollama"]
        PARSE["JSON Response Parser<br/>━━━━━━━━━━━━<br/>• Strip markdown fences<br/>• Fallback: regex { } extraction<br/>• Map to Pydantic models<br/>• LI-RADS enum validation"]
    end

    subgraph OUTPUT["📊 OUTPUT"]
        direction TB
        REPORT["Structured Diagnostic Report<br/>━━━━━━━━━━━━<br/>• Overall impression<br/>• Per-lesion findings:<br/>  – Location (Couinaud segment)<br/>  – Size (mm)<br/>  – LI-RADS category (LR-1→LR-5/M/TIV)<br/>  – APHE / Washout / Capsule<br/>  – Major + Ancillary features<br/>  – Reasoning<br/>• BCLC stage (0/A/B/C/D)<br/>• Vascular involvement<br/>• Differential diagnosis<br/>• Guideline citations<br/>• Recommendations"]
        SIGNOFF["Radiologist Sign-off<br/>━━━━━━━━━━━━<br/>• Approve / Request Changes<br/>• Radiologist ID + comments<br/>• Timestamp"]
        EXPORT["Export Formats<br/>━━━━━━━━━━━━<br/>• PDF (browser print)<br/>• FHIR R4 DiagnosticReport<br/>• Clipboard (plain text)<br/>• Audit log (JSONL)"]
    end

    %% Flow
    DICOM --> DEID
    NIFTI --> CONV
    IMG -->|"Skip segmentation<br/>(image-only path)"| PROMPT

    DEID --> CONV
    DEID --> PHASE
    CONV --> STAGE3
    PHASE --> MONTAGE

    TS_LIVER --> VOL
    TS_TUMOR --> EXTRACT
    EXTRACT --> VOL

    CONV --> RENDER
    VOL --> RENDER
    RENDER --> OVERLAY
    OVERLAY --> MONTAGE

    CONV --> PYRAD
    TS_TUMOR --> PYRAD
    PYRAD --> SUMMARY

    SUMMARY --> PROMPT
    MONTAGE --> PROMPT
    VOL --> PROMPT

    EMBED --> CHROMA
    CHROMA --> GUIDELINES
    CHROMA --> PROMPT

    PROMPT --> VLM
    VLM --> PARSE
    PARSE --> REPORT
    REPORT --> SIGNOFF
    SIGNOFF --> EXPORT

    %% Styling
    classDef input fill:#2d3436,stroke:#00b894,color:#eee
    classDef process fill:#0f3460,stroke:#e94560,color:#eee
    classDef ai fill:#533483,stroke:#e94560,color:#eee
    classDef output fill:#1a1a2e,stroke:#f39c12,color:#eee

    class INPUT input
    class STAGE1,STAGE2,STAGE4 process
    class STAGE3,STAGE5,STAGE6,STAGE7 ai
    class OUTPUT output
```

---

## 3. Framework & Technology Stack Diagram

This diagram shows the **layered technology framework** — every library, tool, and service organized by architectural tier with their specific roles.

```mermaid
graph TB
    subgraph PRESENTATION["🎨 Presentation Layer"]
        direction TB
        subgraph FE_CORE["Core Framework"]
            REACT["React 18<br/>Component UI"]
            TS["TypeScript 5.x<br/>Type Safety"]
            VITE["Vite 6<br/>Dev Server + HMR"]
        end
        subgraph FE_STYLING["Styling"]
            TW["Tailwind CSS 3<br/>Utility-first CSS"]
            POSTCSS["PostCSS<br/>CSS Processing"]
        end
        subgraph FE_LIBS["Libraries"]
            AXIOS["Axios<br/>HTTP Client"]
            DROPZONE["react-dropzone<br/>File Upload"]
            CORNER["Cornerstone3D v4.22<br/>DICOM WebGL Rendering"]
            DCMPARSE["dicom-parser<br/>Client DICOM Reading"]
        end
    end

    subgraph APPLICATION["⚙️ Application Layer"]
        direction TB
        subgraph BE_CORE["Core Framework"]
            PYTHON["Python 3.11<br/>Runtime"]
            FASTAPI["FastAPI<br/>Async REST API"]
            UVICORN["Uvicorn<br/>ASGI Server"]
            PYDANTIC["Pydantic 2.x<br/>Data Validation"]
        end
        subgraph BE_MEDICAL["Medical Imaging"]
            PYDICOM["pydicom 3.x<br/>DICOM I/O"]
            D2N["dicom2nifti<br/>Format Conversion"]
            SITK["SimpleITK<br/>Fallback Conversion"]
            NIBABEL["nibabel<br/>NIfTI I/O"]
            PYLIBJPEG["pylibjpeg<br/>JPEG Transfer Syntax"]
        end
        subgraph BE_IMAGING["Image Processing"]
            PIL["Pillow<br/>Image Rendering"]
            OPENCV["OpenCV<br/>Computer Vision"]
            NUMPY["NumPy<br/>Array Operations"]
            SCIPY["SciPy<br/>Connected Components"]
        end
        subgraph BE_UTIL["Utilities"]
            LOGURU["Loguru<br/>Structured Logging"]
            THREADING["threading<br/>Audit Log Safety"]
        end
    end

    subgraph AI_ML["🧠 AI / ML Layer"]
        direction TB
        subgraph SEGMENTATION["Segmentation Engine"]
            TOTALSEG2["TotalSegmentator 2.3+<br/>Liver + Lesion Segmentation"]
            NNUNET["nnU-Net<br/>(Backbone Architecture)"]
            PYTORCH["PyTorch 2.5.1<br/>+ CUDA 12.1"]
        end
        subgraph RADIOMICS_ENGINE["Radiomics Engine"]
            PYRADIOMICS["PyRadiomics 3.x<br/>1,000+ Features"]
        end
        subgraph RAG_STACK["RAG Stack"]
            LANGCHAIN["LangChain<br/>Document Loading +<br/>Text Splitting"]
            CHROMADB["ChromaDB<br/>Vector Database"]
            OLLAMA_EMB["nomic-embed-text<br/>(via Ollama)<br/>768-dim Embeddings"]
        end
        subgraph VLM_STACK["Vision-Language Model"]
            OLLAMA_SRV["Ollama Server<br/>Local LLM Runtime"]
            MEDGEMMA2["MedGemma 4B<br/>(Q8_0 Quantized)<br/>Google Medical VLM"]
            OPENAI_SDK["OpenAI Python SDK<br/>(Ollama-compatible<br/>API client)"]
        end
    end

    subgraph DATA_LAYER["💾 Data & Storage Layer"]
        direction LR
        subgraph FILE_STORAGE["File System"]
            FS_UPLOADS["uploads/<br/>Raw DICOM/NIfTI"]
            FS_PROCESSED["processed/<br/>NIfTI + Masks + PNGs"]
            FS_KB["knowledge_base/<br/>17 Clinical PDFs"]
        end
        subgraph DB_STORAGE["Databases"]
            CHROMA_DB["ChromaDB<br/>~40 MB Vector Store<br/>(Persistent, HNSW)"]
            SQLITE["ruvector.db<br/>(SQLite)"]
            JSONL["audit.jsonl<br/>Append-only Log"]
        end
        subgraph MEMORY["In-Memory"]
            JOB_STORE["Dict[str, AnalysisJob]<br/>Job State Store"]
            SLICE_CACHE["Dict[str, List[str]]<br/>Base64 Slice Cache"]
        end
    end

    subgraph INFRA["🏗️ Infrastructure Layer"]
        direction LR
        subgraph HARDWARE["Hardware"]
            GPU["NVIDIA RTX 4070<br/>8 GB VRAM"]
            CUDA["CUDA 12.1<br/>GPU Compute"]
        end
        subgraph OS_ENV["Environment"]
            WIN["Windows 11 Pro<br/>Host OS"]
            VENV["Python venv<br/>Isolated Environment"]
            NODE["Node.js 18+<br/>Frontend Runtime"]
            NPM["npm 9+<br/>Package Manager"]
        end
        subgraph COMPLIANCE["Compliance & Safety"]
            DEID2["DICOM PS3.15<br/>De-identification"]
            LOCAL["100% Local<br/>No External APIs"]
            AUDIT2["JSONL Audit Trail<br/>Immutable Logging"]
            HITL["Human-in-the-Loop<br/>Radiologist Sign-off"]
        end
    end

    %% Layer connections
    PRESENTATION -->|"REST API<br/>(JSON over HTTP)"| APPLICATION
    APPLICATION -->|"subprocess +<br/>HTTP API"| AI_ML
    APPLICATION -->|"File I/O +<br/>DB queries"| DATA_LAYER
    AI_ML -->|"GPU Compute<br/>Model Inference"| INFRA
    DATA_LAYER -->|"Persistent<br/>Storage"| INFRA

    %% Styling
    classDef pres fill:#1a1a2e,stroke:#e94560,color:#eee
    classDef app fill:#0f3460,stroke:#16213e,color:#eee
    classDef ai fill:#533483,stroke:#e94560,color:#eee
    classDef data fill:#2d3436,stroke:#00b894,color:#eee
    classDef infra fill:#1a1a2e,stroke:#f39c12,color:#eee

    class PRESENTATION pres
    class APPLICATION app
    class AI_ML ai
    class DATA_LAYER data
    class INFRA infra
```

---

## Quick Reference Table

| Diagram | Purpose | Thesis Chapter |
|---|---|---|
| **System Architecture** | Shows how frontend, backend, AI services, and data stores connect | Chapter 3 — System Design |
| **AI Model Pipeline** | Traces data flow from raw image → structured report through all 7 stages | Chapter 4 — Implementation |
| **Framework & Stack** | Catalogs every technology by architectural layer | Chapter 3 — System Design |

---

> **Note:** All three diagrams reflect the codebase as of June 8, 2026. Key source files:
> - Backend entry: [main.py](file:///d:/Steven Project/Liver Cancer/backend/main.py)
> - Core pipeline: [analysis.py](file:///d:/Steven Project/Liver Cancer/backend/api/routes/analysis.py)
> - Segmentation: [segmentation.py](file:///d:/Steven Project/Liver Cancer/backend/core/segmentation.py)
> - VLM client: [llm_client.py](file:///d:/Steven Project/Liver Cancer/backend/core/llm_client.py)
> - RAG engine: [rag_engine.py](file:///d:/Steven Project/Liver Cancer/backend/core/rag_engine.py)
> - Radiomics: [radiomics_extractor.py](file:///d:/Steven Project/Liver Cancer/backend/core/radiomics_extractor.py)
> - Frontend app: [App.tsx](file:///d:/Steven Project/Liver Cancer/frontend/src/App.tsx)
> - Data models: [schemas.py](file:///d:/Steven Project/Liver Cancer/backend/models/schemas.py)
