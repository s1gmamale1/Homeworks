"""Sanity tier — the new v2 wiring is in place and doesn't break legacy."""
from __future__ import annotations

from server.config import BASE_DIR


def _tpl() -> str:
    return (BASE_DIR / "server" / "template" / "perfect_homework.html").read_text(encoding="utf-8")


def test_set_stage_v2_callable_from_global_scope():
    """The function declaration is at the same indentation level as
    setStage(n) so it ends up in the same scope (script block)."""
    text = _tpl()
    # Both functions should sit at the same indent (8 spaces)
    assert "        function setStage(n) {" in text
    assert "        function setStageV2(" in text


def test_setStageV2_is_parallel_to_setStage_not_a_replacement():
    text = _tpl()
    # Both exist in the file
    assert text.count("function setStage(n)") == 1
    assert text.count("function setStageV2(") == 1
    # The legacy setStage is BEFORE setStageV2 in the source order
    legacy_idx = text.find("function setStage(n)")
    v2_idx = text.find("function setStageV2(")
    assert legacy_idx < v2_idx


def test_init_v2_branch_returns_early():
    """The init() v2 check must short-circuit; otherwise legacy code runs
    too and the runtime double-initializes."""
    text = _tpl()
    init_idx = text.find("function init() {")
    body = text[init_idx:init_idx + 800]
    # The pattern: if (_v2BootDispatcher()) { return; }
    assert "_v2BootDispatcher" in body
    assert "return;" in body


def test_state_v2_has_all_brainstormed_fields():
    """Architect brainstorm §2: state.v2 = {stage, sub, ckp_idx,
    retake_count_by_idx, hero_seen}. Confirm all are present."""
    text = _tpl()
    state_idx = text.find("v2: {")
    body = text[state_idx:state_idx + 1500]
    for field in ("stage", "sub", "ckpIdx", "retakeCountByIdx", "heroSeen"):
        assert field in body, f"state.v2 missing field: {field}"


def test_hub_aria_role_present():
    text = _tpl()
    hub_idx = text.find('id="screen-hub"')
    body = text[hub_idx:hub_idx + 2500]
    assert 'role="group"' in body, "hub-tiles container must declare ARIA role"


def test_pr4_data_flow_attribute_activated_by_dispatcher():
    """PR #4 added CSS rules scoped to `[data-flow=\"v2\"]`. The dispatcher
    in PR #5 must set this attribute so the rules activate."""
    text = _tpl()
    boot_idx = text.find("function _v2BootDispatcher(")
    body = text[boot_idx:boot_idx + 3000]
    assert "setAttribute('data-flow', 'v2')" in body
