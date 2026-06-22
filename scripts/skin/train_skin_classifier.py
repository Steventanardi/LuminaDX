"""Fine-tune a ResNet50 on HAM10000 for 7-class dermoscopy classification.

Produces  backend/data/weights/skin_ham10000_resnet50.pt  which the running app
loads via core/skin_classifier.py (the "HAM10000 classifier" feature).

Usage (from repo root, using the backend venv):
    backend/.venv/Scripts/python.exe scripts/train_skin_classifier.py
    ... --epochs 8 --batch 32 --lr 1e-4 --workers 4

Dataset is expected at  Datasets/Skin/HAM10000  (metadata CSV + image part dirs),
which is already present in this repo.
"""
from __future__ import annotations

import argparse
import csv
import time
from collections import Counter
from pathlib import Path

import torch
import torch.nn as nn
from PIL import Image
from torch.utils.data import DataLoader, Dataset
from torchvision import models, transforms

REPO = Path(__file__).resolve().parents[2]
HAM_DIR = REPO / "Datasets" / "Skin" / "HAM10000"
META_CSV = REPO / "Datasets" / "Skin" / "HAM10000_metadata.csv"
OUT = REPO / "backend" / "data" / "weights" / "skin_ham10000_resnet50.pt"

MEAN = [0.485, 0.456, 0.406]
STD = [0.229, 0.224, 0.225]


def _image_index() -> dict[str, Path]:
    """image_id → file path across both HAM10000 part directories."""
    idx: dict[str, Path] = {}
    for part in HAM_DIR.glob("HAM10000_images_part_*"):
        for img in part.glob("*.jpg"):
            idx[img.stem] = img
    return idx


def _load_samples() -> tuple[list[tuple[Path, str]], list[str]]:
    idx = _image_index()
    samples: list[tuple[Path, str]] = []
    with open(META_CSV, newline="") as fh:
        for row in csv.DictReader(fh):
            p = idx.get(row["image_id"])
            if p is not None:
                samples.append((p, row["dx"]))
    classes = sorted({lbl for _, lbl in samples})
    return samples, classes


def _split(samples, frac_val=0.15, seed=42):
    import random
    rng = random.Random(seed)
    by_cls: dict[str, list] = {}
    for s in samples:
        by_cls.setdefault(s[1], []).append(s)
    train, val = [], []
    for cls, items in by_cls.items():
        rng.shuffle(items)
        n_val = max(1, int(len(items) * frac_val))
        val += items[:n_val]
        train += items[n_val:]
    rng.shuffle(train); rng.shuffle(val)
    return train, val


class HamDataset(Dataset):
    def __init__(self, samples, classes, tf):
        self.samples = samples
        self.cls_to_idx = {c: i for i, c in enumerate(classes)}
        self.tf = tf

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, i):
        path, label = self.samples[i]
        img = Image.open(path).convert("RGB")
        return self.tf(img), self.cls_to_idx[label]


def _existing_val_acc(path: Path) -> float:
    """Validation accuracy baked into an existing checkpoint (0.0 if none)."""
    if not path.exists():
        return 0.0
    try:
        ckpt = torch.load(path, map_location="cpu", weights_only=False)
        return float(ckpt.get("val_acc") or 0.0)
    except Exception:
        return 0.0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--epochs", type=int, default=8)
    ap.add_argument("--batch", type=int, default=32)
    ap.add_argument("--lr", type=float, default=1e-4)
    ap.add_argument("--img", type=int, default=224)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--out", type=Path, default=OUT,
                    help="checkpoint path (default: the deployed weights file)")
    ap.add_argument("--label-smoothing", type=float, default=0.0,
                    help="CrossEntropy label smoothing (try 0.05)")
    ap.add_argument("--patience", type=int, default=0,
                    help="early-stop after N epochs without val improvement (0 = off)")
    ap.add_argument("--no-floor", action="store_true",
                    help="allow overwriting --out even if the new best is WORSE than its "
                         "current val_acc (default: refuse to regress the checkpoint)")
    args = ap.parse_args()
    out_path: Path = args.out

    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Device: {device}  ({torch.cuda.get_device_name(0) if device=='cuda' else 'CPU'})")

    samples, classes = _load_samples()
    print(f"Loaded {len(samples)} images, {len(classes)} classes: {classes}")
    print("Class counts:", dict(Counter(l for _, l in samples)))
    train_s, val_s = _split(samples)
    print(f"Train {len(train_s)}  Val {len(val_s)}")

    train_tf = transforms.Compose([
        transforms.Resize((args.img, args.img)),
        transforms.RandomHorizontalFlip(),
        transforms.RandomVerticalFlip(),
        transforms.RandomRotation(20),
        transforms.ColorJitter(0.1, 0.1, 0.1),
        transforms.ToTensor(),
        transforms.Normalize(MEAN, STD),
    ])
    val_tf = transforms.Compose([
        transforms.Resize((args.img, args.img)),
        transforms.ToTensor(),
        transforms.Normalize(MEAN, STD),
    ])

    train_ds = HamDataset(train_s, classes, train_tf)
    val_ds = HamDataset(val_s, classes, val_tf)
    train_ld = DataLoader(train_ds, batch_size=args.batch, shuffle=True,
                          num_workers=args.workers, pin_memory=(device == "cuda"))
    val_ld = DataLoader(val_ds, batch_size=args.batch, shuffle=False,
                        num_workers=args.workers, pin_memory=(device == "cuda"))

    # class-weighted loss for HAM10000's heavy nv imbalance
    counts = Counter(l for _, l in train_s)
    total = sum(counts.values())
    weights = torch.tensor([total / (len(classes) * counts[c]) for c in classes],
                           dtype=torch.float32, device=device)

    model = models.resnet50(weights=models.ResNet50_Weights.DEFAULT)
    model.fc = nn.Linear(model.fc.in_features, len(classes))
    model.to(device)

    criterion = nn.CrossEntropyLoss(weight=weights, label_smoothing=args.label_smoothing)
    optimizer = torch.optim.Adam(model.parameters(), lr=args.lr)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=args.epochs)
    scaler = torch.amp.GradScaler("cuda", enabled=(device == "cuda"))

    # Regression guard: never overwrite a good checkpoint with a worse one unless
    # --no-floor or a different --out is given.
    floor = 0.0 if (args.no_floor or out_path != OUT) else _existing_val_acc(out_path)
    if floor > 0.0:
        print(f"Regression guard: will only save if val_acc beats existing {floor*100:.2f}%")
    best_acc = floor
    epochs_since_improve = 0
    out_path.parent.mkdir(parents=True, exist_ok=True)

    for epoch in range(1, args.epochs + 1):
        model.train()
        t0 = time.time()
        running = 0.0
        for step, (x, y) in enumerate(train_ld):
            x, y = x.to(device, non_blocking=True), y.to(device, non_blocking=True)
            optimizer.zero_grad()
            with torch.amp.autocast("cuda", enabled=(device == "cuda")):
                out = model(x)
                loss = criterion(out, y)
            scaler.scale(loss).backward()
            scaler.step(optimizer)
            scaler.update()
            running += loss.item()
            if step % 50 == 0:
                print(f"  e{epoch} step {step}/{len(train_ld)} loss {loss.item():.3f}")

        # validation
        model.eval()
        correct = tot = 0
        with torch.no_grad():
            for x, y in val_ld:
                x, y = x.to(device), y.to(device)
                pred = model(x).argmax(1)
                correct += (pred == y).sum().item()
                tot += y.numel()
        acc = correct / max(tot, 1)
        scheduler.step()
        lr_now = scheduler.get_last_lr()[0]
        print(f"Epoch {epoch}/{args.epochs}  loss {running/len(train_ld):.3f}  "
              f"val_acc {acc*100:.2f}%  lr {lr_now:.2e}  ({time.time()-t0:.0f}s)")

        if acc > best_acc:
            best_acc = acc
            epochs_since_improve = 0
            torch.save({
                "state_dict": model.state_dict(),
                "classes": classes,
                "arch": "resnet50",
                "img_size": args.img,
                "mean": MEAN, "std": STD,
                "val_acc": acc,
            }, out_path)
            print(f"  [saved] checkpoint (val_acc {acc*100:.2f}%) -> {out_path}")
        else:
            epochs_since_improve += 1
            if args.patience and epochs_since_improve >= args.patience:
                print(f"  [early stop] no improvement in {args.patience} epoch(s).")
                break

    if best_acc == floor and floor > 0.0:
        print(f"Done. No epoch beat the existing {floor*100:.2f}% checkpoint — left untouched.")
    else:
        print(f"Done. Best val_acc {best_acc*100:.2f}%. Checkpoint: {out_path}")


if __name__ == "__main__":
    main()
