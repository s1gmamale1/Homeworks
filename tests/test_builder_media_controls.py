from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
PREVIEW_JS = ROOT / "frontend" / "js" / "editors" / "preview.js"
RICH_FIELD_JS = ROOT / "frontend" / "js" / "editors" / "_rich-field.js"
APP_CSS = ROOT / "frontend" / "css" / "app.css"


def test_preview_editor_exposes_replace_and_remove_controls_for_media_blocks():
    js = PREVIEW_JS.read_text(encoding="utf-8")

    assert "function mediaActionsHtml(kind)" in js
    assert "js-media-replace" in js
    assert "js-media-remove" in js
    assert '${mediaActionsHtml("image")}<img' in js
    assert '${mediaActionsHtml("svg")}${stripScripts' in js
    assert "removeMediaWrap(wrap, editor)" in js
    assert "replaceMediaWrap(wrap, editor)" in js


def test_compact_rich_field_exposes_media_controls_without_persisting_ui_buttons():
    js = RICH_FIELD_JS.read_text(encoding="utf-8")

    assert "function decorateMediaBlocks(root)" in js
    assert "function serializeEditorHtml(editor)" in js
    assert 'clone.querySelectorAll(".media-wrap-actions").forEach((node) => node.remove())' in js
    assert 'mediaActionsHtml("image")' in js
    assert 'mediaActionsHtml("svg")' in js
    assert "js-media-remove" in js
    assert "js-media-replace" in js


def test_builder_media_controls_are_styled_and_generated_paths_are_allowed():
    css = APP_CSS.read_text(encoding="utf-8")
    preview_js = PREVIEW_JS.read_text(encoding="utf-8")
    rich_js = RICH_FIELD_JS.read_text(encoding="utf-8")

    assert ".media-wrap-actions" in css
    assert ".media-wrap-btn" in css
    assert 'lower.startsWith("/generated/")' in preview_js
    assert 'lower.startsWith("/generated/")' in rich_js


def test_builder_media_controls_are_visible_without_hover():
    css = APP_CSS.read_text(encoding="utf-8")
    block = re.search(
        r"\.rich-editor\s+\.media-wrap-actions,\s*"
        r"\.rich-field\s+\.js-rich-mini\s+\.media-wrap-actions\s*\{(?P<body>[^}]*)\}",
        css,
    )
    assert block, "missing shared media action bar CSS block"
    body = block.group("body")
    assert "opacity: 1" in body
    assert "pointer-events: auto" in body
    assert "transform: translateY(0)" in body


def test_compact_image_wrap_positions_overlay_buttons_locally():
    css = APP_CSS.read_text(encoding="utf-8")
    block = re.search(
        r"\.rich-field\s+\.js-rich-mini\s+\.image-wrap\s*\{(?P<body>[^}]*)\}",
        css,
    )
    assert block, "missing compact RichField image-wrap CSS block"
    assert "position: relative" in block.group("body"), (
        "mini-editor image action buttons are absolutely positioned; "
        ".image-wrap must be the positioned ancestor"
    )


def test_compact_rich_field_decorates_media_after_paste():
    js = RICH_FIELD_JS.read_text(encoding="utf-8")
    assert "decorateMediaBlocks(editor);\n      flushEmit();" in js
