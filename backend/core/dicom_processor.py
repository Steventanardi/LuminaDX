from __future__ import annotations

import uuid
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import dicom2nifti
import numpy as np
import pydicom
import SimpleITK as sitk
from loguru import logger

from models.schemas import Modality, SeriesInfo, StudyPhaseLabel

# Phase preference order for selecting the primary series for segmentation.
# Arterial/portal are best for liver lesion detection; unknown/fallback last.
_PHASE_PRIORITY = [
    StudyPhaseLabel.ARTERIAL,
    StudyPhaseLabel.PORTAL_VENOUS,
    StudyPhaseLabel.DELAYED,
    StudyPhaseLabel.NON_CONTRAST,
    StudyPhaseLabel.T1,
    StudyPhaseLabel.HEPATOBILIARY,
    StudyPhaseLabel.T2,
    StudyPhaseLabel.DWI,
    StudyPhaseLabel.ADC,
    StudyPhaseLabel.UNKNOWN,
]

_PHASE_KEYWORDS: Dict[str, List[str]] = {
    StudyPhaseLabel.ARTERIAL: ["arterial", "art ", "late art", "hepatic art", "cap"],
    StudyPhaseLabel.PORTAL_VENOUS: ["portal", "venous", "pv ", "porto", "pvp"],
    StudyPhaseLabel.DELAYED: ["delayed", "equilibrium", "late ", "5min", "3min", "equil"],
    StudyPhaseLabel.NON_CONTRAST: ["non ", "unenhanced", "pre ", "plain", " nc", "precontrast"],
    StudyPhaseLabel.HEPATOBILIARY: ["hepatobiliary", "hbp", "20min", "hepato"],
    StudyPhaseLabel.T1: ["t1 ", "in phase", "opposed", "in-phase", "t1w"],
    StudyPhaseLabel.T2: ["t2 ", "haste", "ssfse", "fiesta", "t2w", "trufisp"],
    StudyPhaseLabel.DWI: ["dwi", "diffusion", "dw "],
    StudyPhaseLabel.ADC: ["adc", "apparent diffusion"],
}


def detect_phase(description: str) -> str:
    if not description:
        return StudyPhaseLabel.UNKNOWN
    desc = description.lower()
    for phase, keywords in _PHASE_KEYWORDS.items():
        if any(kw in desc for kw in keywords):
            return phase
    return StudyPhaseLabel.UNKNOWN


def detect_modality(ds: pydicom.Dataset) -> Optional[Modality]:
    m = getattr(ds, "Modality", "").upper()
    if m == "CT":
        return Modality.CT
    if m in ("MR", "MRI"):
        return Modality.MRI
    return None


_PHI_REMOVE = [
    # Patient identity
    "PatientName", "PatientBirthDate", "PatientBirthTime",
    "PatientAddress", "PatientTelephoneNumbers", "PatientTelecomInformation",
    "PatientMotherBirthName", "OtherPatientNames", "OtherPatientIDs",
    "OtherPatientIDsSequence", "PatientComments", "PatientInsurancePlanCodeSequence",
    "PatientReligiousPreference", "MedicalAlerts", "Allergies",
    "AdditionalPatientHistory", "LastMenstrualDate", "SmokingStatus",
    "Occupation", "MedicalRecordLocator", "CountryOfResidence",
    "RegionOfResidence", "IssuerOfPatientID", "TypeOfPatientID",
    "QualityControlSubject", "SpecialNeeds",
    # Visit / encounter
    "AdmissionID", "AdmittingDiagnosesDescription",
    "CurrentPatientLocation", "PatientInstitutionResidence", "VisitComments",
    # Scheduled workflow
    "ScheduledPerformingPhysicianName", "PerformedProcedureStepDescription",
    "RequestedProcedureDescription", "RequestAttributesSequence",
    "ScheduledStepAttributesSequence",
    # Device identifiers
    "DeviceSerialNumber", "DeviceUID", "PlateID", "CassetteID",
    "GeneratorID", "GridID",
]

_PHI_ANONYMIZE = [
    # Replace with ANONYMIZED (keep field present for structural integrity)
    "PatientID", "PatientSex", "PatientAge", "PatientSize", "PatientWeight",
    "EthnicGroup", "PatientSpeciesDescription", "PatientBreedDescription",
    "PatientSexNeutered", "PregnancyStatus",
    "ResponsiblePerson", "ResponsibleOrganization",
    "ReferringPhysicianName", "ReferringPhysicianAddress",
    "ReferringPhysicianTelephoneNumbers",
    "InstitutionName", "InstitutionAddress", "InstitutionalDepartmentName",
    "StationName", "OperatorsName", "OperatorIdentificationSequence",
    "PerformingPhysicianName", "PerformingPhysicianIdentificationSequence",
    "PhysiciansOfRecord", "PhysiciansOfRecordIdentificationSequence",
    "NameOfPhysiciansReadingStudy", "PhysiciansReadingStudyIdentificationSequence",
    "RequestingPhysician", "RequestingService",
    "AccessionNumber", "StudyID",
    "NameOfPhysiciansReadingStudy",
]


def anonymize_dataset(ds: pydicom.Dataset) -> pydicom.Dataset:
    """Remove or scrub all PHI fields per DICOM PS3.15 Basic Application Level Confidentiality Profile."""
    for tag in _PHI_REMOVE:
        try:
            if hasattr(ds, tag):
                delattr(ds, tag)
        except Exception:
            pass

    for tag in _PHI_ANONYMIZE:
        try:
            if hasattr(ds, tag):
                setattr(ds, tag, "ANONYMIZED")
        except Exception:
            pass

    ds.PatientID = "ANON_" + str(uuid.uuid4())[:8].upper()
    ds.PatientName = "ANONYMIZED^ANONYMIZED"
    return ds


def load_series_map(study_dir: Path) -> Dict[str, List[pydicom.Dataset]]:
    series_map: Dict[str, List[pydicom.Dataset]] = {}

    candidates = list(study_dir.glob("**/*.dcm")) + list(study_dir.glob("**/*.DCM"))
    if not candidates:
        candidates = [f for f in study_dir.rglob("*") if f.is_file()]

    for path in candidates:
        try:
            ds = pydicom.dcmread(str(path), force=True)
            uid = str(getattr(ds, "SeriesInstanceUID", "unknown"))
            series_map.setdefault(uid, []).append(ds)
        except Exception as exc:
            logger.debug(f"Skip {path.name}: {exc}")

    for uid in series_map:
        series_map[uid].sort(key=lambda x: int(getattr(x, "InstanceNumber", 0)))

    return series_map


def extract_study_info(series_map: Dict[str, List[pydicom.Dataset]]) -> Dict:
    modality = None
    series_list: List[SeriesInfo] = []

    for uid, slices in series_map.items():
        if not slices:
            continue
        ds = slices[0]
        if modality is None:
            modality = detect_modality(ds)

        desc = (
            getattr(ds, "SeriesDescription", "")
            or getattr(ds, "ProtocolName", "")
            or ""
        )
        series_list.append(
            SeriesInfo(
                series_uid=uid,
                description=desc,
                phase=detect_phase(desc),
                num_slices=len(slices),
            )
        )

    return {"modality": modality, "series": series_list}


def convert_to_nifti(study_dir: Path, output_dir: Path) -> List[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        dicom2nifti.convert_directory(
            str(study_dir),
            str(output_dir),
            compression=True,
            reorient=True,
        )
        files = list(output_dir.glob("*.nii.gz"))
        if files:
            logger.info(f"dicom2nifti produced {len(files)} NIfTI file(s)")
            return files
    except Exception as exc:
        logger.warning(f"dicom2nifti failed ({exc}), falling back to SimpleITK")

    return _sitk_convert(study_dir, output_dir)


def _sitk_convert(study_dir: Path, output_dir: Path) -> List[Path]:
    reader = sitk.ImageSeriesReader()
    series_ids = reader.GetGDCMSeriesIDs(str(study_dir))
    results = []

    for sid in series_ids:
        try:
            files = reader.GetGDCMSeriesFileNames(str(study_dir), sid)
            reader.SetFileNames(files)
            image = reader.Execute()
            out = output_dir / f"{sid}.nii.gz"
            sitk.WriteImage(image, str(out))
            results.append(out)
        except Exception as exc:
            logger.warning(f"SimpleITK failed for series {sid}: {exc}")

    logger.info(f"SimpleITK produced {len(results)} NIfTI file(s)")
    return results


def apply_window(
    pixel_array: np.ndarray,
    center: float,
    width: float,
) -> np.ndarray:
    lo = center - width / 2
    hi = center + width / 2
    clipped = np.clip(pixel_array, lo, hi)
    return ((clipped - lo) / (hi - lo) * 255).astype(np.uint8)


def default_window(modality: str) -> Tuple[float, float]:
    """Return (center, width) liver-optimised window."""
    if modality.upper() == "CT":
        return 50.0, 400.0
    return 200.0, 400.0
