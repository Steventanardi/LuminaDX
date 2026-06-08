Deep Research: AI-Powered Liver Cancer Diagnosis from MRI/CT                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            
  ---                                                                                                                                                                                                                                                                          1. The Medical Problem You're Solving                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     Liver cancer diagnosis from imaging centers on three cancer types:                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        ┌────────────────────────────────┬─────────────────────┬──────────────────┬────────────────────────────┐                                                                                                                                                                   
  │             Cancer             │     Prevalence      │ Primary Modality │        Key Protocol        │
  ├────────────────────────────────┼─────────────────────┼──────────────────┼────────────────────────────┤
  │ HCC (Hepatocellular Carcinoma) │ 75-85% of cases     │ MRI / CT         │ LI-RADS scoring            │
  ├────────────────────────────────┼─────────────────────┼──────────────────┼────────────────────────────┤
  │ Cholangiocarcinoma (CCA)       │ ~10-15%             │ MRI / CT         │ Target sign on DWI         │
  ├────────────────────────────────┼─────────────────────┼──────────────────┼────────────────────────────┤
  │ Metastatic                     │ Most common overall │ CT               │ Multiplicity, distribution │
  └────────────────────────────────┴─────────────────────┴──────────────────┴────────────────────────────┘

  What radiologists look for on MRI (the gold standard):
  - Arterial phase hyperenhancement (APHE) — HCC "lights up" from hepatic artery neovascularity
  - Washout — HCC becomes dark on portal venous / delayed phases
  - Enhancing capsule — smooth rim around the tumor
  - LI-RADS score (LR-1 through LR-5) — the standardized scoring rubric for HCC probability
  - DWI restricted diffusion — distinguishes malignancy from benign lesions
  - Hepatobiliary phase — HCC appears dark on gadoxetate-enhanced MRI (20 min post-injection)

  The key challenge: HCC diagnosis requires reading multi-phase dynamics (how the lesion enhances and washes out over time), not a single image. This is what makes it hard for general VLMs.

  ---
  2. The State of AI for Liver Cancer (What Actually Works)

  Specialized Deep Learning Models (Best Accuracy)

  ┌────────────────────────────────┬────────────────────────────────────────────────────┬──────────────────────────────────────┬──────────────────────────────┐
  │             Model              │                    What It Does                    │             Performance              │            Status            │
  ├────────────────────────────────┼────────────────────────────────────────────────────┼──────────────────────────────────────┼──────────────────────────────┤
  │ LiLNet (Nature Commun. 2024)   │ Classifies HCC / CCA / Metastatic / Benign from CT │ AUC 95.6%, ACC 88.7%                 │ Research code                │
  ├────────────────────────────────┼────────────────────────────────────────────────────┼──────────────────────────────────────┼──────────────────────────────┤
  │ SALSA (Cell Reports Med. 2025) │ Detects & segments all liver tumors in CE-CT       │ Patient detection 99.65%, Dice 0.760 │ Research code                │
  ├────────────────────────────────┼────────────────────────────────────────────────────┼──────────────────────────────────────┼──────────────────────────────┤
  │ TotalSegmentator (2025 update) │ Liver + lesion segmentation on CT and MRI          │ Dice ~0.87                           │ Open source, pip installable │
  ├────────────────────────────────┼────────────────────────────────────────────────────┼──────────────────────────────────────┼──────────────────────────────┤
  │ nnU-Net                        │ Gold standard segmentation framework               │ Dice >0.90 on liver tumors           │ Open source                  │
  ├────────────────────────────────┼────────────────────────────────────────────────────┼──────────────────────────────────────┼──────────────────────────────┤
  │ MedSAM                         │ Prompt-guided segmentation (click/box → mask)      │ Competitive with nnU-Net             │ Open source                  │
  └────────────────────────────────┴────────────────────────────────────────────────────┴──────────────────────────────────────┴──────────────────────────────┘

  General VLMs (Best Accessibility, Lower Accuracy on Imaging)

  ┌──────────────────┬────────────────────────────────────────┬───────────────────┬──────────────────────────────────────────────────┐
  │      Model       │           Radiology Accuracy           │ Medical Knowledge │                      Notes                       │
  ├──────────────────┼────────────────────────────────────────┼───────────────────┼──────────────────────────────────────────────────┤
  │ GPT-4o           │ ~57% general radiology                 │ Excellent         │ Best overall API; Azure = HIPAA compliant        │
  ├──────────────────┼────────────────────────────────────────┼───────────────────┼──────────────────────────────────────────────────┤
  │ Gemini 2.0 Flash │ Comparable to GPT-4o                   │ Excellent         │ Fastest, cheapest; Vertex AI = HIPAA             │
  ├──────────────────┼────────────────────────────────────────┼───────────────────┼──────────────────────────────────────────────────┤
  │ Med-Gemini       │ State-of-the-art on medical benchmarks │ Highest           │ Google enterprise only; best medical VLM         │
  ├──────────────────┼────────────────────────────────────────┼───────────────────┼──────────────────────────────────────────────────┤
  │ Claude 3.5/4     │ Competitive on reasoning tasks         │ Very good         │ AWS Bedrock = HIPAA; best for structured reports │
  ├──────────────────┼────────────────────────────────────────┼───────────────────┼──────────────────────────────────────────────────┤
  │ Med3DVLM (2025)  │ Best for 3D volumetric analysis        │ Moderate          │ Open source, self-hosted, GPU required           │
  ├──────────────────┼────────────────────────────────────────┼───────────────────┼──────────────────────────────────────────────────┤
  │ RadFM            │ Radiology-native                       │ High              │ Open source, self-hosted                         │
  └──────────────────┴────────────────────────────────────────┴───────────────────┴──────────────────────────────────────────────────┘

  Critical honest finding: General VLMs (GPT-4o, Claude, Gemini) score 40-60% on radiology benchmarks vs. 61%+ for radiologists. Specialized liver models (LiLNet: 88-94%) vastly outperform them on detection. The right architecture uses both.

  ---
  3. Recommended Architecture: The Hybrid Pipeline

  Do NOT send raw DICOM slices to an LLM and call it done. The production-grade approach combines specialized segmentation with LLM reasoning:

  DICOM Upload (MRI or CT series)
          │
          ▼
  [1] DICOM De-identification (pydicom)
      ─ Strip all PHI tags before any external API call
          │
          ▼
  [2] Format Conversion (dcm2niix)
      ─ DICOM → NIfTI (.nii.gz) for 3D processing
      ─ DICOM → windowed PNG slices for VLM input
          │
          ├──────────────────────────────────────────┐
          ▼                                          ▼
  [3a] Segmentation (GPU)                   [3b] Slice Selection
       TotalSegmentator / nnU-Net                 Pick 3-5 slices per phase
       ─ Liver mask                               (arterial + portal + delayed)
       ─ Lesion mask + size                       ─ Export as montage PNG
       ─ Couinaud segment location
          │
          ▼
  [4] Radiomic Feature Extraction (PyRadiomics)
      ─ Size, shape, texture, enhancement pattern
      ─ >1,000 quantitative features
          │
          └──────────────────┐
                             ▼
                    [5] LLM / VLM Analysis
                    GPT-4o (Azure) or Claude (Bedrock)
                    Input: feature vector + selected slices + patient context
                    Prompt: LI-RADS scoring rubric + report template
                    Output: Structured JSON report
                             │
                             ▼
                    [6] OHIF Viewer (Frontend)
                    ─ Display DICOM + segmentation overlay
                    ─ AI report sidebar
                    ─ Radiologist review + sign-off workflow
                             │
                             ▼
                    [7] FHIR DiagnosticReport / DICOM SR
                    ─ Integration with EHR / PACS

  ---
  4. LLM Recommendation (Best Fit for This Workflow)

  Primary Recommendation: GPT-4o via Azure OpenAI

  Why:
  - Best vision + medical reasoning combination among accessible APIs
  - Azure OpenAI offers HIPAA BAA (Business Associate Agreement) — legally required if handling real patient data
  - Structured JSON output mode for reliable LI-RADS report generation
  - Fine-tuning API available for future model customization on your own cases
  - $2.50 / $10 per 1M tokens (input/output) — manageable cost per scan

  Use it for: Step 5 — synthesizing segmentation features + multi-phase slice montage → generating structured LI-RADS report + clinical impression

  Secondary / Alternative: Claude 4 Sonnet/Opus via AWS Bedrock

  - Strongest structured reasoning and long-document synthesis
  - Anthropic now has direct HIPAA-ready enterprise plans + AWS Bedrock BAA
  - Best choice if you want more nuanced, narrative-style radiology reports
  - No fine-tuning option currently

  For Maximum Accuracy (Self-Hosted, Research Grade): Med3DVLM

  - True 3D volumetric understanding — processes the entire NIfTI volume, no slice selection
  - Demonstrated correct identification of multifocal hepatic masses, portal vein thrombosis in CT
  - Requires A100-class GPU (~80GB VRAM for the full model)
  - No PHI ever leaves your server — no BAA needed
  - Open weights on GitHub (mirthAI/Med3DVLM)

  My Final Stack Recommendation:

  Segmentation:  TotalSegmentator (free, pip install, CPU-capable for inference)
                 + SALSA or nnU-Net if you retrain on liver tumor data
  Report LLM:    GPT-4o (Azure) for production
                 OR Claude 4 Sonnet (AWS Bedrock) if you prefer Anthropic
  3D Analysis:   Med3DVLM for high-stakes cases (GPU server)
  Viewer:        OHIF Viewer v3 (React, open source, free)

  ---
  5. Technical Stack

  Frontend

  ┌──────────────────┬───────────────────────┬──────────────────────────────────────┐
  │    Component     │      Technology       │                Notes                 │
  ├──────────────────┼───────────────────────┼──────────────────────────────────────┤
  │ DICOM Viewer     │ OHIF Viewer v3        │ React, open source, MPR/3D rendering │
  ├──────────────────┼───────────────────────┼──────────────────────────────────────┤
  │ Rendering Engine │ Cornerstone3D         │ WebGL, built into OHIF               │
  ├──────────────────┼───────────────────────┼──────────────────────────────────────┤
  │ UI Framework     │ React + TypeScript    │ OHIF is already React                │
  ├──────────────────┼───────────────────────┼──────────────────────────────────────┤
  │ AI Panel         │ Custom OHIF Extension │ Sidebar for AI results               │
  └──────────────────┴───────────────────────┴──────────────────────────────────────┘

  Backend

  ┌────────────────────┬───────────────────────────────────────────────┐
  │     Component      │                  Technology                   │
  ├────────────────────┼───────────────────────────────────────────────┤
  │ API Framework      │ FastAPI (Python)                              │
  ├────────────────────┼───────────────────────────────────────────────┤
  │ DICOM Reading      │ pydicom                                       │
  ├────────────────────┼───────────────────────────────────────────────┤
  │ DICOM→NIfTI        │ dcm2niix                                      │
  ├────────────────────┼───────────────────────────────────────────────┤
  │ 3D Processing      │ SimpleITK, nibabel                            │
  ├────────────────────┼───────────────────────────────────────────────┤
  │ Segmentation       │ TotalSegmentator, nnU-Net, MONAI              │
  ├────────────────────┼───────────────────────────────────────────────┤
  │ Feature Extraction │ PyRadiomics                                   │
  ├────────────────────┼───────────────────────────────────────────────┤
  │ AI API             │ OpenAI SDK (Azure) or Anthropic SDK (Bedrock) │
  ├────────────────────┼───────────────────────────────────────────────┤
  │ Task Queue         │ Celery + Redis (async GPU jobs)               │
  ├────────────────────┼───────────────────────────────────────────────┤
  │ PACS Server        │ Orthanc (open source, DICOMweb)               │
  ├────────────────────┼───────────────────────────────────────────────┤
  │ Auth               │ OAuth2 + MFA                                  │
  └────────────────────┴───────────────────────────────────────────────┘

  Hosting

  ┌──────────────────────────────────────────────┬───────────────────────────┬────────────────────┐
  │                    Option                    │         Best For          │   Cost Estimate    │
  ├──────────────────────────────────────────────┼───────────────────────────┼────────────────────┤
  │ AWS (HealthImaging + Bedrock + EC2)          │ Production with HIPAA BAA │ $2-8K/month        │
  ├──────────────────────────────────────────────┼───────────────────────────┼────────────────────┤
  │ Azure (DICOM service + Azure OpenAI)         │ Microsoft-centric orgs    │ Similar            │
  ├──────────────────────────────────────────────┼───────────────────────────┼────────────────────┤
  │ On-premise (bare metal + self-hosted models) │ Max privacy, research     │ Hardware cost only │
  └──────────────────────────────────────────────┴───────────────────────────┴────────────────────┘

  ---
  6. Regulatory Reality Check (Non-Negotiable)

  This is the most important section for building this responsibly:

  If you're in the US:
  - Your tool = Software as a Medical Device (SaMD) if it provides diagnosis
  - Requires FDA 510(k) clearance to deploy clinically (median 142 days, $10-50K+ process)
  - Safe harbor: Position it as "Clinical Decision Support" that is transparent, based on accepted guidelines, and requires a clinician to interpret — this may exempt it from FDA oversight
  - Azure OpenAI BAA is required if any real patient DICOM touches the API

  If you're in the EU:
  - Liver cancer diagnostic AI = High-Risk AI System under the EU AI Act
  - August 2026 deadline for full compliance
  - CE marking required for clinical use

  Required in all cases:
  - DICOM de-identification before any external API call (strip 200+ PHI tags)
  - Prominent disclaimer: "This is AI-assisted decision support, not a diagnosis. A licensed radiologist must review all outputs."
  - Radiologist-in-the-loop review workflow (human must approve every report)
  - Audit logging (who accessed what, when)

  ---
  7. What to Build First (Practical Roadmap)

  Phase 1 — Proof of Concept (1-2 months)
  - Upload DICOM → pydicom de-identify → PNG export → GPT-4o analysis → text report
  - Use OHIF Viewer for display
  - No segmentation yet — validate the report quality

  Phase 2 — Add Segmentation (2-3 months)
  - Integrate TotalSegmentator for liver + lesion masks
  - Overlay on OHIF Viewer (DICOM SEG format)
  - Feed lesion size + location to LLM prompt

  Phase 3 — Full Pipeline (3-4 months)
  - PyRadiomics feature extraction
  - LI-RADS scoring logic in the prompt
  - Radiologist review + sign-off workflow
  - FHIR DiagnosticReport output

  Phase 4 — Regulatory & Validation
  - Retrospective validation on de-identified cases
  - August 2026 deadline for full compliance
  - CE marking required for clinical use

  Required in all cases:
  - DICOM de-identification before any external API call (strip 200+ PHI tags)
  - Prominent disclaimer: "This is AI-assisted decision support, not a diagnosis. A licensed radiologist must review all outputs."
  - Radiologist-in-the-loop review workflow (human must approve every report)
  - Audit logging (who accessed what, when)

  ---
  7. What to Build First (Practical Roadmap)

  Phase 1 — Proof of Concept (1-2 months)
  - Upload DICOM → pydicom de-identify → PNG export → GPT-4o analysis → text report
  - Use OHIF Viewer for display
  - No segmentation yet — validate the report quality

  Phase 2 — Add Segmentation (2-3 months)
  - Integrate TotalSegmentator for liver + lesion masks
  - Overlay on OHIF Viewer (DICOM SEG format)
  - Feed lesion size + location to LLM prompt

  Phase 3 — Full Pipeline (3-4 months)
  - PyRadiomics feature extraction
  - LI-RADS scoring logic in the prompt
  - Radiologist review + sign-off workflow
  - FHIR DiagnosticReport output

  Phase 4 — Regulatory & Validation
  - Retrospective validation on de-identified cases
  - FDA pre-submission meeting (Q-Sub) if targeting US clinical use

  ---
  Key Numbers to Know

  - General VLMs on radiology: 40-60% accuracy (radiologists: 61%)
  - Specialized liver AI (LiLNet): 88-94% accuracy on CT
  - TotalSegmentator liver segmentation: Dice ~0.87
  - SALSA liver tumor detection: patient-level 99.65% precision
  - LI-RADS APHE detection by AI: 96.6% sensitivity (but 66.7% specificity — not production-ready alone)
