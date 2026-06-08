# Chapter 1: Introduction

---

## 1.1 Background and Motivation

Liver cancer is one of the most prevalent and lethal malignancies worldwide. According to the Global Cancer Observatory (GLOBOCAN), primary liver cancer ranks as the sixth most commonly diagnosed cancer and the third leading cause of cancer-related mortality globally, accounting for approximately 905,677 new cases and 830,180 deaths in 2020 alone [1]. Hepatocellular carcinoma (HCC) constitutes approximately 75–85% of all primary liver cancers and arises predominantly in the setting of chronic liver disease, including cirrhosis secondary to hepatitis B or C infection, alcohol-related liver disease, and non-alcoholic fatty liver disease (NAFLD) [2]. The incidence of HCC is rising in many regions, particularly in Western countries where NAFLD is reaching epidemic proportions, while remaining disproportionately high in sub-Saharan Africa and Eastern Asia due to endemic hepatitis B infection [3].

The prognosis for HCC is strongly stage-dependent. When detected at an early stage, curative therapies such as surgical resection, liver transplantation, and radiofrequency ablation offer five-year survival rates exceeding 70% [4]. However, the majority of patients present at an advanced stage due to the insidious onset of symptoms and the limited sensitivity of current surveillance programmes, resulting in a median overall survival of less than twelve months for advanced-stage disease [5]. This stark survival gradient underscores the critical importance of early and accurate detection.

The primary imaging modalities for liver cancer diagnosis are contrast-enhanced computed tomography (CT) and magnetic resonance imaging (MRI). These modalities are central to the non-invasive diagnosis of HCC because HCC exhibits a characteristic vascular pattern — arterial phase hyperenhancement (APHE) followed by portal venous or delayed washout — that is considered pathognomonic and, under specific criteria, sufficient for diagnosis without histological confirmation [6]. The Liver Imaging Reporting and Data System (LI-RADS), developed by the American College of Radiology (ACR) and updated to version 2024, provides a standardised framework for the reporting and scoring of liver observations in at-risk patients, assigning categories from LR-1 (definitely benign) to LR-5 (definitely HCC), with additional categories for probable or definite malignancy not specific to HCC (LR-M) and tumour in vein (LR-TIV) [7].

Despite the availability of this structured reporting framework, the accurate interpretation of liver imaging remains a highly specialised skill. Proficiency in LI-RADS requires extensive training and experience, yet even among experienced radiologists, inter-reader variability in LI-RADS category assignment has been reported, with weighted kappa values ranging from 0.49 to 0.72 in multicentre studies [8]. This variability is clinically consequential: misclassification of an LR-4 observation as LR-3 may lead to delayed diagnosis, while over-classification of a benign lesion may lead to unnecessary biopsy or treatment. Furthermore, the global shortage of radiologists — estimated at 16,000 unfilled positions in the United States alone and substantially larger in low- and middle-income countries — creates diagnostic bottlenecks and increased workload that may further compromise accuracy [9].

These challenges create a compelling case for the development of artificial intelligence (AI)-based decision support tools that can assist radiologists in the structured interpretation of liver imaging studies.

---

## 1.2 The Role of Artificial Intelligence in Medical Imaging

The past decade has witnessed a rapid proliferation of AI applications in medical imaging. Deep learning models, particularly convolutional neural networks (CNNs) and more recently vision transformers (ViTs), have demonstrated performance comparable to or exceeding that of expert radiologists in tasks including the detection, classification, and segmentation of pathological findings across a range of imaging domains [10].

In liver imaging specifically, AI models have been applied to tasks such as automated liver segmentation [11], lesion detection [12], and HCC classification [13]. Automated segmentation tools such as TotalSegmentator [14] — a nnU-Net-based model trained on a large multi-organ dataset — can reliably delineate hepatic anatomy from CT volumes, providing the volumetric foundation for downstream quantitative analysis.

A complementary approach is radiomics, the high-throughput extraction of quantitative features from medical images, including shape descriptors, intensity statistics, and texture features derived from matrices such as the grey-level co-occurrence matrix (GLCM) and grey-level run-length matrix (GLRLM) [15]. Radiomic features can capture imaging characteristics that are not apparent to the human eye, and have been shown in multiple studies to correlate with histological grade, microvascular invasion, and overall survival in HCC [16]. The PyRadiomics library [17] provides an open-source, reproducible implementation of a standardised radiomic feature set encompassing over 1,000 features across seven feature classes.

More recently, large language models (LLMs) and vision-language models (VLMs) have emerged as powerful tools for medical text generation and image-grounded reasoning. Models such as LLaVA [18] combine a visual encoder with a large language decoder, enabling them to accept image inputs alongside text prompts and produce clinically relevant narrative outputs. Retrieval-augmented generation (RAG) [19] further enhances LLM-based systems by grounding generated text in retrieved passages from a curated knowledge base, reducing hallucination and improving adherence to clinical guidelines.

The convergence of these technologies — automated segmentation, radiomics, VLMs, and RAG — offers the potential to construct a comprehensive, end-to-end AI-assisted workflow for liver cancer imaging that is interpretable, evidence-grounded, and aligned with established clinical reporting standards.

---

## 1.3 Problem Statement

Current AI tools for liver cancer imaging are typically narrow in scope, addressing individual sub-tasks (e.g., segmentation only, or classification only) rather than the full diagnostic workflow from image intake to structured clinical report. Existing systems also raise concerns regarding data privacy: cloud-based AI services require the transmission of patient imaging data to external servers, creating regulatory challenges under frameworks such as the Health Insurance Portability and Accountability Act (HIPAA) in the United States and the General Data Protection Regulation (GDPR) in the European Union. Furthermore, most published AI tools lack integration with the LI-RADS reporting standard, limiting their clinical applicability.

There is therefore an unmet need for an integrated, privacy-preserving AI decision support system that can:

1. Accept real-world clinical imaging inputs (DICOM-format CT and MRI studies);
2. Perform automated liver and lesion segmentation and quantitative radiomics analysis;
3. Generate a structured, LI-RADS-compliant diagnostic report using a vision-language model augmented with clinical guideline retrieval;
4. Support a radiologist review and sign-off workflow consistent with regulatory requirements for AI-based clinical decision support;
5. Operate entirely on local infrastructure, ensuring that no patient data leaves the clinical environment.

---

## 1.4 Research Objectives

The primary aim of this thesis is to design, implement, and evaluate an AI-powered clinical decision support system for liver cancer diagnosis from cross-sectional imaging. The specific objectives are:

**Objective 1 — System Design:**  
To design a modular, end-to-end software architecture that integrates DICOM ingestion, de-identification, NIfTI conversion, automated segmentation, radiomic feature extraction, retrieval-augmented generation, and vision-language model inference into a cohesive diagnostic pipeline.

**Objective 2 — LI-RADS-Aligned Reporting:**  
To implement a structured prompting strategy that directs the vision-language model to produce reports consistent with LI-RADS v2024 criteria, including the assessment of arterial phase hyperenhancement, washout, enhancing capsule, lesion size, and ancillary features.

**Objective 3 — Privacy-Preserving Local Inference:**  
To demonstrate that all AI inference can be executed locally using open-source models served via Ollama, with no patient data transmitted to external systems, and to verify DICOM de-identification against a 45+ tag PHI removal protocol aligned with DICOM PS3.15 Basic Application Level Confidentiality Profile.

**Objective 4 — Clinical Workflow Integration:**  
To implement a radiologist review and sign-off interface, an audit logging system, and regulatory-compliant report export mechanisms (PDF and FHIR R4 DiagnosticReport), supporting the requirements of AI as a decision support tool rather than an autonomous diagnostic device.

**Objective 5 — Performance Evaluation:**  
To evaluate the system against a cohort of de-identified liver CT cases from a public imaging repository, measuring LI-RADS category agreement with radiologist ground truth (Cohen's κ), sensitivity and specificity for HCC detection, and end-to-end processing time per case.

---

## 1.5 Scope and Limitations

This work focuses on the development and evaluation of a decision support tool for liver cancer imaging and explicitly excludes the following from its scope:

- **Autonomous diagnosis:** The system is designed as a second-reader aid. All outputs require radiologist review before clinical use. The tool does not replace and is not intended to replace a qualified radiologist.
- **Therapeutic planning:** The system produces a diagnostic impression and staging estimate but does not generate treatment recommendations beyond referencing Barcelona Clinic Liver Cancer (BCLC) staging guidelines in general terms.
- **Non-HCC primary liver tumours:** The primary focus is HCC. While the system may flag observations as LR-M (possibly malignant, non-HCC specific), detailed characterisation of cholangiocarcinoma or hepatic metastases is outside the scope of this iteration.
- **Paediatric imaging:** All validation is conducted on adult patients.
- **Real-time clinical deployment:** The system is evaluated as a research prototype. It has not undergone the regulatory review required for deployment as a medical device under EU MDR 2017/745 or FDA 510(k)/De Novo pathways.

Key technical limitations include the use of a 7-billion parameter vision-language model (LLaVA-7B), which, while capable of image-grounded reasoning, is substantially smaller than frontier multimodal models and may produce less nuanced radiological descriptions. The segmentation pipeline relies on TotalSegmentator's `liver_lesions` task, which was trained on a general clinical dataset; its performance on atypical or early-stage lesions is known to be lower [14]. Radiomic feature stability depends on consistent image acquisition parameters, which may vary across institutions and scanner models.

---

## 1.6 Significance and Contributions

This thesis makes the following contributions to the field:

1. **An open-source, end-to-end AI liver cancer diagnostic pipeline** integrating DICOM processing, TotalSegmentator segmentation, PyRadiomics feature extraction, RAG with clinical guideline retrieval, and VLM-based report generation — deployed as a web application accessible via a standard browser.

2. **A privacy-preserving architecture** in which all AI inference runs locally via the Ollama server framework, eliminating the need to transmit patient imaging data to any external service and enabling deployment in environments where cloud connectivity is restricted or prohibited.

3. **LI-RADS v2024 integration** through a structured system prompt encoding the complete diagnostic criteria for LR-1 through LR-5, LR-M, and LR-TIV, including major and ancillary features, enabling the model to produce category-aligned reports.

4. **A clinical workflow scaffold** including radiologist sign-off enforcement, append-only audit logging, PDF report export, and FHIR R4 DiagnosticReport export, demonstrating the integration of AI-generated content into existing clinical information infrastructure.

5. **Empirical evaluation** of system accuracy, inter-rater agreement with radiologist ground truth, and per-step computational benchmarks, providing a quantitative basis for assessing the readiness of local, open-source VLM-based tools for clinical decision support in hepatology.

---

## 1.7 Thesis Structure

The remainder of this thesis is organised as follows:

**Chapter 2 — Literature Review** surveys the epidemiology of HCC, the evolution of LI-RADS, and the state of the art in AI-based liver imaging analysis, including deep learning segmentation, radiomics, and multimodal language models. The chapter identifies the research gap that motivates this work.

**Chapter 3 — Methodology** describes the overall system design, dataset selection and preparation, model selection rationale, and experimental design for validation.

**Chapter 4 — Implementation** provides a detailed technical description of each system component: the FastAPI backend, DICOM processing pipeline, TotalSegmentator integration, PyRadiomics feature extraction, RAG engine, VLM prompting strategy, and React frontend.

**Chapter 5 — Results and Validation** presents the quantitative evaluation results, including LI-RADS category agreement, HCC detection metrics, and processing time benchmarks, alongside qualitative case studies illustrating system behaviour on representative imaging findings.

**Chapter 6 — Discussion** interprets the results in the context of related work, addresses the limitations of the system, and analyses the ethical, regulatory, and clinical deployment considerations, including an assessment against EU AI Act high-risk AI system requirements.

**Chapter 7 — Conclusion** summarises the contributions of this thesis, reflects on lessons learned, and proposes directions for future research including model scaling, prospective clinical evaluation, and regulatory pathway planning.

---

## References

[1] H. Sung et al., "Global Cancer Statistics 2020: GLOBOCAN Estimates of Incidence and Mortality Worldwide for 36 Cancers in 185 Countries," *CA: A Cancer Journal for Clinicians*, vol. 71, no. 3, pp. 209–249, 2021.

[2] A. Forner, M. Reig, and J. Bruix, "Hepatocellular carcinoma," *The Lancet*, vol. 391, no. 10127, pp. 1301–1314, 2018.

[3] F. Bray et al., "Global cancer statistics 2018: GLOBOCAN estimates of incidence and mortality worldwide for 36 cancers in 185 countries," *CA: A Cancer Journal for Clinicians*, vol. 68, no. 6, pp. 394–424, 2018.

[4] EASL Clinical Practice Guidelines, "Management of hepatocellular carcinoma," *Journal of Hepatology*, vol. 69, no. 1, pp. 182–236, 2018.

[5] J. M. Llovet et al., "Hepatocellular carcinoma," *Nature Reviews Disease Primers*, vol. 7, no. 1, p. 6, 2021.

[6] V. Chernyak et al., "Liver Imaging Reporting and Data System (LI-RADS) Version 2018: Imaging of Hepatocellular Carcinoma in At-Risk Patients," *Radiology*, vol. 289, no. 3, pp. 816–830, 2018.

[7] American College of Radiology, "Liver Imaging Reporting and Data System (LI-RADS) v2024," ACR, 2024.

[8] A. G. van der Pol et al., "Inter-reader agreement of LI-RADS v2018 for CT and MRI: A systematic review and meta-analysis," *European Radiology*, vol. 31, no. 11, pp. 8526–8538, 2021.

[9] R. Geis et al., "Ethics of Artificial Intelligence in Radiology: Summary of the Joint European and North American Multisociety Statement," *Radiology*, vol. 293, no. 2, pp. 436–440, 2019.

[10] R. Shen et al., "Deep learning in medical image analysis," *Annual Review of Biomedical Engineering*, vol. 19, pp. 221–248, 2017.

[11] J. Ma et al., "Segment Anything in Medical Images," *Nature Communications*, vol. 15, p. 654, 2024.

[12] D. Bilic et al., "The liver tumor segmentation benchmark (LiTS)," *Medical Image Analysis*, vol. 84, p. 102680, 2023.

[13] S. Yasaka et al., "Deep learning with convolutional neural network for differentiation of liver masses at dynamic contrast-enhanced CT: A preliminary study," *Radiology*, vol. 286, no. 3, pp. 887–896, 2018.

[14] J. Wasserthal et al., "TotalSegmentator: Robust Segmentation of 104 Anatomic Structures in CT Images," *Radiology: Artificial Intelligence*, vol. 5, no. 5, p. e230024, 2023.

[15] P. Lambin et al., "Radiomics: extracting more information from medical images using advanced feature analysis," *European Journal of Cancer*, vol. 48, no. 4, pp. 441–446, 2012.

[16] Y. Liu et al., "Radiomics of multiparametric MRI for pretreatment prediction of pathologic complete response to neoadjuvant chemotherapy in breast cancer: a multicenter study," *Clinical Cancer Research*, vol. 25, no. 12, pp. 3538–3547, 2019.

[17] J. J. M. van Griethuysen et al., "Computational Radiomics System to Decode the Radiographic Phenotype," *Cancer Research*, vol. 77, no. 21, pp. e104–e107, 2017.

[18] H. Liu et al., "Visual Instruction Tuning," in *Advances in Neural Information Processing Systems*, vol. 36, 2024.

[19] P. Lewis et al., "Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks," in *Advances in Neural Information Processing Systems*, vol. 33, pp. 9459–9474, 2020.

---

*Word count (approx.): 2,650 words (body text, excluding references)*
