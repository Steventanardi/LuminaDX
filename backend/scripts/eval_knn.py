"""Evaluate the KNN classifier against a held-out labelled test set.

Runs every image under <test-dir>/<label>/ through the KNN classifier (which
votes using the built reference index) and reports accuracy, a confusion matrix,
and per-class precision / recall / F1 — the validation numbers for the thesis.

The test set must NOT overlap with the reference set (data/reference/<cancer>/),
otherwise accuracy is inflated by data leakage.

Usage (from backend/):
    .venv\\Scripts\\python.exe scripts\\eval_knn.py --cancer skin \\
        --test-dir "C:\\path\\to\\kaggle\\test" --backbone cnn_resnet50 --k 5
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

# Make `core` / `config` importable when run as a standalone script.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config import settings  # noqa: E402
from core import knn_classifier as knn  # noqa: E402

_IMG_EXTS = (".jpg", ".jpeg", ".png")


def _collect(test_dir: Path) -> list[tuple[Path, str]]:
    pairs: list[tuple[Path, str]] = []
    for label_dir in sorted(p for p in test_dir.iterdir() if p.is_dir()):
        for img in sorted(label_dir.iterdir()):
            if img.suffix.lower() in _IMG_EXTS:
                pairs.append((img, label_dir.name))
    return pairs


def main() -> None:
    ap = argparse.ArgumentParser(description="Evaluate KNN classifier on a test set.")
    ap.add_argument("--cancer", default="skin")
    ap.add_argument("--test-dir", required=True, type=Path)
    ap.add_argument("--backbone", default="cnn_resnet50")
    ap.add_argument("--k", type=int, default=5)
    ap.add_argument("--limit", type=int, default=0, help="cap images per class (0 = all)")
    args = ap.parse_args()

    if not args.test_dir.exists():
        sys.exit(f"Test dir not found: {args.test_dir}")

    st = knn.status(args.cancer)
    if not st["ready"]:
        sys.exit(f"KNN not ready for {args.cancer}: {st}. Build the index first.")
    print(f"Reference set: {st['n_reference']} images, classes={st['classes']}")

    pairs = _collect(args.test_dir)
    if args.limit:
        capped: list[tuple[Path, str]] = []
        seen: dict[str, int] = {}
        for img, lbl in pairs:
            if seen.get(lbl, 0) < args.limit:
                capped.append((img, lbl))
                seen[lbl] = seen.get(lbl, 0) + 1
        pairs = capped
    if not pairs:
        sys.exit(f"No images found under {args.test_dir}/<label>/")

    labels = sorted({lbl for _, lbl in pairs})
    idx = {l: i for i, l in enumerate(labels)}
    n = len(labels)
    confusion = [[0] * n for _ in range(n)]  # confusion[true][pred]

    print(f"Evaluating {len(pairs)} images (k={args.k}, backbone={args.backbone}) …")
    t0 = time.time()
    correct = skipped = 0
    for i, (img, true_lbl) in enumerate(pairs, 1):
        res = knn.classify(args.cancer, img, backbone=args.backbone,
                           device=settings.device, k=args.k)
        if res is None:
            skipped += 1
            continue
        pred = res.predicted_label
        if pred not in idx:  # predicted a class not present in the test set
            idx[pred] = len(labels); labels.append(pred)
            for row in confusion:
                row.append(0)
            confusion.append([0] * len(labels))
            n = len(labels)
        confusion[idx[true_lbl]][idx[pred]] += 1
        if pred == true_lbl:
            correct += 1
        if i % 200 == 0:
            print(f"  {i}/{len(pairs)} … running acc {correct / (i - skipped):.3f}")

    total = len(pairs) - skipped
    if total == 0:
        sys.exit("All classifications failed — check the index/backbone.")

    print("\n" + "=" * 56)
    print(f"ACCURACY: {correct}/{total} = {correct / total:.4f}")
    if skipped:
        print(f"(skipped {skipped} unreadable/failed images)")
    print(f"Elapsed: {time.time() - t0:.0f}s")

    print("\nConfusion matrix (rows = true, cols = predicted):")
    head = "true\\pred".ljust(14) + "".join(l[:10].ljust(12) for l in labels)
    print(head)
    for t_lbl in labels:
        if idx[t_lbl] >= len(confusion):
            continue
        row = confusion[idx[t_lbl]]
        line = t_lbl[:12].ljust(14) + "".join(str(c).ljust(12) for c in row)
        print(line)

    print("\nPer-class precision / recall / F1:")
    for l in labels:
        li = idx[l]
        tp = confusion[li][li] if li < len(confusion) else 0
        fp = sum(confusion[r][li] for r in range(len(confusion)) if r != li)
        fn = sum(confusion[li]) - tp if li < len(confusion) else 0
        prec = tp / (tp + fp) if tp + fp else 0.0
        rec = tp / (tp + fn) if tp + fn else 0.0
        f1 = 2 * prec * rec / (prec + rec) if prec + rec else 0.0
        print(f"  {l:<12} precision={prec:.3f}  recall={rec:.3f}  f1={f1:.3f}")


if __name__ == "__main__":
    main()
