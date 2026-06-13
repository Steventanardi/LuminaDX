"""KNN classifier over CNN embeddings.

A supervised k-nearest-neighbour classifier that votes on a query image by
comparing its CNN embedding (VGG16/19 or ResNet50) against a library of
labelled reference images.

Reference data layout (you supply this — KNN cannot predict without labels):
    data/reference/<cancer>/<label>/*.{jpg,jpeg,png}
e.g.
    data/reference/skin/melanoma/ISIC_xxx.jpg
    data/reference/skin/benign/ISIC_yyy.jpg

Built indices are cached as .npz under data/knn_index/<cancer>__<backbone>.npz
and rebuilt when the reference folder changes. If no reference set exists the
classifier returns None (the pipeline then reports that KNN is unavailable)
rather than inventing a prediction.

Cosine-similarity KNN is implemented directly on numpy — no scikit-learn
dependency is added.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import numpy as np
from loguru import logger

from config import settings
from core import cnn_features

_IMG_EXTS = (".jpg", ".jpeg", ".png")
_DEFAULT_BACKBONE = "cnn_resnet50"
_DEFAULT_K = 5

# In-memory index cache: (cancer, backbone) → (embeddings, labels, fingerprint).
# Avoids re-reading the .npz from disk on every classify() call.
_INDEX_CACHE: dict[tuple[str, str], tuple] = {}


@dataclass
class KnnResult:
    backbone: str
    predicted_label: str
    confidence: float          # fraction of the k neighbours that voted the winner
    k: int                     # neighbours actually used
    n_reference: int           # size of the reference library
    n_classes: int
    neighbor_labels: list[str]
    neighbor_sims: list[float]

    def summary(self) -> str:
        votes = ", ".join(
            f"{lbl} ({sim:.2f})" for lbl, sim in zip(self.neighbor_labels, self.neighbor_sims)
        )
        bb = self.backbone.replace("cnn_", "").upper()
        return (
            f"KNN classification ({bb} embeddings, k={self.k} over "
            f"{self.n_reference} labelled reference images, {self.n_classes} classes):\n"
            f"  • Predicted class: {self.predicted_label.upper()} "
            f"(confidence {self.confidence * 100:.0f}% — neighbour vote)\n"
            f"  • Nearest neighbours: {votes}\n"
            "NOTE: prediction reflects similarity to the supplied reference library; "
            "it is only as reliable as that labelled dataset. Not a substitute for "
            "histopathology."
        )


def reference_dir(cancer: str) -> Path:
    return settings.reference_dir / cancer


def _index_path(cancer: str, backbone: str) -> Path:
    return settings.knn_index_dir / f"{cancer}__{backbone}.npz"


def _scan_reference(cancer: str) -> list[tuple[Path, str]]:
    """Return (image_path, label) for every labelled reference image."""
    root = reference_dir(cancer)
    if not root.exists():
        return []
    pairs: list[tuple[Path, str]] = []
    for label_dir in sorted(p for p in root.iterdir() if p.is_dir()):
        for img in sorted(label_dir.iterdir()):
            if img.suffix.lower() in _IMG_EXTS:
                pairs.append((img, label_dir.name))
    return pairs


def _reference_fingerprint(cancer: str) -> str:
    """Cheap signature of the reference set (count + newest mtime) for cache validity."""
    pairs = _scan_reference(cancer)
    if not pairs:
        return "empty"
    newest = max(p.stat().st_mtime for p, _ in pairs)
    return f"{len(pairs)}:{newest:.0f}"


def build_index(cancer: str, backbone: str = _DEFAULT_BACKBONE, device: str = "cpu") -> int:
    """Embed every labelled reference image and cache the index. Returns image count."""
    pairs = _scan_reference(cancer)
    if not pairs:
        logger.warning(f"KNN: no reference images under {reference_dir(cancer)}")
        return 0

    embeds: list[np.ndarray] = []
    labels: list[str] = []
    for img_path, label in pairs:
        vec = cnn_features.embed(backbone, img_path, device=device)
        if vec is None:
            continue
        embeds.append(vec)
        labels.append(label)

    if not embeds:
        logger.warning(f"KNN: failed to embed any reference image for {cancer}/{backbone}")
        return 0

    matrix = np.vstack(embeds).astype(np.float32)
    settings.knn_index_dir.mkdir(parents=True, exist_ok=True)
    np.savez(
        _index_path(cancer, backbone),
        embeddings=matrix,
        labels=np.array(labels),
        fingerprint=np.array(_reference_fingerprint(cancer)),
    )
    logger.info(f"KNN index built: {cancer}/{backbone} — {len(labels)} images, "
                f"{len(set(labels))} classes")
    return len(labels)


def _load_index(cancer: str, backbone: str, device: str):
    """Load a cached index, rebuilding it if stale or missing. Returns (matrix, labels) or None."""
    current = _reference_fingerprint(cancer)
    if current == "empty":
        return None

    cache_key = (cancer, backbone)
    cached = _INDEX_CACHE.get(cache_key)
    if cached is not None and cached[2] == current:
        return cached[0], cached[1]

    path = _index_path(cancer, backbone)
    if not (path.exists() and str(np.load(path, allow_pickle=True)["fingerprint"]) == current):
        # stale or missing → rebuild
        if build_index(cancer, backbone, device) == 0:
            return None
    data = np.load(path, allow_pickle=True)
    matrix, labels = data["embeddings"], data["labels"]
    _INDEX_CACHE[cache_key] = (matrix, labels, current)
    return matrix, labels


def classify(
    cancer: str,
    query_image: Path,
    backbone: str = _DEFAULT_BACKBONE,
    device: str = "cpu",
    k: int = _DEFAULT_K,
) -> Optional[KnnResult]:
    """Classify a query image by majority vote of its k nearest reference neighbours.

    Returns None if no usable reference library exists or embedding fails.
    """
    loaded = _load_index(cancer, backbone, device)
    if loaded is None:
        return None
    matrix, labels = loaded

    query = cnn_features.embed(backbone, query_image, device=device)
    if query is None:
        return None

    # cosine similarity = normalised dot product
    ref_norm = matrix / (np.linalg.norm(matrix, axis=1, keepdims=True) + 1e-8)
    q_norm = query / (np.linalg.norm(query) + 1e-8)
    sims = ref_norm @ q_norm

    k_eff = int(min(k, len(labels)))
    top_idx = np.argsort(sims)[::-1][:k_eff]
    top_labels = [str(labels[i]) for i in top_idx]
    top_sims = [float(sims[i]) for i in top_idx]

    # majority vote, ties broken by summed similarity
    classes = sorted(set(str(l) for l in labels))
    scores: dict[str, float] = {c: 0.0 for c in classes}
    counts: dict[str, int] = {c: 0 for c in classes}
    for lbl, sim in zip(top_labels, top_sims):
        counts[lbl] += 1
        scores[lbl] += sim
    winner = max(classes, key=lambda c: (counts[c], scores[c]))

    return KnnResult(
        backbone=backbone,
        predicted_label=winner,
        confidence=counts[winner] / k_eff,
        k=k_eff,
        n_reference=len(labels),
        n_classes=len(classes),
        neighbor_labels=top_labels,
        neighbor_sims=top_sims,
    )


def status(cancer: str) -> dict:
    """Reference-library status for a cancer (for the UI / build endpoint)."""
    pairs = _scan_reference(cancer)
    by_label: dict[str, int] = {}
    for _, label in pairs:
        by_label[label] = by_label.get(label, 0) + 1
    return {
        "cancer": cancer,
        "n_reference": len(pairs),
        "classes": by_label,
        "ready": len(pairs) > 0 and len(by_label) >= 2,
        "reference_dir": str(reference_dir(cancer)),
    }
