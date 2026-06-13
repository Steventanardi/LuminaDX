export type Modality = 'CT' | 'MRI'

export type CancerType = 'liver' | 'lung' | 'skin' | 'breast' | 'colorectal'

export type LiRadsCategory =
  | 'LR-1' | 'LR-2' | 'LR-3' | 'LR-4' | 'LR-5'
  | 'LR-M' | 'LR-TIV' | 'Indeterminate'

export type AnalysisStatus =
  | 'pending' | 'processing' | 'segmenting'
  | 'extracting' | 'analyzing' | 'complete' | 'failed'

export type UserRole = 'admin' | 'chief_physician' | 'radiologist'

export interface User {
  id: string
  email: string
  full_name: string
  role: UserRole
  department?: string | null
  is_active?: boolean
  created_at?: string
  last_login?: string | null
}

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
  cancer_type: string
  owner_user_id: string | null
}

export interface UploadResponse {
  study_id: string
  num_files: number
  modality: string | null
  series: SeriesInfo[]
  message: string
  suggested_cancer_type?: string | null    // auto-detected from DICOM metadata
  detection_confidence?: 'high' | 'medium' | 'low' | null
  detection_reason?: string | null
}

export interface LesionFinding {
  lesion_id: string
  location_segment: string | null
  size_mm: number | null
  // LI-RADS (liver-specific)
  lirads_category: LiRadsCategory
  aphe_present: boolean | null
  washout_present: boolean | null
  capsule_present: boolean | null
  diffusion_restriction: boolean | null
  // Generic scoring (skin / lung / breast / colorectal)
  score_system: string | null
  score: string | null
  major_features: string[]
  ancillary_features: string[]
  reasoning: string | null
}

export interface DiagnosticReport {
  study_id: string
  generated_at: string
  modality: string
  cancer_type: string
  model: string | null
  overall_impression: string
  lesions: LesionFinding[]
  differential_diagnosis: string[]
  bclc_stage: string | null          // liver
  vascular_involvement: string | null // liver
  staging: string | null             // generic (other cancers)
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
  cancer_type: string
  model: string | null
  owner_user_id: string | null
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

export const CANCER_TYPE_META: Record<CancerType, { label: string; icon: string; scoreSystem: string; color: string }> = {
  liver:      { label: 'Liver',      icon: '🫀', scoreSystem: 'LI-RADS',    color: 'violet'  },
  lung:       { label: 'Lung',       icon: '🫁', scoreSystem: 'Lung-RADS',  color: 'sky'     },
  skin:       { label: 'Skin',       icon: '🩹', scoreSystem: 'ABCDE',      color: 'amber'   },
  breast:     { label: 'Breast',     icon: '🎀', scoreSystem: 'BI-RADS',    color: 'pink'    },
  colorectal: { label: 'Colorectal', icon: '🔴', scoreSystem: 'C-RADS',     color: 'orange'  },
}

// Per-cancer LLM model catalog (from GET /api/analysis/models)
export interface ModelOption {
  tag: string
  label: string
}

export interface CancerModelInfo {
  default: string
  options: ModelOption[]
}

export type ModelCatalog = Record<string, CancerModelInfo>

// Per-cancer feature/extractor catalog (from GET /api/analysis/features)
export interface FeatureOption {
  key: string
  label: string
  group: string      // "preprocessing" | "extractor" | "cnn"
  default: boolean
}

export interface CancerFeatureInfo {
  defaults: string[]
  options: FeatureOption[]
}

export type FeatureCatalog = Record<string, CancerFeatureInfo>
