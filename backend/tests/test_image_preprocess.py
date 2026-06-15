"""Tests for the OpenCV image-preprocessing / extractor module (no torch needed)."""
import cv2
import numpy as np
import pytest

from core import image_preprocess as ip


def _lesion_image(size: int = 200) -> np.ndarray:
    """Light-skin background with a dark off-centre blob (a fake lesion)."""
    img = np.full((size, size, 3), 200, dtype=np.uint8)
    cv2.circle(img, (90, 110), 45, (60, 40, 40), thickness=-1)
    return img


def _mammo_image(size: int = 200) -> np.ndarray:
    """Black background with a bright breast region containing a denser core."""
    img = np.zeros((size, size, 3), dtype=np.uint8)
    cv2.circle(img, (size // 2, size // 2), 70, (120, 120, 120), thickness=-1)
    cv2.circle(img, (size // 2, size // 2), 35, (210, 210, 210), thickness=-1)
    return img


def test_shades_of_gray_preserves_shape_and_dtype():
    img = _lesion_image()
    out = ip.shades_of_gray(img)
    assert out.shape == img.shape
    assert out.dtype == np.uint8


def test_clahe_preserves_shape():
    img = _lesion_image()
    out = ip.apply_clahe(img)
    assert out.shape == img.shape
    assert out.dtype == np.uint8


def test_remove_hair_preserves_shape():
    img = _lesion_image()
    out = ip.remove_hair(img)
    assert out.shape == img.shape


def test_preprocess_dermoscopy_writes_file_and_returns_features(tmp_path):
    src = tmp_path / "lesion.png"
    cv2.imwrite(str(src), _lesion_image())
    out = tmp_path / "enhanced.png"
    feats = ip.preprocess_dermoscopy(src, out)
    assert out.exists()
    assert feats is not None and feats.segmented
    assert 0 <= feats.asymmetry_pct <= 100
    assert feats.diameter_px > 0
    assert "Asymmetry" in feats.summary()


def test_preprocess_dermoscopy_toggles_skip_steps(tmp_path):
    src = tmp_path / "lesion.png"
    cv2.imwrite(str(src), _lesion_image())
    out = tmp_path / "enhanced.png"
    # No ABCD requested → returns None but still writes the (unmodified) image
    feats = ip.preprocess_dermoscopy(
        src, out, color_constancy=False, hair_removal=False, clahe=False, compute_abcd=False,
    )
    assert out.exists()
    assert feats is None


def test_preprocess_dermoscopy_handles_unreadable(tmp_path):
    assert ip.preprocess_dermoscopy(tmp_path / "missing.png", tmp_path / "o.png") is None


def test_mammographic_density_classifies(tmp_path):
    src = tmp_path / "mammo.png"
    cv2.imwrite(str(src), _mammo_image())
    mf = ip.compute_mammographic_density(src)
    assert mf is not None and mf.segmented
    assert mf.birads_density in {"a", "b", "c", "d"}
    assert 0 <= mf.percent_density <= 100
    assert 0 < mf.breast_area_frac < 1


@pytest.mark.parametrize("pct,cat", [(10, "a"), (40, "b"), (60, "c"), (90, "d")])
def test_birads_density_thresholds(pct, cat):
    assert ip._birads_density(pct) == cat


def test_preprocess_mammography_writes_file(tmp_path):
    src = tmp_path / "mammo.png"
    cv2.imwrite(str(src), _mammo_image())
    out = tmp_path / "enhanced.png"
    assert ip.preprocess_mammography(src, out) is True
    assert out.exists()
