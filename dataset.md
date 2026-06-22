# LuminaDx — Public Imaging Datasets (2020–2026)

Curated public datasets per cancer module, biased toward **2020–2026** releases. Each
entry notes modality, size, label type, access terms, and **how it plugs into LuminaDx**.

Two integration shapes exist in this repo:

- **Skin** → the KNN classifier consumes a *labelled image folder* tree
  (`data/reference/skin/<label>/*.jpg`). Datasets for skin must therefore be
  **classification** sets (benign / malignant or per-diagnosis classes). Use one set to
  *build* the reference index and a **non-overlapping** set to run `backend/scripts/shared/eval_knn.py`.
- **Liver / Lung / Breast / Colorectal** → the DICOM pipeline (TotalSegmentator +
  PyRadiomics + multimodal LLM). These want **DICOM CT/MR volumes** (or, for breast,
  full-field digital mammography), ideally with segmentation masks or lesion labels.

> ⚠️ **Leakage rule:** whatever images go into `data/reference/<cancer>/`, your eval/test
> set must contain *different* images. Overlap silently inflates accuracy.

> ⚖️ **Access terms vary.** "Open" = direct download; "Registration" = free account;
> "DUA" = signed data-use agreement / application. Check each dataset's licence before
> using in a thesis, and cite the source paper.

---

## 🔬 Skin (dermoscopy / lesion images) — KNN reference + eval

| Dataset | Year | Size | Labels | Access |
|---|---|---|---|---|
| **ISIC 2020 (SIIM-ISIC Melanoma)** | 2020 | ~33,000 dermoscopic images | benign / malignant (binary) | Open (Kaggle) |
| **HAM10000** | 2018 (still standard) | 10,015 dermoscopic images | 7 diagnostic classes | Open |
| **ISIC 2024 — Skin Cancer Detection with 3D-TBP (SLICE-3D)** | 2024 | ~400,000 lesion crops | malignant label + rich metadata | Registration (Kaggle) |
| **ISIC Archive (live)** | continuously updated | 100k+ images | multi-class, metadata | Open |

**Recommendation for your KNN eval:** the binary benign/malignant structure of your
current `data/reference/skin/` matches **ISIC 2020** exactly. Build the index from one
slice, then point `eval_knn.py --test-dir` at a held-out slice. ISIC 2024 is *non-dermoscopic*
(3D total-body-photo crops, smartphone-like) — only mix it in if you want to test
robustness to a different image style, not as a like-for-like test set.

- ISIC 2024 challenge: https://www.kaggle.com/competitions/isic-2024-challenge
- ISIC 2024 dataset home: https://challenge2024.isic-archive.com/
- ISIC Archive: https://www.isic-archive.com/
- 2025 longitudinal tile/dermoscopy dataset (Nature Sci Data): https://www.nature.com/articles/s41597-025-05880-2

---

## 🫀 Liver (CT / MR — HCC) — DICOM pipeline

| Dataset | Year | Modality | Size | Labels | Access |
|---|---|---|---|---|---|
| **HCC-TACE-Seg** (TCIA) | 2021 | CT | HCC patients pre-TACE | tumour + liver segmentation | Open (TCIA) |
| **LiverHccSeg** | 2023 | multiphasic MRI | liver + HCC masks | segmentation + inter-rater | Open |
| **Multi-phase CT liver-tumor differential dx** (Nature Sci Data) | 2025 | multi-phase CT | multi-class liver tumors | diagnosis labels | Open |
| **LiTS — Liver Tumor Segmentation** | 2017 (benchmark) | CT | 201 CE-CT volumes | liver + tumour masks | Registration |
| **WAW-TACE** | 2024 | CT | HCC pre-treatment | clinical + imaging | Open |

**Recommendation:** **HCC-TACE-Seg** (TCIA) is the cleanest HCC-specific CT set with
segmentations and matches your LI-RADS/BCLC liver module. **LiverHccSeg** adds the MR
phase if you want multiphasic MR coverage. LiTS is older but the standard segmentation
benchmark.

- HCC-TACE-Seg: https://www.cancerimagingarchive.net/collection/hcc-tace-seg/
- LiverHccSeg (2023): https://www.sciencedirect.com/science/article/pii/S2352340923007473
- Multi-phase CT (2025): https://www.nature.com/articles/s41597-025-06343-4

---

## 🫁 Lung (CT / PET-CT — nodules & cancer) — DICOM pipeline

| Dataset | Year | Modality | Size | Labels | Access |
|---|---|---|---|---|---|
| **Lung-PET-CT-Dx** (TCIA) | 2020 | CT + PET/CT (DICOM) | 355 subjects | tumour bounding boxes (XML) + clinical | Open (TCIA) |
| **NLSTseg** | 2025 | low-dose CT | 605 patients, 715 lesions | pixel-level lesion masks | Open |
| **NLST** (full trial) | ongoing | low-dose CT | 75,000+ scans | screening outcomes | DUA |
| **LUNA16** | 2016 (still standard) | CT | 888 scans, 1,186 nodules | nodule annotations | Open |

**Recommendation:** **Lung-PET-CT-Dx** is DICOM-native with clinical data and bounding
boxes — best fit for your Lung-RADS module and the DICOM upload path. **NLSTseg** (2025)
adds modern pixel-level masks if you need segmentation ground truth.

- Lung-PET-CT-Dx: https://www.cancerimagingarchive.net/collection/lung-pet-ct-dx/
- NLSTseg (2025): https://www.nature.com/articles/s41597-025-05742-x

---

## 🎗️ Breast (mammography / MR / US) — DICOM pipeline

| Dataset | Year | Modality | Size | Labels | Access |
|---|---|---|---|---|---|
| **RSNA 2023 Screening Mammography** | 2023 | FFDM (DICOM) | ~54k images, Australia + US | cancer label + path follow-up | Registration (Kaggle) |
| **VinDr-Mammo** | 2023 | FFDM (DICOM) | 5,000 four-view exams | BI-RADS + lesion annotations | Registration (PhysioNet) |
| **MammosighTR** | 2024 | mammography | nationwide screening | BI-RADS annotations | Open |
| **CBIS-DDSM** | 2017 (standard) | mammography | 2,620 cases | mass/calc + pathology | Open |

**Recommendation:** **VinDr-Mammo** gives you explicit **BI-RADS + lesion** annotations —
a direct match for your BI-RADS breast module. **RSNA 2023** is larger and DICOM-native
with pathology-confirmed cancer labels, ideal for binary validation.

- RSNA 2023 challenge: https://www.rsna.org/artificial-intelligence/ai-image-challenge/screening-mammography-breast-cancer-detection-ai-challenge
- VinDr-Mammo (Nature Sci Data 2023): https://www.nature.com/articles/s41597-023-02100-7
- RSNA open-source dataset paper (2025): https://pubs.rsna.org/doi/10.1148/ryai.250375
- MammosighTR (2024): https://pubs.rsna.org/doi/10.1148/ryai.240841

---

## 🩻 Colorectal (CT colonography / colonoscopy) — DICOM + image pipeline

| Dataset | Year | Modality | Size | Labels | Access |
|---|---|---|---|---|---|
| **PolypGen** | 2023 | colonoscopy | 1,537 images + 2,225 seq + 4,275 neg frames | pixel-level polyp masks, 6 centres | Open (GitHub) |
| **Kvasir-SEG** | 2020 | colonoscopy | 1,000 images | polyp segmentation masks | Open |
| **CT COLONOGRAPHY** (TCIA) | (classic) | CT colonography (DICOM) | 825 patients | polyp findings | Open (TCIA) |
| **RRTS** | 2025 | colonoscopy | resource-limited-setting benchmark | CAD labels | Open |

**Recommendation:** your colorectal module references **C-RADS** (CT colonography) — so
**CT COLONOGRAPHY (TCIA)** is the DICOM-native fit for the volumetric pipeline. If you
instead want optical-colonoscopy polyp classification/segmentation (image pipeline /
future KNN), **PolypGen** (2023, multi-centre) is the strongest modern option.

- PolypGen (Nature Sci Data 2023): https://www.nature.com/articles/s41597-023-01981-y
- PolypGen GitHub: https://github.com/DebeshJha/PolypGen

---

## 🟢 Healthy / non-cancer control sets (one per module)

Every module needs a **negative class** — normal anatomy with *no* tumour — so the
classifier/eval has something to contrast against and you can measure specificity
(false-positive rate), not just sensitivity. Same **leakage rule** applies: controls in
`data/reference/<cancer>/` must not reappear in your eval set.

| Module | Dataset | Year | Modality | Why it's "healthy" | Access |
|---|---|---|---|---|---|
| **Skin** | **HAM10000 — `nv` (melanocytic nevi) + `bkl` classes** | 2018 | dermoscopy | benign, non-malignant lesions; the natural negative class for binary skin KNN | Open |
| **Skin** | **Fitzpatrick17k (non-neoplastic subset)** | 2021 | clinical photos | inflammatory/benign conditions across skin tones — robustness control | Open |
| **Liver** | **CHAOS** | 2019 | CT + MR (DICOM) | abdominal scans from **healthy liver-donor candidates** — no tumour, liver masks included | Registration |
| **Lung** | **CT-RATE** (normal-labelled subset) | 2024 | chest CT (DICOM) | 50k+ chest CT with reports; filter to report-confirmed **normal** lungs | Registration (HF) |
| **Lung** | **NLST screen-negative** | ongoing | low-dose CT | trial participants with **no detected nodule/cancer** | DUA |
| **Breast** | **VinDr-Mammo / RSNA — BI-RADS 1 cases** | 2023 | FFDM (DICOM) | BI-RADS 1 = normal, no finding; the built-in negative class | Registration |
| **Colorectal** | **HyperKvasir — `normal-cecum` / `normal-pylorus` / `normal-z-line`** | 2020 | colonoscopy | labelled **normal anatomical landmarks**, no polyp/lesion | Open |
| **Colorectal** | **CT COLONOGRAPHY (TCIA) — negative exams** | classic | CT colonography (DICOM) | patients with **no polyp findings** — DICOM negative class | Open (TCIA) |
| **Multi-organ** | **TotalSegmentator dataset** | 2023 | CT (DICOM) | 1,228 CTs with organ masks (the tool this repo already uses); use scans **without** the target tumour as anatomical controls for liver/lung | Open |

**How to wire it in**

- **Skin (KNN):** add a third reference folder `data/reference/skin/benign/` (or keep the
  existing benign/malignant split) — HAM10000 `nv`/`bkl` images are the cleanest negatives.
  Hold out a non-overlapping slice for `eval_knn.py` so specificity is measured on unseen normals.
- **Liver/Lung/Breast/Colorectal (DICOM):** drop normal volumes into the same upload path;
  for breast just include **BI-RADS 1** exams, for colorectal include **polyp-negative**
  CT colonography. CHAOS (liver) and CT-RATE/NLST-negative (lung) are the dedicated controls.

- CHAOS: https://chaos.grand-challenge.org/
- CT-RATE (2024): https://huggingface.co/datasets/ibrahimhamamci/CT-RATE
- HyperKvasir (Nature Sci Data 2020): https://www.nature.com/articles/s41597-020-00622-y
- Fitzpatrick17k: https://github.com/mattgroh/fitzpatrick17k
- TotalSegmentator dataset: https://zenodo.org/records/10047292

---

## Quick start for the skin KNN validation

1. Download **ISIC 2020** (benign/malignant).
2. Split into two non-overlapping folders, each `…/benign/` + `…/malignant/`:
   one to build the index, one to test.
3. Build (if needed): `POST /api/analysis/knn/build/skin` or rebuild via the reference dir.
4. Evaluate:
   ```powershell
   .venv\Scripts\python.exe scripts\shared\eval_knn.py --cancer skin --test-dir "C:\path\to\isic2020_test" --backbone cnn_resnet50 --k 5
   ```
5. Repeat with `--backbone cnn_vgg19` to compare extractors for the thesis.
6. To compare KNN against the **trained classifier and LLM** on one shared split,
   use `backend/scripts/skin/eval_skin.py` (see its README).

---

_Sources: TCIA, ISIC Archive, Kaggle, RSNA, Nature Scientific Data, PhysioNet, GitHub.
Verify each licence/DUA before use and cite the originating paper. Compiled June 2026._
