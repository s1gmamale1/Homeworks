"""Integration tier — POST a v2 homework and confirm the rendered /h/{id}
page contains the Hub HTML + the v2 dispatcher hooks."""
from __future__ import annotations


def _v2_payload():
    return {
        "title": "PR5 integration",
        "subject": "math-algebra",
        "grade": 8,
        "mode": "hard",
        "family": "aniq-fanlar",
        "content_json": {
            "meta": {"title": "t", "subject_display": "Math", "section": "1"},
            "panels": [],
            "flashcards": [],
            "memory_sprint": [],
            "boss_questions": [],
            "flow_version": "v2",
            "case_based_preview": {
                "title": "Test CBP",
                "case_setup": {"story": "s", "role": "r", "task": "t"},
                "checkpoints": [
                    {"kind": "identify", "question": "q1", "answer_spec": {"type": "option_index", "option_index": 0}, "options": ["a", "b"]},
                    {"kind": "decide", "question": "q2", "answer_spec": {"type": "option_index", "option_index": 0}, "options": ["a", "b"]},
                    {"kind": "justify", "question": "q3", "answer_spec": {"type": "option_index", "option_index": 0}, "options": ["a", "b"]},
                ],
                "final_simulation": {"correct_path": "c", "wrong_path": "w"},
            },
        },
    }


def _v1_payload():
    p = _v2_payload()
    p["content_json"].pop("flow_version", None)
    p["content_json"].pop("case_based_preview", None)
    return p


def test_v2_homework_rendered_with_hub_html(client):
    resp = client.post("/api/homeworks", json=_v2_payload())
    assert resp.status_code == 200, resp.text
    hw_id = resp.json()["id"]
    page = client.get(f"/h/{hw_id}").text
    assert 'id="screen-hub"' in page
    assert 'id="hub-tile-cbp"' in page
    assert 'id="hub-tile-fc"' in page


def test_v2_homework_rendered_with_dispatcher(client):
    resp = client.post("/api/homeworks", json=_v2_payload())
    hw_id = resp.json()["id"]
    page = client.get(f"/h/{hw_id}").text
    assert "function setStageV2(" in page
    assert "function _v2BootDispatcher(" in page


def test_v1_homework_still_renders_hub_html_unconditionally(client):
    """The Hub HTML is in the template unconditionally — it defaults to
    `hidden` and the boot dispatcher only un-hides it for v2 mode.

    NOTE: the actual CBP-payload-driven activation requires PR #1's
    `const CBP = {};` template stub + `_OBJECT_CONSTANTS` entry, which
    lives on the `cbpr-01-schema-injector` branch. When both PRs land
    on `cbpr`, the end-to-end flow works. In PR #5 isolation we test
    only the dispatcher infrastructure shipped by this branch."""
    resp = client.post("/api/homeworks", json=_v1_payload())
    assert resp.status_code == 200
    hw_id = resp.json()["id"]
    page = client.get(f"/h/{hw_id}").text
    assert 'id="screen-hub"' in page
    # Default hidden state preserves legacy rendering until v2 boot
    hub_idx = page.find('id="screen-hub"')
    assert "hidden" in page[hub_idx:hub_idx + 200]
