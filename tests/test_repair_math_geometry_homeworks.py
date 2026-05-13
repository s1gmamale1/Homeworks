import json
import urllib.parse
from pathlib import Path

from scripts.oneoff.repair_math_geometry_homeworks import (
    HOMEWORK_BLOAT_THRESHOLD,
    INLINE_IMAGE_BLOAT_THRESHOLD,
    _needs_subject_display_fix,
    _repair_homework,
    _svg_data_uri,
)


def _big_data_uri() -> str:
    return "data:image/png;base64," + ("A" * (INLINE_IMAGE_BLOAT_THRESHOLD + 500))


def _small_data_uri() -> str:
    return "data:image/png;base64," + ("A" * 128)


def _generated_url() -> str:
    return "http://192.168.1.87:8000/generated/HW-20260505-008__panels_1_pages_0_blocks_4_text__handdrawn.png"


def test_static_replacement_asset_exists():
    asset = Path(__file__).resolve().parents[1] / "frontend" / "generated" / "HW-20260505-008_factorization_methods.svg"
    assert asset.exists()
    svg = asset.read_text(encoding="utf-8")
    assert "Ko'phadlarni ajratish" in svg
    assert "Homework diagram" not in svg
    assert "Formula diagram" not in svg


def test_repair_homework_preserves_existing_authored_images():
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

    assert changed is False
    assert stats.src_replaced == 0
    assert stats.html_replaced == 0
    big_src = repaired["panels"][0]["pages"][0]["blocks"][0]["src"]
    small_src = repaired["panels"][0]["pages"][0]["blocks"][1]["src"]
    assert big_src == _big_data_uri()
    assert small_src == _small_data_uri()
    assert _big_data_uri() in repaired["consolidation"]["gallery"][0]["html"]
    assert _small_data_uri() in repaired["consolidation"]["gallery"][1]["html"]


def test_repair_homework_moves_generated_img_html_to_image_block_without_changing_src():
    content = {
        "meta": {"subject_display": "Algebra"},
        "panels": [
            {"pages": [{"blocks": [
                {"type": "quote", "text": f'<img src="{_generated_url()}" alt="Handdrawn diagram" />'},
                {"type": "image", "src": _generated_url()},
            ]}]}
        ],
    }
    repaired_json, changed, stats = _repair_homework(json.dumps(content, ensure_ascii=False), "math-algebra")
    repaired = json.loads(repaired_json)

    assert changed is True
    assert stats.html_replaced == 1
    assert stats.src_replaced == 2
    assert _generated_url() not in repaired_json
    quote_repair = repaired["panels"][0]["pages"][0]["blocks"][0]
    image_repair = repaired["panels"][0]["pages"][0]["blocks"][1]
    assert quote_repair == {
        "type": "image",
        "src": "/generated/HW-20260505-008__panels_1_pages_0_blocks_4_text__handdrawn.png",
        "alt": "Handdrawn diagram",
    }
    assert image_repair["type"] == "image"
    assert image_repair["src"] == "/generated/HW-20260505-008__panels_1_pages_0_blocks_4_text__handdrawn.png"
    assert "data:image/svg+xml;utf8," not in repaired_json


def test_repair_homework_decodes_svg_data_uri_without_rewriting_artwork():
    generic_svg = """
    <svg xmlns="http://www.w3.org/2000/svg" width="1200" height="720">
      <text>Homework diagram</text>
      <text>Formula diagram</text>
    </svg>
    """
    previous_bad_src = "data:image/svg+xml;utf8," + urllib.parse.quote(generic_svg, safe="")
    content = {
        "meta": {"subject_display": "Algebra"},
        "panels": [
            {"pages": [{"blocks": [
                {"type": "quote", "text": f'<img src="{previous_bad_src}" alt="Handdrawn diagram" />'},
                {"type": "image", "src": previous_bad_src},
            ]}]}
        ],
    }
    repaired_json, changed, stats = _repair_homework(json.dumps(content, ensure_ascii=False), "math-algebra")
    repaired = json.loads(repaired_json)

    assert changed is True
    assert stats.html_replaced == 1
    assert stats.src_replaced == 2
    assert "data:image/svg+xml;utf8," not in repaired_json
    assert repaired["panels"][0]["pages"][0]["blocks"][0]["type"] == "svg"
    assert repaired["panels"][0]["pages"][0]["blocks"][0]["html"].startswith("<svg")
    assert repaired["panels"][0]["pages"][0]["blocks"][1]["type"] == "svg"
    assert repaired["panels"][0]["pages"][0]["blocks"][1]["html"].startswith("<svg")
    assert "Homework diagram" in repaired_json
    assert "Formula diagram" in repaired_json


def test_repair_homework_preserves_generic_placeholder_svg_for_manual_review():
    generic_svg = """
    <svg xmlns="http://www.w3.org/2000/svg" width="1200" height="720">
      <text>Homework diagram</text>
      <text>Formula diagram</text>
    </svg>
    """
    content = {
        "meta": {"subject_display": "Algebra"},
        "panels": [
            {
                "title": "Ko'phadlarni ajratish",
                "pages": [{"blocks": [{"type": "svg", "html": generic_svg}]}],
            }
        ],
    }
    repaired_json, changed, stats = _repair_homework(json.dumps(content, ensure_ascii=False), "math-algebra")
    repaired = json.loads(repaired_json)

    assert changed is False
    assert stats.html_replaced == 0
    html = repaired["panels"][0]["pages"][0]["blocks"][0]["html"]
    assert "Homework diagram" in html
    assert "Formula diagram" in html


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
