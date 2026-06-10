# Reference — Similar Research & Theses

> Papers and theses that are **identical or similar** to this project:
> *"AI-Powered Liver Cancer Diagnosis from MRI/CT Scans Using Vision-Language Models"*

---

## 🔴 MOST SIMILAR — End-to-End Liver AI + LLM/VLM + RAG Systems

These are the closest matches to your thesis — they combine imaging AI with language models and/or RAG for liver cancer.

### 1. LiVersa — Liver Disease-Specific LLM with RAG
- **Title:** "Development of a liver disease-specific large language model chat interface using retrieval-augmented generation"
- **Authors:** Ge J, Sun S, Owens J, Galvez V, Gologorskaya O, Lai JC, Pletcher MJ, Lai K
- **Year:** 2024
- **Venue:** *Hepatology*
- **DOI:** `10.1097/HEP.0000000000000834`
- **Free Full Text (PMC):** https://www.ncbi.nlm.nih.gov/pmc/articles/PMC11706764/
- **Why Similar:** Uses RAG with AASLD guidelines (same approach as your project) to ground LLM outputs for HCC management. Privacy-preserving, PHI-compliant. Directly comparable RAG architecture.

### 2. PHENO-RAG — RAG for HCC Clinical Management
- **Title:** "PHENO-RAG: Retrieval-Augmented Generation for Hepatocellular Carcinoma Clinical Management"
- **Authors:** (Multiple — check PMC)
- **Year:** 2024
- **Venue:** PubMed Central
- **Link:** https://pubmed.ncbi.nlm.nih.gov/ (search: "PHENO-RAG hepatocellular carcinoma")
- **Why Similar:** RAG-based system using clinical guidelines for HCC treatment allocation and decision support. Tests multiple LLMs (Llama-3, Qwen-3) — very similar to your Ollama/MedGemma approach.

### 3. LiverAI — GPT-4 for LI-RADS Categorization
- **Title:** "LiverAI: A GPT-4-Based Model for Automated LI-RADS Feature Extraction and Categorization"
- **Authors:** (Search on ResearchGate/PubMed)
- **Year:** 2024
- **Why Similar:** Uses LLM to automate LI-RADS categorization from radiology reports. Your project does the same but adds imaging + segmentation + radiomics in the pipeline.

---

## 🟠 HIGHLY RELEVANT — Automated LI-RADS Classification with Deep Learning

### 4. Fully Automating LI-RADS on MRI with Deep Learning
- **Title:** "Fully automating LI-RADS on MRI with deep learning"
- **Year:** 2024
- **Free Full Text (PMC):** https://pubmed.ncbi.nlm.nih.gov/ (search title)
- **Why Similar:** End-to-end DL pipeline: segmentation → feature characterization (APHE, washout, capsule) → LI-RADS score. Two-step architecture similar to your pipeline.

### 5. Deep Learning for LI-RADS Major Features Classification
- **Title:** "Development of a deep-learning model for classification of LI-RADS major features from MRI"
- **Authors:** (Elsevier Pure — search title)
- **Year:** 2024–2025
- **Why Similar:** Multi-task DL model that classifies APHE, washout, and capsule — the same features your VLM evaluates.

### 6. LiLNet — Liver Lesion Network for HCC Classification
- **Title:** "LiLNet: Accurate Deep Learning-Based Focal Liver Lesion Diagnosis from CT"
- **Year:** 2023–2024
- **Link:** Search PubMed/ResearchGate for "LiLNet focal liver lesion"
- **Why Similar:** CNN-based model for liver lesion detection and classification achieving ~94.7% accuracy. Benchmark comparison for your VLM approach.

### 7. Deep Learning for HCC Segmentation — Systematic Review
- **Title:** "Deep learning for hepatocellular carcinoma segmentation in MRI: A systematic review"
- **Year:** 2024–2025
- **Free Full Text:** https://pubmed.ncbi.nlm.nih.gov/ (search title)
- **Why Similar:** Comprehensive review of nnU-Net and U-Net++ models for liver/lesion segmentation — directly relevant to your TotalSegmentator component.

---

## 🟡 RELEVANT — VLM Radiology Report Generation

### 8. RaDialog — Vision-Language Model for Radiology Reports
- **Title:** "RaDialog: A Large Vision-Language Model for Radiology Report Generation and Conversational Assistance"
- **Authors:** Pellegrini C, et al.
- **Year:** 2023 (accepted MIDL 2025)
- **arXiv:** https://arxiv.org/abs/2311.18681
- **Why Similar:** VLM that generates structured radiology reports with human-in-the-loop correction — architecturally very similar to your system (VLM + radiologist review).

### 9. Concept-Enhanced RAG for Radiology Report Generation
- **Title:** (Search: "concept-enhanced RAG radiology report generation" on DiVA Portal / arXiv)
- **Year:** 2024
- **Why Similar:** Decomposes visual features into clinical concepts before language generation — matches your approach of feeding segmentation + radiomics to the VLM.

### 10. Multimodal Foundation Models for Radiology Report Generation — Survey
- **Title:** "From CNN-RNN to Multimodal Foundation Models: A Survey on Radiology Report Generation"
- **Year:** 2024
- **Link:** Search on arXiv or Frontiers in AI
- **Why Similar:** Comprehensive survey covering the evolution from traditional to VLM-based report generation. Excellent for your Literature Review (Chapter 2).

---

## 🟢 RELEVANT — Component-Level Research

### A. Segmentation

#### 11. TotalSegmentator (Core Paper)
- **Title:** "TotalSegmentator: Robust Segmentation of 104 Anatomic Structures in CT Images"
- **Authors:** Wasserthal J, et al.
- **Year:** 2023
- **Venue:** *Radiology: Artificial Intelligence*, vol. 5, no. 5, e230024
- **DOI:** `10.1148/ryai.230024`
- **Already in your references as [14]**

#### 12. LiTS — Liver Tumor Segmentation Benchmark
- **Title:** "The liver tumor segmentation benchmark (LiTS)"
- **Authors:** Bilic D, et al.
- **Year:** 2023
- **Venue:** *Medical Image Analysis*, vol. 84, 102680
- **Already in your references as [12]**

### B. Radiomics for HCC

#### 13. Radiomics for Microvascular Invasion in HCC
- **Title:** "Radiomic analysis of contrast-enhanced CT predicts microvascular invasion and outcome in hepatocellular carcinoma"
- **Authors:** Xu X, et al.
- **Year:** 2019
- **Venue:** *Journal of Hepatology*, vol. 70, no. 6, pp. 1133–1144
- **Already in your references as [16] — note: verify this is the correct citation (your Improvements.md flagged [16] as wrong)**

#### 14. PyRadiomics (Core Paper)
- **Title:** "Computational Radiomics System to Decode the Radiographic Phenotype"
- **Authors:** van Griethuysen JJM, et al.
- **Year:** 2017
- **Venue:** *Cancer Research*, vol. 77, no. 21, pp. e104–e107
- **Already in your references as [17]**

### C. Privacy-Preserving Medical AI

#### 15. Privacy-Preserving Local LLMs for Healthcare
- **Title:** Search: "local LLM deployment HIPAA medical imaging privacy" on PubMed/arXiv
- **Year:** 2024–2025
- **Why Similar:** Growing body of work on running open-source LLMs locally (via Ollama, vLLM) for HIPAA compliance — your project is a practical implementation of this paradigm.

### D. LI-RADS Standards

#### 16. LI-RADS v2018 Inter-Reader Agreement
- **Title:** "Inter-reader agreement of LI-RADS v2018 for CT and MRI: A systematic review and meta-analysis"
- **Authors:** van der Pol AG, et al.
- **Year:** 2021
- **Venue:** *European Radiology*, vol. 31, no. 11, pp. 8526–8538
- **Already in your references as [8]**

#### 17. LI-RADS v2024 Update
- **Title:** "LI-RADS CT/MR Radiation Treatment Response Algorithm v2024"
- **Authors:** American College of Radiology
- **Year:** 2024
- **Link:** https://www.acr.org/Clinical-Resources/Clinical-Tools-and-Reference/Reporting-and-Data-Systems/LI-RADS
- **Already in your references as [7]**

---

## 📥 Download Links — Key Papers (Free Access)

| # | Paper | Free PDF Link |
|---|-------|---------------|
| 1 | LiVersa (RAG + LLM for Liver Disease) | https://www.ncbi.nlm.nih.gov/pmc/articles/PMC11706764/ |
| 2 | RaDialog (VLM for Radiology Reports) | https://arxiv.org/abs/2311.18681 |
| 3 | TotalSegmentator | https://pubs.rsna.org/doi/10.1148/ryai.230024 |
| 4 | PyRadiomics | https://aacrjournals.org/cancerres/article/77/21/e104/662617 |
| 5 | LiTS Benchmark | https://doi.org/10.1016/j.media.2022.102680 |
| 6 | LI-RADS v2018 Inter-Reader Agreement | https://doi.org/10.1007/s00330-021-08199-8 |
| 7 | LLaVA (Visual Instruction Tuning) | https://arxiv.org/abs/2304.08485 |
| 8 | RAG (Lewis et al.) | https://arxiv.org/abs/2005.11401 |
| 9 | MedGemma Technical Report | https://arxiv.org/abs/2505.10757 |

---

## 🔍 Recommended Search Queries (for finding more)

Use these queries on **Google Scholar**, **PubMed**, or **arXiv** to find additional similar work:

1. `"LI-RADS" "deep learning" "automated" classification CT MRI 2024`
2. `"vision language model" radiology report liver cancer`
3. `"retrieval augmented generation" hepatocellular carcinoma clinical guidelines`
4. `"end-to-end" liver segmentation radiomics LLM report`
5. `"privacy preserving" local LLM medical imaging DICOM de-identification`
6. `TotalSegmentator liver lesion PyRadiomics`
7. `"clinical decision support" liver cancer AI web application`

---

## 📎 Original Quick References

LI-RADS PDF GUIDELINE
https://www.acr.org/Clinical-Resources/Clinical-Tools-and-Reference/Reporting-and-Data-Systems/LI-RADS

INGEST GUIDELINES
cd "D:\Steven Project\Liver Cancer"                                                              
  backend\.venv\Scripts\python.exe scripts/ingest_guidelines.py

https://www.journal-of-hepatology.eu/action/showPdf?pii=S0168-8278%2821%2902223-6
https://www.acr.org/Clinical-Resources/Clinical-Tools-and-Reference/Reporting-and-Data-Systems/LI-RADS
https://pubmed.ncbi.nlm.nih.gov/36263666/
