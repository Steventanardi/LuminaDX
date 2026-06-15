from core import feature_catalog as fc


CANCER_TYPES = ["liver", "lung", "skin", "breast", "colorectal"]


def test_catalog_covers_all_cancers():
    assert sorted(fc.catalog()) == sorted(CANCER_TYPES)


def test_defaults_are_subset_of_applicable():
    for ct in CANCER_TYPES:
        assert set(fc.defaults_for(ct)) <= set(fc.applicable_for(ct)), ct


def test_options_flag_defaults_correctly():
    for ct in CANCER_TYPES:
        defaults = set(fc.defaults_for(ct))
        for opt in fc.options_for(ct):
            assert opt["default"] == (opt["key"] in defaults), (ct, opt["key"])


def test_resolve_none_returns_defaults():
    assert fc.resolve("skin", None) == set(fc.defaults_for("skin"))


def test_resolve_drops_inapplicable_and_unknown():
    # radiomics is not applicable to skin; "bogus" is unknown
    got = fc.resolve("skin", ["clahe", "cnn_vgg16", "radiomics", "bogus"])
    assert got == {"clahe", "cnn_vgg16"}


def test_resolve_empty_list_runs_nothing():
    assert fc.resolve("liver", []) == set()


def test_cnn_backbones_in_filters_and_orders():
    chosen = fc.cnn_backbones_in({"clahe", "cnn_resnet50", "cnn_vgg16", "knn_classifier"})
    assert chosen == ["cnn_vgg16", "cnn_resnet50"]  # catalog order, CNN only


def test_knn_backbone_uses_single_selected_cnn():
    assert fc.knn_backbone_for({"cnn_vgg19"}) == "cnn_vgg19"


def test_knn_backbone_defaults_when_ambiguous():
    assert fc.knn_backbone_for(set()) == "cnn_resnet50"
    assert fc.knn_backbone_for({"cnn_vgg16", "cnn_resnet50"}) == "cnn_resnet50"


def test_skin_has_dermoscopy_breast_has_density():
    assert "dermoscopy_abcd" in fc.applicable_for("skin")
    assert "breast_density" in fc.applicable_for("breast")
    # and not cross-contaminated
    assert "dermoscopy_abcd" not in fc.applicable_for("breast")
    assert "radiomics" not in fc.applicable_for("skin")


def test_volumetric_cancers_share_radiomics():
    for ct in ("liver", "lung", "colorectal"):
        assert "radiomics" in fc.defaults_for(ct), ct


def test_every_cancer_offers_cnn_and_knn():
    for ct in CANCER_TYPES:
        keys = set(fc.applicable_for(ct))
        assert {"cnn_vgg16", "cnn_vgg19", "cnn_resnet50", "knn_classifier"} <= keys, ct


def test_unknown_cancer_falls_back_to_radiomics():
    assert fc.applicable_for("pancreas") == ["radiomics"]
    assert fc.resolve("pancreas", None) == {"radiomics"}
