"""Function tier — end-to-end render of v1 and v2 homeworks.

NOTE on cross-PR dependency: PR #5 ships the dispatcher + Hub HTML in
the template. The `const CBP = {};` stub + the `_OBJECT_CONSTANTS`
entry that wires CBP payloads into the runtime live in PR #1. On the
`cbpr-05-dispatcher-hub` branch in isolation, posted v2 homeworks
will NOT have CBP injected as a runtime constant — that's expected.

Tests here verify PR #5's *own* deliverables in the rendered output:
the Hub HTML, the setStageV2 function, the _v2BootDispatcher function,
and the [data-flow="v2"] attribute hook. Cross-PR end-to-end
integration (CBP payload reaches the runtime) is covered by PR #1's
test_cbp_schema_function.py once both PRs land on `cbpr`.
"""
from __future__ import annotations


def _v1_payload():
    return {
        "title": "Legacy v1",
        "subject": "biology",
        "grade": 7,
        "mode": "hard",
        "family": "tabiiy-fanlar",
        "content_json": {
            "meta": {"title": "t", "subject_display": "Biology", "section": "1"},
            "panels": [],
            "flashcards": [],
            "memory_sprint": [],
            "boss_questions": [],
        },
    }


def test_render_contains_hub_html(client):
    """The Hub HTML is in the template unconditionally — it just defaults
    to `hidden`. Verify it lands in the rendered output for any homework."""
    resp = client.post("/api/homeworks", json=_v1_payload())
    assert resp.status_code == 200
    hw_id = resp.json()["id"]
    page = client.get(f"/h/{hw_id}").text
    assert 'id="screen-hub"' in page
    assert 'id="hub-tile-cbp"' in page
    assert 'id="hub-tile-fc"' in page


def test_render_contains_setStageV2_function(client):
    resp = client.post("/api/homeworks", json=_v1_payload())
    hw_id = resp.json()["id"]
    page = client.get(f"/h/{hw_id}").text
    assert "function setStageV2(" in page


def test_render_contains_boot_dispatcher_function(client):
    resp = client.post("/api/homeworks", json=_v1_payload())
    hw_id = resp.json()["id"]
    page = client.get(f"/h/{hw_id}").text
    assert "function _v2BootDispatcher(" in page
    assert "setAttribute('data-flow', 'v2')" in page


def test_render_contains_state_v2_block(client):
    resp = client.post("/api/homeworks", json=_v1_payload())
    hw_id = resp.json()["id"]
    page = client.get(f"/h/{hw_id}").text
    # state.v2 is in the rendered HTML's JavaScript
    assert "v2: {" in page
    assert "active: false" in page


def test_legacy_setStage_still_in_rendered_output(client):
    """v1 homeworks still need the legacy stage machine — confirm it's
    not accidentally removed."""
    resp = client.post("/api/homeworks", json=_v1_payload())
    hw_id = resp.json()["id"]
    page = client.get(f"/h/{hw_id}").text
    assert "function setStage(n) {" in page
    assert "state.stage = n;" in page


def test_init_v2_dispatch_branch_in_rendered_output(client):
    """init() must contain the early-return branch for v2 mode."""
    resp = client.post("/api/homeworks", json=_v1_payload())
    hw_id = resp.json()["id"]
    page = client.get(f"/h/{hw_id}").text
    # Find init() function body and check for the v2 short-circuit
    init_idx = page.find("function init() {")
    assert init_idx > 0
    init_body = page[init_idx:init_idx + 1500]
    assert "_v2BootDispatcher" in init_body
