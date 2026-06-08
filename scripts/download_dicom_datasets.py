#!/usr/bin/env python3
"""
Download liver cancer DICOM datasets.

Sources (both free, no login required):
  1. TCIA TCGA-LIHC  — public liver HCC multi-modality CT + MRI
  2. CHAOS MRI        — abdominal T1/T2 MRI with liver masks (Zenodo)

Usage:
  python scripts/download_dicom_datasets.py
  python scripts/download_dicom_datasets.py --ct 5 --mr 3   # custom limits
"""

import argparse
import sys
import zipfile
import requests
from pathlib import Path

DATASETS_DIR = Path(__file__).resolve().parent.parent / "Datasets"
TCIA_ENDPOINTS = [
    "https://services.cancerimagingarchive.net/nbia-api/services/v2",
    "https://nbia.cancerimagingarchive.net/nbia-api/services/v2",
]
TCIA = TCIA_ENDPOINTS[0]  # resolved at runtime by _tcia_series


# ── Shared helpers ────────────────────────────────────────────────────────────

def _download(url: str, dest: Path, params: dict = None, label: str = ""):
    dest.parent.mkdir(parents=True, exist_ok=True)
    r = requests.get(url, params=params, stream=True, timeout=600)
    r.raise_for_status()
    total = int(r.headers.get("content-length", 0))
    done = 0
    last_pct = -1
    with open(dest, "wb") as f:
        for chunk in r.iter_content(65_536):
            f.write(chunk)
            done += len(chunk)
            if total:
                pct = done * 100 // total
                if pct != last_pct and pct % 10 == 0:
                    print(f"  {label}: {pct}% ({done//1_000_000}/{total//1_000_000} MB)")
                    last_pct = pct


def _unzip(zip_path: Path, dest_dir: Path):
    with zipfile.ZipFile(zip_path, "r") as z:
        z.extractall(dest_dir)
    zip_path.unlink()


def _dcm_count(folder: Path) -> int:
    return sum(1 for _ in folder.rglob("*.dcm"))


# ── TCIA TCGA-LIHC ───────────────────────────────────────────────────────────

def _tcia_series(collection: str, modality: str) -> list:
    global TCIA
    for endpoint in TCIA_ENDPOINTS:
        try:
            r = requests.get(
                f"{endpoint}/getSeries",
                params={"Collection": collection, "Modality": modality},
                timeout=15,
            )
            r.raise_for_status()
            TCIA = endpoint  # cache working endpoint
            return r.json()
        except Exception as e:
            print(f"  [warn] {endpoint} failed: {e}")
    raise RuntimeError("All TCIA endpoints unreachable")


def _tcia_download_series(uid: str, dest: Path):
    dest.mkdir(parents=True, exist_ok=True)
    tmp = dest / "_series.zip"
    _download(
        f"{TCIA}/getImage",
        tmp,
        params={"SeriesInstanceUID": uid},
        label=f"series {uid[:20]}…",
    )
    _unzip(tmp, dest)


def download_tcga_lihc(max_ct: int = 3, max_mr: int = 2):
    """Download TCIA TCGA-LIHC liver HCC scans (public, no credentials)."""
    print("\n[1/2] TCGA-LIHC  (TCIA public collection)")

    targets = [
        ("CT", max_ct, DATASETS_DIR / "multi_phase_ct" / "TCGA-LIHC"),
        ("MR", max_mr, DATASETS_DIR / "mri"           / "TCGA-LIHC"),
    ]

    for modality, limit, base_dir in targets:
        all_series = _tcia_series("TCGA-LIHC", modality)
        print(f"  {modality}: {len(all_series)} series available — fetching {limit}")

        fetched = 0
        for s in all_series:
            if fetched >= limit:
                break
            patient = s.get("PatientID", f"patient_{fetched+1}")
            uid     = s["SeriesInstanceUID"]
            dest    = base_dir / patient / uid[:12]

            if dest.exists() and _dcm_count(dest) > 0:
                print(f"  [skip] skip (cached): {patient}")
                fetched += 1
                continue

            print(f"  [get] {modality} {patient}")
            try:
                _tcia_download_series(uid, dest)
                n = _dcm_count(dest)
                print(f"    [ok] {n} DICOM files → {dest.relative_to(DATASETS_DIR)}")
                fetched += 1
            except Exception as e:
                print(f"    [err] failed: {e}")


# ── CHAOS MRI (Zenodo) ────────────────────────────────────────────────────────

ZENODO_CHAOS_ID = "3431873"


def download_chaos_mri():
    """Download CHAOS abdominal MRI dataset (T1/T2) from Zenodo."""
    print("\n[2/2] CHAOS MRI  (Zenodo record 3431873)")
    dest = DATASETS_DIR / "mri" / "CHAOS"
    dest.mkdir(parents=True, exist_ok=True)

    meta = requests.get(
        f"https://zenodo.org/api/records/{ZENODO_CHAOS_ID}", timeout=30
    ).json()
    files = meta.get("files", [])

    # Prefer the training set zip; fall back to first file
    wanted = next(
        (f for f in files if "Train" in f["key"] and f["key"].endswith(".zip")),
        files[0] if files else None,
    )
    if not wanted:
        print("  [err] no files found in Zenodo record")
        return

    name     = wanted["key"]
    size_mb  = wanted["size"] // 1_000_000
    link     = wanted["links"]["self"]
    zip_path = dest / name

    if zip_path.exists():
        print(f"  [skip] skip (cached): {name}")
    else:
        print(f"  [get] {name}  ({size_mb} MB)")
        _download(link, zip_path, label=name)

    print(f"  Extracting {name}…")
    _unzip(zip_path, dest)
    n = _dcm_count(dest)
    print(f"  [ok] {n} DICOM files → {dest.relative_to(DATASETS_DIR)}")


# ── Entry point ───────────────────────────────────────────────────────────────

def _print_tree():
    print("\nDataset layout:")
    seen = set()
    for p in sorted(DATASETS_DIR.rglob("*.dcm")):
        rel = p.relative_to(DATASETS_DIR)
        top = Path(*rel.parts[:3])  # modality / collection / patient
        if top not in seen:
            seen.add(top)
            print(f"  {top}/")
    print(f"  Total unique patient folders: {len(seen)}")


def main():
    ap = argparse.ArgumentParser(description="Download liver DICOM datasets")
    ap.add_argument("--ct",  type=int, default=3,  help="CT series to download (default 3)")
    ap.add_argument("--mr",  type=int, default=2,  help="MRI series from TCGA-LIHC (default 2)")
    ap.add_argument("--no-chaos", action="store_true", help="Skip CHAOS MRI download")
    args = ap.parse_args()

    print("==========================================")
    print("  Liver Cancer DICOM Dataset Downloader  ")
    print("==========================================")
    print(f"  Output: {DATASETS_DIR}")

    errors = []

    try:
        download_tcga_lihc(max_ct=args.ct, max_mr=args.mr)
    except Exception as e:
        errors.append(f"TCGA-LIHC: {e}")
        print(f"\n  [err] TCGA-LIHC failed: {e}")

    if not args.no_chaos:
        try:
            download_chaos_mri()
        except Exception as e:
            errors.append(f"CHAOS MRI: {e}")
            print(f"\n  [err] CHAOS MRI failed: {e}")

    _print_tree()

    print("\n==========================================")
    if errors:
        print("Completed with errors:")
        for err in errors:
            print(f"  - {err}")
        sys.exit(1)
    else:
        print("All datasets downloaded successfully.")


if __name__ == "__main__":
    main()
