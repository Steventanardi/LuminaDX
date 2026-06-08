"""
Summarize batch validation results from validation_results.csv.

Usage:
    python scripts/summarize_results.py
    python scripts/summarize_results.py --csv scripts/validation_results.csv
"""
from __future__ import annotations

import argparse
import csv
import statistics
from collections import Counter, defaultdict
from pathlib import Path

DEFAULT_CSV = Path(__file__).parent / "validation_results.csv"


def _load(path: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _float(v: str) -> float | None:
    try:
        return float(v) if v.strip() else None
    except ValueError:
        return None


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", type=Path, default=DEFAULT_CSV)
    args = parser.parse_args()

    if not args.csv.exists():
        print(f"CSV not found: {args.csv}")
        return

    rows = _load(args.csv)

    # De-duplicate: keep best row per case_id (complete > failed)
    best: dict[str, dict] = {}
    for row in rows:
        cid = row["case_id"]
        if cid not in best or row["status"] == "complete":
            best[cid] = row

    cases = list(best.values())
    complete = [r for r in cases if r["status"] == "complete"]
    failed  = [r for r in cases if r["status"] != "complete"]

    total = len(cases)
    n_ok  = len(complete)
    n_fail = len(failed)
    pct   = n_ok / total * 100 if total else 0

    print("=" * 60)
    print("  BATCH VALIDATION SUMMARY")
    print("=" * 60)
    print(f"  Cases processed : {total}")
    print(f"  Complete        : {n_ok}  ({pct:.1f}%)")
    print(f"  Failed          : {n_fail}  ({100 - pct:.1f}%)")
    print()

    # ── Timing stats ──────────────────────────────────────────────
    timing_cols = ["conversion_s", "segmentation_s", "radiomics_s", "rag_s", "llm_s", "total_s"]
    timing_data: dict[str, list[float]] = defaultdict(list)
    for r in complete:
        for col in timing_cols:
            v = _float(r.get(col, ""))
            if v is not None:
                timing_data[col].append(v)

    print("  PIPELINE TIMINGS  (complete cases only)")
    print(f"  {'Step':<16}  {'Mean':>7}  {'Min':>7}  {'Max':>7}  {'Median':>7}")
    print("  " + "-" * 52)
    labels = {
        "conversion_s":   "DICOM→NIfTI",
        "segmentation_s": "Segmentation",
        "radiomics_s":    "Radiomics",
        "rag_s":          "RAG",
        "llm_s":          "LLM",
        "total_s":        "TOTAL",
    }
    for col in timing_cols:
        vals = timing_data[col]
        if not vals:
            continue
        sep = "  " + "-" * 52 if col == "total_s" else ""
        if sep:
            print(sep)
        print(
            f"  {labels[col]:<16}  "
            f"{statistics.mean(vals):>6.1f}s  "
            f"{min(vals):>6.1f}s  "
            f"{max(vals):>6.1f}s  "
            f"{statistics.median(vals):>6.1f}s"
        )
    print()

    # ── LI-RADS distribution ──────────────────────────────────────
    lr_counts = Counter(r["li_rads_category"] or "—" for r in complete)
    print("  LI-RADS DISTRIBUTION  (complete cases)")
    for cat, cnt in sorted(lr_counts.items()):
        bar = "█" * cnt
        print(f"  {cat:<12}  {cnt:3d}  {bar}")
    print()

    # ── BCLC distribution ─────────────────────────────────────────
    bclc_counts = Counter(r["bclc_stage"] or "—" for r in complete)
    print("  BCLC STAGE DISTRIBUTION  (complete cases)")
    for stage, cnt in sorted(bclc_counts.items()):
        bar = "█" * cnt
        print(f"  {stage:<12}  {cnt:3d}  {bar}")
    print()

    # ── Anomalies ─────────────────────────────────────────────────
    anomalies = [
        r for r in complete
        if not r.get("li_rads_category") or not r.get("bclc_stage")
    ]
    if anomalies:
        print(f"  ANOMALIES  ({len(anomalies)} complete cases with missing LI-RADS/BCLC)")
        for r in anomalies:
            print(f"    {r['case_id']}  lesions={r.get('num_lesions', '?')}  llm_s={r.get('llm_s', '?')}")
        print()

    # ── Failures ──────────────────────────────────────────────────
    if failed:
        print(f"  FAILED CASES  ({n_fail})")
        error_groups: dict[str, list[str]] = defaultdict(list)
        for r in failed:
            err = r.get("error", "") or "unknown"
            key = "timeout" if "timed out" in err.lower() else err[:60] or "unknown"
            error_groups[key].append(r["case_id"])
        for err_key, cids in sorted(error_groups.items(), key=lambda x: -len(x[1])):
            print(f"    [{len(cids)}×] {err_key}")
            print(f"         → {', '.join(sorted(cids))}")
        print()

    # ── Total runs in CSV (including retries) ────────────────────
    n_rows = len(rows)
    n_retries = n_rows - total
    if n_retries > 0:
        print(f"  Total CSV rows: {n_rows}  (including {n_retries} retries/duplicates)")
    print("=" * 60)


if __name__ == "__main__":
    main()
