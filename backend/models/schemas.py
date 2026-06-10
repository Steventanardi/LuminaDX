from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class Modality(str, Enum):
    CT = "CT"
    MRI = "MRI"


class LiRadsCategory(str, Enum):
    LR_1 = "LR-1"
    LR_2 = "LR-2"
    LR_3 = "LR-3"
    LR_4 = "LR-4"
    LR_5 = "LR-5"
    LR_M = "LR-M"
    LR_TIV = "LR-TIV"
    INDETERMINATE = "Indeterminate"


class AnalysisStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    SEGMENTING = "segmenting"
    EXTRACTING = "extracting"
    ANALYZING = "analyzing"
    COMPLETE = "complete"
    FAILED = "failed"


class StudyPhaseLabel(str, Enum):
    NON_CONTRAST = "non_contrast"
    ARTERIAL = "arterial"
    PORTAL_VENOUS = "portal_venous"
    DELAYED = "delayed"
    HEPATOBILIARY = "hepatobiliary"
    T1 = "T1"
    T2 = "T2"
    DWI = "dwi"
    ADC = "adc"
    UNKNOWN = "unknown"


class SeriesInfo(BaseModel):
    series_uid: str
    description: str
    phase: Optional[str] = None
    num_slices: int = 0


class DicomStudy(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    upload_time: datetime = Field(default_factory=datetime.utcnow)
    modality: Optional[Modality] = None
    study_description: Optional[str] = None
    num_files: int = 0
    series: List[SeriesInfo] = []
    cancer_type: str = "liver"
    owner_user_id: Optional[str] = None
    owner_department: Optional[str] = None

    @property
    def phases(self) -> List[str]:
        return [s.phase or "unknown" for s in self.series]


class LesionFinding(BaseModel):
    lesion_id: str
    location_segment: Optional[str] = None
    size_mm: Optional[float] = None
    # LI-RADS (liver-specific; kept for backward compat)
    lirads_category: LiRadsCategory = LiRadsCategory.INDETERMINATE
    aphe_present: Optional[bool] = None
    washout_present: Optional[bool] = None
    capsule_present: Optional[bool] = None
    diffusion_restriction: Optional[bool] = None
    # Generic scoring (used by skin / lung / breast / colorectal modules)
    score_system: Optional[str] = None   # e.g. "ABCDE", "BI-RADS", "Lung-RADS"
    score: Optional[str] = None          # human-readable score, e.g. "High risk (5/7)"
    major_features: List[str] = []
    ancillary_features: List[str] = []
    reasoning: Optional[str] = None


class DiagnosticReport(BaseModel):
    study_id: str
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    modality: str
    cancer_type: str = "liver"
    model: Optional[str] = None   # LLM tag that produced this report (for comparison)
    overall_impression: str
    lesions: List[LesionFinding] = []
    differential_diagnosis: List[str] = []
    bclc_stage: Optional[str] = None          # liver-specific (BCLC)
    vascular_involvement: Optional[str] = None # liver-specific
    staging: Optional[str] = None              # generic staging for other cancers
    recommendations: List[str] = []
    guideline_citations: List[str] = []
    raw_llm_output: Optional[str] = None
    rag_context_used: bool = False
    radiomics_summary: Optional[str] = None


class SignOffDecision(str, Enum):
    APPROVED = "approved"
    CHANGES_REQUESTED = "changes_requested"


class SignOff(BaseModel):
    radiologist_name: str
    decision: SignOffDecision
    comments: Optional[str] = None
    signed_at: datetime = Field(default_factory=datetime.utcnow)


class SignOffRequest(BaseModel):
    radiologist_name: str
    decision: SignOffDecision
    comments: Optional[str] = None


class AnalysisJob(BaseModel):
    job_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    study_id: str
    cancer_type: str = "liver"
    model: Optional[str] = None   # LLM tag chosen for this run
    owner_user_id: Optional[str] = None
    owner_department: Optional[str] = None
    status: AnalysisStatus = AnalysisStatus.PENDING
    progress: int = 0
    current_step: str = "Queued"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    error: Optional[str] = None
    report: Optional[DiagnosticReport] = None
    sign_off: Optional[SignOff] = None
    timings: Dict[str, float] = Field(default_factory=dict)


class UploadResponse(BaseModel):
    study_id: str
    num_files: int
    modality: Optional[str]
    series: List[SeriesInfo] = []
    message: str
    suggested_cancer_type: Optional[str] = None   # e.g. "liver" — from DICOM metadata
    detection_confidence: Optional[str] = None    # "high" | "medium" | "low"
    detection_reason: Optional[str] = None        # e.g. "BodyPartExamined: LIVER"


class RagQueryRequest(BaseModel):
    query: str
    n_results: int = 5


class PatientContext(BaseModel):
    cirrhosis: bool = False
    hepatitis_b: bool = False
    hepatitis_c: bool = False
    afp_level: Optional[float] = None
    prior_hcc: bool = False
    notes: Optional[str] = None
