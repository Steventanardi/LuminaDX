"""Parser-robustness tests for the cancer-module LLM-output handling.

Regression cover for the markdown-escape bug: local LLMs emit "overall\\_impression"
(backslash-escaped underscores), which is invalid JSON and used to collapse the
whole report to the "Analysis complete — see raw output." placeholder.
"""
from core.modules.base import coerce_json
from core.modules.skin import SkinModule


def test_coerce_json_plain():
    assert coerce_json('{"a": 1}') == {"a": 1}


def test_coerce_json_markdown_escaped_underscores():
    # The exact failure mode seen in production output.
    raw = '{"overall\\_impression": "ok", "lesion\\_id": "L1"}'
    data = coerce_json(raw)
    assert data == {"overall_impression": "ok", "lesion_id": "L1"}


def test_coerce_json_fenced():
    raw = '```json\n{"x": "y"}\n```'
    assert coerce_json(raw) == {"x": "y"}


def test_coerce_json_prose_wrapped():
    raw = 'Here is the analysis:\n{"x": 2}\nThanks!'
    assert coerce_json(raw) == {"x": 2}


def test_coerce_json_unrecoverable_returns_none():
    assert coerce_json("not json at all") is None
    assert coerce_json("") is None


def test_coerce_json_line_comments():
    # minicpm-v:8b emitted // comments inside the object, which is invalid JSON.
    raw = '{"D_diameter": false, // estimated diameter not available\n"x": 1}'
    assert coerce_json(raw) == {"D_diameter": False, "x": 1}


def test_coerce_json_comment_does_not_eat_url_in_string():
    raw = '{"src": "http://example.com/path", "ok": true}'
    assert coerce_json(raw) == {"src": "http://example.com/path", "ok": True}


def test_coerce_json_trailing_comma_and_block_comment():
    raw = '{"a": 1, /* note */ "b": [1, 2,], }'
    assert coerce_json(raw) == {"a": 1, "b": [1, 2]}


def test_coerce_json_combined_failure_mode():
    # The full production failure: fences + escaped underscores + // comment + trailing comma.
    raw = (
        '```json\n'
        '{"overall\\_impression": "Highly suspicious", '
        '"abcde": {"D\\_diameter": false, // estimated\n"E\\_evolution": null},}\n'
        '```'
    )
    assert coerce_json(raw) == {
        "overall_impression": "Highly suspicious",
        "abcde": {"D_diameter": False, "E_evolution": None},
    }


def test_skin_parse_recovers_escaped_report():
    raw = (
        '{\n'
        '"overall\\_impression": "Highly suspicious for melanoma",\n'
        '"lesions": [{"lesion\\_id": "L1", "dermoscopy\\_score": 5,\n'
        '  "abcde": {"A\\_asymmetry": true, "B\\_border": false},\n'
        '  "major\\_features": ["Blue-white veil"]}],\n'
        '"recommendations": ["Urgent excisional biopsy"]\n'
        '}'
    )
    report = SkinModule().parse_report(raw, "Dermoscopy", True, "rad")
    assert report.overall_impression == "Highly suspicious for melanoma"
    assert len(report.lesions) == 1
    assert report.lesions[0].dermoscopy_score == 5
    assert report.lesions[0].major_features == ["Blue-white veil"]
    assert report.recommendations == ["Urgent excisional biopsy"]
