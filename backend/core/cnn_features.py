"""CNN backbone feature extractors (VGG16, VGG19, ResNet50).

Label-free deep feature extraction using ImageNet-pretrained torchvision models.
For each image we produce:
  • a global feature embedding + summary statistics (fed into the LLM prompt), and
  • a class-agnostic activation heatmap overlay (mean of the last conv feature map)
    saved to disk so the doctor can see where the backbone focuses.

No fine-tuning and no classifier head — these are interpretable feature maps, not
predictions. Models are loaded lazily and cached for reuse.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

import cv2
import numpy as np
from loguru import logger

# torch is heavy; import lazily inside functions so the module imports cheaply.
_MODEL_CACHE: dict[str, object] = {}

# tag → (torchvision constructor name, weights enum name, last-conv module path)
_BACKBONES: dict[str, tuple[str, str, str]] = {
    "cnn_vgg16":    ("vgg16",    "VGG16_Weights",    "features"),
    "cnn_vgg19":    ("vgg19",    "VGG19_Weights",    "features"),
    "cnn_resnet50": ("resnet50", "ResNet50_Weights", "layer4"),
}

_LABELS: dict[str, str] = {
    "cnn_vgg16":    "VGG16 deep features",
    "cnn_vgg19":    "VGG19 deep features",
    "cnn_resnet50": "ResNet50 deep features",
}

# ImageNet normalisation
_MEAN = np.array([0.485, 0.456, 0.406], dtype=np.float32)
_STD = np.array([0.229, 0.224, 0.225], dtype=np.float32)


@dataclass
class CnnFeatures:
    backbone: str          # tag, e.g. "cnn_resnet50"
    label: str             # human label
    embed_dim: int         # length of the pooled feature vector
    l2_norm: float         # L2 norm of the embedding
    mean_activation: float
    sparsity_pct: float    # fraction of near-zero activations
    peak_xy: tuple[int, int]  # location of peak activation in original-image coords
    heatmap_path: Optional[str]

    def summary(self) -> str:
        loc = f"({self.peak_xy[0]}, {self.peak_xy[1]})"
        return (
            f"{self.label} (ImageNet-pretrained, label-free):\n"
            f"  • Embedding: {self.embed_dim}-d, L2 norm {self.l2_norm:.1f}\n"
            f"  • Mean activation {self.mean_activation:.3f}, "
            f"sparsity {self.sparsity_pct:.0f}%\n"
            f"  • Strongest textural salience near pixel {loc} "
            "(see activation heatmap overlay)\n"
            "NOTE: backbone features highlight texture/structure regions; they are "
            "not a trained diagnosis. Use to corroborate visual assessment."
        )


def available_backbones() -> dict[str, str]:
    """tag → label for every supported CNN backbone."""
    return dict(_LABELS)


def is_backbone(tag: str) -> bool:
    return tag in _BACKBONES


def _torch_device(device: str) -> str:
    """Map app device names (e.g. TotalSegmentator's 'gpu') to torch device strings."""
    import torch
    d = (device or "cpu").lower()
    if d in ("gpu", "cuda"):
        return "cuda" if torch.cuda.is_available() else "cpu"
    return d


def _load_model(tag: str, device: str):
    if tag in _MODEL_CACHE:
        return _MODEL_CACHE[tag]
    import torch  # noqa: F401
    import torchvision.models as tvm

    ctor_name, weights_name, _ = _BACKBONES[tag]
    weights = getattr(tvm, weights_name).DEFAULT
    model = getattr(tvm, ctor_name)(weights=weights)
    model.eval()
    model.to(device)
    _MODEL_CACHE[tag] = model
    logger.info(f"Loaded CNN backbone {tag} on {device}")
    return model


def _preprocess(img_bgr: np.ndarray, device: str):
    import torch
    rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
    rgb = cv2.resize(rgb, (224, 224)).astype(np.float32) / 255.0
    rgb = (rgb - _MEAN) / _STD
    tensor = torch.from_numpy(rgb.transpose(2, 0, 1)).unsqueeze(0).to(device)
    return tensor


def _last_conv_map(model, tag: str, tensor):
    """Return the last conv feature map (C, H, W) as a torch tensor."""
    import torch
    _, _, module_path = _BACKBONES[tag]
    feat: dict[str, object] = {}

    target = model
    for part in module_path.split("."):
        target = getattr(target, part)

    def hook(_m, _i, out):
        feat["map"] = out

    handle = target.register_forward_hook(hook)
    with torch.no_grad():
        model(tensor)
    handle.remove()
    return feat["map"][0]  # drop batch dim → (C, H, W)


def _make_heatmap(fmap, img_bgr: np.ndarray, out_path: Path) -> tuple[int, int]:
    """Mean-over-channels activation heatmap, overlaid on the original image.

    Returns the peak activation location in original-image pixel coords.
    """
    import torch
    h, w = img_bgr.shape[:2]
    heat = fmap.mean(dim=0)  # (H, W)
    heat = heat - heat.min()
    if float(heat.max()) > 0:
        heat = heat / heat.max()
    heat_np = heat.cpu().numpy().astype(np.float32)

    # peak location (in feature-map space) → original image coords
    fy, fx = np.unravel_index(int(np.argmax(heat_np)), heat_np.shape)
    fh, fw = heat_np.shape
    peak_xy = (int(fx / fw * w), int(fy / fh * h))

    heat_big = cv2.resize(heat_np, (w, h))
    heat_u8 = np.uint8(255 * heat_big)
    colored = cv2.applyColorMap(heat_u8, cv2.COLORMAP_JET)
    overlay = cv2.addWeighted(img_bgr, 0.6, colored, 0.4, 0)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(out_path), overlay)
    return peak_xy


def embed(tag: str, src_path: Path, device: str = "cpu") -> Optional[np.ndarray]:
    """Return the global-average-pooled CNN embedding (1-D float32) for an image.

    Shared by feature extraction and the KNN classifier. Returns None on any
    failure (unavailable torch, unreadable image, etc.).
    """
    if not is_backbone(tag):
        return None
    try:
        import torch  # noqa: F401
    except ImportError:
        logger.warning("torch unavailable — CNN embedding skipped")
        return None
    img = cv2.imread(str(src_path))
    if img is None:
        logger.warning(f"CNN embed: could not read image {src_path}")
        return None
    try:
        dev = _torch_device(device)
        model = _load_model(tag, dev)
        tensor = _preprocess(img, dev)
        fmap = _last_conv_map(model, tag, tensor)         # (C, H, W)
        vec = fmap.mean(dim=(1, 2)).cpu().numpy().astype(np.float32)
        return vec
    except Exception as exc:
        logger.warning(f"CNN embed failed for {tag}: {exc}")
        return None


def extract_cnn_features(
    tag: str, src_path: Path, out_path: Path, device: str = "cpu"
) -> Optional[CnnFeatures]:
    """Run a CNN backbone on an image; write heatmap overlay; return feature stats.

    Returns None if torch/torchvision is unavailable or the image can't be read.
    """
    if not is_backbone(tag):
        return None
    try:
        import torch  # noqa: F401
    except ImportError:
        logger.warning("torch unavailable — CNN feature extraction skipped")
        return None

    img = cv2.imread(str(src_path))
    if img is None:
        logger.warning(f"CNN features: could not read image {src_path}")
        return None

    try:
        device = _torch_device(device)
        model = _load_model(tag, device)
        tensor = _preprocess(img, device)
        fmap = _last_conv_map(model, tag, tensor)  # (C, H, W)

        pooled = fmap.mean(dim=(1, 2))  # global average pool → (C,)
        vec = pooled.cpu().numpy().astype(np.float32)
        l2 = float(np.linalg.norm(vec))
        mean_act = float(vec.mean())
        sparsity = float(np.mean(np.abs(vec) < 1e-3) * 100)

        peak_xy = _make_heatmap(fmap, img, out_path)
    except Exception as exc:
        logger.warning(f"CNN feature extraction failed for {tag}: {exc}")
        return None

    return CnnFeatures(
        backbone=tag,
        label=_LABELS[tag],
        embed_dim=int(vec.shape[0]),
        l2_norm=l2,
        mean_activation=mean_act,
        sparsity_pct=sparsity,
        peak_xy=peak_xy,
        heatmap_path=str(out_path),
    )
