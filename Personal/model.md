# LuminaDx — Per-Cancer Local Model Reference

> All models run fully locally. LLMs served via Ollama (`http://localhost:11434`).
> Classifiers/segmentors downloaded via HuggingFace CLI or pip.

---

## Prerequisites

```bash
# Ollama (serves LLMs)
# Download installer from https://ollama.com  — then:
ollama serve   # keep running in background

# HuggingFace CLI (downloads HF models)
pip install huggingface_hub

# MONAI (medical imaging toolkit)
pip install monai
```

### Hardware requirements

| Tier | GPU VRAM | What runs |
|------|---------|-----------|
| **My laptop (RTX 4070, 8 GB)** | **8 GB** | **4B–8B vision LLMs at q4/q8 + small classifiers** |
| Recommended | 12 GB | 11B vision LLMs + classifiers concurrently |
| DGX Spark / full | 16 GB+ | `medgemma:27b` quantised, 11B+ LLMs |

> 🎯 **My primary machine is the RTX 4070 Laptop (8 GB VRAM).** Every cancer below
> leads with an **8 GB-safe LLM** I can run anytime. The bigger models
> (`medgemma:27b`, `llama3.2-vision:11b`) are a **"DGX Spark" tier** — only used when
> I actually have the Spark connected, which isn't always. The app must work fully
> on 8 GB alone.

> ⚠️ **8 GB VRAM budgeting:** you **cannot** hold the vision LLM + TotalSegmentator
> + a HuggingFace classifier in VRAM at the same time. TotalSegmentator/nnU-Net
> needs ~4–6 GB during inference. So on the laptop:
> - Run **segmentation first** (it releases VRAM when done), **then** load the LLM, **or**
> - Put segmentation on CPU (`DEVICE=cpu` in `.env`) and keep the 8 GB free for the LLM.
> - HF classifiers (ViT/ResNet/YOLOS) are tiny (~0.3–0.5 GB) and fit alongside a 4B LLM.

> **No GPU at all?** Everything still runs on CPU — set `device=-1` for HuggingFace
> classifiers; Ollama auto-falls back to CPU. Expect 4–10× slower inference.

---

## ⚠️ Model availability note (read before pulling)

Not every model below is in the **official** Ollama library. Two cases:

1. **Official library** (`ollama pull <tag>` just works):
   `llama3.2-vision`, `llava`, `minicpm-v`, `qwen2.5vl`, `nomic-embed-text`.

2. **MedGemma — NOT in the official library.** It is a Google research model.
   You already have `medgemma:4b-it-q8_0` working, so it was imported once. To
   reproduce on another machine, either pull a community mirror **or** import the
   GGUF from HuggingFace with a Modelfile:

   ```bash
   # Option A — community mirror (check the tag exists first)
   ollama pull amsaravi/medgemma-4b-it:q8

   # Option B — import official GGUF yourself
   #  1. download GGUF from huggingface.co/unsloth/medgemma-4b-it-GGUF
   huggingface-cli download unsloth/medgemma-4b-it-GGUF \
       medgemma-4b-it-Q8_0.gguf --local-dir ./gguf
   #  2. create a Modelfile
   #     FROM ./gguf/medgemma-4b-it-Q8_0.gguf
   #  3. register it under the name the app expects
   ollama create medgemma:4b-it-q8_0 -f Modelfile
   ```

   The same GGUF-import flow works for MedGemma 27B
   (`unsloth/medgemma-27b-it-GGUF`).

---

## Global Vision LLMs (Ollama — any cancer)

Switch active model in `.env`:
```env
LLM_MODEL=qwen2.5vl:7b
```

Legend — **Fits 8 GB?** ✅ runs on the RTX 4070 Laptop · ✅* fits but with less
headroom (Windows display takes ~0.5–1 GB; keep the montage moderate-resolution) ·
❌ DGX Spark only.

| Model | Tag | VRAM | Fits 8 GB? | In official library? | Best for |
|-------|-----|------|:---------:|----------------------|---------|
| Med-Gemma 4B *(default)* | `medgemma:4b-it-q8_0` | ~6 GB | ✅ | No — import GGUF (see above) | General medical, fast |
| Med-Gemma 4B (lighter) | `medgemma:4b-it-q4_K_M` | ~3.5 GB | ✅ | No — import GGUF | Most headroom on 8 GB |
| Qwen2.5-VL 3B | `qwen2.5vl:3b` | ~3.5 GB | ✅ | ✅ Yes | Structured JSON, safe on 8 GB |
| MiniCPM-V 8B | `minicpm-v:8b` | ~5.5 GB (q4) | ✅ | ✅ Yes | Dermoscopy, mammography |
| LLaVA 7B | `llava:7b` | ~4.7 GB | ✅ | ✅ Yes | Widely tested in medical research |
| Qwen2.5-VL 7B | `qwen2.5vl:7b` | ~6.5–7 GB (q4) | ✅* | ✅ Yes | Charts/tables; *less headroom on Windows |
| LLaMA 3.2 Vision 11B | `llama3.2-vision:11b` | ~9 GB | ❌ | ✅ Yes | Strong general vision (Spark) |
| LLaVA 13B | `llava:13b` | ~10 GB | ❌ | ✅ Yes | (Spark) |
| Med-Gemma 27B | `medgemma:27b-it-q4_K_M` | ~16 GB | ❌ | No — import GGUF | Best reasoning (Spark) |

```bash
# ── 8 GB Laptop set (pull these for daily use) ──────────────
ollama pull qwen2.5vl:3b
ollama pull minicpm-v:8b
ollama pull llava:7b
ollama pull medgemma:4b-it-q8_0     # via GGUF import — see note above

# ── DGX Spark tier (only when Spark is connected) ───────────
ollama pull qwen2.5vl:7b
ollama pull llama3.2-vision:11b
ollama pull medgemma:27b-it-q4_K_M  # via GGUF import
```

> **VRAM figures include weights only.** Vision models also spend VRAM on image
> tokens (the KV cache). The montage the pipeline sends is a single PNG, so a 4B
> model at q8 (~6 GB) leaves ~2 GB for image tokens — comfortable. A 7B at q4
> (~6 GB) is the realistic ceiling on 8 GB; go q4 and avoid very large montages.

---

## Per-Cancer Recommended Stack

### Liver

**🎯 8 GB Laptop LLM:** `medgemma:4b-it-q8_0` *(current default — keep it)*
**🚀 DGX Spark LLM:** `medgemma:27b-it-q4_K_M`
Rationale: MedGemma is trained on radiology reports including hepatology. The 4B at
q8 (~6 GB) runs LI-RADS reasoning fine on the laptop; the 27B is a quality upgrade
only when the Spark is available. On 8 GB, run TotalSegmentator **first**, then load
the LLM (or set `DEVICE=cpu` for segmentation).

| Role | Model | Source |
|------|-------|--------|
| Organ + lesion segmentation | TotalSegmentator *(already integrated)* | `pip install TotalSegmentator` |
| Whole-body CT segmentation | `monai/wholeBody_ct_segmentation` | MONAI model zoo |
| Report generation (8 GB) | `medgemma:4b-it-q8_0` | Ollama |
| Report generation (Spark) | `medgemma:27b-it-q4_K_M` | Ollama |

```bash
# 8 GB laptop
ollama pull medgemma:4b-it-q8_0     # via GGUF import (see note above)
python -c "from monai.bundle import download; download('wholeBody_ct_segmentation')"

# DGX Spark upgrade
ollama pull medgemma:27b-it-q4_K_M
```

---

### Lung

**🎯 8 GB Laptop LLM:** `qwen2.5vl:7b` *(q4 — fits ~6.5–7 GB; use `qwen2.5vl:3b` if VRAM-pressed)*
**🚀 DGX Spark LLM:** `qwen2.5vl:32b`
Rationale: Qwen2.5-VL reads structured tabular data well — good for multi-nodule
Lung-RADS tables. The 7B (q4) fits 8 GB as long as you run **LungMask/nodule
segmentation first** (so it isn't competing for VRAM); drop to the 3B if you hit OOM.

| Role | Model | Source |
|------|-------|--------|
| Lobe segmentation | **LungMask** | `pip install lungmask` |
| Nodule detection | `monai/lung_nodule_ct_detection` | MONAI model zoo |
| Opacity classifier | `marcellusruben/medimeta-lung_opacity-vit_base` | HuggingFace |
| Report generation (8 GB) | `qwen2.5vl:7b` *(or `:3b` fallback)* | Ollama |
| Report generation (Spark) | `qwen2.5vl:32b` | Ollama |

```bash
pip install lungmask
# 8 GB laptop
ollama pull qwen2.5vl:7b      # or qwen2.5vl:3b if VRAM-pressed
# DGX Spark upgrade
ollama pull qwen2.5vl:32b
python -c "from monai.bundle import download; download('lung_nodule_ct_detection')"
huggingface-cli download marcellusruben/medimeta-lung_opacity-vit_base \
    --local-dir backend/models/lung_opacity
```

---

### Skin

**🎯 8 GB Laptop LLM:** `minicpm-v:8b` *(fits 8 GB — no Spark needed)*
**🚀 DGX Spark (optional):** `llama3.2-vision:11b` for tougher cases
Rationale: MiniCPM-V is compact and fast on 2D images; dermoscopy images are small
so the 8B model (q4 ~5.5 GB) runs entirely on the laptop. Skin is an **image-only**
pipeline (no segmentation), so all 8 GB is free for the LLM + the tiny ViT classifier.

| Role | Model | Source |
|------|-------|--------|
| Lesion classifier (HAM10000/ISIC) | `Anwarkh1/Skin_Cancer-Image_Classification` | HuggingFace |
| Fine-grained derm (7 classes) | `nickmuchi/vit-base-patch16-224-skin-disease-classification` | HuggingFace |
| Report generation (8 GB) | `minicpm-v:8b` | Ollama |

```bash
ollama pull minicpm-v:8b
huggingface-cli download Anwarkh1/Skin_Cancer-Image_Classification \
    --local-dir backend/models/skin_isic
huggingface-cli download nickmuchi/vit-base-patch16-224-skin-disease-classification \
    --local-dir backend/models/skin_vit
```

**Classifier labels (ISIC):** Melanoma · Melanocytic nevus · BCC · AK · Benign keratosis · Dermatofibroma · Vascular lesion

---

### Breast

**🎯 8 GB Laptop LLM:** `minicpm-v:8b` *(fits 8 GB)*
**🚀 DGX Spark LLM:** `llama3.2-vision:11b` for stronger BI-RADS reasoning
Rationale: Mammography images are 2D; MiniCPM-V (q4 ~5.5 GB) handles high-res 2D
images on the laptop. Image-only pipeline, so no segmentation competing for VRAM.
The 11B model is a quality upgrade reserved for the Spark.

| Role | Model | Source |
|------|-------|--------|
| Malignancy classifier | `Falah/Breast_Cancer_Detection` | HuggingFace |
| BI-RADS density / ResNet | `farleyknight/resnet-breast-cancer` | HuggingFace |
| Report generation (8 GB) | `minicpm-v:8b` | Ollama |
| Report generation (Spark) | `llama3.2-vision:11b` | Ollama |

```bash
ollama pull minicpm-v:8b
huggingface-cli download Falah/Breast_Cancer_Detection \
    --local-dir backend/models/breast_detection
huggingface-cli download farleyknight/resnet-breast-cancer \
    --local-dir backend/models/breast_resnet
```

---

### Colorectal

**🎯 8 GB Laptop LLM:** `qwen2.5vl:7b` *(q4 — fits; `:3b` or `medgemma:4b` as fallback)*
**🚀 DGX Spark LLM:** `llama3.2-vision:11b`
Rationale: Colorectal CT colonography has complex 3D geometry; the 11B Meta model
gives stronger spatial reasoning for T-staging — but it **does not fit 8 GB** (~9 GB),
so on the laptop use `qwen2.5vl:7b` (run polyp detection/segmentation first to free
VRAM). Reserve the 11B for the Spark.

| Role | Model | Source |
|------|-------|--------|
| Polyp detection (YOLOS) | `nickmuchi/yolos-small-colon-polyp-segmentation` | HuggingFace |
| Polyp segmentation (PraNet-style) | `kvsnoufal/pranet-colon-polyp-segmentation` | HuggingFace |
| Report generation (8 GB) | `qwen2.5vl:7b` *(or `:3b` / `medgemma:4b`)* | Ollama |
| Report generation (Spark) | `llama3.2-vision:11b` | Ollama |

```bash
# 8 GB laptop
ollama pull qwen2.5vl:7b      # or qwen2.5vl:3b if VRAM-pressed
# DGX Spark upgrade
ollama pull llama3.2-vision:11b
huggingface-cli download nickmuchi/yolos-small-colon-polyp-segmentation \
    --local-dir backend/models/colon_polyp_det
huggingface-cli download kvsnoufal/pranet-colon-polyp-segmentation \
    --local-dir backend/models/colon_polyp_seg
```

---

## Summary Table

| Cancer | 🎯 8 GB Laptop LLM | 🚀 DGX Spark LLM | Local Classifier | Segmentor |
|--------|-------------------|------------------|-----------------|-----------|
| Liver | `medgemma:4b-it-q8_0` *(default)* | `medgemma:27b-it-q4_K_M` | — | TotalSegmentator (built-in) |
| Lung | `qwen2.5vl:7b` *(`:3b` fallback)* | `qwen2.5vl:32b` | `medimeta-lung_opacity-vit_base` | LungMask + MONAI nodule |
| Skin | `minicpm-v:8b` | *(same / 11B optional)* | `Skin_Cancer-Image_Classification` | — (image-only pipeline) |
| Breast | `minicpm-v:8b` | `llama3.2-vision:11b` | `Breast_Cancer_Detection` | — (image-only pipeline) |
| Colorectal | `qwen2.5vl:7b` *(`:3b`/`medgemma:4b`)* | `llama3.2-vision:11b` | `yolos-small-colon-polyp-segmentation` | PraNet polyp seg |

> The **8 GB Laptop column is the one to set in `.env` for daily use.** Switch to the
> Spark column only when the DGX Spark is connected.

---

## Switching the Active LLM

Edit `.env` (or `backend/.env`):

```env
# Daily driver on the RTX 4070 Laptop (8 GB) — medical-tuned, fits comfortably
LLM_MODEL=medgemma:4b-it-q8_0

# When the DGX Spark is connected, swap up:
# LLM_MODEL=medgemma:27b-it-q4_K_M
```

Restart the backend — no code changes needed. The `LLMClient` in `backend/core/llm_client.py` reads `settings.llm_model` at startup.

> Want per-cancer auto-switching (each cancer uses its own tag) instead of one global
> `LLM_MODEL`? That needs a small change in `config.py` + `llm_client.py` to read a
> model from the active module. Ask and I'll wire it in.

---

## Integrating HuggingFace Classifiers into the Pipeline

Each cancer module's `build_prompt()` can call a local classifier and inject its output as additional evidence:

```python
# Example: skin.py — lazy-load to avoid startup cost
from transformers import pipeline as hf_pipeline

_classifier = None

def _get_classifier():
    global _classifier
    if _classifier is None:
        _classifier = hf_pipeline(
            "image-classification",
            model="backend/models/skin_isic",
            device=0,   # GPU; use -1 for CPU
        )
    return _classifier

def build_prompt(self, seg, modality, rag_context, radiomics_summary, patient_info):
    extra = ""
    if image_path:
        result = _get_classifier()(str(image_path))[0]
        extra = f"\nLOCAL ISIC CLASSIFIER: {result['label']} ({result['score']:.0%} confidence)\n"
    # prepend extra to the user prompt so the LLM sees it as supporting evidence
    ...
```

---

## Embed Model (RAG)

The RAG engine uses `nomic-embed-text` for all cancer types — one shared embedding
model, but a **separate ChromaDB collection per cancer**
(`{cancer}_cancer_guidelines`, see `backend/core/rag_engine.py`). You still need to
supply each cancer's guideline PDFs — see **`Personal/RAG.md`** for where to get them.

```bash
ollama pull nomic-embed-text   # already set in config, auto-pulled on first ingest
```

Optional higher-accuracy medical embedding (swap `EMBED_MODEL` in `.env`):

| Model | Tag | Note |
|-------|-----|------|
| Nomic Embed *(default)* | `nomic-embed-text` | Fast, general, 768-dim |
| MxBai Embed Large | `mxbai-embed-large` | Higher retrieval accuracy, 1024-dim |
| BGE-M3 | `bge-m3` | Strong on long clinical passages |

---

*Last updated: 2026-06-10*
