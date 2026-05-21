"""Sanity tier — the CBP engine is wired, gates work, retry contract holds."""
from __future__ import annotations

from server.config import BASE_DIR


def _tpl() -> str:
    return (BASE_DIR / "server" / "template" / "perfect_homework.html").read_text(encoding="utf-8")


def test_engine_lives_in_runtime_script_block():
    """The CBP engine must be inside the inline <script> block of the
    template, not in a separate file — runtime convention."""
    text = _tpl()
    # The engine functions sit alongside setStageV2 (from PR #5)
    assert "function setStageV2(" in text
    assert "function cbpStart(" in text
    set_pos = text.find("function setStageV2(")
    cbp_pos = text.find("function cbpStart(")
    assert 0 < set_pos < cbp_pos


def test_pass_threshold_is_two_of_three():
    """Plan §'Locked design decisions' item 2: ≥2 of 3 checkpoints
    correct. Verify the threshold lives in the finalize function."""
    text = _tpl()
    finalize_idx = text.find("function cbpFinalize(")
    body = text[finalize_idx:finalize_idx + 2500]
    assert "passed >= 2" in body


def test_soft_retry_increments_retake_counter():
    """Each wrong answer increments `state.v2.retakeCountByIdx[idx]` so the
    runtime can pick a different `retake_variants[i]` each time."""
    text = _tpl()
    answer_idx = text.find("function cbpAnswer(")
    body = text[answer_idx:answer_idx + 2000]
    assert "state.v2.retakeCountByIdx[idx]" in body


def test_lb_continue_button_advances_to_next_checkpoint():
    """The Learning Block 'Davom etish' button should bump ckpIdx and
    render the next checkpoint."""
    text = _tpl()
    lb_idx = text.find("function cbpRenderLearningBlock(")
    body = text[lb_idx:lb_idx + 1500]
    assert "ckpIdx" in body
    assert "cbpRenderCheckpoint(idx + 1" in body


def test_hub_tile_click_starts_cbp_engine():
    """PR #5 stubbed the CBP tile click handler. PR #6 rewires it to
    actually invoke cbpStart() after setStageV2('cbp', 'setup')."""
    text = _tpl()
    boot_idx = text.find("function _v2BootDispatcher(")
    body = text[boot_idx:boot_idx + 3500]
    assert "cbpStart()" in body or "cbpStart === 'function'" in body


def test_no_legacy_setStage_replacement():
    """PR #6 must not replace setStage(n). Verify the legacy function
    is still defined at the same place."""
    text = _tpl()
    assert text.count("function setStage(n) {") == 1
    assert "state.stage = n;" in text


def test_unlock_gate_only_fires_after_both_sections_pass():
    text = _tpl()
    maybe_idx = text.find("function cbpMaybeOpenUnlockGate(")
    body = text[maybe_idx:maybe_idx + 600]
    assert "state.v2.cbp.passed" in body
    assert "state.v2.fc.passed" in body
    assert "setStageV2('unlock')" in body
