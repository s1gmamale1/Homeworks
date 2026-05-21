"""Unit tier — template structural assertions for the CBP engine."""
from __future__ import annotations

from server.config import BASE_DIR


def _tpl() -> str:
    return (BASE_DIR / "server" / "template" / "perfect_homework.html").read_text(encoding="utf-8")


def test_screen_cbp_html_present():
    assert 'id="screen-cbp"' in _tpl()


def test_screen_cbp_has_all_substages():
    text = _tpl()
    cbp_idx = text.find('id="screen-cbp"')
    body = text[cbp_idx:cbp_idx + 8000]
    for sub in ('data-sub="setup"', 'data-sub="ckp"', 'data-sub="lb"',
                'data-sub="sim"', 'data-sub="fb"'):
        assert sub in body, f"substage marker missing: {sub}"


def test_unlock_screen_present():
    assert 'id="screen-unlock"' in _tpl()


def test_cbp_engine_functions_defined():
    text = _tpl()
    for fn in ("cbpShowSub", "cbpStart", "cbpRenderCheckpoint",
               "cbpAnswer", "cbpAdvanceFromCheckpoint",
               "cbpRenderLearningBlock", "cbpRenderSimulation",
               "cbpFinalize", "cbpUpdateHubTileStatus", "cbpMaybeOpenUnlockGate"):
        assert "function " + fn + "(" in text, f"engine function missing: {fn}"


def test_gate_logic_present():
    """≥2 of 3 correct → state.v2.cbp.passed = true."""
    text = _tpl()
    finalize_idx = text.find("function cbpFinalize(")
    body = text[finalize_idx:finalize_idx + 2500]
    assert "passed >= 2" in body
    assert "state.v2.cbp.passed" in body


def test_soft_retry_uses_regenerated_variants():
    """Forbid #19 — on a wrong answer, swap in `retake_variants[i]`."""
    text = _tpl()
    render_idx = text.find("function cbpRenderCheckpoint(")
    body = text[render_idx:render_idx + 2500]
    assert "retake_variants" in body
    assert "isRetake" in body


def test_retake_chip_announces_regenerated_variant():
    """Flow v2 forbid #19 — student must see the variant is regenerated,
    not think the system is buggy. Chip text in Uzbek + English."""
    text = _tpl()
    assert 'id="cbp-retake-chip"' in text
    chip_idx = text.find('id="cbp-retake-chip"')
    body = text[chip_idx:chip_idx + 400]
    assert "Qayta ishlangan" in body or "Regenerated" in body
    # aria-live for screen readers
    assert 'aria-live="assertive"' in body


def test_radiogroup_aria_on_options():
    """Checkpoint options use role=\"radiogroup\" + role=\"radio\"."""
    text = _tpl()
    assert 'role="radiogroup"' in text
    # The render function should set role=radio on each option button
    render_idx = text.find("function cbpRenderCheckpoint(")
    body = text[render_idx:render_idx + 2500]
    assert "setAttribute('role', 'radio')" in body
    assert "setAttribute('aria-checked'" in body


def test_kind_to_eyebrow_mapping():
    """The runtime maps `identify`/`decide`/`justify` to Uzbek eyebrow
    text on each checkpoint."""
    text = _tpl()
    render_idx = text.find("function cbpRenderCheckpoint(")
    body = text[render_idx:render_idx + 2500]
    for kind in ("identify", "decide", "justify"):
        assert f"{kind}:" in body or f"'{kind}'" in body


def test_final_simulation_renders_three_cards():
    text = _tpl()
    cbp_idx = text.find('id="screen-cbp"')
    body = text[cbp_idx:cbp_idx + 8000]
    for card_class in ("cbp-sim-correct", "cbp-sim-wrong", "cbp-sim-review"):
        assert card_class in body


def test_feedback_card_uses_tutor_card_light():
    """Per the plan §'Frontend design language', AI feedback uses
    .tutor-card-light."""
    text = _tpl()
    fb_idx = text.find('data-sub="fb"')
    body = text[fb_idx:fb_idx + 1500]
    assert "tutor-card-light" in body


def test_pass_label_uses_topshirildi_terminology():
    """Flow v2 forbid #20: never 'Tugallanmadi' alone. Use 'Topshirildi' /
    'Qayta urinish kerak'."""
    text = _tpl()
    finalize_idx = text.find("function cbpFinalize(")
    body = text[finalize_idx:finalize_idx + 2500]
    assert "Topshirildi" in body
    assert "Qayta urinish kerak" in body
    # Negative — "Tugallanmadi" alone is forbidden
    assert "Tugallanmadi" not in body


def test_unlock_gate_requires_both_sections_passed():
    text = _tpl()
    unlock_idx = text.find("function cbpMaybeOpenUnlockGate(")
    body = text[unlock_idx:unlock_idx + 600]
    # Gate fires only when both `cbp.passed` AND `fc.passed`
    assert "state.v2.cbp.passed" in body
    assert "state.v2.fc.passed" in body


def test_finish_button_returns_to_hub_and_updates_tile_status():
    text = _tpl()
    finalize_idx = text.find("function cbpFinalize(")
    body = text[finalize_idx:finalize_idx + 2500]
    assert "cbpUpdateHubTileStatus" in body
    assert "setStageV2('hub')" in body


def test_cbp_start_validates_payload_shape():
    """cbpStart must check checkpoints.length === 3 before proceeding."""
    text = _tpl()
    start_idx = text.find("function cbpStart(")
    body = text[start_idx:start_idx + 1500]
    assert "cbp.checkpoints" in body
    assert "checkpoints.length !== 3" in body or "length === 3" in body
