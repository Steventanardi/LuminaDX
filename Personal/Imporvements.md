---
  🔴 MUST FIX (substantive — professor will catch these)

  1. Objective 5 promises "specificity" but your dataset has no negatives.
  Section 1.4, Objective 5 says you'll measure "sensitivity and specificity for HCC detection" and
  "LI-RADS category agreement (Cohen's κ)." But your validation set (HCC-TACE-Seg, 105 cases) is all 
  confirmed HCC — THESIS_TODO.md even notes "all cases are confirmed HCC → expected LR-4 or LR-5."

  - You cannot compute specificity without benign/negative cases.
  - Cohen's κ across LI-RADS categories needs per-case ground-truth LI-RADS labels spanning multiple   
  categories — confirmed-HCC pathology labels aren't the same thing, and with only LR-4/LR-5 outputs κ 
  is near-meaningless.

  → Fix: either reframe Objective 5 to what the data supports (HCC detection sensitivity, LR-4/LR-5    
  capture rate, category distribution) or state you'll add benign/lower-category cases (LR-1/2/3) to   
  enable specificity and κ. This is the single most important thing to resolve — better to raise it    
  with the professor yourself than have them find it.

  2. Two citations don't support their claims.
  - [16] Liu et al. is cited for radiomics correlating with "histological grade, microvascular
  invasion, and overall survival in HCC" — but that paper is about breast cancer (pCR to neoadjuvant   
  chemo). Wrong-disease citation. Swap for an actual HCC radiomics paper.
  - [9] Geis et al. ("Ethics of AI in Radiology") is cited for the "16,000 unfilled radiologist        
  positions" statistic — that ethics statement doesn't contain that figure. Find a real source for the 
  shortage number (or soften the claim).

  → Audit every reference against the exact sentence it's attached to before handing it over. [8] (van 
  der Pol) and the 16,000 figure should also be verified for existence.

  ---
  🟡 SHOULD IMPROVE

  3. CT vs MRI mismatch. Title and Objective 1 say "CT and MRI," but evaluation (Obj. 5) and your      
  actual data are CT-only (TODO notes "modality detection needs MRI DICOM"). State explicitly in 1.5   
  Scope that validation in this iteration is CT-only; MRI support is implemented but unvalidated.      
  Otherwise the professor asks "where's the MRI evaluation?"

  4. Redundancy between 1.3 / 1.4 / 1.6. The numbered list in Problem Statement (1.3), the Objectives  
  (1.4), and the Contributions (1.6) restate the same 5 points three times. It reads slightly
  repetitive. Tighten 1.3 to motivate the gap and let 1.4/1.6 carry the specifics.

  5. Name the dataset. Obj. 5 says "a public imaging repository" — naming HCC-TACE-Seg (TCIA) up front 
  reads more concrete and credible.

  6. Surveillance motivation. 1.1 would hit harder with one quantified line on why current surveillance
  misses early HCC (e.g., ultrasound sensitivity for early-stage HCC is only ~47–63%) — strengthens    
  the case for your tool.

  ---
  🟢 COULD ADD (nice-to-have, raises the grade)

  - Research Questions. Many examiners expect explicit RQs alongside objectives — add a short 1.4.x    
  with 2–3 RQs (e.g., "Can a locally-run 7B VLM produce LI-RADS-aligned reports with agreement
  comparable to..."). Maps cleanly onto your objectives.
  - Research approach paragraph. One short subsection naming your methodology (design-science /        
  system-development research) — examiners like to see the method framed, not just the artifact.       
  - A pipeline figure. Reference a "Figure 1.1" high-level pipeline diagram in 1.2 or 1.6 — you already

  → Audit every reference against the exact sentence it's attached to before handing it over. [8] (van 
  der Pol) and the 16,000 figure should also be verified for existence.

  ---
  🟡 SHOULD IMPROVE

  3. CT vs MRI mismatch. Title and Objective 1 say "CT and MRI," but evaluation (Obj. 5) and your      
  actual data are CT-only (TODO notes "modality detection needs MRI DICOM"). State explicitly in 1.5   
  Scope that validation in this iteration is CT-only; MRI support is implemented but unvalidated.      
  Otherwise the professor asks "where's the MRI evaluation?"

  4. Redundancy between 1.3 / 1.4 / 1.6. The numbered list in Problem Statement (1.3), the Objectives  
  (1.4), and the Contributions (1.6) restate the same 5 points three times. It reads slightly
  repetitive. Tighten 1.3 to motivate the gap and let 1.4/1.6 carry the specifics.

  5. Name the dataset. Obj. 5 says "a public imaging repository" — naming HCC-TACE-Seg (TCIA) up front 
  reads more concrete and credible.

  6. Surveillance motivation. 1.1 would hit harder with one quantified line on why current surveillance
  misses early HCC (e.g., ultrasound sensitivity for early-stage HCC is only ~47–63%) — strengthens    
  the case for your tool.

  ---
  🟢 COULD ADD (nice-to-have, raises the grade)

  - Research Questions. Many examiners expect explicit RQs alongside objectives — add a short 1.4.x    
  with 2–3 RQs (e.g., "Can a locally-run 7B VLM produce LI-RADS-aligned reports with agreement
  comparable to..."). Maps cleanly onto your objectives.
  - Research approach paragraph. One short subsection naming your methodology (design-science /        
  system-development research) — examiners like to see the method framed, not just the artifact.       
  - A pipeline figure. Reference a "Figure 1.1" high-level pipeline diagram in 1.2 or 1.6 — you already
  have Personal/System Architecture Diagram.png to adapt.

  ---
  ✅ What's already good

  Spelling is consistently British (programme/tumour/standardised) — keep it. GLOBOCAN 2020 figures    
  (905,677 / 830,180) are correct. LLaVA-7B / Ollama / 45+ PHI-tag / TotalSegmentator liver_lesions    
  claims all match your actual implementation. Honesty about the 7B model's limitations in 1.5 is      
  exactly what examiners want to see. Structure and the chapter-by-chapter roadmap (1.7) are
  textbook-correct.

  ---
  Bottom line for today: structurally green-light — go ahead and show it. But lead with issue #1       
  yourself (the specificity/κ vs all-positive dataset problem), because it affects Chapter 5 and is    
  easier to fix now than after you've written the methodology around it.

  Want me to apply the safe fixes now (CT-only scope wording, the two citation swaps, naming the       
  dataset, tightening 1.3), and draft an optional Research Questions subsection for you to review? 