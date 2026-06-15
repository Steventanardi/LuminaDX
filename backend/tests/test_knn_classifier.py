"""Tests for the KNN classifier logic — CNN embedding is stubbed so no torch/GPU
or model download is needed; this exercises scanning, index build/cache, and the
cosine majority vote."""
import numpy as np
import pytest

from core import knn_classifier as knn


@pytest.fixture
def ref_env(tmp_path, monkeypatch):
    """Point the classifier at temp reference/index dirs with a labelled set,
    and stub the CNN embedder to a deterministic per-label vector."""
    ref = tmp_path / "reference"
    idx = tmp_path / "index"
    (ref / "skin" / "malignant").mkdir(parents=True)
    (ref / "skin" / "benign").mkdir(parents=True)
    idx.mkdir()
    monkeypatch.setattr(knn.settings, "reference_dir", ref)
    monkeypatch.setattr(knn.settings, "knn_index_dir", idx)

    # create dummy image files (content irrelevant — embed is stubbed)
    for i in range(4):
        (ref / "skin" / "malignant" / f"m{i}.png").write_bytes(b"x")
        (ref / "skin" / "benign" / f"b{i}.png").write_bytes(b"x")

    def fake_embed(tag, path, device="cpu"):
        p = str(path).lower()
        if "malignant" in p:
            return np.array([1.0, 0.0], dtype=np.float32)
        if "benign" in p:
            return np.array([0.0, 1.0], dtype=np.float32)
        return None

    monkeypatch.setattr(knn.cnn_features, "embed", fake_embed)
    knn._INDEX_CACHE.clear()
    return ref, idx


def test_status_empty(tmp_path, monkeypatch):
    monkeypatch.setattr(knn.settings, "reference_dir", tmp_path / "none")
    st = knn.status("skin")
    assert st["n_reference"] == 0
    assert st["ready"] is False


def test_status_ready(ref_env):
    st = knn.status("skin")
    assert st["n_reference"] == 8
    assert st["classes"] == {"benign": 4, "malignant": 4}
    assert st["ready"] is True


def test_build_index_counts_all(ref_env):
    n = knn.build_index("skin", "cnn_resnet50", device="cpu")
    assert n == 8


def test_classify_predicts_majority_label(ref_env, tmp_path):
    knn.build_index("skin", "cnn_resnet50", device="cpu")
    query = tmp_path / "malignant_query.png"
    query.write_bytes(b"x")
    res = knn.classify("skin", query, backbone="cnn_resnet50", device="cpu", k=5)
    assert res is not None
    assert res.predicted_label == "malignant"
    assert res.confidence > 0.5
    assert res.n_reference == 8
    assert "MALIGNANT" in res.summary()


def test_classify_returns_none_without_reference(tmp_path, monkeypatch):
    monkeypatch.setattr(knn.settings, "reference_dir", tmp_path / "none")
    monkeypatch.setattr(knn.settings, "knn_index_dir", tmp_path / "idx")
    knn._INDEX_CACHE.clear()
    res = knn.classify("skin", tmp_path / "q.png", device="cpu")
    assert res is None


def test_index_cache_is_used(ref_env, monkeypatch):
    knn.build_index("skin", "cnn_resnet50", device="cpu")
    query = ref_env[0] / "skin" / "benign" / "b0.png"
    knn.classify("skin", query, backbone="cnn_resnet50", device="cpu")
    # corrupt the on-disk index; cache should still serve a result
    (ref_env[1] / "skin__cnn_resnet50.npz").write_bytes(b"corrupt")
    res = knn.classify("skin", query, backbone="cnn_resnet50", device="cpu")
    assert res is not None
