export type Modality = 'CT' | 'MRI'

export type LiRadsCategory =
  | 'LR-1' | 'LR-2' | 'LR-3' | 'LR-4' | 'LR-5'
  | 'LR-M' | 'LR-TIV' | 'Indeterminate'

export type AnalysisStatus =
  | 'pending' | 'processing' | 'segmenting'
  | 'extracting' | 'analyzing' | 'complete' | 'failed'

export interface SeriesInfo {
  series_uid: string
  description: string
  phase: string | null
  num_slices: number
}

export interface DicomStudy {
  id: string
  upload_time: string
  modality: Modality | null
  num_files: number
  series: SeriesInfo[]
}

export interface UploadResponse {
  study_id: string
  num_files: number
  modality: string | null
  series: SeriesInfo[]
  message: string
}

export interface LesionFinding {
  lesion_id: string
  location_segment: string | null
  size_mm: number | null
  lirads_category: LiRadsCategory
  aphe_present: boolean | null
  washout_present: boolean | null
  capsule_present: boolean | null
  diffusion_restriction: boolean | null
  major_features: string[]
  ancillary_features: string[]
  reasoning: string | null
}

export interface DiagnosticReport {
  study_id: string
  generated_at: string
  modality: string
  overall_impression: string
  lesions: LesionFinding[]
  differential_diagnosis: string[]
  bclc_stage: string | null
  vascular_involvement: string | null
  recommendations: string[]
  guideline_citations: string[]
  rag_context_used: boolean
  radiomics_summary: string | null
  raw_llm_output: string | null
}

export type SignOffDecision = 'approved' | 'changes_requested'

export interface SignOff {
  radiologist_name: string
  decision: SignOffDecision
  comments: string | null
  signed_at: string
}

export interface AnalysisJob {
  job_id: string
  study_id: string
  status: AnalysisStatus
  progress: number
  current_step: string
  created_at: string
  completed_at: string | null
  error: string | null
  report: DiagnosticReport | null
  sign_off: SignOff | null
}

export interface PatientContext {
  cirrhosis: boolean
  hepatitis_b: boolean
  hepatitis_c: boolean
  afp_level: number | null
  prior_hcc: boolean
  notes: string
}
