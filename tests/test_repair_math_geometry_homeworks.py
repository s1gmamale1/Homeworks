import json

from scripts.oneoff.repair_math_geometry_homeworks import (
    HOMEWORK_BLOAT_THRESHOLD,
    INLINE_IMAGE_BLOAT_THRESHOLD,
    _needs_subject_display_fix,
    _repair_homework,
)


def _big_data_uri() -> str:
    return "data:image/png;base64," + ("A" * (INLINE_IMAGE_BLOAT_THRESHOLD + 500))


def _small_data_uri() -> str:
    return "data:image/png;base64," + ("A" * 128)


def test_repair_homework_replaces_only_bloated_assets():
    content = {
        "meta": {"subject_display": "Algebra"},
        "panels": [
            {"pages": [{"blocks": [
                {"type": "image", "src": _big_data_uri()},
                {"type": "image", "src": _small_data_uri()},
            ]}]}
        ],
        "consolidation": {
            "gallery": [
                {"html": f'<img src="{_big_data_uri()}" alt="big">'},
                {"html": f'<img src="{_small_data_uri()}" alt="small">'},
            ],
            "notes": "X" * HOMEWORK_BLOAT_THRESHOLD,
        },
    }
    repaired_json, changed, stats = _repair_homework(json.dumps(content, ensure_ascii=False), "math-algebra")
    repaired = json.loads(repaired_json)

    assert changed is True
    assert stats.src_replaced == 1
    assert stats.html_replaced == 1
    big_src = repaired["panels"][0]["pages"][0]["blocks"][0]["src"]
    small_src = repaired["panels"][0]["pages"][0]["blocks"][1]["src"]
    assert big_src.startswith("data:image/svg+xml;utf8,")
    assert small_src == _small_data_uri()
    assert 'data:image/svg+xml;utf8,' in repaired["consolidation"]["gallery"][0]["html"]
    assert _small_data_uri() in repaired["consolidation"]["gallery"][1]["html"]


def test_repair_homework_skips_small_rows_except_known_bad_subject_display():
    content = {
        "meta": {"subject_display": "Algebra"},
        "panels": [{"pages": [{"blocks": [{"type": "image", "src": _big_data_uri()}]}]}],
    }
    repaired_json, changed, stats = _repair_homework(json.dumps(content, ensure_ascii=False), "math-algebra")
    repaired = json.loads(repaired_json)

    assert changed is False
    assert stats.src_replaced == 0
    assert repaired["panels"][0]["pages"][0]["blocks"][0]["src"] == _big_data_uri()


def test_repair_homework_only_normalizes_clearly_broken_subject_display():
    content = {
        "meta": {"subject_display": "geometriya-g7-11"},
        "panels": [],
    }
    repaired_json, changed, stats = _repair_homework(json.dumps(content, ensure_ascii=False), "geometriya-g7-11")
    repaired = json.loads(repaired_json)

    assert changed is True
    assert stats.metadata_fixed == 1
    assert repaired["meta"]["subject_display"] == "Geometriya"

    assert _needs_subject_display_fix("math-algebra", "math-algebra") is True
    assert _needs_subject_display_fix("math-algebra", "Algebra") is False
    assert _needs_subject_display_fix("geometriya-g7-11", "Geometriya") is False
