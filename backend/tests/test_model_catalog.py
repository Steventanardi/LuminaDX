from core import model_catalog


CANCER_TYPES = ["liver", "lung", "skin", "breast", "colorectal"]


def test_catalog_covers_all_cancers():
    cat = model_catalog.catalog()
    assert sorted(cat) == sorted(CANCER_TYPES)


def test_default_is_first_option():
    for ct, entry in model_catalog.catalog().items():
        assert entry["options"][0]["tag"] == entry["default"], ct


def test_every_default_is_an_allowed_model():
    for ct in CANCER_TYPES:
        assert model_catalog.is_allowed(model_catalog.default_for(ct)), ct


def test_options_list_every_vision_model_once():
    for ct in CANCER_TYPES:
        tags = [o["tag"] for o in model_catalog.options_for(ct)]
        assert sorted(tags) == sorted(model_catalog.VISION_MODELS)


def test_resolve_honours_valid_request():
    assert model_catalog.resolve("liver", "llava:7b") == "llava:7b"


def test_resolve_falls_back_on_unknown_model():
    assert model_catalog.resolve("liver", "gpt-4o") == model_catalog.default_for("liver")


def test_resolve_falls_back_on_none():
    assert model_catalog.resolve("lung", None) == model_catalog.default_for("lung")


def test_unknown_cancer_uses_fallback_default():
    assert model_catalog.default_for("pancreas") == model_catalog._FALLBACK_DEFAULT
