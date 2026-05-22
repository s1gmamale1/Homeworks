"""Regression tests for the server-authoritative Reflection finalization engine.

All DB repos + the AI orchestrator are mocked — these never hit a provider or a
real database. Tests are named by the behavior they guard.

Covered invariants:
  • extraction groups attempts into the correct divisions (incl. boss split-out)
  • the deterministic verdict at the 60% boundary (59 → needs_retry, 60 → passed
    when boss + gates are OK)
  • a failed boss forces needs_retry even at a high overall_pct
  • AI-unavailable still returns a valid debrief with ai_unavailable: True
  • finalize persists a final_report whose TOP-LEVEL key is `verdict`
  • get_debrief returns the persisted report
  • redo flips status → active and clears Division-3 progress only
  • the debrief NEVER contains weak_point_keywords / rubric / expected answers
"""
import pytest

from server.services import reflection_engine as RE


# ── Shared fixtures / helpers ───────────────────────────────────────────────

def _attempt(phase, *, correct=None, score=None, qid=None, score_val=None, tags=None):
    return {
        "phase": phase,
        "correct": correct,
        "score": score if score is not None else score_val,
        "question_id": qid,
        "item_id": None,
        "axis_1": None,
        "axis_2": None,
        "misconception_tags_json": tags,
    }


@pytest.fixture
def patch_repos(monkeypatch):
    """Patch every repo + AI call the engine touches, returning a control dict.

    The caller seeds `state["attempts"]`, `state["metrics"]`, `state["gate"]`,
    and optionally `state["ai"]` (a dict the mocked AI returns) or
    `state["ai_raises"]` (an exception class). Reads back `state["stored"]`
    (final_report) and `state["session_writes"]` / `state["deleted_phases"]`.
    """
    state = {
        "attempts": [],
        "metrics": {"weak_topics": [], "strong_topics": []},
        "gate": {"cbp": {"passed": True}, "mc": {"passed": True}},
        "ai": {
            "narrative": "Yaxshi ish.",
            "weak_points": ["bo'lim A"],
            "strong_points": ["bo'lim B"],
            "next_steps": ["qayta ko'ring"],
            "redo_recommendation": "none",
        },
        "ai_raises": None,
        "ai_prompts": [],
        "stored": None,
        "session_writes": [],
        "deleted_phases": None,
    }

    async def mock_list_attempts(session_id, hw_id, phase=None, limit=1000):
        if phase is None:
            return list(state["attempts"])
        return [a for a in state["attempts"] if a.get("phase") == phase]

    async def mock_recompute(session_id, hw_id):
        return dict(state["metrics"])

    async def mock_gate(session_id, hw_id):
        return dict(state["gate"])

    async def mock_upsert(session_id, hw_id, report):
        state["stored"] = report

    async def mock_get_report(session_id, hw_id):
        return state["stored"]

    def mock_build_input(payload, *a, **k):  # sync — matches the real signature
        return "INPUT:\n{}"

    async def mock_generate_json(prompt, *a, **k):
        state["ai_prompts"].append(prompt)
        if state["ai_raises"] is not None:
            raise state["ai_raises"]
        return dict(state["ai"])

    monkeypatch.setattr(RE, "list_phase_attempts", mock_list_attempts)
    monkeypatch.setattr(RE, "recompute_session_metrics", mock_recompute)
    monkeypatch.setattr(RE, "compute_gate_state", mock_gate)
    monkeypatch.setattr(RE, "upsert_final_report", mock_upsert)
    monkeypatch.setattr(RE, "get_final_report", mock_get_report)
    monkeypatch.setattr(RE.ai_orchestrator, "build_input_section", mock_build_input)
    monkeypatch.setattr(RE.ai_orchestrator, "generate_json", mock_generate_json)

    # _write_session_mark + redo hit the DB directly via connect() — stub the
    # connection so no real DB is touched.
    class _FakeCursor:
        rowcount = 7

    class _FakeConn:
        async def execute(self, sql, params=()):
            if sql.strip().upper().startswith("UPDATE SESSIONS"):
                state["session_writes"].append((sql, params))
            elif "DELETE FROM PHASE_ATTEMPTS" in " ".join(sql.split()).upper():
                state["deleted_phases"] = params
            return _FakeCursor()

        async def commit(self):
            pass

        async def close(self):
            pass

    async def mock_connect():
        return _FakeConn()

    monkeypatch.setattr(RE, "connect", mock_connect)

    return state


# ── EXTRACTION ──────────────────────────────────────────────────────────────

def test_extraction_groups_attempts_into_the_four_divisions():
    attempts = [
        _attempt("case_based_preview", correct=1),
        _attempt("memory_check", correct=0),
        _attempt("tile-match", correct=1),
        _attempt("adaptive-quiz", correct=1),
        _attempt("final-boss", correct=1),
        _attempt("theme-preview", correct=1),  # unknown/ungraded → dropped
    ]
    buckets = RE.group_attempts_by_division(attempts)
    assert len(buckets["cbp"]) == 1
    assert len(buckets["mc"]) == 1
    # tile-match + adaptive-quiz are practice; final-boss is split into `boss`.
    assert len(buckets["practice"]) == 2
    assert len(buckets["boss"]) == 1
    # The unknown phase contributed nothing anywhere.
    total = sum(len(v) for v in buckets.values())
    assert total == 5


def test_extraction_does_not_count_final_boss_in_the_practice_bucket():
    buckets = RE.group_attempts_by_division([_attempt("final-boss", correct=1)])
    assert buckets["practice"] == []
    assert len(buckets["boss"]) == 1


def test_extraction_groups_dynamic_boss_phase_into_boss_division():
    # The dynamic /ai/boss/* rebuild (PR #252/#253) persists phase="boss", not
    # "final-boss". Without recognizing it the boss bucket is empty and every
    # real v2 verdict wrongly becomes needs_retry. Guards that cross-session
    # integration: phase="boss" must land in the boss division and count as a win.
    buckets = RE.group_attempts_by_division([_attempt("boss", correct=1)])
    assert buckets["practice"] == []
    assert len(buckets["boss"]) == 1
    assert RE.boss_passed([_attempt("boss", correct=1)]) is True


def test_grading_items_alias_maps_v2_phases_so_they_count_in_overall_pct():
    # The v2 runtime persists newer phase strings than grading's v1 table, so
    # real-life-challenge (the key AMR signal), the dynamic "boss", and the
    # v2-only Game-Break games were SILENTLY dropped from overall_pct. The alias
    # in _grading_items_from_attempts must normalize them onto counted keys.
    rows = [
        _attempt("real-life-challenge", correct=1, score=0.9),
        _attempt("boss", correct=1, score=0.8),
        _attempt("mystery-box", correct=1),
        _attempt("puzzle-lock", correct=1),
        _attempt("ttt", correct=1),
        _attempt("memory-palace", correct=1),
    ]
    items = RE._grading_items_from_attempts(rows)
    phases = {it["phase"] for it in items}
    # exact semantic remaps
    assert "real-life" in phases and "real-life-challenge" not in phases
    assert "final-boss" in phases and "boss" not in phases
    # v2-only closed games routed onto a counted closed Game-Break key
    assert "adaptive-quiz" in phases
    # and they actually contribute to overall_pct (was 0 before the alias)
    from server.services import grading
    assert grading.aggregate(items)["overall_pct"] > 0


# ── DETERMINISTIC VERDICT ───────────────────────────────────────────────────

def test_verdict_is_needs_retry_at_59_pct_even_with_boss_and_gates_ok():
    verdict = RE.compute_verdict(
        overall_pct=59,
        boss_rows=[_attempt("final-boss", correct=1)],
        cbp_passed=True,
        mc_passed=True,
    )
    assert verdict == RE.VERDICT_NEEDS_RETRY


def test_verdict_is_passed_at_exactly_60_pct_when_boss_and_gates_ok():
    verdict = RE.compute_verdict(
        overall_pct=60,
        boss_rows=[_attempt("final-boss", correct=1)],
        cbp_passed=True,
        mc_passed=True,
    )
    assert verdict == RE.VERDICT_PASSED


def test_verdict_is_needs_retry_when_boss_failed_despite_high_pct():
    # 95% overall but the boss was never beaten / no solid damage.
    verdict = RE.compute_verdict(
        overall_pct=95,
        boss_rows=[_attempt("final-boss", correct=0, score=0.1)],
        cbp_passed=True,
        mc_passed=True,
    )
    assert verdict == RE.VERDICT_NEEDS_RETRY


def test_verdict_is_needs_retry_when_cbp_gate_failed_despite_high_pct():
    verdict = RE.compute_verdict(
        overall_pct=90,
        boss_rows=[_attempt("final-boss", correct=1)],
        cbp_passed=False,
        mc_passed=True,
    )
    assert verdict == RE.VERDICT_NEEDS_RETRY


def test_boss_passed_on_outright_win():
    assert RE.boss_passed([_attempt("final-boss", correct=1)]) is True


def test_boss_passed_on_pool_exhausted_with_solid_damage():
    # No win row, but mean score clears the solid-damage floor.
    rows = [
        _attempt("final-boss", correct=0, score=0.7),
        _attempt("final-boss", correct=0, score=0.7),
    ]
    assert RE.boss_passed(rows) is True


def test_boss_not_passed_when_no_boss_attempts():
    assert RE.boss_passed([]) is False


def test_boss_not_passed_on_low_damage():
    rows = [_attempt("final-boss", correct=0, score=0.2)]
    assert RE.boss_passed(rows) is False


# ── MISTAKE REPAIRS ─────────────────────────────────────────────────────────

def test_mistake_repairs_counts_wrong_early_then_right_in_boss_by_question_id():
    attempts = [
        _attempt("memory_check", correct=0, qid="concept-x"),
        _attempt("adaptive-quiz", correct=0, qid="concept-y"),
        _attempt("final-boss", correct=1, qid="concept-x"),  # repaired
        _attempt("final-boss", correct=1, qid="concept-z"),  # never missed early
    ]
    buckets = RE.group_attempts_by_division(attempts)
    assert RE.count_mistake_repairs(buckets) == 1


def test_mistake_repairs_is_zero_when_nothing_missed_early():
    attempts = [_attempt("final-boss", correct=1, qid="q1")]
    buckets = RE.group_attempts_by_division(attempts)
    assert RE.count_mistake_repairs(buckets) == 0


# ── FINALIZE (full pipeline) ────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_finalize_persists_final_report_with_top_level_verdict_key(patch_repos):
    patch_repos["attempts"] = [
        _attempt("case_based_preview", correct=1),
        _attempt("memory_check", correct=1),
        _attempt("adaptive-quiz", correct=1),
        _attempt("final-boss", correct=1),
    ]
    debrief = await RE.finalize("s1", "hw1", ["Men ko'p narsa o'rgandim."])

    # The persisted report IS the debrief, and `verdict` is a TOP-LEVEL key.
    assert patch_repos["stored"] is not None
    assert "verdict" in patch_repos["stored"]
    assert patch_repos["stored"]["verdict"] == debrief["verdict"]
    assert debrief["verdict"] in (RE.VERDICT_PASSED, RE.VERDICT_NEEDS_RETRY)


@pytest.mark.asyncio
async def test_finalize_response_matches_the_fe_contract_shape(patch_repos):
    patch_repos["attempts"] = [_attempt("final-boss", correct=1)]
    debrief = await RE.finalize("s1", "hw1", [])
    for key in (
        "verdict", "verdict_label", "overall_pct", "band", "divisions",
        "weak_points", "strong_points", "next_steps", "narrative",
        "encouragement", "redo_recommendation", "mistake_repairs", "ai_unavailable",
    ):
        assert key in debrief, f"missing contract key: {key}"
    assert isinstance(debrief["divisions"], list)
    # divisions always lists the four canonical keys.
    assert {d["key"] for d in debrief["divisions"]} == {"cbp", "mc", "practice", "boss"}


@pytest.mark.asyncio
async def test_finalize_writes_completed_status_on_pass(patch_repos):
    patch_repos["attempts"] = [
        _attempt("adaptive-quiz", correct=1),
        _attempt("final-boss", correct=1),
    ]
    await RE.finalize("s1", "hw1", [])
    # The session UPDATE carried 'completed' as the status param on a pass.
    assert patch_repos["session_writes"], "expected a sessions UPDATE"
    _sql, params = patch_repos["session_writes"][0]
    assert params[0] == "completed"


@pytest.mark.asyncio
async def test_finalize_writes_needs_retry_status_on_fail(patch_repos):
    # Boss never beaten → needs_retry regardless of pct.
    patch_repos["attempts"] = [
        _attempt("adaptive-quiz", correct=1),
        _attempt("final-boss", correct=0, score=0.1),
    ]
    await RE.finalize("s1", "hw1", [])
    _sql, params = patch_repos["session_writes"][0]
    assert params[0] == "needs_retry"


# ── AI FALLBACK ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_finalize_returns_valid_debrief_when_ai_unavailable(patch_repos):
    patch_repos["attempts"] = [_attempt("final-boss", correct=1)]
    patch_repos["ai_raises"] = RuntimeError("no provider")
    debrief = await RE.finalize("s1", "hw1", [])
    assert debrief["ai_unavailable"] is True
    # Still a structurally-valid, non-empty debrief.
    assert debrief["narrative"]
    assert isinstance(debrief["next_steps"], list) and debrief["next_steps"]
    # Verdict is still deterministic, unaffected by AI being down.
    assert debrief["verdict"] in (RE.VERDICT_PASSED, RE.VERDICT_NEEDS_RETRY)


@pytest.mark.asyncio
async def test_finalize_flags_ai_unavailable_on_prompt_too_large(patch_repos):
    patch_repos["attempts"] = [_attempt("final-boss", correct=1)]
    patch_repos["ai_raises"] = RE.ai_orchestrator.PromptTooLargeError(size=999, cap=10)
    debrief = await RE.finalize("s1", "hw1", [])
    assert debrief["ai_unavailable"] is True


# ── ANSWER-LEAK GUARD ───────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_debrief_never_contains_keyword_anchors_or_expected_answers(patch_repos):
    # Seed the metrics with topic anchors + put a "secret expected" in attempts.
    patch_repos["metrics"] = {
        "weak_topics": ["SECRET_WEAK_KEYWORD"],
        "strong_topics": ["SECRET_STRONG_KEYWORD"],
    }
    patch_repos["attempts"] = [
        {
            **_attempt("adaptive-quiz", correct=0, qid="q1"),
            "answer_spec_json": '{"expected": "SECRET_EXPECTED_ANSWER"}',
            "student_answer": "SECRET_RAW_ANSWER",
        },
        _attempt("final-boss", correct=1),
    ]
    # AI must not echo the anchors — emulate a well-behaved model.
    debrief = await RE.finalize("s1", "hw1", [])

    import json
    blob = json.dumps(debrief, ensure_ascii=False)
    assert "SECRET_WEAK_KEYWORD" not in blob
    assert "SECRET_STRONG_KEYWORD" not in blob
    assert "SECRET_EXPECTED_ANSWER" not in blob
    assert "SECRET_RAW_ANSWER" not in blob
    # No answer-spec / rubric keys leak into the response.
    assert "answer_spec_json" not in blob
    assert "weak_point_keywords" not in blob
    assert "rubric" not in blob


@pytest.mark.asyncio
async def test_keyword_anchors_ride_into_the_prompt_only(patch_repos):
    patch_repos["metrics"] = {"weak_topics": ["anchor-term"], "strong_topics": []}
    patch_repos["attempts"] = [_attempt("final-boss", correct=1)]
    await RE.finalize("s1", "hw1", [])
    # The anchor reached the AI via the prompt (build_input_section is mocked to
    # a stub, so we assert it was at least called by checking a prompt was sent).
    assert patch_repos["ai_prompts"], "AI prompt was never built"


# ── GET ─────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_debrief_returns_persisted_report(patch_repos):
    patch_repos["attempts"] = [_attempt("final-boss", correct=1)]
    await RE.finalize("s1", "hw1", [])
    got = await RE.get_debrief("s1", "hw1")
    assert got is not None
    assert got["verdict"] == patch_repos["stored"]["verdict"]


@pytest.mark.asyncio
async def test_get_debrief_returns_none_when_not_finalized(patch_repos):
    # Nothing finalized yet.
    assert await RE.get_debrief("s-none", "hw-none") is None


# ── REDO ────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_redo_flips_status_to_active(patch_repos):
    result = await RE.redo("s1", "hw1")
    assert result["ok"] is True
    assert result["reshuffled"] is True
    # A sessions UPDATE set status = 'active'.
    update_sqls = [sql for sql, _ in patch_repos["session_writes"]]
    assert any("status = 'active'" in " ".join(s.split()) for s in update_sqls)


@pytest.mark.asyncio
async def test_redo_clears_only_division_three_phases(patch_repos):
    await RE.redo("s1", "hw1")
    # The DELETE targeted the Division-3 phase strings, scoped to session + hw.
    params = patch_repos["deleted_phases"]
    assert params is not None
    assert params[0] == "s1"
    assert params[1] == "hw1"
    deleted_phase_set = set(params[2:])
    # Division-3 phases are deleted; CBP + MC are NOT in the delete set.
    assert "final-boss" in deleted_phase_set
    assert "adaptive-quiz" in deleted_phase_set
    assert "case_based_preview" not in deleted_phase_set
    assert "memory_check" not in deleted_phase_set
