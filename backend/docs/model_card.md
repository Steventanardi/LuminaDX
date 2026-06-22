# Model Card — Liver Cancer AI Diagnostic System

**Version:** 1.1.0  
**Date:** 2026-06-03  
**Author:** Thesis project — AI-Powered Liver Cancer Diagnosis from MRI/CT Scans Using LLMs  
**Intended Use:** Research / academic demonstration only — NOT for clinical use

---

## 1. Model Details

| Field | Value |
|---|---|
| Base model | MedGemma 4B (medgemma:4b via Ollama) |
| Model type | Vision-Language Model (VLM) — medical domain |
| Architecture | Gemma 3 4B + SigLIP vision encoder, fine-tuned on medical data by Google DeepMind |
| Parameters | ~4 billion |
| Quantisation | 4-bit (Q4_K_M via llama.cpp) |
| Inference runtime | Ollama (local, CPU/GPU) |
| Context window | 8192 tokens |

---

## 2. Intended Use

### Primary use
AI-assisted **decision support** for liver lesion characterisation on CT/MRI using LI-RADS v2024 criteria.

The system:
1. Accepts DICOM, NIfTI, or image uploads
2. Performs automated liver/lesion segmentation (TotalSegmentator)
3. Extracts quantitative radiomic features (PyRadiomics, >1 000 features)
4. Retrieves relevant clinical guideline text (RAG, ChromaDB)
5. Presents all findings to the LLM to generate a structured LI-RADS report

### Out-of-scope use
- **NOT** a standalone diagnostic device
- **NOT** approved or intended for clinical patient management
- **NOT** validated for paediatric liver disease, non-HCC primary tumours, or transplant contexts
- Must NOT be used as the sole basis for clinical decisions

---

## 3. Training Data

MedGemma 4B was fine-tuned by Google DeepMind on medical literature, radiology reports, and medical imaging datasets (including CT and MRI). It was **not** specifically fine-tuned on liver MRI/CT data. Liver-specific knowledge is injected at inference time via:
- A detailed LI-RADS v2024 + BCLC staging system prompt
- RAG retrieval from LI-RADS v2024 PDF and AASLD 2023 guidelines (when available)
- Quantitative segmentation + radiomics input in the user prompt

---

## 4. Evaluation

### Qualitative evaluation (Phase 1)
- Tested on synthetic DICOM dataset (30 slices, simulated liver phantom)
- LI-RADS LR-4 category correctly assigned on initial test
- BCLC-A staging correctly inferred from lesion size and count

### Planned quantitative evaluation (Phase 5 — July 2026)
- 20–50 de-identified liver CT/MRI cases from TCIA (LiTS dataset)
- Metrics: sensitivity, specificity, AUC for HCC detection
- LI-RADS category agreement: Cohen's κ vs. radiologist ground truth
- Expected in Chapter 5 (Results) of the thesis

### Skin — HAM10000 classifier (ResNet50, measured 2026-06-16)
Held-out HAM10000 validation split (1,499 images, stratified seed-42 15%), scored
via `backend/scripts/skin/eval_skin.py --ham-split --tta`:
- **7-class top-1: 89.4%** (val-acc baked into checkpoint: 88.9%)
- **Malignant-vs-benign:** accuracy 0.937, sensitivity 0.808, specificity 0.968, **ROC-AUC 0.959** (TTA, threshold 0.5)
- Screening operating point (sens ≥ 0.90): threshold ≈ 0.15 → sens 0.95 / spec 0.71
- Inference uses the **same PIL preprocessing as training** (a prior cv2.resize
  path aliased the images and cost ~6% accuracy — fixed). Test-time augmentation
  (4 flip views) adds ~+1% acc / +1.8 AUC.
- ⚠ Bounded by HAM10000's distribution; not a substitute for histopathology.

---

## 5. Known Limitations

| Limitation | Impact |
|---|---|
| Not fine-tuned on liver MRI/CT | May hallucinate or misclassify rare lesion subtypes |
| MedGemma 4B is a compact model | Lower accuracy than larger models (GPT-4V, Med-PaLM); mitigated by structured radiomics input |
| RAG only active when PDFs are ingested | Reports without RAG lack guideline citations |
| TotalSegmentator liver_lesions task | Optimised for abdominal CT; may miss small (<10mm) lesions |
| Radiomics require segmentation mask | Image-only uploads skip quantitative feature extraction |
| In-memory job store | All jobs lost on server restart (no persistent database) |
| Single-user design | Not built for concurrent multi-user clinical deployment |
| Synthetic test data | Results on phantoms may not reflect real clinical performance |

---

## 6. Ethical Considerations

- All DICOM uploads are **de-identified** on receipt per DICOM PS3.15 Basic Application Level Confidentiality Profile (45+ PHI tags removed/replaced — see `scripts/shared/verify_deidentification.py`)
- All inference runs **locally** — no patient data leaves the machine
- **Radiologist-in-the-loop**: PDF and FHIR export are blocked until a licensed radiologist provides a signed review
- Every upload, analysis, and sign-off is logged in an append-only audit file (`backend/data/logs/audit.jsonl`)
- Prominent disclaimer shown in the UI: *"AI decision support only — not a clinical diagnosis"*

---

## 7. Regulatory Status

| Framework | Status |
|---|---|
| EU AI Act (High-Risk AI — medical device) | Under review — thesis context only |
| CE marking / FDA 510(k) | Not applicable — research prototype |
| ISO 13485 (medical device QMS) | Not applicable |
| HIPAA (US) | PHI de-identified before processing; no data transmitted externally |

This system is a **research prototype** for a university thesis. It is **not** a certified medical device and must not be used for patient care.

---

## 8. Technical Contact

- **Project:** Liver Cancer AI Diagnostics (MSc/PhD Thesis)
- **Email:** stevntbank77@gmail.com
- **Codebase:** `D:\Steven Project\Liver Cancer\`
- **API docs:** `http://localhost:8000/docs` (when backend is running)
