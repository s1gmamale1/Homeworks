"""Regression tests for `/api/ai/check-answer` with phase=memory-palace.

Pins the per-session grading branch added in T2 of the Memory Palace backend
build (MEMORY_PALACE_BACKEND_PLAN.md §1.3, §1.4, §2.1, §5, §7):

- Outcome ladder maps (correct_count, total) to one of four buckets:
    perfect (5/5)            → "Proficient" + 250 + 200 = 450 cosmetic XP
    yaxshi (4/5)             → "Apprentice ↗" + 200 + 100 = 300 cosmetic XP
    hali_emas_partial (3/5)  → "Apprentice"  + 150 + 0   = 150 cosmetic XP
    hali_emas_fail (1/5)     → "Pending"     + 50 + 0    = 50  cosmetic XP

- Server recomputes `is_correct` from the submitted Step-2 placement_map; the
  client-supplied `is_correct` flag is IGNORED. This is the trivial-tamper
  defense documented in the route's docstring + plan §2.2. NOT side-disjoint
  (validation key travels in the same POST), but the v1 XP is cosmetic-only,
  so the upside of a forge attack is zero.

- Cosmetic XP (`session_xp_display`) is COSMETIC ONLY per plan §7 #9 — it
  doesn't roll into any user-visible XP wallet in v1. Once cross-session
  persistence lands, the helper is replaced by a ledger write.

- `recall_speed_avg_s` is the mean of `elapsed_ms / 1000`, rounded to 1 dp.
  Frontend uses this to flash a "speed" badge on the outcome card.

- `missed_location_indices` is sorted ascending; frontend uses this to pulse
  the missed locations during the "second walkthrough" retry path.

- Validation errors:
    400 MP_MISSING_PALACE_KEY  → missing palace_key
    400 MP_MISSING_RECALL      → empty recall_results

All tests use the standard `client` fixture from conftest.py — no monkeypatch
needed. The route lookup is `db.get_homework`, populated by the standard
`POST /api/homeworks` create path (no preview round-trip required).
"""
from __future__ import annotations

import pytest


async def _always_unlocked(*a, **k):
    return True


@pytest.fixture(autouse=True)
def _unlock_practice_arc(monkeypatch):
    """Memory Palace is now a server-gated practice-arc game (BLOCKER #3).
    These are grading unit tests, not gating tests — patch the unlock check
    always-True so they exercise the grader, not the 403 PRACTICE_LOCKED guard.
    The gate itself is pinned by tests/test_practice_gate_server_enforced.py."""
    monkeypatch.setattr("server.routes.ai.is_practice_unlocked", _always_unlocked)


# ---------------------------------------------------------------------------
# Helpers — minimal homework + 5-location palace + 5 concepts.
# ---------------------------------------------------------------------------


def _build_palace(n_locations: int = 5) -> dict:
    return {
        "key": "test-palace",
        "name": "Test Palace",
        "icon": None,
        "description": None,
        "subject_family": "universal",
        "tier": "basic",
        "locations": [
            {"name": f"Location {i + 1}", "sensory_cue": f"Cue {i + 1}", "icon": None}
            for i in range(n_locations)
        ],
    }


def _build_concepts(n_concepts: int = 5) -> list[dict]:
    return [
        {
            "id": f"mp-c{i + 1}",
            "term": f"Concept {i + 1}",
            "description": f"Desc {i + 1}",
            "image_cue": f"Cue {i + 1}",
        }
        for i in range(n_concepts)
    ]


def _seed_homework(client, *, n_locations: int = 5, n_concepts: int = 5) -> str:
    """Insert a homework with a Memory Palace game and return its id."""
    content: dict = {
        "meta": {"title": "MP check-answer test HW"},
        "panels": [],
        "flashcards": [],
        "boss_questions": [],
        "memory_sprint": [],
        "gb_memory_palace": {
            "palaces": [_build_palace(n_locations)],
            "concepts": _build_concepts(n_concepts),
        },
    }
    payload = {
        "title": "MP check-answer test HW",
        "subject": "math-algebra",
        "grade": 8,
        "mode": "hard",
        "family": "aniq-fanlar",
        "content_json": content,
    }
    resp = client.post("/api/homeworks", json=payload)
    assert resp.status_code == 200, resp.text
    return resp.json()["id"]


def _build_placements(n: int = 5) -> list[dict]:
    """Return canonical Step-2 bindings: location_idx i ↔ mp-c{i+1}."""
    return [{"location_idx": i, "concept_id": f"mp-c{i + 1}"} for i in range(n)]


def _build_correct_recall(n: int = 5, elapsed_ms: int = 2000) -> list[dict]:
    """Return 5 recall picks that all match the canonical placements."""
    return [
        {
            "location_idx": i,
            "picked_concept_id": f"mp-c{i + 1}",
            "is_correct": True,           # echo what the client thinks
            "elapsed_ms": elapsed_ms,
        }
        for i in range(n)
    ]


def _post_check(client, **body) -> tuple[int, dict]:
    resp = client.post("/api/ai/check-answer", json=body)
    try:
        return resp.status_code, resp.json()
    except Exception:
        return resp.status_code, {"_raw": resp.text}


# ---------------------------------------------------------------------------
# 1. Perfect 5/5 → outcome="perfect", level="Proficient", xp_display=450
# ---------------------------------------------------------------------------


def test_mp_perfect_session_returns_perfect_outcome(client):
    hw_id = _seed_homework(client)
    placements = _build_placements(5)
    recall = _build_correct_recall(5)

    code, data = _post_check(
        client,
        phase="memory-palace",
        homework_id=hw_id,
        palace_key="test-palace",
        placements=placements,
        recall_results=recall,
    )
    assert code == 200, data
    assert data["outcome"] == "perfect"
    assert data["outcome_title"] == "Ajoyib!"
    assert data["correct_count"] == 5
    assert data["total_count"] == 5
    assert data["accuracy_pct"] == 100
    assert data["level_label"] == "Proficient"
    # 5 * 50 = 250, plus +200 perfect bonus
    assert data["session_xp_display"] == 450
    assert data["retry_offered"] is False
    assert data["missed_location_indices"] == []


def test_mp_persists_phase_attempts_for_reflection(client):
    """Memory Palace was the ONLY graded Practice-Arc game writing NOTHING to
    phase_attempts, so the Reflection engine's data extraction was blind to it.
    A graded submit with a session_id must now persist one row per recall
    location under phase="memory-palace" (the string the engine groups)."""
    import asyncio
    from server.db.attempts_repo import list_phase_attempts

    hw_id = _seed_homework(client)
    sid = "mp-persist-sess"
    code, data = _post_check(
        client,
        phase="memory-palace",
        homework_id=hw_id,
        session_id=sid,
        palace_key="test-palace",
        placements=_build_placements(5),
        recall_results=_build_correct_recall(5),
    )
    assert code == 200, data

    loop = asyncio.new_event_loop()
    try:
        rows = loop.run_until_complete(
            list_phase_attempts(sid, hw_id, phase="memory-palace")
        )
    finally:
        loop.close()

    assert len(rows) == 5  # one row per recall location
    assert all(r["phase"] == "memory-palace" for r in rows)
    assert sum(1 for r in rows if r["correct"] == 1) == 5  # perfect session


# ---------------------------------------------------------------------------
# 2. 4/5 → outcome="yaxshi", level="Apprentice ↗", xp_display=300
# ---------------------------------------------------------------------------


def test_mp_yaxshi_session_4_of_5(client):
    hw_id = _seed_homework(client)
    placements = _build_placements(5)
    # Make recall index 2 wrong by picking a different concept_id.
    recall = _build_correct_recall(5)
    recall[2]["picked_concept_id"] = "mp-c5"  # mismatch with placement
    recall[2]["is_correct"] = False

    code, data = _post_check(
        client,
        phase="memory-palace",
        homework_id=hw_id,
        palace_key="test-palace",
        placements=placements,
        recall_results=recall,
    )
    assert code == 200, data
    assert data["outcome"] == "yaxshi"
    assert data["outcome_title"] == "Yaxshi!"
    assert data["correct_count"] == 4
    assert data["accuracy_pct"] == 80
    assert data["level_label"] == "Apprentice ↗"
    # 4 * 50 = 200, plus +100 yaxshi bonus
    assert data["session_xp_display"] == 300
    assert data["retry_offered"] is True
    assert len(data["missed_location_indices"]) == 1
    assert data["missed_location_indices"] == [2]


# ---------------------------------------------------------------------------
# 3. 3/5 → outcome="hali_emas_partial", level="Apprentice", xp_display=150
# ---------------------------------------------------------------------------


def test_mp_partial_session_3_of_5(client):
    hw_id = _seed_homework(client)
    placements = _build_placements(5)
    recall = _build_correct_recall(5)
    # Make 2 wrong: indices 1 and 3.
    recall[1]["picked_concept_id"] = "mp-c5"
    recall[3]["picked_concept_id"] = "mp-c1"

    code, data = _post_check(
        client,
        phase="memory-palace",
        homework_id=hw_id,
        palace_key="test-palace",
        placements=placements,
        recall_results=recall,
    )
    assert code == 200, data
    assert data["outcome"] == "hali_emas_partial"
    assert data["outcome_title"] == "Hali emas"
    assert data["correct_count"] == 3
    assert data["accuracy_pct"] == 60
    assert data["level_label"] == "Apprentice"
    # 3 * 50 = 150, no bonus
    assert data["session_xp_display"] == 150
    assert data["retry_offered"] is True


# ---------------------------------------------------------------------------
# 4. 1/5 → outcome="hali_emas_fail", level="Pending", xp_display=50
# ---------------------------------------------------------------------------


def test_mp_fail_session_1_of_5(client):
    hw_id = _seed_homework(client)
    placements = _build_placements(5)
    recall = _build_correct_recall(5)
    # Wrong at indices 1, 2, 3, 4 (only index 0 correct).
    recall[1]["picked_concept_id"] = "mp-c5"
    recall[2]["picked_concept_id"] = "mp-c1"
    recall[3]["picked_concept_id"] = "mp-c2"
    recall[4]["picked_concept_id"] = "mp-c1"

    code, data = _post_check(
        client,
        phase="memory-palace",
        homework_id=hw_id,
        palace_key="test-palace",
        placements=placements,
        recall_results=recall,
    )
    assert code == 200, data
    assert data["outcome"] == "hali_emas_fail"
    assert data["outcome_title"] == "Hali emas"
    assert data["correct_count"] == 1
    assert data["accuracy_pct"] == 20
    assert data["level_label"] == "Pending"
    # 1 * 50 = 50, no bonus
    assert data["session_xp_display"] == 50
    assert data["retry_offered"] is True


# ---------------------------------------------------------------------------
# 5. CRITICAL — server recomputes is_correct, ignores client-supplied flag.
# ---------------------------------------------------------------------------


def test_mp_server_recomputes_is_correct_overrides_client(client):
    """Tampering defense: a malicious client claims 5/5 by setting is_correct=True
    on every recall_result, but 2 of the picked_concept_ids don't actually
    match the Step-2 placements. The server MUST recompute → correct_count=3,
    outcome="hali_emas_partial".
    """
    hw_id = _seed_homework(client)
    placements = _build_placements(5)
    # Build recall where every entry CLAIMS is_correct=True, but indices 1 + 3
    # have picked_concept_ids that do NOT match the placement_map.
    recall = []
    for i in range(5):
        if i in (1, 3):
            picked = "mp-c5" if i == 1 else "mp-c2"  # mismatched on purpose
        else:
            picked = f"mp-c{i + 1}"
        recall.append({
            "location_idx": i,
            "picked_concept_id": picked,
            "is_correct": True,   # client lies
            "elapsed_ms": 2000,
        })

    code, data = _post_check(
        client,
        phase="memory-palace",
        homework_id=hw_id,
        palace_key="test-palace",
        placements=placements,
        recall_results=recall,
    )
    assert code == 200, data
    # Server-side recompute strips the client-supplied is_correct=True at
    # locations 1 + 3 and finds 3 actual matches → hali_emas_partial.
    assert data["correct_count"] == 3
    assert data["total_count"] == 5
    assert data["outcome"] == "hali_emas_partial"
    assert data["accuracy_pct"] == 60
    assert sorted(data["missed_location_indices"]) == [1, 3]


# ---------------------------------------------------------------------------
# 6. recall_speed_avg_s — mean of elapsed_ms / 1000, rounded to 1 dp
# ---------------------------------------------------------------------------


def test_mp_recall_speed_avg_correct_math(client):
    hw_id = _seed_homework(client)
    placements = _build_placements(5)
    elapsed_values = [2400, 1900, 2100, 3800, 2600]  # mean = 2560 ms = 2.56 s → round to 2.6
    recall = []
    for i, ms in enumerate(elapsed_values):
        recall.append({
            "location_idx": i,
            "picked_concept_id": f"mp-c{i + 1}",
            "is_correct": True,
            "elapsed_ms": ms,
        })

    code, data = _post_check(
        client,
        phase="memory-palace",
        homework_id=hw_id,
        palace_key="test-palace",
        placements=placements,
        recall_results=recall,
    )
    assert code == 200, data
    assert data["recall_speed_avg_s"] == 2.6


# ---------------------------------------------------------------------------
# 7. missed_location_indices is sorted ascending
# ---------------------------------------------------------------------------


def test_mp_missed_location_indices_populated_and_sorted(client):
    """Wrong picks at locations 3 + 1 (in arbitrary submit order) → server
    returns [1, 3] sorted ascending."""
    hw_id = _seed_homework(client)
    placements = _build_placements(5)
    recall = _build_correct_recall(5)
    # Submit wrong picks at indices 3 + 1, but reorder them (3 first) to make
    # sure the route does its own sort rather than echoing input order.
    recall[3]["picked_concept_id"] = "mp-c5"
    recall[1]["picked_concept_id"] = "mp-c4"
    # Reorder the recall list so wrong picks come in non-ascending order.
    recall = [recall[3], recall[0], recall[1], recall[2], recall[4]]

    code, data = _post_check(
        client,
        phase="memory-palace",
        homework_id=hw_id,
        palace_key="test-palace",
        placements=placements,
        recall_results=recall,
    )
    assert code == 200, data
    assert data["missed_location_indices"] == [1, 3]


# ---------------------------------------------------------------------------
# 8. 400 when palace_key missing
# ---------------------------------------------------------------------------


def test_mp_400_when_palace_key_missing(client):
    hw_id = _seed_homework(client)
    placements = _build_placements(5)
    recall = _build_correct_recall(5)

    code, data = _post_check(
        client,
        phase="memory-palace",
        homework_id=hw_id,
        # palace_key intentionally omitted
        placements=placements,
        recall_results=recall,
    )
    assert code == 400, data
    # FastAPI envelopes our dict detail under "detail".
    assert data["detail"]["code"] == "MP_MISSING_PALACE_KEY"


# ---------------------------------------------------------------------------
# 9. 400 when recall_results empty
# ---------------------------------------------------------------------------


def test_mp_400_when_recall_results_empty(client):
    hw_id = _seed_homework(client)
    placements = _build_placements(5)

    code, data = _post_check(
        client,
        phase="memory-palace",
        homework_id=hw_id,
        palace_key="test-palace",
        placements=placements,
        recall_results=[],
    )
    assert code == 400, data
    assert data["detail"]["code"] == "MP_MISSING_RECALL"
