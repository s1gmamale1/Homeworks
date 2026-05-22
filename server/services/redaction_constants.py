"""Single source of truth for answer-bearing field names.

Both the legacy injector (`injector.py`) and the React hydration redactor
(`runtime_redactor.py`) import from here so they CANNOT drift. Adding a new
answer-bearing field to the schema means adding it here once.

The whole point: the student's browser must never receive the grading key for
any gated question. Grading is server-side (POST /api/ai/check-answer etc.);
post-submit feedback comes from the interaction-endpoint *response*, never the
hydration payload.
"""

# ---- Per-game server-only fields (the injector's historical deny-lists) ----
TM_SERVER_ONLY = frozenset({"explanation"})                       # tile-match
SF_SERVER_ONLY = frozenset({"answers", "explanations"})           # sentence-fill
RLC_SERVER_ONLY = frozenset({"is_correct", "consequence", "acceptable_keywords"})  # real-life-challenge
BOSS_SERVER_ONLY = frozenset({"accepted", "ans", "accepted_answers", "answer_spec"})  # boss

# ---- Global answer-bearing keys stripped at EVERY nesting level ----
# Union of the per-game sets + the deterministic-grading contract fields +
# the v2 (CBP / Memory Check) answer fields. Fail-closed: the entire
# `answer_spec` subtree is deleted wholesale wherever it appears, so any NEW
# field added inside answer_spec later is gone automatically.
ANSWER_BEARING_KEYS = frozenset(
    {
        # answer_spec contract (content.py AnswerSpec)
        "answer_spec",
        "expected",
        "accepted_answers",
        "accepted",
        "ans",
        "correct",
        "option_index",
        "canonical_display",
        "tolerance",
        "allow_ai_fallback",
        # deterministic / grading aliases
        "is_correct",
        "acceptable_keywords",
        "solution",
        "solution_text",
        "rubric",
        "matched_expected",
        # per-game server-only
        "explanation",
        "explanations",
        "answers",
        "consequence",
        # v2 case-based preview / memory-check answer-revealing fields
        "correct_path",
        "correct_answer",
        "correct_option",
        # CBP teaching text — post-submit only (returned by /check-answer
        # response in ai.py); never in hydration.
        "learning_block",
        # CBP "Decision Process Explanation" — open-ended AI-graded reasoning
        # step. The keyword buckets + pass_score are server-only grading anchors;
        # the recursive _scrub strips them inside decision_process_explanation so
        # hydration exposes ONLY `prompt` + `min_chars`. (`acceptable_keywords` +
        # `rubric` are already deny-listed above.)
        "concept_keywords",
        "method_keywords",
        "mistake_keywords",
        "pass_score",
        # Boss-Arena authored grading anchor (spec §6) — the concept list the
        # answer-checker grades coverage against. Server-only; never hydrated.
        "expected_concepts",
        # Reflection "analysis" debrief — server-only grading config. The
        # student-visible debrief fields (narrative / weak_points / strong_points
        # / next_steps / redo_recommendation) SURVIVE hydration; only the rubric
        # + keyword buckets + pass_threshold are stripped. (content.py
        # ReflectionAnalysis.) `pass_threshold` is distinct from `pass_score`
        # above (the CBP reasoning anchor) — both are server-only.
        "analysis_rubric",
        "weak_point_keywords",
        "strong_point_keywords",
        "pass_threshold",
        # short answer aliases + invariants the grader keys on
        "a",
        "answer",
        "inv",
        "invariant",
        "expect",
        "expected_answer",
        "acceptable",
        "ans_all",
        # distractors enumerate the wrong options' grading metadata
        "distractors",
        # Practice Arc games (Ibo PR #248: Memory/Jigsaw Matching, Error
        # Detection, Assembly). Answer-side fields stripped at hydration.
        "expected_order",         # Assembly — solution sequence
        "is_broken",              # Error Detection — which work-block carries the error
        "correction",             # Error Detection — expected correction text
        # Division-3 Practices (per _DIV3_CONTRACT.md). Uniform MCQ key + the 4
        # new games' server-only grading keys. Stripped at every nesting depth.
        "correct_index",          # uniform MCQ checkpoint — index of the right option
        "expected_components",    # DPE grading anchor (sentence-repair / memory- & jigsaw-matching)
        "correction_answer_spec", # Error Detection — correction grading spec
        "meter_deltas",           # TTT-Grid — per-cell per-meter score impact
        "best_cell_id",           # TTT-Grid — the winning cell id
        "answer_case_id",         # Counterexample — the case that breaks the rule
        "breaks_rule",            # Counterexample — which rule the case breaks
        "final_answer",           # Problem-Trace — optional final answer
        # Division-3 Practices — 2 MORE games. (`correct_index` above already
        # covers both new games' MCQ keys.) `carry_label` is the only NEW
        # server-only field: it encodes a Dependency-Chain step's RESULT (e.g.
        # "x = 5 →") which is surfaced by the server ONLY after a correct answer,
        # so it must be stripped from hydration like any answer-bearing field.
        "carry_label",            # Dependency-Chain — a step's carried result token
    }
)
