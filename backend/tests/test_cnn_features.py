"""Tests for cnn_features metadata/helpers. The actual CNN forward pass needs
torch + a model download, so those are not exercised here — only the pure logic."""
from core import cnn_features as cf


def test_available_backbones_are_the_three_expected():
    bb = cf.available_backbones()
    assert set(bb) == {"cnn_vgg16", "cnn_vgg19", "cnn_resnet50"}
    assert all(isinstance(v, str) and v for v in bb.values())


def test_is_backbone():
    assert cf.is_backbone("cnn_resnet50")
    assert not cf.is_backbone("cnn_alexnet")
    assert not cf.is_backbone("radiomics")


def test_extract_returns_none_for_unknown_backbone(tmp_path):
    out = cf.extract_cnn_features("not_a_model", tmp_path / "x.png", tmp_path / "h.png")
    assert out is None


def test_embed_returns_none_for_unknown_backbone(tmp_path):
    assert cf.embed("not_a_model", tmp_path / "x.png") is None


def test_torch_device_maps_gpu(monkeypatch):
    import torch
    monkeypatch.setattr(torch.cuda, "is_available", lambda: False)
    assert cf._torch_device("gpu") == "cpu"
    assert cf._torch_device("cuda") == "cpu"
    assert cf._torch_device("cpu") == "cpu"
    monkeypatch.setattr(torch.cuda, "is_available", lambda: True)
    assert cf._torch_device("gpu") == "cuda"
