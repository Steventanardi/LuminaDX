from __future__ import annotations

import re
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


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
    upload_time: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
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
    # Skin-specific structured scoring
    dermoscopy_score: Optional[int] = None                # 7-point checklist total (0-7)
    abcde: Optional[Dict[str, Optional[bool]]] = None     # ABCDE flag breakdown
    major_features: List[str] = []
    ancillary_features: List[str] = []
    reasoning: Optional[str] = None

    @field_validator("score", "score_system", mode="before")
    @classmethod
    def _stringify_score(cls, v: Any) -> Any:
        # LLMs occasionally emit a bare number (e.g. 8.4) for a field we model as a
        # human-readable string. Coerce it so an otherwise-valid analysis isn't lost
        # to a Pydantic validation error that crashes the whole report.
        if v is None or isinstance(v, str):
            return v
        if isinstance(v, bool):
            return str(v)
        if isinstance(v, float) and v.is_integer():
            return str(int(v))          # 5.0 -> "5", not "5.0"
        if isinstance(v, (int, float)):
            return str(v)
        return str(v)

    @field_validator("size_mm", mode="before")
    @classmethod
    def _coerce_size(cls, v: Any) -> Any:
        # Accept ints, floats and strings like "8 mm" or "8.4"; give up gracefully
        # (-> None) on anything we can't read as a number.
        if v is None or isinstance(v, bool):
            return None
        if isinstance(v, (int, float)):
            return float(v)
        if isinstance(v, str):
            m = re.search(r"-?\d+(?:\.\d+)?", v)
            return float(m.group()) if m else None
        return None


class DifferentialItem(BaseModel):
    """One candidate diagnosis with explicit for/against evidence (pros/cons) and a
    likelihood the model must reconcile with the trained classifier's probability.
    Used by the skin module; other cancers keep the flat `differential_diagnosis`."""
    diagnosis: str
    likelihood: Optional[str] = None          # "high" | "moderate" | "low"
    supporting_features: List[str] = []       # evidence FOR this diagnosis (pros)
    opposing_features: List[str] = []         # evidence AGAINST this diagnosis (cons)


# Keys an LLM commonly nests its text under when it returns a list of objects
# instead of a list of strings (e.g. [{"step": "..."}] or [{"source": "..."}]).
_TEXT_KEYS = ("step", "text", "recommendation", "action", "detail", "description",
              "citation", "source", "reference", "guideline", "title", "name", "value")


def _flatten_str_item(v: Any) -> Optional[str]:
    """Coerce one list element to a string. LLMs frequently emit a dict like
    {"step": "..."} or {"source": "[guide.pdf p.7]"} where we model a plain
    string — pull the human-readable text out instead of crashing the report."""
    if v is None:
        return None
    if isinstance(v, str):
        return v
    if isinstance(v, dict):
        for k in _TEXT_KEYS:
            if k in v and isinstance(v[k], (str, int, float)):
                return str(v[k])
        parts = [str(x) for x in v.values() if isinstance(x, (str, int, float)) and str(x).strip()]
        return " — ".join(parts) if parts else None
    return str(v)


class DiagnosticReport(BaseModel):
    study_id: str
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    modality: str
    cancer_type: str = "liver"
    model: Optional[str] = None   # LLM tag that produced this report (for comparison)
    overall_impression: str
    lesions: List[LesionFinding] = []
    differential_diagnosis: List[str] = []
    # Structured for/against differential (skin); falls back to the flat list above.
    differential_assessment: List[DifferentialItem] = []
    bclc_stage: Optional[str] = None          # liver-specific (BCLC)
    vascular_involvement: Optional[str] = None # liver-specific
    staging: Optional[str] = None              # generic staging for other cancers
    recommendations: List[str] = []
    guideline_citations: List[str] = []
    raw_llm_output: Optional[str] = None
    rag_context_used: bool = False
    radiomics_summary: Optional[str] = None

    @field_validator("recommendations", "guideline_citations", "differential_diagnosis",
                     mode="before")
    @classmethod
    def _flatten_str_list(cls, v: Any) -> Any:
        # Local LLMs often return these as a list of objects (e.g. [{"step": "..."}])
        # rather than a list of strings; flatten each item so one stylistic quirk
        # doesn't fail the whole report with a Pydantic validation error.
        if not isinstance(v, list):
            return v
        out = [_flatten_str_item(item) for item in v]
        return [s for s in out if s is not None and str(s).strip()]


class SignOffDecision(str, Enum):
    APPROVED = "approved"
    CHANGES_REQUESTED = "changes_requested"


class SignOff(BaseModel):
    radiologist_name: str
    decision: SignOffDecision
    comments: Optional[str] = None
    signed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class SignOffRequest(BaseModel):
    radiologist_name: str
    decision: SignOffDecision
    comments: Optional[str] = None


class AnalysisJob(BaseModel):
    job_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    study_id: str
    cancer_type: str = "liver"
    model: Optional[str] = None   # LLM tag chosen for this run
    features: List[str] = Field(default_factory=list)  # selected feature/extractor keys
    owner_user_id: Optional[str] = None
    owner_department: Optional[str] = None
    status: AnalysisStatus = AnalysisStatus.PENDING
    progress: int = 0
    current_step: str = "Queued"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
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


class RagQueryRequest(BaseModel):
    query: str
    n_results: int = 5


class PatientContext(BaseModel):
    # Liver (HCC) context
    cirrhosis: bool = False
    hepatitis_b: bool = False
    hepatitis_c: bool = False
    afp_level: Optional[float] = None
    prior_hcc: bool = False
    # Skin (melanoma / NMSC) context
    fitzpatrick: Optional[str] = None          # skin phototype I–VI
    lesion_site: Optional[str] = None          # anatomical location of the lesion
    evolution: Optional[str] = None            # change over time → ABCDE "E"
    personal_melanoma_hx: bool = False
    family_melanoma_hx: bool = False
    immunosuppressed: bool = False
    notes: Optional[str] = None
