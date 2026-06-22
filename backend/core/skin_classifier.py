"""HAM10000 7-class dermoscopy classifier (trained, calibrated probabilities).

Unlike cnn_features.py (label-free ImageNet backbones) this is a *trained* head:
a ResNet50 fine-tuned on HAM10000 that predicts the seven dermatoscopic classes
and a derived malignancy probability. The softmax output is fed into the LLM
prompt as decision support.

Weights live at  data/weights/skin_ham10000_resnet50.pt  and are produced by
    scripts/train_skin_classifier.py
If the checkpoint is absent the classifier reports unavailable (mirroring the KNN
classifier) rather than inventing a prediction.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from loguru import logger

from config import settings
from core.cnn_features import _torch_device

CHECKPOINT = settings.weights_dir / "skin_ham10000_resnet50.pt"

# HAM10000 dx codes → human-readable name + malignancy.
CLASS_INFO: dict[str, tuple[str, bool]] = {
    "akiec": ("Actinic keratosis / Bowen's (in-situ SCC)", True),
    "bcc":   ("Basal cell carcinoma", True),
    "mel":   ("Melanoma", True),
    "bkl":   ("Benign keratosis", False),
    "df":    ("Dermatofibroma", False),
    "nv":    ("Melanocytic nevus", False),
    "vasc":  ("Vascular lesion", False),
}

# Loaded (model, classes) cache.
_MODEL_CACHE: dict[str, tuple] = {}


@dataclass
class SkinClassResult:
    top_label: str            # dx code, e.g. "mel"
    top_name: str             # human name
    top_prob: float           # softmax prob of the top class
    malignancy_prob: float    # summed prob over malignant classes
    probs: dict[str, float]   # full class → prob map
    val_acc: Optional[float]  # checkpoint validation accuracy (provenance)
    melanoma_prob: float = 0.0          # prob of the melanoma ("mel") class specifically
    temperature: float = 1.0            # calibration temperature applied to the logits
    malignancy_threshold: float = 0.5   # operating point for the malignant-vs-benign call
    melanoma_threshold: float = 0.20    # melanoma-sensitive urgent threshold
    urgent: bool = False                # screening flag: prompt review / excision advised
    urgent_reason: str = ""             # why the urgent flag fired

    def summary(self) -> str:
        ranked = sorted(self.probs.items(), key=lambda kv: kv[1], reverse=True)
        lines = "\n".join(
            f"    - {CLASS_INFO.get(c, (c, False))[0]} ({c}): {p * 100:.1f}%"
            for c, p in ranked[:4]
        )
        prov = f" (val acc {self.val_acc * 100:.1f}%)" if self.val_acc else ""
        calib = "" if abs(self.temperature - 1.0) < 1e-6 else f", temperature-calibrated T={self.temperature:.2f}"
        flag = ""
        if self.urgent:
            flag = (f"  • ⚠ SCREENING FLAG: URGENT — {self.urgent_reason}. "
                    "Recommend prompt dermatological review / excisional biopsy.\n")
        return (
            f"HAM10000 trained classifier (ResNet50, 7-class{calib}){prov}:\n"
            f"  • Most likely: {self.top_name} ({self.top_label}) — {self.top_prob * 100:.1f}%\n"
            f"  • Estimated malignancy probability: {self.malignancy_prob * 100:.1f}% "
            f"(sum of melanoma + BCC + AKIEC; operating threshold {self.malignancy_threshold * 100:.0f}%)\n"
            f"{flag}"
            f"  • Class probabilities:\n{lines}\n"
            "NOTE: probabilities are calibrated decision support, trained on HAM10000 "
            "dermoscopy images; reliability is bounded by that dataset's distribution. "
            "Not a substitute for histopathology."
        )


def is_available() -> bool:
    return CHECKPOINT.exists()


def status() -> dict:
    return {
        "available": is_available(),
        "checkpoint": str(CHECKPOINT),
        "classes": list(CLASS_INFO.keys()),
    }


def _load(device: str):
    key = device
    if key in _MODEL_CACHE:
        return _MODEL_CACHE[key]
    import torch
    import torchvision.models as tvm
    from torchvision import transforms

    # weights_only=False: our checkpoint stores metadata (classes, mean/std) too.
    ckpt = torch.load(CHECKPOINT, map_location=device, weights_only=False)
    classes: list[str] = list(ckpt["classes"])
    model = tvm.resnet50(weights=None)
    model.fc = torch.nn.Linear(model.fc.in_features, len(classes))
    model.load_state_dict(ckpt["state_dict"])
    model.eval().to(device)
    val_acc = ckpt.get("val_acc")
    # Build the SAME transform the trainer validated with (PIL resize + ImageNet
    # norm) so deployed inference matches training — a cv2.resize here aliases the
    # large HAM images and costs ~5% accuracy.
    img_size = int(ckpt.get("img_size", 224))
    mean = ckpt.get("mean", [0.485, 0.456, 0.406])
    std = ckpt.get("std", [0.229, 0.224, 0.225])
    tf = transforms.Compose([
        transforms.Resize((img_size, img_size)),
        transforms.ToTensor(),
        transforms.Normalize(mean, std),
    ])
    # Calibration metadata, written by scripts/skin/calibrate_skin.py. Absent in
    # older checkpoints → safe no-op defaults (T=1.0, plain 0.5 malignant cutoff).
    calib = {
        "temperature": float(ckpt.get("temperature", 1.0) or 1.0),
        "malignancy_threshold": float(ckpt.get("malignancy_threshold", 0.5) or 0.5),
        "melanoma_threshold": float(ckpt.get("melanoma_threshold", 0.20) or 0.20),
    }
    if calib["temperature"] <= 0:
        calib["temperature"] = 1.0
    _MODEL_CACHE[key] = (model, classes, val_acc, tf, calib)
    logger.info(
        f"Loaded skin HAM10000 classifier on {device} ({len(classes)} classes, "
        f"T={calib['temperature']:.2f}, mal_thr={calib['malignancy_threshold']:.2f})"
    )
    return _MODEL_CACHE[key]


def classify(image_path: Path, device: str = "cpu", tta: bool = False) -> Optional[SkinClassResult]:
    """Return calibrated class probabilities for a dermoscopy image, or None.

    None when the checkpoint is missing, torch is unavailable, or the image is
    unreadable — the caller then reports the classifier as unavailable.

    With ``tta=True`` the softmax is averaged over four flip views (identity,
    horizontal, vertical, both). Lesion class is flip-invariant, so this is a
    cheap, label-safe accuracy bump (4 forward passes, still <1 s on GPU).
    """
    if not is_available():
        return None
    try:
        import torch
        from PIL import Image
    except ImportError:
        logger.warning("torch/PIL unavailable — skin classifier skipped")
        return None
    try:
        pil_img = Image.open(image_path).convert("RGB")
    except Exception:
        logger.warning(f"Skin classifier: could not read image {image_path}")
        return None
    try:
        dev = _torch_device(device)
        model, classes, val_acc, tf, calib = _load(dev)
        temp = calib["temperature"]
        tensor = tf(pil_img).unsqueeze(0).to(dev)
        with torch.no_grad():
            if tta:
                views = [tensor, torch.flip(tensor, [3]),
                         torch.flip(tensor, [2]), torch.flip(tensor, [2, 3])]
                # Temperature-scale each view's logits before softmax, then average.
                stacked = torch.stack([torch.softmax(model(v) / temp, dim=1)[0] for v in views])
                probs_t = stacked.mean(0).cpu().numpy().astype(float)
            else:
                logits = model(tensor) / temp
                probs_t = torch.softmax(logits, dim=1)[0].cpu().numpy().astype(float)
        probs = {c: float(p) for c, p in zip(classes, probs_t)}
        top_label = max(probs, key=probs.get)
        malignancy = float(sum(p for c, p in probs.items() if CLASS_INFO.get(c, ("", False))[1]))
        mel_prob = float(probs.get("mel", 0.0))
        mal_thr = calib["malignancy_threshold"]
        mel_thr = calib["melanoma_threshold"]
        # Melanoma-sensitive safety net: flag urgent when the malignant mass clears the
        # tuned operating point, OR when melanoma alone clears its (lower) threshold even
        # if a benign class is top-1 — missing a melanoma is the costly error.
        urgent, reason = False, ""
        if mel_prob >= mel_thr and top_label != "mel":
            urgent = True
            reason = (f"melanoma probability {mel_prob * 100:.1f}% ≥ {mel_thr * 100:.0f}% safety "
                      f"threshold (flagged though {CLASS_INFO.get(top_label, (top_label, False))[0]} "
                      "is most likely)")
        elif malignancy >= mal_thr:
            urgent = True
            reason = (f"malignancy probability {malignancy * 100:.1f}% ≥ "
                      f"{mal_thr * 100:.0f}% operating threshold")
        return SkinClassResult(
            top_label=top_label,
            top_name=CLASS_INFO.get(top_label, (top_label, False))[0],
            top_prob=probs[top_label],
            malignancy_prob=malignancy,
            probs=probs,
            val_acc=val_acc,
            melanoma_prob=mel_prob,
            temperature=temp,
            malignancy_threshold=mal_thr,
            melanoma_threshold=mel_thr,
            urgent=urgent,
            urgent_reason=reason,
        )
    except Exception as exc:
        logger.warning(f"Skin classifier failed: {exc}")
        return None
