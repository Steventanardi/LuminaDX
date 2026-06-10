# LuminaDx — RAG Guideline Sources (Per Cancer)

> Where to download the clinical guideline PDFs that feed each cancer's RAG
> knowledge base, and how to load them.

---

## How the RAG store is organised

From `backend/core/rag_engine.py` — **one ChromaDB collection per cancer**:

| Cancer | Collection name | PDF folder |
|--------|-----------------|-----------|
| Liver | `liver_cancer_guidelines` | `backend/data/knowledge_base/` *(root — already populated)* |
| Lung | `lung_cancer_guidelines` | `backend/data/knowledge_base/lung/` |
| Skin | `skin_cancer_guidelines` | `backend/data/knowledge_base/skin/` |
| Breast | `breast_cancer_guidelines` | `backend/data/knowledge_base/breast/` |
| Colorectal | `colorectal_cancer_guidelines` | `backend/data/knowledge_base/colorectal/` |

> ⚠️ Liver PDFs live in the **root** `knowledge_base/` folder (legacy default).
> Every other cancer reads from its own **subfolder**. Create the subfolders:

```powershell
cd "D:\Steven Project\LuminaDx\backend\data\knowledge_base"
mkdir lung, skin, breast, colorectal
```

### Loading PDFs into the store

1. Drop the `.pdf` files into the matching folder above.
2. Trigger ingestion per namespace (auth cookie required):

```bash
# via API — one call per cancer
curl -X POST "http://localhost:8000/api/rag/ingest?namespace=lung"        --cookie "access_token=<your-token>"
curl -X POST "http://localhost:8000/api/rag/ingest?namespace=skin"        --cookie "access_token=<your-token>"
curl -X POST "http://localhost:8000/api/rag/ingest?namespace=breast"      --cookie "access_token=<your-token>"
curl -X POST "http://localhost:8000/api/rag/ingest?namespace=colorectal"  --cookie "access_token=<your-token>"
```

Or use the **Settings → Ingest Knowledge Base** button in the UI (ingests the
active cancer's namespace).

> Text-based PDFs only. Scanned/image-only PDFs won't extract — run OCR first
> (e.g. `ocrmypdf in.pdf out.pdf`) before dropping them in.

---

## Liver — ✅ already populated

Current files in `knowledge_base/` (LI-RADS + HCC management):
LI-RADS v2024 Core, LI-RADS 2018 Diagnosis, LI-RADS Lexicon, AASLD HCC practice
guidance, EASL HCC CPG, BCLC strategy, KLCA-NCC Korea 2022.

Top-up sources if needed:

| Guideline | Where | Cost |
|-----------|-------|------|
| ACR LI-RADS v2018/v2024 Core + Lexicon | acr.org → Clinical Resources → LI-RADS | Free |
| AASLD HCC Guidance 2023 | aasld.org / journal *Hepatology* | Free |
| EASL CPG on HCC management | easl.eu / *J Hepatol* | Free |
| BCLC 2022 update (Reig et al) | *J Hepatol* 2022;76(3) | Open access |
| NCCN Hepatobiliary Cancers | nccn.org (free account) | Free w/ registration |

---

## Lung — Lung-RADS / Fleischner

Folder: `knowledge_base/lung/`

| Guideline | Source | Cost | Direct route |
|-----------|--------|------|--------------|
| **ACR Lung-RADS v2022** | American College of Radiology | **Free** | acr.org → Clinical Resources → Lung-RADS → "Lung-RADS v2022 Assessment Categories" PDF |
| **Fleischner Society 2017** (incidental pulmonary nodules) | *Radiology*, MacMahon et al. | Open access | pubs.rsna.org/doi/10.1148/radiol.2017161659 |
| NCCN Lung Cancer Screening | nccn.org | Free (registration) | nccn.org → Guidelines → "Lung Cancer Screening" |
| NCCN Non-Small Cell Lung Cancer | nccn.org | Free (registration) | NCCN guideline PDF |
| USPSTF Lung Cancer Screening 2021 | uspreventiveservicestaskforce.org | Free | recommendation statement PDF |
| BTS Guidelines for Pulmonary Nodules | brit-thoracic.org.uk | Free | BTS guideline PDF |

**Minimum set for the thesis:** ACR Lung-RADS v2022 + Fleischner 2017.

---

## Skin — Melanoma / ABCDE / 7-point

Folder: `knowledge_base/skin/`

| Guideline | Source | Cost | Direct route |
|-----------|--------|------|--------------|
| **AAD Melanoma Guidelines of Care** | American Academy of Dermatology, *J Am Acad Dermatol* | Open access | jaad.org → "Guidelines of care for the management of primary cutaneous melanoma" (2019) |
| **NCCN Cutaneous Melanoma** | nccn.org | Free (registration) | NCCN → "Melanoma: Cutaneous" |
| AJCC 8th Edition Melanoma Staging | AJCC / *CA Cancer J Clin* (Gershenwald et al 2017) | Article open access; full manual paid | summary article free on PubMed Central |
| ESMO Cutaneous Melanoma CPG | esmo.org / *Ann Oncol* | Open access | esmo.org → Guidelines → Melanoma |
| Dermoscopy 7-point checklist (Argenziano) | *Arch Dermatol* original paper | Via library / open mirrors | search "7-point checklist dermoscopy Argenziano" |
| British Association of Dermatologists Melanoma | bad.org.uk | Free | BAD guideline PDF |

**Minimum set:** AAD Melanoma Guidelines + NCCN Cutaneous Melanoma + AJCC 8th staging summary.

---

## Breast — BI-RADS / Mammography

Folder: `knowledge_base/breast/`

| Guideline | Source | Cost | Direct route |
|-----------|--------|------|--------------|
| **ACR BI-RADS Atlas 5th Ed.** | American College of Radiology | **Paid** (book/eBook) | acr.org → BI-RADS — purchase required |
| ACR BI-RADS — free summaries | radiopaedia.org / ACR overview pages | Free | use as substitute for the paywalled atlas |
| **NCCN Breast Cancer Screening & Diagnosis** | nccn.org | Free (registration) | NCCN → "Breast Cancer Screening and Diagnosis" |
| NCCN Breast Cancer (treatment) | nccn.org | Free (registration) | NCCN guideline PDF |
| USPSTF Breast Cancer Screening 2024 | uspreventiveservicestaskforce.org | Free | recommendation statement PDF |
| ACR Appropriateness Criteria — Breast | acr.org | Free | per-scenario PDFs |
| ESMO Early Breast Cancer CPG | esmo.org / *Ann Oncol* | Open access | esmo.org → Guidelines → Breast |

> **BI-RADS note:** the official 5th-edition Atlas is **not free**. For a thesis
> prototype, combine the free NCCN screening guideline + ACR Appropriateness
> Criteria + a BI-RADS category summary (radiopaedia) to cover the assessment
> language without the paywalled atlas.

**Minimum set:** NCCN Breast Screening + ACR Appropriateness Criteria (Breast) + a BI-RADS category reference.

---

## Colorectal — C-RADS / TNM

Folder: `knowledge_base/colorectal/`

| Guideline | Source | Cost | Direct route |
|-----------|--------|------|--------------|
| **C-RADS** (CT Colonography Reporting & Data System) | Zalis et al., *Radiology* 2005;236:3 | Open access | pubs.rsna.org/doi/10.1148/radiol.2361041926 |
| **ACR–SAR CT Colonography practice parameter** | acr.org | Free | acr.org → Practice Parameters → "CT Colonography" |
| ESGAR CT Colonography Consensus | *Eur Radiol* | Open access | search "ESGAR CT colonography consensus" |
| **NCCN Colon Cancer** | nccn.org | Free (registration) | NCCN → "Colon Cancer" |
| **NCCN Rectal Cancer** | nccn.org | Free (registration) | NCCN → "Rectal Cancer" |
| AJCC 8th Colorectal Staging | AJCC / summary articles | Article free; manual paid | PubMed summary of AJCC 8th CRC |
| ESMO Colorectal Cancer CPG | esmo.org / *Ann Oncol* | Open access | esmo.org → Guidelines → GI → Colorectal |

**Minimum set:** C-RADS (Zalis 2005) + ACR CT Colonography parameter + NCCN Colon/Rectal.

---

## Quick "minimum viable" download checklist

For a working multi-cancer demo, the free + open-access essentials:

- [ ] **Lung:** ACR Lung-RADS v2022 · Fleischner 2017 (RSNA open access)
- [ ] **Skin:** AAD Melanoma Guidelines (JAAD) · NCCN Cutaneous Melanoma
- [ ] **Breast:** NCCN Breast Screening · ACR Appropriateness Criteria (Breast)
- [ ] **Colorectal:** C-RADS Zalis 2005 (RSNA) · NCCN Colon + Rectal
- [ ] **Liver:** already done ✅

All NCCN guidelines: free account at **nccn.org/guidelines** → download PDF.
All ACR resources: **acr.org → Clinical Resources**.
Open-access journal articles: **pubs.rsna.org**, **jaad.org**, **esmo.org**, PubMed Central.

---

## Source authority tiers (cite this in the thesis)

1. **Reporting systems** (drive the score the model outputs) — LI-RADS, Lung-RADS,
   BI-RADS, C-RADS. These are the highest-priority ingests; they define the
   vocabulary the LLM must use.
2. **Staging standards** — AJCC 8th (TNM), BCLC. Needed for the `staging` field.
3. **Management guidelines** — NCCN, ESMO, AASLD, EASL, AAD. Provide the
   `recommendations` and follow-up intervals.

Prioritise tier 1 per cancer first — a single good reporting-system PDF already
makes RAG materially better than zero-shot.

---

*Last updated: 2026-06-10*
