"""Skin eval harness — compare KNN vs the trained HAM10000 classifier (vs the LLM)
on a held-out test split.

Every method is scored on the same binary task that matters clinically —
**malignant vs benign** — plus the trained classifier's native 7-class top-1
accuracy. For each it reports accuracy, sensitivity (malignant recall),
specificity, precision and F1 so the thesis can state, on one shared test set,
how the geometric/CNN methods stack up.

Test sets
---------
1. ``--ham-split``  reconstructs the *exact* validation split the classifier was
   trained against (stratified, seed 42, 15%% — see train_skin_classifier.py), so
   the trained model is scored on data it never saw. Ground-truth malignancy is
   derived from the HAM10000 ``dx`` code.
   ⚠ The KNN reference library may overlap HAM10000; if so, KNN numbers on this
   split are optimistic. Prefer an independent ``--test-dir`` for KNN.
2. ``--test-dir DIR`` with ``DIR/<label>/*.jpg`` where <label> is either a
   HAM10000 dx code (akiec/bcc/mel/bkl/df/nv/vasc) or plain ``benign``/``malignant``.

Usage (from backend/):
    .venv\\Scripts\\python.exe scripts\\eval_skin.py --ham-split --limit 60
    .venv\\Scripts\\python.exe scripts\\eval_skin.py --test-dir "C:\\isic\\test" --llm
"""
from __future__ import annotations

import argparse
import random
import sys
import time
from collections import defaultdict
from pathlib import Path
from typing import Optional

# Make `core` / `config` importable when run as a standalone script.
BACKEND = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BACKEND))
REPO = BACKEND.parent

# Windows consoles default to cp1252 and choke on → / ⚠ etc. — force UTF-8 output.
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

from config import settings  # noqa: E402
from core import knn_classifier as knn  # noqa: E402
from core import skin_classifier  # noqa: E402
from core.skin_classifier import CLASS_INFO  # noqa: E402

_IMG_EXTS = (".jpg", ".jpeg", ".png")
HAM_DIR = REPO / "Datasets" / "Skin" / "HAM10000"
META_CSV = REPO / "Datasets" / "Skin" / "HAM10000_metadata.csv"

# LLM lesion risk levels that count as a "malignant" call when scoring the LLM.
_LLM_POSITIVE_RISKS = {"high", "intermediate", "medium"}


# ── ground truth ────────────────────────────────────────────────────────────
def _is_malignant(label: str) -> Optional[bool]:
    """Map a dx code or benign/malignant label to a malignancy boolean (None = skip)."""
    if label in CLASS_INFO:
        return CLASS_INFO[label][1]
    low = label.lower()
    if low in ("malignant", "benign"):
        return low == "malignant"
    return None


# ── test-set collection ─────────────────────────────────────────────────────
def _collect_test_dir(test_dir: Path) -> list[tuple[Path, str]]:
    pairs: list[tuple[Path, str]] = []
    for label_dir in sorted(p for p in test_dir.iterdir() if p.is_dir()):
        for img in sorted(label_dir.iterdir()):
            if img.suffix.lower() in _IMG_EXTS:
                pairs.append((img, label_dir.name))
    return pairs


def _collect_ham_val(frac_val: float = 0.15, seed: int = 42) -> list[tuple[Path, str]]:
    """Reconstruct train_skin_classifier.py's stratified validation split (dx codes)."""
    import csv
    idx: dict[str, Path] = {}
    for part in HAM_DIR.glob("HAM10000_images_part_*"):
        for img in part.glob("*.jpg"):
            idx[img.stem] = img
    samples: list[tuple[Path, str]] = []
    with open(META_CSV, newline="") as fh:
        for row in csv.DictReader(fh):
            p = idx.get(row["image_id"])
            if p is not None:
                samples.append((p, row["dx"]))
    by_cls: dict[str, list] = defaultdict(list)
    for s in samples:
        by_cls[s[1]].append(s)
    rng = random.Random(seed)
    val: list[tuple[Path, str]] = []
    for items in by_cls.values():
        rng.shuffle(items)
        n_val = max(1, int(len(items) * frac_val))
        val += items[:n_val]
    return val


def _cap_per_class(pairs: list[tuple[Path, str]], limit: int) -> list[tuple[Path, str]]:
    if not limit:
        return pairs
    seen: dict[str, int] = defaultdict(int)
    out: list[tuple[Path, str]] = []
    for img, lbl in pairs:
        if seen[lbl] < limit:
            out.append((img, lbl))
            seen[lbl] += 1
    return out


# ── binary-metric bookkeeping ───────────────────────────────────────────────
class BinaryScore:
    """Confusion counts for the malignant(=positive)/benign task."""

    def __init__(self, name: str) -> None:
        self.name = name
        self.tp = self.fp = self.fn = self.tn = self.skipped = 0

    def add(self, pred_malignant: Optional[bool], true_malignant: bool) -> None:
        if pred_malignant is None:
            self.skipped += 1
            return
        if true_malignant and pred_malignant:
            self.tp += 1
        elif true_malignant and not pred_malignant:
            self.fn += 1
        elif not true_malignant and pred_malignant:
            self.fp += 1
        else:
            self.tn += 1

    def report(self) -> str:
        n = self.tp + self.fp + self.fn + self.tn
        if n == 0:
            return f"  {self.name:<12} — no scored images ({self.skipped} skipped)"
        acc = (self.tp + self.tn) / n
        sens = self.tp / (self.tp + self.fn) if (self.tp + self.fn) else 0.0
        spec = self.tn / (self.tn + self.fp) if (self.tn + self.fp) else 0.0
        prec = self.tp / (self.tp + self.fp) if (self.tp + self.fp) else 0.0
        f1 = 2 * prec * sens / (prec + sens) if (prec + sens) else 0.0
        skip = f"  (+{self.skipped} skipped)" if self.skipped else ""
        return (f"  {self.name:<12} acc={acc:.3f}  sens={sens:.3f}  spec={spec:.3f}  "
                f"prec={prec:.3f}  f1={f1:.3f}  [TP{self.tp} FP{self.fp} FN{self.fn} "
                f"TN{self.tn}]{skip}")


# ── per-method predictions ──────────────────────────────────────────────────
def _knn_malignant(img: Path) -> Optional[bool]:
    res = knn.classify("skin", img, device=settings.device)
    if res is None:
        return None
    return _is_malignant(res.predicted_label)


def _clf_predict(img: Path, thresh: float, tta: bool):
    """Return (malignant_bool|None, top_dx_code|None, malignancy_prob|None)."""
    res = skin_classifier.classify(img, device=settings.device, tta=tta)
    if res is None:
        return None, None, None
    return res.malignancy_prob >= thresh, res.top_label, res.malignancy_prob


def _auc(probs: list[tuple[float, bool]]) -> Optional[float]:
    """Threshold-independent ROC-AUC via the rank (Mann–Whitney U) formula, with
    tie-averaged ranks. No sklearn dependency."""
    n_pos = sum(1 for _, y in probs if y)
    n_neg = len(probs) - n_pos
    if n_pos == 0 or n_neg == 0:
        return None
    ordered = sorted(probs, key=lambda t: t[0])
    ranks = [0.0] * len(ordered)
    i = 0
    while i < len(ordered):
        j = i
        while j + 1 < len(ordered) and ordered[j + 1][0] == ordered[i][0]:
            j += 1
        avg_rank = (i + j) / 2.0 + 1.0  # ranks are 1-based
        for k in range(i, j + 1):
            ranks[k] = avg_rank
        i = j + 1
    sum_ranks_pos = sum(r for r, (_, y) in zip(ranks, ordered) if y)
    return (sum_ranks_pos - n_pos * (n_pos + 1) / 2.0) / (n_pos * n_neg)


def _sweep(probs: list[tuple[float, bool]]) -> None:
    """Print acc/sens/spec across malignancy-probability cutoffs and recommend the
    screening operating point (highest specificity that still keeps sens ≥ 0.90)."""
    if not probs:
        return
    print("\nClassifier threshold sweep (malignant = positive):")
    print("  thr    acc    sens   spec")
    best_screen = None  # (spec, thr, sens, acc)
    for t in [i / 20 for i in range(2, 19)]:  # 0.10 … 0.90
        tp = sum(1 for p, y in probs if y and p >= t)
        fn = sum(1 for p, y in probs if y and p < t)
        tn = sum(1 for p, y in probs if not y and p < t)
        fp = sum(1 for p, y in probs if not y and p >= t)
        n = tp + fn + tn + fp
        acc = (tp + tn) / n if n else 0.0
        sens = tp / (tp + fn) if (tp + fn) else 0.0
        spec = tn / (tn + fp) if (tn + fp) else 0.0
        print(f"  {t:.2f}  {acc:.3f}  {sens:.3f}  {spec:.3f}")
        if sens >= 0.90 and (best_screen is None or spec > best_screen[0]):
            best_screen = (spec, t, sens, acc)
    if best_screen:
        spec, t, sens, acc = best_screen
        print(f"  → screening operating point: thr={t:.2f} "
              f"(sens={sens:.3f}, spec={spec:.3f}, acc={acc:.3f})")
    else:
        print("  → no cutoff reached sens ≥ 0.90 on this set.")


async def _llm_malignant(img: Path, module, tmp_dir: Path, i: int) -> Optional[bool]:
    from core.image_preprocess import preprocess_dermoscopy
    from core.llm_client import llm_client
    from core.segmentation import SegmentationResult

    enhanced = tmp_dir / f"eval_{i}.png"
    radiomics = ""
    try:
        feats = preprocess_dermoscopy(img, enhanced, compute_abcd=True)
        send = enhanced if enhanced.exists() else img
        if feats is not None:
            radiomics = feats.summary()
    except Exception:
        send = img
    report = await llm_client.analyze(
        send, SegmentationResult(), "Dermoscopy",
        radiomics_summary=radiomics, module=module,
    )
    risks = [(l.score or "").lower() for l in report.lesions]
    risk_levels = " ".join(risks) + " " + (report.overall_impression or "").lower()
    # Positive if any lesion is flagged elevated risk, or melanoma/carcinoma is named.
    if any(r in risk_levels for r in _LLM_POSITIVE_RISKS):
        return True
    diff = " ".join(report.differential_diagnosis[:1]).lower()
    return any(k in diff for k in ("melanoma", "carcinoma", "malignan"))


# ── main ────────────────────────────────────────────────────────────────────
def main() -> None:
    ap = argparse.ArgumentParser(description="Compare KNN / trained classifier / LLM on skin.")
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--ham-split", action="store_true",
                     help="score on the classifier's held-out HAM10000 val split")
    src.add_argument("--test-dir", type=Path, help="DIR/<label>/*.jpg test set")
    ap.add_argument("--limit", type=int, default=0, help="cap images per class (0 = all)")
    ap.add_argument("--clf-thresh", type=float, default=0.5,
                    help="malignancy-probability cutoff for the trained classifier")
    ap.add_argument("--tta", action="store_true",
                    help="score the trained classifier with test-time augmentation")
    ap.add_argument("--sweep", action="store_true",
                    help="sweep classifier malignancy thresholds and suggest an operating point")
    ap.add_argument("--llm", action="store_true", help="also score the LLM (slow; needs Ollama)")
    ap.add_argument("--no-knn", action="store_true", help="skip the KNN method")
    args = ap.parse_args()

    if args.ham_split:
        if not META_CSV.exists():
            sys.exit(f"HAM10000 metadata not found at {META_CSV}")
        pairs = _collect_ham_val()
        print(f"HAM10000 held-out val split: {len(pairs)} images")
    else:
        if not args.test_dir.exists():
            sys.exit(f"Test dir not found: {args.test_dir}")
        pairs = _collect_test_dir(args.test_dir)
        print(f"Test dir {args.test_dir}: {len(pairs)} images")

    pairs = _cap_per_class(pairs, args.limit)
    # keep only images whose ground-truth malignancy we can resolve
    pairs = [(p, l) for p, l in pairs if _is_malignant(l) is not None]
    if not pairs:
        sys.exit("No usable labelled images (unknown labels?).")
    n_mal = sum(_is_malignant(l) for _, l in pairs)
    print(f"Scoring {len(pairs)} images — {n_mal} malignant / {len(pairs) - n_mal} benign\n")

    use_knn = not args.no_knn
    if use_knn:
        st = knn.status("skin")
        if not st["ready"]:
            print(f"  [warn] KNN not ready ({st}); disabling KNN.")
            use_knn = False
    clf_ok = skin_classifier.is_available()
    if not clf_ok:
        print(f"  [warn] no trained checkpoint at {skin_classifier.CHECKPOINT}; disabling classifier.")

    knn_score = BinaryScore("KNN")
    clf_score = BinaryScore("Classifier")
    llm_score = BinaryScore("LLM")
    clf_7class_correct = clf_7class_n = 0
    clf_probs: list[tuple[float, bool]] = []  # (malignancy_prob, true_malignant) for the sweep

    module = tmp_dir = loop = None
    if args.llm:
        import asyncio
        import tempfile
        from core.modules.skin import SkinModule
        module = SkinModule()
        tmp_dir = Path(tempfile.mkdtemp(prefix="skin_eval_"))
        loop = asyncio.new_event_loop()

    t0 = time.time()
    for i, (img, label) in enumerate(pairs, 1):
        truth = bool(_is_malignant(label))
        if use_knn:
            try:
                knn_score.add(_knn_malignant(img), truth)
            except Exception as exc:
                print(f"  [knn fail] {img.name}: {exc}"); knn_score.skipped += 1
        if clf_ok:
            try:
                mal, top, prob = _clf_predict(img, args.clf_thresh, args.tta)
                clf_score.add(mal, truth)
                if prob is not None:
                    clf_probs.append((prob, truth))
                if top is not None and label in CLASS_INFO:
                    clf_7class_n += 1
                    clf_7class_correct += int(top == label)
            except Exception as exc:
                print(f"  [clf fail] {img.name}: {exc}"); clf_score.skipped += 1
        if args.llm:
            try:
                llm_score.add(loop.run_until_complete(
                    _llm_malignant(img, module, tmp_dir, i)), truth)
            except Exception as exc:
                print(f"  [llm fail] {img.name}: {exc}"); llm_score.skipped += 1
        if i % 25 == 0:
            print(f"  {i}/{len(pairs)} … ({time.time() - t0:.0f}s)")

    if loop is not None:
        loop.close()

    print("\n" + "=" * 70)
    print(f"MALIGNANT-vs-BENIGN  ({len(pairs)} images, clf-thresh={args.clf_thresh})")
    print("=" * 70)
    if use_knn:
        print(knn_score.report())
    if clf_ok:
        print(clf_score.report())
        auc = _auc(clf_probs)
        if auc is not None:
            print(f"  {'Classifier':<12} ROC-AUC={auc:.3f}  (threshold-independent)")
    if args.llm:
        print(llm_score.report())
    if clf_7class_n:
        print(f"\nTrained classifier 7-class top-1: "
              f"{clf_7class_correct}/{clf_7class_n} = {clf_7class_correct / clf_7class_n:.4f}")
    if args.sweep and clf_probs:
        _sweep(clf_probs)
    print(f"\nElapsed: {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
