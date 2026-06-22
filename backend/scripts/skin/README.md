# Skin eval scripts (backend)

Backend-side evaluation for the **skin / melanoma** module. Run from the
**`backend/` directory** with the backend virtualenv so `core`/`config` import.

| Script | Purpose |
|--------|---------|
| `eval_skin.py` | Compare **KNN vs the trained HAM10000 classifier vs the LLM** on a held-out test split. |

## eval_skin.py

Scores every method on the same clinically-meaningful task — **malignant vs
benign** (accuracy / sensitivity / specificity / precision / F1) — plus the
trained classifier's native 7-class top-1 accuracy.

```powershell
# from backend/
.venv\Scripts\python.exe scripts\skin\eval_skin.py --ham-split --no-knn --tta --sweep
```

### Test-set selection (pick one, required)
| Flag | Meaning |
|------|---------|
| `--ham-split` | Rebuilds the classifier's exact held-out HAM10000 val split (stratified, seed 42, 15%). Fairest for the trained model. |
| `--test-dir DIR` | A `DIR/<label>/*.jpg` set where `<label>` is a HAM10000 dx code (`mel`,`bcc`,`akiec`,`nv`,`bkl`,`df`,`vasc`) or plain `benign`/`malignant`. Use this for an independent set. |

### Options
| Flag | Default | Notes |
|------|---------|-------|
| `--limit N` | 0 (all) | Cap images per class — handy for a quick smoke run. |
| `--tta` | off | Score the classifier with test-time augmentation (4 flip views). |
| `--sweep` | off | Print acc/sens/spec across malignancy thresholds and suggest a screening operating point (highest specificity keeping sensitivity ≥ 0.90). |
| `--clf-thresh` | 0.5 | Malignancy-probability cutoff for the binary call. |
| `--llm` | off | Also score the LLM (slow; needs Ollama running). Decision derived from lesion risk + differential. |
| `--no-knn` | off | Skip KNN. |

> ⚠ **Data leakage warning:** the KNN reference library
> (`backend/data/reference/skin/`) may overlap HAM10000. If so, KNN numbers on
> `--ham-split` are optimistic — use an independent `--test-dir` for a fair KNN
> comparison. The trained classifier never saw the `--ham-split` val images.
