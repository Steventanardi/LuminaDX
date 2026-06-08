DICOM Datasets for Testing

  All of these are free and publicly available:

  1. LiTS — Liver Tumor Segmentation Challenge

  Best starting point. 201 abdominal CT scans with expert-annotated liver + tumor segmentation masks.
  - URL: https://competitions.codalab.org/competitions/17094
  - Also on Kaggle: search "LiTS liver tumor segmentation"
  - Format: NIfTI (already converted from DICOM)
  - Ground truth masks included — perfect for evaluating your segmentation step

  2. HCC-TACE-Seg (The Cancer Imaging Archive)

  Best for your specific use case. 105 HCC patients, multi-phase contrast CT (arterial + venous + delayed), with expert tumor segmentations.
  - URL: https://www.cancerimagingarchive.net/collection/hcc-tace-seg/
  - Format: DICOM (real multi-phase scans, closest to clinical reality)
  - Requires free TCIA account registration

  3. TCGA-LIHC (The Cancer Imaging Archive)

  MRI and CT of liver HCC from The Cancer Genome Atlas. Linked to genomic data.
  - URL: https://www.cancerimagingarchive.net/collection/tcga-lihc/
  - Good for HCC-specific cases

  4. Medical Segmentation Decathlon — Task 08 Liver

  131 CT scans with liver + tumor annotations. Clean, well-curated.
  - URL: http://medicaldecathlon.com/
  - Direct download link on the site (no registration needed)

  5. CHAOS Challenge (MRI)

  For MRI specifically — abdominal MRI (T1, T2) with liver segmentation masks.
  - URL: https://chaos.grand-challenge.org/
  - Important since you want both MRI and CT

  6. TotalSegmentator Test Dataset

  Small set of CT scans used to validate TotalSegmentator — useful for quick pipeline testing.
  - Available on Zenodo, search "TotalSegmentator dataset"