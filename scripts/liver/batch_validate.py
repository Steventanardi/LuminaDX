"""
Batch validation script for HCC-TACE-Seg dataset.

Iterates all HCC_XXX cases, uploads CT DICOM files to the running API,
waits for analysis to complete, then saves results to a CSV file.

Usage:
    python scripts/batch_validate.py
    python scripts/batch_validate.py --cases HCC_001 HCC_002 HCC_010
    python scripts/batch_validate.py --limit 10
    python scripts/batch_validate.py --resume   # skip already-processed cases

Output:
    scripts/validation_results.csv
"""

from __future__ import annotations

import argparse
import csv
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

# ── Config ────────────────────────────────────────────────────────────────────
BASE_URL        = "http://localhost:8000"
DATASET_DIR     = Path(__file__).resolve().parents[2] / "Datasets" / "HCC-TACE-Seg" / "hcc_tace_seg"
OUTPUT_CSV      = Path(__file__).parent / "validation_results.csv"
POLL_INTERVAL_S = 10      # seconds between status checks
TIMEOUT_S       = 1200    # 20 min max per case (TotalSegmentator can be slow)
REQUEST_TIMEOUT = 300     # HTTP request timeout (seconds)
POLL_TIMEOUT    = 120     # status-check timeout — server can be slow under GPU load
RETRY_ATTEMPTS  = 3       # retry a case this many times before marking failed
COOLDOWN_S      = 20      # seconds between cases (lets GPU memory clear)

CSV_FIELDS = [
    "case_id", "study_id", "job_id", "status",
    "li_rads_category", "bclc_stage", "num_lesions",
    "lesion_1_size_mm", "lesion_1_location",
    "aphe", "washout", "capsule",
    "conversion_s", "segmentation_s", "radiomics_s", "rag_s", "llm_s",
    "total_s", "error", "processed_at",
]


# ── Helpers ───────────────────────────────────────────────────────────────────

def _get_ct_dicoms(case_dir: Path) -> list[Path]:
    """Return all .dcm files from CT_ series folders only (skip SEG_)."""
    dcm_files: list[Path] = []
    for series_dir in case_dir.rglob("CT_*"):
        if series_dir.is_dir():
            dcm_files.extend(series_dir.glob("*.dcm"))
    return sorted(dcm_files)


def _upload(dcm_files: list[Path]) -> str:
    """Upload DICOM files and return study_id."""
    files = [("files", (f.name, f.read_bytes(), "application/dicom")) for f in dcm_files]
    r = requests.post(f"{BASE_URL}/api/dicom/upload", files=files, timeout=REQUEST_TIMEOUT)
    r.raise_for_status()
    return r.json()["study_id"]


def _start_analysis(study_id: str) -> str:
    """Start analysis and return job_id."""
    r = requests.post(f"{BASE_URL}/api/analysis/start/{study_id}", timeout=30)
    r.raise_for_status()
    return r.json()["job_id"]


def _poll_until_done(job_id: str) -> dict:
    """Poll status until complete/failed or timeout. Returns the job dict."""
    deadline = time.monotonic() + TIMEOUT_S
    while time.monotonic() < deadline:
        r = requests.get(f"{BASE_URL}/api/analysis/status/{job_id}", timeout=POLL_TIMEOUT)
        r.raise_for_status()
        job = r.json()
        status = job.get("status", "")
        pct = job.get("progress", 0)
        step = job.get("current_step", "")
        print(f"      {pct:3d}%  {step}", end="\r", flush=True)
        if status in ("complete", "failed"):
            print()  # newline after \r
            return job
        time.sleep(POLL_INTERVAL_S)
    raise TimeoutError(f"Job {job_id} did not finish within {TIMEOUT_S}s")


def _get_benchmark(job_id: str) -> dict:
    try:
        r = requests.get(f"{BASE_URL}/api/analysis/benchmark/{job_id}", timeout=30)
        if r.ok:
            return r.json()
    except Exception:
        pass
    return {}


def _extract_row(case_id: str, study_id: str, job_id: str, job: dict, bench: dict) -> dict:
    """Flatten job/report/benchmark into a CSV row dict."""
    report = job.get("report") or {}
    lesions = report.get("lesions") or []
    first = lesions[0] if lesions else {}
    timings = job.get("timings") or {}

    # total_s: use benchmark wall-clock total if available, else sum timings
    total_s = bench.get("total_s") or sum(timings.values()) or ""

    return {
        "case_id":          case_id,
        "study_id":         study_id,
        "job_id":           job_id,
        "status":           job.get("status", ""),
        "li_rads_category": first.get("lirads_category", ""),
        "bclc_stage":       report.get("bclc_stage", ""),
        "num_lesions":      len(lesions),
        "lesion_1_size_mm": first.get("size_mm", ""),
        "lesion_1_location":first.get("location_segment", ""),
        "aphe":             first.get("aphe_present", ""),
        "washout":          first.get("washout_present", ""),
        "capsule":          first.get("capsule_present", ""),
        "conversion_s":     timings.get("conversion_s", ""),
        "segmentation_s":   timings.get("segmentation_s", ""),
        "radiomics_s":      timings.get("radiomics_s", ""),
        "rag_s":            timings.get("rag_s", ""),
        "llm_s":            timings.get("llm_s", ""),
        "total_s":          total_s,
        "error":            job.get("error", ""),
        "processed_at":     datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }


def _load_done_cases() -> set[str]:
    """Return set of case_ids already in the output CSV."""
    if not OUTPUT_CSV.exists():
        return set()
    with OUTPUT_CSV.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return {row["case_id"] for row in reader if row.get("status") == "complete"}


def _append_row(row: dict, write_header: bool) -> None:
    with OUTPUT_CSV.open("a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        if write_header:
            writer.writeheader()
        writer.writerow(row)


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Batch validate HCC-TACE-Seg cases.")
    parser.add_argument("--cases", nargs="+", help="Run only specific case IDs, e.g. HCC_001 HCC_002")
    parser.add_argument("--limit", type=int, default=0, help="Stop after N cases (0 = all)")
    parser.add_argument("--resume", action="store_true", help="Skip cases already in output CSV with status=complete")
    args = parser.parse_args()

    # Check API is reachable
    try:
        requests.get(f"{BASE_URL}/api/dicom/studies", timeout=5)
    except Exception:
        print(f"ERROR: Cannot reach API at {BASE_URL}. Start the backend first (Launch.bat).")
        sys.exit(1)

    # Discover cases
    if args.cases:
        all_cases = sorted([DATASET_DIR / c for c in args.cases if (DATASET_DIR / c).exists()])
    else:
        all_cases = sorted(p for p in DATASET_DIR.iterdir() if p.is_dir() and p.name.startswith("HCC_"))

    if not all_cases:
        print(f"No cases found in {DATASET_DIR}")
        sys.exit(1)

    done_cases = _load_done_cases() if args.resume else set()
    if done_cases:
        print(f"Resume: skipping {len(done_cases)} already-complete cases.")

    cases_to_run = [c for c in all_cases if c.name not in done_cases]
    if args.limit:
        cases_to_run = cases_to_run[:args.limit]

    write_header = not OUTPUT_CSV.exists()
    total = len(cases_to_run)
    passed = failed = skipped = 0

    print(f"Running {total} cases → {OUTPUT_CSV.name}")
    print("-" * 60)

    for i, case_dir in enumerate(cases_to_run, 1):
        case_id = case_dir.name
        print(f"[{i:3d}/{total}] {case_id}")

        # cooldown between cases so GPU memory clears
        if i > 1:
            time.sleep(COOLDOWN_S)

        dcm_files = _get_ct_dicoms(case_dir)
        if not dcm_files:
            print(f"      SKIP — no CT DICOM files found")
            skipped += 1
            continue

        last_exc: Exception | None = None
        succeeded = False

        for attempt in range(1, RETRY_ATTEMPTS + 1):
            if attempt > 1:
                print(f"      Retry {attempt}/{RETRY_ATTEMPTS} after {COOLDOWN_S}s …")
                time.sleep(COOLDOWN_S)

            try:
                t_start = time.monotonic()
                print(f"      Uploading {len(dcm_files)} CT slices …")
                study_id = _upload(dcm_files)

                print(f"      Starting analysis (study {study_id[:8]}…)")
                job_id = _start_analysis(study_id)

                job = _poll_until_done(job_id)
                bench = _get_benchmark(job_id)
                elapsed = round(time.monotonic() - t_start, 1)

                row = _extract_row(case_id, study_id, job_id, job, bench)
                _append_row(row, write_header)
                write_header = False

                if job.get("status") == "complete":
                    lr = row["li_rads_category"] or "?"
                    bclc = row["bclc_stage"] or "?"
                    print(f"      ✓  LR={lr}  BCLC={bclc}  {elapsed}s")
                    passed += 1
                    succeeded = True
                    break
                else:
                    last_exc = RuntimeError(job.get("error") or "pipeline failed")

            except KeyboardInterrupt:
                print("\nInterrupted — partial results saved to CSV.")
                sys.exit(0)
            except Exception as exc:
                last_exc = exc

        if not succeeded:
            err_msg = str(last_exc) if last_exc else "unknown error"
            print(f"      ✗  FAILED after {RETRY_ATTEMPTS} attempts: {err_msg[:120]}")
            error_row = {f: "" for f in CSV_FIELDS}
            error_row.update({
                "case_id":      case_id,
                "status":       "failed",
                "error":        err_msg,
                "processed_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            })
            _append_row(error_row, write_header)
            write_header = False
            failed += 1

    print("-" * 60)
    print(f"Done.  ✓ {passed} complete  ✗ {failed} failed  — {skipped} skipped")
    print(f"Results saved to: {OUTPUT_CSV}")


if __name__ == "__main__":
    main()
