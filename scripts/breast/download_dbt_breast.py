#!/usr/bin/env python3
"""
Sort the Breast-Cancer-Screening-DBT (Duke DBT, 2024) TEST split into LuminaDx's
breast Healthy / Non-Healthy folders, using the dataset's own label + file-path CSVs.

Why the test split: it contains exactly 30 Cancer patients and 298 Normal — so you
get all 30 cancers plus a balanced 30 normals from ONE consistent source.

Selection:
  - Cancer patients  -> Non-Healthy/3. Breast-Cancer-Screening-DBT (2024)/   (all 30)
  - Normal patients  -> Healthy/Breast-Cancer-Screening-DBT (2024)/          (first --normals, default 30)

It reads the CSVs you downloaded into Datasets/breast/_dbt_meta/, resolves each case
to its SeriesInstanceUID (embedded in `classic_path`), and pulls ONLY those series
from the TCIA public API — no 1.4 TB full download, no login.

Usage:
  python scripts/download_dbt_breast.py                # 30 cancer + 30 normal
  python scripts/download_dbt_breast.py --normals 50   # all cancers + 50 normals
  python scripts/download_dbt_breast.py --dry-run      # list the selection, download nothing
"""

import argparse
import collections
import csv
import sys
import zipfile
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
META = ROOT / "Datasets" / "breast" / "_dbt_meta"
HEALTHY = ROOT / "Datasets" / "breast" / "Healthy" / "Breast-Cancer-Screening-DBT (2024)"
NONHEALTHY = ROOT / "Datasets" / "breast" / "Non-Healthy" / "3. Breast-Cancer-Screening-DBT (2024)"

LABELS = META / "BCS-DBT-labels-test-PHASE-2.csv"
PATHS = META / "BCS-DBT-file-paths-test-v2.csv"

TCIA_ENDPOINTS = [
    "https://services.cancerimagingarchive.net/nbia-api/services/v2",
    "https://nbia.cancerimagingarchive.net/nbia-api/services/v2",
]


# ── selection from CSVs ───────────────────────────────────────────────────────

def _worst(rows):
    """Patient label = worst finding across their views (Cancer > Benign > Actionable > Normal)."""
    a = {k: 0 for k in ("Cancer", "Benign", "Actionable", "Normal")}
    for r in rows:
        for k in a:
            a[k] |= int(r[k])
    if a["Cancer"]:
        return "Cancer"
    if a["Benign"]:
        return "Benign"
    if a["Actionable"]:
        return "Actionable"
    return "Normal"


def select_patients(n_normal):
    if not LABELS.exists():
        sys.exit(f"[err] labels CSV not found: {LABELS}\n      Put the DBT CSVs in {META}")
    by_pt = collections.defaultdict(list)
    with open(LABELS, newline="") as fh:
        for r in csv.DictReader(fh):
            by_pt[r["PatientID"]].append(r)
    cancer = sorted(p for p, v in by_pt.items() if _worst(v) == "Cancer")
    normal = sorted(p for p, v in by_pt.items() if _worst(v) == "Normal")[:n_normal]
    return cancer, normal


def series_for(pids):
    """patient_id -> list of (series_uid, view), parsed from classic_path."""
    if not PATHS.exists():
        sys.exit(f"[err] file-paths CSV not found: {PATHS}")
    want = set(pids)
    out = collections.defaultdict(list)
    with open(PATHS, newline="") as fh:
        for r in csv.DictReader(fh):
            if r["PatientID"] in want:
                # classic_path = Collection/PatientID/StudyUID/SeriesUID/file.dcm
                parts = r["classic_path"].split("/")
                if len(parts) >= 4:
                    out[r["PatientID"]].append((parts[3], r["View"]))
    return out


# ── TCIA download ─────────────────────────────────────────────────────────────

def tcia_download_series(uid, dest, label):
    dest.mkdir(parents=True, exist_ok=True)
    tmp = dest / "_series.zip"
    last_err = None
    for ep in TCIA_ENDPOINTS:
        try:
            with requests.get(f"{ep}/getImage", params={"SeriesInstanceUID": uid},
                              stream=True, timeout=600) as r:
                r.raise_for_status()
                with open(tmp, "wb") as f:
                    for chunk in r.iter_content(65_536):
                        f.write(chunk)
            with zipfile.ZipFile(tmp) as z:
                z.extractall(dest)
            tmp.unlink()
            return True
        except Exception as e:  # noqa: BLE001 - try next endpoint, then report
            last_err = e
    print(f"  [err] {label} {uid[:24]}...: {last_err}")
    return False


def fetch(pids, base, label, dry):
    smap = series_for(pids)
    nseries = sum(len(v) for v in smap.values())
    print(f"\n[{label}] {len(pids)} patients -> {nseries} series")
    done = 0
    for pid in pids:
        for uid, view in smap.get(pid, []):
            dest = base / pid / view
            if dry:
                print(f"  would fetch {pid}/{view:5s} {uid[:32]}...")
                continue
            if any(dest.glob("*.dcm")):
                done += 1
                continue
            if tcia_download_series(uid, dest, label):
                done += 1
            if done % 10 == 0:
                print(f"  {label}: {done}/{nseries}")
    if not dry:
        print(f"[ok] {label}: {done}/{nseries} series -> {base.relative_to(ROOT)}")
    return done


def main():
    ap = argparse.ArgumentParser(
        description="Sort DBT test split into breast Healthy/Non-Healthy via the TCIA API"
    )
    ap.add_argument("--normals", type=int, default=30,
                    help="number of Normal patients -> Healthy (default 30; all 30 cancers always included)")
    ap.add_argument("--dry-run", action="store_true", help="list the selection, download nothing")
    args = ap.parse_args()

    cancer, normal = select_patients(args.normals)
    print("=" * 54)
    print("  Breast-Cancer-Screening-DBT sorter (LuminaDx)")
    print("=" * 54)
    print(f"  cancer={len(cancer)} -> Non-Healthy | normal={len(normal)} -> Healthy")

    nc = fetch(cancer, NONHEALTHY, "cancer", args.dry_run)
    nn = fetch(normal, HEALTHY, "normal", args.dry_run)

    if not args.dry_run:
        print("\n" + "=" * 54)
        print(f"  Healthy     -> {HEALTHY}  ({nn} series)")
        print(f"  Non-Healthy -> {NONHEALTHY}  ({nc} series)")
        print("  Note: DBT series are tomosynthesis stacks. For your 2D CLAHE pipeline,")
        print("  use the synthesized-2D view or central slices.")
        print("=" * 54)
        if nc == 0 and nn == 0:
            sys.exit(1)


if __name__ == "__main__":
    main()
