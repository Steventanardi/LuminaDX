# Liver Cancer AI Diagnostics — Thesis To-Do List

**Project:** AI-Powered Liver Cancer Diagnosis from MRI/CT Scans Using LLMs  
**Status:** Phases 1–4 Complete ✅ — Ahead of schedule · Focus: data collection + thesis writing  
**Last Updated:** 2026-06-02

Legend: `[ ]` Not started · `[~]` In progress / ready to extract · `[x]` Done

---

## PART A — ENVIRONMENT & INFRASTRUCTURE

### A1. Development Environment
- [x] Install Ollama (local LLM server)
- [x] Pull llava:7b vision model via Ollama *(switched from llama3.2-vision:11b — not available)*
- [x] Pull nomic-embed-text embedding model via Ollama
- [x] Install Python 3.11
- [x] Create Python virtual environment (`backend/.venv`)
- [x] Install PyTorch 2.5.1 with CUDA 12.1
- [x] Upgrade pip inside venv
- [x] Install all backend Python packages (`requirements.txt`)
- [x] Verify CUDA is working (`torch.cuda.is_available()` returns True)
- [x] Install Node.js + npm
- [x] Install frontend npm packages
- [x] Create `backend/.env` config file

### A2. Project Structure
- [x] FastAPI backend scaffolded
- [x] React + TypeScript frontend scaffolded
- [x] DICOM processing module written
- [x] Segmentation module written
- [x] Radiomics module written
- [x] LLM client module written
- [x] RAG engine module written
- [x] API routes written (DICOM, Analysis, RAG, Audit)
- [x] Frontend components written (Viewer, Upload, Report, Progress)
- [x] Synthetic test DICOM data generated (30 slices)

---

## PART B — PHASE 1: PROOF OF CONCEPT ✅

*Goal: Upload DICOM → process → get AI report → display in browser*

### B1. Get the App Running
- [x] Start backend (`uvicorn main:app`)
- [x] Start frontend (`npm run dev`)
- [x] Open browser at `http://localhost:5173` — confirm UI loads
- [x] Upload synthetic test DICOM (`Datasets/sample_ct/series_arterial/`)
- [x] Confirm upload endpoint receives files (check backend logs)
- [x] Confirm DICOM de-identification runs (PHI tags stripped)
- [x] Confirm slice PNG export works (windowed CT images)
- [x] Confirm LLM receives montage and returns JSON report
- [x] Confirm frontend displays the AI report *(LR-4 Probably HCC displayed correctly)*
- [x] Keyboard navigation in DICOM viewer (arrow keys)
- [x] Slice scroll slider in DICOM viewer
- [x] Mouse wheel scroll in DICOM viewer *(2026-05-27)*

### B2. Fix Runtime Issues
- [x] Fix TotalSegmentator CLI not in PATH → subprocess approach
- [x] Fix wrong task name `liver_vessels_and_tumors` → `liver_lesions`
- [x] Fix Windows multiprocessing crash → isolated subprocess with `__main__` guard
- [x] Fix LLM model mismatch → updated `.env` to `llava:7b`
- [x] Confirm all API routes respond correctly

### B3. Test With Real DICOM Data
- [x] Download public liver CT with known tumor *(HCC-TACE-Seg: 105 confirmed HCC cases downloaded 2026-06-02)*
- [x] Upload real DICOM study and run full pipeline *(HCC_001 → LR-4 Probably HCC ✅ 2026-06-02)*
- [x] Verify phase detection works *(HCC-TACE-Seg is multi-phase CT — arterial + portal series per case)*
- [ ] Verify modality detection works *(needs MRI DICOM)*
- [x] Verify NIfTI conversion succeeds
- [x] Verify windowing *(smart HU fallback — percentile-based when >90% pixels dark)*
- [x] Check LLM report quality *(LR-4, BCLC-A, recommendations generated)*
- [x] Add NIfTI upload support (.nii / .nii.gz)
- [x] Add JPEG/PNG upload support — LLM-only path

### B4. UI Polish
- [x] Disclaimer banner *(amber bar + report footer + print window)*
- [x] Loading spinner during analysis *(ProgressTracker + viewer overlay)*
- [x] Error messages for failed uploads and analysis jobs
- [x] File size / format validation on upload
- [x] Responsive slice viewer
- [x] Phase label on each DICOM slice
- [x] Instant DICOM preview after upload *(pydicom pixel extraction)*
- [x] Smart HU windowing fallback
- [x] One-click launcher *(Launch.bat)*

---

## PART C — PHASE 2: SEGMENTATION ✅

*Goal: Add automated liver and lesion detection with visual overlay*

### C1. TotalSegmentator Integration
- [x] Test TotalSegmentator on synthetic + real NIfTI
- [x] Confirm liver mask generated correctly
- [~] Confirm lesion mask generated *(liver_lesions task runs; synthetic data has no lesion — verify with TCIA)*
- [x] Extract lesion size in mm (max diameter) *(28mm on test case)*
- [~] Extract lesion volume in mL *(code complete — `volume_ml` field passed to LLM — verify with real tumor mask)*
- [x] Estimate Couinaud segment location *(Segment VI reported by LLM)*
- [x] Calculate total liver volume

### C2. Segmentation Overlay in Viewer
- [x] Liver mask → orange overlay (server-side Pillow)
- [x] Lesion mask → red overlay (server-side Pillow)
- [x] Blend overlay onto CT slice
- [x] Toggle overlay ON/OFF in viewer *(frontend toggle; backend serves both raw + overlaid)*
- [x] Lesion size label on overlay *(crosshair at tumor centroid + "L1: 28mm" — 2026-05-27)*

### C3. Feed Segmentation to LLM
- [x] Pass liver volume to LLM prompt
- [x] Pass lesion size and count to LLM prompt
- [~] Programmatic Couinaud segment from centroid *(LLM infers from image; geometric estimation deferred)*
- [x] Verified LLM uses segmentation data in its report

---

## PART D — PHASE 3: FULL PIPELINE ✅

*Goal: Complete clinical-grade workflow with radiomics, LI-RADS scoring, and sign-off*

### D1. PyRadiomics Feature Extraction
- [x] Extract radiomic features — all 7 classes (shape, firstorder, glcm, glrlm, glszm, gldm, ngtdm) *(2026-05-27)*
- [x] >1,000 features via Original + Wavelet + LoG image types *(2026-05-27)*
- [x] LLM receives structured 35-feature summary with clinical interpretation hints *(2026-05-27)*
- [ ] Verify radiomics improves LLM report quality *(needs real tumor mask — TCIA data)*

### D2. RAG — Clinical Guidelines
- [ ] Download LI-RADS v2024 PDF from ACR website *(acr.org/Clinical-Resources/Reporting-and-Data-Systems/LI-RADS)*
- [ ] Download AASLD 2023 HCC guidelines PDF
- [ ] Place both PDFs in `backend/data/knowledge_base/`
- [ ] Run `python scripts/ingest_guidelines.py`
- [ ] Verify guideline chunks retrieved during analysis
- [ ] Verify LLM cites guidelines in report

### D3. LI-RADS Scoring Refinement
- [x] LR-1 through LR-5 criteria in system prompt with exact size thresholds *(2026-05-27)*
- [x] LR-M (non-HCC malignancy) criteria in system prompt *(2026-05-27)*
- [x] LR-TIV (tumour in vein) criteria in system prompt *(2026-05-27)*
- [x] APHE, washout, capsule logic — explicit major/ancillary feature guidance *(2026-05-27)*
- [x] BCLC-0/A/B/C/D staging guide in system prompt *(2026-05-27)*
- [ ] Verify LR category accuracy against radiologist ground truth *(needs TCIA data)*

### D4. Radiologist Review Workflow
- [x] Approve / Request Changes buttons with comments field *(2026-05-27)*
- [x] Radiologist name / ID field *(2026-05-27)*
- [x] Sign-off stored in backend (`POST /api/analysis/signoff/{job_id}`) *(2026-05-27)*
- [x] Sign-off badge displayed in report panel *(2026-05-27)*

### D5. Audit Logging
- [x] Upload events logged (timestamp, study ID, type, modality) *(2026-05-27)*
- [x] Analysis events logged (start + complete with model + duration) *(2026-05-27)*
- [x] Sign-off events logged (radiologist ID, decision) *(2026-05-27)*
- [x] Append-only JSONL at `backend/data/logs/audit.jsonl` *(2026-05-27)*
- [x] Audit log viewer — `GET /api/audit?n=100&event=signoff` *(2026-05-27)*

### D6. Report Export
- [x] PDF — Print/PDF button → clean print window → browser Save as PDF *(2026-05-27)*
- [x] FHIR R4 DiagnosticReport JSON — `GET /api/analysis/fhir/{job_id}` + download button *(2026-05-27)*
- [x] Copy-to-clipboard plain text *(2026-05-27)*

---

## PART E — PHASE 4: VALIDATION & COMPLIANCE

*Goal: Make the tool thesis-defensible and clinically responsible*

### E1. Retrospective Validation
- [x] Collect 20–50 de-identified liver CT/MRI cases *(HCC-TACE-Seg: 105 confirmed HCC cases + TCGA-LIHC downloaded 2026-06-02)*
- [x] First case confirmed: HCC_001 → LR-4 Probably HCC *(pipeline works on real HCC DICOM 2026-06-02)*
- [ ] Write batch validation script (`scripts/batch_validate.py`) — auto-runs all 105 cases, saves results CSV
- [ ] Run all 105 HCC-TACE-Seg cases through the pipeline
- [ ] Compare AI LI-RADS scores against ground truth *(all cases are confirmed HCC → expected LR-4 or LR-5)*
- [ ] Calculate sensitivity, specificity, AUC for HCC detection
- [ ] Calculate LI-RADS category agreement rate (Cohen's κ)
- [ ] Document failure cases and error analysis
- [ ] Write validation results section for thesis

### E2. Performance Benchmarking
- [x] Per-step timing in `AnalysisJob.timings` (conversion, segmentation, radiomics, RAG, LLM) *(2026-05-27)*
- [x] `GET /api/analysis/benchmark/{job_id}` endpoint *(2026-05-27)*
- [ ] Run benchmarks on 10+ cases and record results *(data available — do alongside batch validation)*
- [ ] Document results in thesis Ch.5 table *(target: August 2026)*

### E3. Safety & Compliance
- [x] DICOM de-id — `anonymize_dataset` covers 45+ PHI tags per PS3.15 BALCP *(2026-05-27)*
- [x] Verification script — `scripts/verify_deidentification.py` *(2026-05-27)*
- [x] No patient data sent to external API — all inference local via Ollama *(confirmed in model card)*
- [x] Prominent disclaimer on every report page *(UI + print window)*
- [x] Radiologist-in-loop enforcement — export blocked until sign-off *(2026-05-27)*
- [~] EU AI Act High-Risk AI review *(documented in model card as "under review" — needs formal analysis for thesis Ch.6)*
- [x] Model card — `backend/docs/model_card.md` — `GET /api/model-card` *(2026-05-27)*

---

## PART F — THESIS DOCUMENT

### F1. Writing — Core Chapters *(all target dates below)*
- [ ] **Chapter 1: Introduction** — liver cancer burden, AI motivation, objectives, scope *(target: Jun 1)*
- [ ] **Chapter 2: Literature Review** — existing tools, LI-RADS, VLMs in radiology, research gap *(target: Jun 15)*
- [ ] **Chapter 3: Methodology** — architecture, pipeline, model selection, dataset *(target: Jul 1)*
- [ ] **Chapter 4: Implementation** — tech stack, backend/frontend, segmentation, LLM prompts *(target: Jul 15)*
- [ ] **Chapter 5: Results & Validation** — metrics, benchmarks, case studies, failures *(target: Aug 1)*
- [ ] **Chapter 6: Discussion** — interpretation, limitations, ethics, regulatory *(target: Aug 15)*
- [ ] **Chapter 7: Conclusion** — summary, contributions, future work *(target: Aug 25)*
- [ ] **Abstract** — 250–300 words, written last *(target: Aug 30)*
- [ ] **References** — IEEE or APA, minimum 40 sources *(build throughout writing)*

### F2. Figures & Diagrams
- [ ] System architecture diagram *(draw.io / Lucidchart — can do now, no data needed)*
- [ ] LI-RADS scoring rubric table *(can write now)*
- [ ] Screenshot: frontend UI with DICOM viewer *(take now — app is running)*
- [ ] Screenshot: AI report panel with LI-RADS score *(take now — app is running)*
- [ ] Screenshot: segmentation overlay on CT slice *(take now — app is running)*
- [ ] ROC curve for HCC detection *(needs validation data — after TCIA download)*
- [ ] Confusion matrix for LI-RADS categories *(needs validation data)*
- [ ] Processing time bar chart *(run benchmark on 10+ cases via /api/analysis/benchmark)*

### F3. Supporting Documents / Appendices
- [~] **Appendix A: Full LLM system prompt** *(ready — copy from `backend/core/llm_client.py` `_SYSTEM` + `_build_prompt`)*
- [~] **Appendix B: Radiomic features list** *(ready — copy `_SUMMARY_FEATURES` + feature class list from `radiomics_extractor.py`)*
- [~] **Appendix C: DICOM de-identification tag list** *(ready — copy `PHI_TAGS` list from `scripts/verify_deidentification.py`)*
- [x] **Appendix D: API documentation** *(FastAPI auto-docs at `http://localhost:8000/docs` — always available)*
- [ ] Ethics approval / IRB waiver *(contact university ethics board — de-identified public data may be exempt)*

---

## PART G — OPTIONAL IMPROVEMENTS (Post-Thesis / Extra Credit)

- [ ] Switch LLM to GPT-4o via Azure OpenAI (higher accuracy, needs BAA)
- [ ] Add MedSAM for interactive lesion marking (click → mask)
- [ ] Add multi-phase comparison view (arterial + portal + delayed side by side)
- [ ] Add DWI / ADC map support for MRI
- [ ] Add Orthanc PACS server integration (DICOM send/receive)
- [ ] Deploy to AWS with HIPAA BAA (production-grade)
- [ ] Add user authentication (OAuth2 + MFA)
- [ ] Add case history / patient list view
- [ ] Train nnU-Net on LiTS dataset for better liver segmentation
- [ ] Mobile responsive design
- [ ] Programmatic Couinaud segment estimation from tumor centroid

---

## Current Priority Order

```
✅ DONE — All coding complete (finished 2026-05-27, ~6 weeks ahead of original July target)
✅ DONE — HCC-TACE-Seg 105 cases + TCGA-LIHC downloaded (2026-06-02)
✅ DONE — HCC_001 verified: pipeline → LR-4 Probably HCC (2026-06-02)

IMMEDIATE (this week — June 2026):
1. ⚠️  Write batch validation script (scripts/batch_validate.py) → runs all 105 cases, saves results to CSV
2. ⚠️  Download LI-RADS v2024 PDF (acr.org) + AASLD 2023 PDF → place in backend/data/knowledge_base/
3. ⚠️  Run: python scripts/ingest_guidelines.py
4. ✏️  Take screenshots of the app (UI, report panel, overlay) — 30 minutes
5. ✏️  Write Chapter 1: Introduction (OVERDUE — was Jun 1)
6. ✏️  Write Chapter 2: Literature Review (target: Jun 15)

ALSO THIS WEEK:
7. 🔬  Run all 105 HCC-TACE-Seg cases through pipeline (use batch script)
8. 📊  Collect LI-RADS scores + benchmark timings per case → results CSV

JULY 2026:
9. ✏️  Write Chapter 3: Methodology (target: Jul 1)
10. ✏️  Write Chapter 4: Implementation (target: Jul 15)
11. 📊  Compile validation + benchmark results → Ch.5 tables and charts
```

---

## Thesis Deadline Tracking

**Start Date:** 2026-05-05  
**Hard Deadline:** 2026-12-31 (official)  
**Personal Target:** 2026-10-31 (leaves 2 months for revision buffer)

| Milestone | Original Deadline | Actual / Status |
|---|---|---|
| Phase 1 complete | 2026-05-25 | ✅ 2026-05-26 |
| Phase 2 complete (segmentation overlay) | 2026-06-15 | ✅ 2026-05-27 (3 weeks early) |
| Phase 3 complete (full pipeline) | 2026-07-15 | ✅ 2026-05-27 (7 weeks early) |
| Phase 4 (benchmarking, compliance, model card) | 2026-07-15 | ✅ 2026-05-27 (7 weeks early) |
| Download validation dataset | 2026-05-31 | ✅ HCC-TACE-Seg (105 cases) + TCGA-LIHC — 2026-06-02 |
| First case pipeline verification | 2026-06-02 | ✅ HCC_001 → LR-4 Probably HCC |
| RAG PDFs ingested | 2026-06-15 | ⚠️ Pending — needs PDFs |
| Batch validation (all 105 cases) | 2026-06-30 | Not Started |
| Start writing Ch.1 Introduction | 2026-06-01 | Not Started |
| Start writing Ch.2 Literature Review | 2026-06-15 | Not Started |
| Validation experiments done | 2026-07-31 | Not Started |
| Start writing Ch.3 Methodology | 2026-07-01 | Not Started |
| Start writing Ch.4 Implementation | 2026-07-15 | Not Started |
| Start writing Ch.5 Results & Validation | 2026-08-01 | Not Started |
| Start writing Ch.6 Discussion | 2026-08-15 | Not Started |
| Start writing Ch.7 Conclusion + Abstract | 2026-08-25 | Not Started |
| All figures and diagrams done | 2026-09-01 | Not Started |
| **First full thesis draft complete** | **2026-09-15** | Not Started |
| Submit draft to supervisor for feedback | 2026-09-15 | Not Started |
| Incorporate supervisor feedback (Round 1) | 2026-10-05 | Not Started |
| Second draft — proofreading + formatting | 2026-10-20 | Not Started |
| **Personal submission target** | **2026-10-31** | Not Started |
| Revision buffer (supervisor Round 2) | Nov 2026 | Not Started |
| **Hard deadline submission** | **2026-12-31** | Not Started |

---

## Monthly Plan (Updated 2026-05-27)

### May 2026 — Coding Sprint ✅ COMPLETE
- ~~Phase 1: full pipeline~~ ✅
- ~~Phase 2: segmentation overlay~~ ✅
- ~~Phase 3: radiomics, RAG, LI-RADS, sign-off, audit, PDF/FHIR~~ ✅
- ~~Phase 4: benchmarking, de-id audit, model card, compliance~~ ✅
- **Still to do this month:**
  - Register on TCIA + request LiTS dataset
  - Download LI-RADS v2024 PDF + AASLD 2023 PDF → run ingest

### June 2026 — Writing Sprint (Weeks 5–8)
- Take all UI screenshots (30 min — do first day of June)
- Draw system architecture diagram (draw.io)
- As soon as TCIA data arrives: run 20–50 cases, collect benchmark + accuracy numbers
- Ingest RAG PDFs if not done in May
- **Write:** Chapter 1 (Introduction) — *target: June 1–7*
- **Write:** Chapter 2 (Literature Review) — *target: June 8–22*
- Start building reference list (Zotero / Mendeley — target 40+ sources)
- ⚠️ Coding is DONE — no new features unless a critical bug appears

### July 2026 — Validation + Writing (Weeks 9–12)
- Finish running all TCIA validation cases through the pipeline
- Calculate: sensitivity, specificity, AUC, Cohen's κ
- Generate ROC curve, confusion matrix, benchmark bar chart
- **Write:** Chapter 3 (Methodology) — *target: July 1–10*
- **Write:** Chapter 4 (Implementation) — *target: July 11–20*
- Start Chapter 5 (Results) as validation data comes in

### August 2026 — Results + Discussion (Weeks 13–17)
- **Write:** Chapter 5 (Results & Validation) — *target: Aug 1–12*
- **Write:** Chapter 6 (Discussion) — limitations, ethics, EU AI Act — *target: Aug 13–22*
- **Write:** Chapter 7 (Conclusion) + Abstract — *target: Aug 23–30*
- Finalise all appendices (copy from code — see F3 above)
- First complete draft target: September 15

### September 2026 — First Full Draft
- Compile complete thesis document
- Check all references (minimum 40 sources, IEEE or APA)
- Finalize all figures, tables, appendices
- Proofread entire document
- Submit to supervisor by **September 15**

### October 2026 — Revision Round 1
- Incorporate supervisor feedback
- Fix structure, arguments, formatting
- Second proofread pass
- **Submit personal target: October 31**
- November + December = safety buffer

### November–December 2026 — Buffer
- Supervisor revision round 2 if needed
- Final formatting and submission
- **Hard deadline: December 31**
