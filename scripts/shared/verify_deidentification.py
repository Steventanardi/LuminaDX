"""
verify_deidentification.py — Appendix C audit tool for DICOM PHI removal.

Usage:
    python scripts/verify_deidentification.py <dicom_dir_or_file> [--verbose]

Checks every DICOM file in the given directory against the DICOM PS3.15
Basic Application Level Confidentiality Profile tag list and reports any
tags that still contain non-anonymized values.

Exit code: 0 = clean, 1 = PHI found.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pydicom

# Full DICOM PS3.15 Table E.1-1 — Basic Application Level Confidentiality Profile
# Tags expected to be empty / "ANONYMIZED" / replaced after de-identification
PHI_TAGS = [
    # Patient demographic identifiers
    ("PatientName",                   "0010,0010"),
    ("PatientID",                     "0010,0020"),
    ("PatientBirthDate",              "0010,0030"),
    ("PatientBirthTime",              "0010,0032"),
    ("PatientSex",                    "0010,0040"),
    ("OtherPatientIDs",               "0010,1000"),
    ("OtherPatientNames",             "0010,1001"),
    ("PatientMotherBirthName",        "0010,1060"),
    ("PatientAddress",                "0010,1040"),
    ("PatientTelephoneNumbers",       "0010,2154"),
    ("PatientTelecomInformation",     "0010,2155"),
    ("PatientComments",               "0010,4000"),
    ("EthnicGroup",                   "0010,2160"),
    ("Occupation",                    "0010,2180"),
    ("MedicalRecordLocator",          "0010,1090"),
    ("CountryOfResidence",            "0010,2150"),
    ("RegionOfResidence",             "0010,2152"),
    ("ResponsiblePerson",             "0010,2297"),
    ("ResponsibleOrganization",       "0010,2299"),
    ("LastMenstrualDate",             "0010,21D0"),
    ("MedicalAlerts",                 "0010,2000"),
    ("Allergies",                     "0010,2110"),
    ("AdditionalPatientHistory",      "0010,21B0"),
    ("IssuerOfPatientID",             "0010,0021"),
    # Referring / performing clinicians
    ("ReferringPhysicianName",        "0008,0090"),
    ("ReferringPhysicianAddress",     "0008,0092"),
    ("NameOfPhysiciansReadingStudy",  "0008,1048"),
    ("PhysiciansOfRecord",            "0008,1048"),
    ("PerformingPhysicianName",       "0008,1050"),
    ("OperatorsName",                 "0008,1070"),
    ("RequestingPhysician",           "0032,1032"),
    # Institution identifiers
    ("InstitutionName",               "0008,0080"),
    ("InstitutionAddress",            "0008,0081"),
    ("InstitutionalDepartmentName",   "0008,1040"),
    ("StationName",                   "0008,1010"),
    # Study / encounter identifiers
    ("AccessionNumber",               "0008,0050"),
    ("StudyID",                       "0020,0010"),
    ("AdmissionID",                   "0038,0010"),
    ("AdmittingDiagnosesDescription", "0008,1080"),
    ("VisitComments",                 "0038,4000"),
    # Device identifiers
    ("DeviceSerialNumber",            "0018,1000"),
    ("DeviceUID",                     "0018,1002"),
]

SAFE_VALUES = {"ANONYMIZED", "ANONYMIZED^ANONYMIZED", "", "ANON"}


def is_phi(value: str) -> bool:
    """Return True if the value looks like real PHI (not blank / not anonymized)."""
    v = str(value).strip()
    if not v:
        return False
    if v.upper() in SAFE_VALUES:
        return False
    if v.upper().startswith("ANON_") or v.upper().startswith("ANONYMIZED"):
        return False
    return True


def check_file(path: Path, verbose: bool = False) -> list[tuple[str, str, str]]:
    """Return list of (tag_name, dicom_tag, value) for any remaining PHI."""
    findings = []
    try:
        ds = pydicom.dcmread(str(path), stop_before_pixels=True, force=True)
    except Exception as exc:
        print(f"  WARN cannot read {path.name}: {exc}", file=sys.stderr)
        return findings

    for name, tag in PHI_TAGS:
        val = getattr(ds, name, None)
        if val is None:
            continue
        val_str = str(val).strip()
        if is_phi(val_str):
            findings.append((name, tag, val_str))
            if verbose:
                print(f"  [PHI] {name} ({tag}) = {val_str!r}")

    return findings


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify DICOM de-identification (PS3.15)")
    parser.add_argument("path", help="DICOM file or directory to audit")
    parser.add_argument("--verbose", "-v", action="store_true", help="Print each PHI tag found")
    args = parser.parse_args()

    root = Path(args.path)
    if root.is_file():
        files = [root]
    else:
        files = list(root.rglob("*.dcm")) + list(root.rglob("*.DCM"))
        if not files:
            files = [f for f in root.rglob("*") if f.is_file() and not f.suffix.lower() in (".json", ".txt")]

    if not files:
        print(f"No DICOM files found in {root}")
        return 0

    total_phi = 0
    clean = 0
    dirty = 0

    for f in files:
        findings = check_file(f, verbose=args.verbose)
        if findings:
            dirty += 1
            total_phi += len(findings)
            if not args.verbose:
                print(f"  [PHI] {f.name}: {len(findings)} tag(s) — {', '.join(n for n,_,_ in findings)}")
        else:
            clean += 1
            if args.verbose:
                print(f"  [OK]  {f.name}")

    print(f"\n{'='*60}")
    print(f"Files checked : {len(files)}")
    print(f"  Clean       : {clean}")
    print(f"  With PHI    : {dirty}")
    print(f"  PHI tags    : {total_phi}")
    if dirty == 0:
        print("RESULT: PASS — No PHI detected in any file.")
        return 0
    else:
        print("RESULT: FAIL — PHI detected. Review output above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
