# Skin scripts

Project-level scripts for the **skin / melanoma** module. Run from the **repo root**
using the backend virtualenv (`backend/.venv`). On Windows use
`backend\.venv\Scripts\python.exe`.

| Script | Purpose |
|--------|---------|
| `train_skin_classifier.py` | Fine-tune a ResNet50 on HAM10000 → the 7-class dermoscopy classifier the app serves. |
| `calibrate_skin.py` | Temperature-scale the trained classifier + pick a malignancy operating threshold, written back into the checkpoint. |

## train_skin_classifier.py

Produces `backend/data/weights/skin_ham10000_resnet50.pt`, which
`backend/core/skin_classifier.py` auto-loads (the "HAM10000 classifier" feature).
Dataset is expected at `Datasets/Skin/HAM10000` (+ `HAM10000_metadata.csv`).

```powershell
# from repo root
backend\.venv\Scripts\python.exe scripts\skin\train_skin_classifier.py `
    --epochs 16 --batch 32 --lr 1e-4 --label-smoothing 0.05 --patience 5 --workers 4
```

### Flags
| Flag | Default | Notes |
|------|---------|-------|
| `--epochs` | 8 | 12–16 with `--patience` usually beats the 8-epoch baseline. |
| `--batch` | 32 | Drop to 16 if the 8 GB 4070 OOMs. |
| `--lr` | 1e-4 | Cosine-annealed to 0 over the run. |
| `--label-smoothing` | 0.0 | Try `0.05` — calibrates probabilities, small acc gain. |
| `--patience` | 0 (off) | Early-stop after N epochs without val improvement. |
| `--img` | 224 | Must match inference preprocessing — leave at 224. |
| `--workers` | 4 | Lower to 2 if the Windows dataloader is flaky. |
| `--out` | deployed weights file | Point at a `*.candidate.pt` to train without touching the live model. |
| `--no-floor` | off | By default the trainer **refuses to overwrite a checkpoint with a worse one**. Pass this to force-overwrite. |

> ⚠ **Do not move or edit this file while a training run is in progress** — the
> spawned dataloader workers re-import it by path and will crash if it moves.

### Recommended safe workflow (never regress the live model)
```powershell
# 1) train to a candidate file
backend\.venv\Scripts\python.exe scripts\skin\train_skin_classifier.py `
    --epochs 16 --patience 5 --label-smoothing 0.05 `
    --out backend\data\weights\skin_ham10000_resnet50.candidate.pt

# 2) score it (see backend/scripts/skin/eval_skin.py)
cd backend; .venv\Scripts\python.exe scripts\skin\eval_skin.py --ham-split --no-knn --tta --sweep

# 3) promote only if it beats the live model
copy backend\data\weights\skin_ham10000_resnet50.candidate.pt `
     backend\data\weights\skin_ham10000_resnet50.pt
```

## calibrate_skin.py

Run **after** training (or after promoting a new checkpoint). Fits one temperature
`T` on the HAM10000 val split (seed=42, same split as training) to fix ResNet
softmax over/under-confidence, then sweeps the malignant-vs-benign threshold and
stores the Youden-J optimum. Writes three keys into the checkpoint —
`temperature`, `malignancy_threshold`, `melanoma_threshold` — which
`core/skin_classifier.py` then applies (dividing logits by `T`, flagging "URGENT"
when malignancy clears the operating point or melanoma clears its safety
threshold). Older checkpoints without these keys fall back to `T=1.0` / `0.5`, so
running this is purely additive.

```powershell
# from repo root (writes back into the deployed checkpoint)
backend\.venv\Scripts\python.exe scripts\skin\calibrate_skin.py

# inspect without modifying, or change the melanoma safety threshold
backend\.venv\Scripts\python.exe scripts\skin\calibrate_skin.py --dry-run
backend\.venv\Scripts\python.exe scripts\skin\calibrate_skin.py --mel-threshold 0.15
```

| Flag | Default | Notes |
|------|---------|-------|
| `--ckpt` | deployed weights file | Calibrate a `*.candidate.pt` before promoting it. |
| `--mel-threshold` | 0.20 | Lower = more melanoma-sensitive urgent flagging (more false alarms). |
| `--dry-run` | off | Print `T` / threshold / ECE without writing the checkpoint. |

`health_check.ps1` (Step 7) reports whether the live checkpoint carries this
calibration, and warns if it is missing.
