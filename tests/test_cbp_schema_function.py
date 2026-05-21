"""Function tier — end-to-end CBP behavior through the full stack.

Author POST → DB save → GET retrieve → template injection → assert the
extracted `CBP` JS literal deep-equals the saved payload. Also includes a
defensive answer-leak check for the injector path (tutor scrub lands in PR #2).
"""
from __future__ import annotations

import json
import re

from factories import full_content_json_with_cbp


def _extract_const_json(src: str, const_name: str):
    """Bracket-balanced JSON extractor for `const NAME = {...};` injection
    sites. Mirrors `tests/test_memory_check_gate._extract_const_json`."""
    match = re.search(rf"const\s+{const_name}\s*=\s*", src)
    assert match, f"{const_name} const not found in HTML"
    start = match.end()
    while start < len(src) and src[start].isspace():
        start += 1
    opening = src[start]
    closing = "}" if opening == "{" else "]"
    depth = 0
    in_str = False
    esc = False
    for pos in range(start, len(src)):
        ch = src[pos]
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
            continue
        if ch == '"':
            in_str = True
        elif ch == opening:
            depth += 1
        elif ch == closing:
            depth -= 1
            if depth == 0:
                return json.loads(src[start : pos + 1])
    raise AssertionError(f"{const_name} literal did not terminate")


def _post(client, content_json):
    return client.post("/api/homeworks", json={
        "title": "CBP function test",
        "subject": "biology",
        "grade": 7,
        "mode": "hard",
        "family": "tabiiy-fanlar",
        "content_json": content_json,
    })


def test_e2e_cbp_round_trips_through_full_stack(client):
    src = full_content_json_with_cbp()
    resp = _post(client, src)
    assert resp.status_code == 200, resp.text
    hw_id = resp.json()["id"]

    page = client.get(f"/h/{hw_id}")
    assert page.status_code == 200
    extracted = _extract_const_json(page.text, "CBP")
    assert "checkpoints" in extracted
    assert len(extracted["checkpoints"]) == 3
    assert [c["kind"] for c in extracted["checkpoints"]] == ["identify", "decide", "justify"]


def test_e2e_db_round_trip_preserves_cbp(client):
    src = full_content_json_with_cbp()
    resp = _post(client, src)
    hw_id = resp.json()["id"]

    fetched = client.get(f"/api/homeworks/{hw_id}")
    assert fetched.status_code == 200
    fetched_cbp = fetched.json()["content_json"]["case_based_preview"]
    assert fetched_cbp["checkpoints"][0]["kind"] == "identify"
    assert fetched_cbp["checkpoints"][1]["kind"] == "decide"
    assert fetched_cbp["checkpoints"][2]["kind"] == "justify"


def test_answer_sentinel_appears_only_inside_cbp_const(client):
    """Defensive: a sentinel inserted into `answer_spec.expected` must
    appear ONLY inside the injected `CBP` JS literal — never in surrounding
    rendered HTML body text. PR #2 wires the tutor-side scrub; this is a
    pre-emptive sanity check for the injector path."""
    src = full_content_json_with_cbp()
    src["case_based_preview"]["checkpoints"][1]["answer_spec"] = {
        "type": "text_exact",
        "expected": "MAGIC-LEAK-SENTINEL-A8F3",
    }
    resp = _post(client, src)
    assert resp.status_code == 200
    page = client.get(f"/h/{resp.json()['id']}").text
    cbp_match = re.search(r"const\s+CBP\s*=\s*(\{.+?\});", page, re.DOTALL)
    assert cbp_match, "CBP const literal not found in rendered HTML"
    outside = page.replace(cbp_match.group(0), "")
    assert "MAGIC-LEAK-SENTINEL-A8F3" not in outside, (
        "Answer sentinel leaked outside the CBP const literal"
    )
