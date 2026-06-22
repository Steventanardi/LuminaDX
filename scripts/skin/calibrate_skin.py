"""Calibrate the trained HAM10000 skin classifier and pick a malignancy operating
point, writing both back into the checkpoint so the running app applies them.

What it does (on the same stratified val split the trainer used, seed=42):
  1. Temperature scaling  — fits a single T (Platt-style) by minimising NLL, the
     standard fix for ResNet softmax over-confidence. Stored as ``temperature``.
  2. Operating threshold  — sweeps the malignant-vs-benign decision threshold and
     picks the Youden-J optimum (best sensitivity+specificity). Stored as
     ``malignancy_threshold``.
  3. Melanoma-sensitive urgent threshold — kept as a tunable (default 0.20),
     stored as ``melanoma_threshold``.

core/skin_classifier.py reads these keys (older checkpoints without them fall back
to T=1.0 / 0.5, so this is purely additive).

Run from repo root with the backend venv:
    backend/.venv/Scripts/python.exe scripts/skin/calibrate_skin.py
    ... --mel-threshold 0.20 --dry-run
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader
from torchvision import models, transforms

# Reuse the trainer's dataset/index/split so the val set matches exactly.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from train_skin_classifier import _load_samples, _split, HamDataset, MEAN, STD, OUT  # noqa: E402

MALIGNANT = {"akiec", "bcc", "mel"}


def _collect_logits(model, loader, device) -> tuple[torch.Tensor, torch.Tensor]:
    model.eval()
    logits_all, labels_all = [], []
    with torch.no_grad():
        for x, y in loader:
            logits_all.append(model(x.to(device)).cpu())
            labels_all.append(y)
    return torch.cat(logits_all), torch.cat(labels_all)


def _fit_temperature(logits: torch.Tensor, labels: torch.Tensor) -> float:
    """Fit a single temperature T minimising validation NLL via LBFGS."""
    T = nn.Parameter(torch.ones(1))
    nll = nn.CrossEntropyLoss()
    opt = torch.optim.LBFGS([T], lr=0.01, max_iter=200)

    def closure():
        opt.zero_grad()
        loss = nll(logits / T.clamp(min=1e-3), labels)
        loss.backward()
        return loss

    opt.step(closure)
    return float(T.clamp(min=1e-3).item())


def _metrics(probs_mal: np.ndarray, is_mal: np.ndarray, t: float) -> tuple[float, float]:
    pred = probs_mal >= t
    tp = int(np.sum(pred & is_mal)); fn = int(np.sum(~pred & is_mal))
    tn = int(np.sum(~pred & ~is_mal)); fp = int(np.sum(pred & ~is_mal))
    sens = tp / (tp + fn) if (tp + fn) else 0.0
    spec = tn / (tn + fp) if (tn + fp) else 0.0
    return sens, spec


def _best_threshold(probs_mal: np.ndarray, is_mal: np.ndarray) -> float:
    best_t, best_j = 0.5, -1.0
    for t in np.linspace(0.05, 0.95, 91):
        sens, spec = _metrics(probs_mal, is_mal, float(t))
        j = sens + spec - 1.0
        if j > best_j:
            best_j, best_t = j, float(t)
    return best_t


def _ece(probs: np.ndarray, labels: np.ndarray, bins: int = 15) -> float:
    """Expected Calibration Error of the top-1 prediction."""
    conf = probs.max(axis=1)
    pred = probs.argmax(axis=1)
    acc = (pred == labels).astype(float)
    edges = np.linspace(0, 1, bins + 1)
    ece = 0.0
    for lo, hi in zip(edges[:-1], edges[1:]):
        m = (conf > lo) & (conf <= hi)
        if m.any():
            ece += m.mean() * abs(acc[m].mean() - conf[m].mean())
    return float(ece)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ckpt", type=Path, default=OUT, help="checkpoint to calibrate")
    ap.add_argument("--img", type=int, default=0, help="override img_size (0 = use checkpoint)")
    ap.add_argument("--batch", type=int, default=64)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--mel-threshold", type=float, default=0.20,
                    help="melanoma-sensitive urgent flag threshold (stored verbatim)")
    ap.add_argument("--dry-run", action="store_true", help="compute but do not write checkpoint")
    args = ap.parse_args()

    if not args.ckpt.exists():
        print(f"Checkpoint not found: {args.ckpt}")
        sys.exit(1)

    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Device: {device}")
    ckpt = torch.load(args.ckpt, map_location=device, weights_only=False)
    classes = list(ckpt["classes"])
    img_size = args.img or int(ckpt.get("img_size", 224))

    model = models.resnet50(weights=None)
    model.fc = nn.Linear(model.fc.in_features, len(classes))
    model.load_state_dict(ckpt["state_dict"])
    model.to(device)

    samples, _ = _load_samples()
    _, val_s = _split(samples)  # seed=42, stratified — same val set as training
    tf = transforms.Compose([
        transforms.Resize((img_size, img_size)),
        transforms.ToTensor(),
        transforms.Normalize(MEAN, STD),
    ])
    val_ld = DataLoader(HamDataset(val_s, classes, tf), batch_size=args.batch,
                        shuffle=False, num_workers=args.workers,
                        pin_memory=(device == "cuda"))
    print(f"Val images: {len(val_s)}  classes: {classes}")

    logits, labels = _collect_logits(model, val_ld, device)
    labels_np = labels.numpy()

    ece_before = _ece(torch.softmax(logits, dim=1).numpy(), labels_np)
    T = _fit_temperature(logits, labels)
    probs = torch.softmax(logits / T, dim=1).numpy()
    ece_after = _ece(probs, labels_np)
    print(f"Temperature T = {T:.4f}   ECE {ece_before:.4f} -> {ece_after:.4f}")

    cls_idx = {c: i for i, c in enumerate(classes)}
    mal_cols = [cls_idx[c] for c in MALIGNANT if c in cls_idx]
    probs_mal = probs[:, mal_cols].sum(axis=1)
    is_mal = np.array([classes[l] in MALIGNANT for l in labels_np])

    thr = _best_threshold(probs_mal, is_mal)
    sens, spec = _metrics(probs_mal, is_mal, thr)
    sens05, spec05 = _metrics(probs_mal, is_mal, 0.5)
    print(f"Malignant operating point: threshold={thr:.3f}  sens={sens:.3f} spec={spec:.3f}  "
          f"(vs 0.50: sens={sens05:.3f} spec={spec05:.3f})")
    print(f"Melanoma urgent threshold: {args.mel_threshold:.3f}")

    if args.dry_run:
        print("Dry run — checkpoint NOT modified.")
        return

    ckpt["temperature"] = float(T)
    ckpt["malignancy_threshold"] = float(thr)
    ckpt["melanoma_threshold"] = float(args.mel_threshold)
    torch.save(ckpt, args.ckpt)
    print(f"[saved] calibration metadata written to {args.ckpt}")


if __name__ == "__main__":
    main()
