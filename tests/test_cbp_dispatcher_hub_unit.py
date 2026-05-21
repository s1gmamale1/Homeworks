"""Unit tier — template-output structural assertions for the v2 dispatcher
and the Hub HTML. Pure file-read; no DB, no TestClient, no rendering.
"""
from __future__ import annotations

from server.config import BASE_DIR


def _tpl() -> str:
    return (BASE_DIR / "server" / "template" / "perfect_homework.html").read_text(encoding="utf-8")


def test_screen_hub_html_present():
    assert 'id="screen-hub"' in _tpl()


def test_hub_marked_v2_surface_class():
    text = _tpl()
    assert 'class="screen v2-surface"' in text


def test_hub_starts_hidden():
    """The screen must default to `hidden` so legacy homeworks don't see it.
    The boot dispatcher toggles it visible when v2 mode activates."""
    text = _tpl()
    # The screen-hub div opens with `hidden` attribute
    idx = text.find('id="screen-hub"')
    assert idx > 0
    # Within ~200 chars of the tag opening, `hidden` should appear
    assert "hidden" in text[idx:idx + 200]


def test_hub_has_two_tiles():
    text = _tpl()
    assert 'id="hub-tile-cbp"' in text
    assert 'id="hub-tile-fc"' in text


def test_hub_tiles_have_aria_labels():
    text = _tpl()
    # Both tiles should carry aria-label for screen readers
    cbp_idx = text.find('id="hub-tile-cbp"')
    fc_idx = text.find('id="hub-tile-fc"')
    assert "aria-label=" in text[cbp_idx:cbp_idx + 300]
    assert "aria-label=" in text[fc_idx:fc_idx + 300]


def test_hub_tiles_have_status_pills():
    text = _tpl()
    assert 'data-hub-status="cbp"' in text
    assert 'data-hub-status="fc"' in text


def test_set_stage_v2_function_defined():
    text = _tpl()
    assert "function setStageV2(" in text


def test_v2_boot_dispatcher_defined():
    text = _tpl()
    assert "function _v2BootDispatcher(" in text


def test_setStageV2_handles_all_known_stages():
    """setStageV2's stage→phase mapping must include the v2 stage tokens."""
    text = _tpl()
    # We map cbp/mc/practice/reflection to phase names. Verify each is present
    # in the function body.
    func_idx = text.find("function setStageV2(")
    assert func_idx > 0
    # Body extends until next top-level function — search ~3500 chars
    body = text[func_idx:func_idx + 3500]
    for stage in ("cbp", "mc", "practice", "reflection"):
        assert f"'{stage}'" in body, f"setStageV2 doesn't mention stage '{stage}'"


def test_boot_dispatcher_sets_data_flow_attribute():
    text = _tpl()
    assert "setAttribute('data-flow', 'v2')" in text


def test_boot_dispatcher_wires_both_tile_clicks():
    text = _tpl()
    assert "hub-tile-cbp" in text
    assert "hub-tile-fc" in text
    # The dispatcher wires addEventListener for both
    boot_idx = text.find("function _v2BootDispatcher(")
    body = text[boot_idx:boot_idx + 3000]
    assert body.count("addEventListener") >= 2


def test_init_invokes_v2_boot_dispatcher():
    text = _tpl()
    # init() must check _v2BootDispatcher and early-return when v2 mode applies
    init_idx = text.find("function init() {")
    assert init_idx > 0
    init_body = text[init_idx:init_idx + 1500]
    assert "_v2BootDispatcher" in init_body
    assert "return;" in init_body


def test_state_object_has_v2_sub_state():
    text = _tpl()
    assert "v2: {" in text
    # Key fields
    for key in ("active:", "stage:", "sub:", "ckpIdx:", "heroSeen:", "cbp:", "fc:"):
        assert key in text, f"state.v2 missing field: {key}"


def test_legacy_setStage_function_unchanged():
    """PR #5 is parallel to setStage(n); the legacy function MUST still exist
    with its original signature. PR #5 doesn't replace it."""
    text = _tpl()
    assert "function setStage(n) {" in text
    assert "state.stage = n;" in text
