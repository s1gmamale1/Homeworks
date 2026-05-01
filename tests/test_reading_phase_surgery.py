"""Regression tests for the Reading phase template surgery (Bug #3).

Pins the invariants that make the phase work the way the user actually wants:

  - The passage is no longer chunked into a stream of 16 micro-pages.
    Content_json declares N explicit segments; the runtime renders them
    alternating with N checkpoints (segment → question → segment → question).

  - The "Davom etish uchun savolga javob bering" lock message only appears
    on a question panel that's still unanswered. Text-segment panels never
    show it; an all-done state hides it.

  - The Keyingi button is removed for segment-aware panels. The student
    advances text panels via swipe-left and question panels via auto-
    advance after a correct answer.

  - The edge-swipe phase-skip gesture (hard swipe inward from the very
    left or right edge) bypasses the question-answer lock. The student
    has explicitly asked to leave the reading phase, so unanswered
    checkpoints don't gate that exit.

  - Legacy fixtures (passage as one text blob + parallel checkpoints
    array, no segments[]) still render via the existing chunker so old
    homework rows don't break.

If any of these invariants regress, the user's reading-phase bug returns.
Each test is named after the regression it guards.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

TEMPLATE_PATH = Path(__file__).resolve().parent.parent / "server" / "template" / "perfect_homework.html"
TEMPLATE = TEMPLATE_PATH.read_text(encoding="utf-8")


def _slice_function(name: str) -> str:
    """Return the source slice for a JS `function name(...)` block.

    Cuts from the function header to the next top-level `function ` keyword.
    Good enough for invariant grepping — we don't need a proper JS parser.
    """
    start = TEMPLATE.find(f"function {name}(")
    assert start != -1, f"function {name} not found in template"
    # Find the next function declaration after this one
    after = TEMPLATE.find("\n        function ", start + 1)
    if after == -1:
        after = len(TEMPLATE)
    return TEMPLATE[start:after]


# ---- Invariant 1: segment-aware renderer is wired -------------------------

def test_reading_build_pages_accepts_segments_argument():
    """readingBuildPages(rawPassage, segments) — segments arg is the new contract."""
    body = _slice_function("readingBuildPages")
    assert "readingBuildPages(rawPassage, segments)" in body, (
        "readingBuildPages must accept the segments[] argument so the segment-aware "
        "code path activates when content_json declares them"
    )


def test_reading_build_pages_emits_alternating_text_question_pages_for_segments():
    """N segments produce 2N pages alternating kind:'text' → kind:'question'."""
    body = _slice_function("readingBuildPages")
    assert "Array.isArray(segments) && segments.length" in body
    assert "kind: 'text'" in body
    assert "kind: 'question', cpIndex: i" in body, (
        "each segment's checkpoint panel must reference its index explicitly so "
        "the renderer knows which checkpoint goes on which page"
    )


def test_reading_build_pages_falls_back_to_legacy_chunker_when_no_segments():
    """Old fixtures (no segments[]) still render via chunker → kind:'legacy' pages."""
    body = _slice_function("readingBuildPages")
    assert "kind: 'legacy', html" in body, (
        "legacy chunker output must be tagged kind:'legacy' so renderReading can "
        "tell it apart from segment-aware text panels and apply the geometric "
        "checkpoint distribution"
    )


# ---- Invariant 2: lock message is scoped to unanswered question panels ----

def test_reading_lock_message_does_not_render_on_text_segment_panels():
    """`reading.must_answer` only renders when pageNeedsAnswer is true."""
    body = _slice_function("updateReadingContinueState")
    # The whole guarded scope must be present
    assert "pageNeedsAnswer" in body
    assert "currentPage.kind === 'question'" in body
    assert "currentPage.kind === 'legacy'" in body
    # The message is inside an `if (pageNeedsAnswer)` branch — meaning text panels
    # (where pageNeedsAnswer stays false) skip it. Catch any unconditional set.
    must_answer_uses = re.findall(r"reading\.must_answer", body)
    assert len(must_answer_uses) == 1, (
        "must_answer should be referenced exactly once inside the pageNeedsAnswer "
        "branch — multiple references suggest it's still being set unconditionally"
    )


# ---- Invariant 3: Keyingi button removed for segment-aware panels ---------

def test_reading_per_checkpoint_next_button_rendered_only_in_legacy_mode():
    """The per-checkpoint manual Next button is gated on legacy chunker pages."""
    body = _slice_function("renderReading")
    assert re.search(
        r"if\s*\(\s*currentPage\.kind\s*===\s*'legacy'\s*\)\s*\{[^}]*?nextBtn\s*=\s*document\.createElement",
        body, flags=re.DOTALL,
    ), "per-checkpoint nextBtn must be rendered only when currentPage.kind is 'legacy'"


def test_reading_bottom_page_nav_rendered_only_in_legacy_mode():
    """The bottom prev/next page-nav row is gated on legacy chunker pages."""
    body = _slice_function("renderReading")
    # The bottom nav block (with prev/next page buttons) must be inside an
    # `if (currentPage.kind === 'legacy')` guard, not unconditional.
    legacy_guards = re.findall(r"currentPage\.kind\s*===\s*'legacy'", body)
    assert len(legacy_guards) >= 2, (
        "expected at least 2 'currentPage.kind === \"legacy\"' guards in renderReading "
        "(one for per-checkpoint nextBtn, one for the bottom page-nav row); "
        f"found {len(legacy_guards)}"
    )


# ---- Invariant 4: auto-advance after correct answer -----------------------

def test_reading_correct_answer_auto_advances_on_question_panel():
    """A correct answer on a question panel triggers a setTimeout-driven advance."""
    body = _slice_function("renderReading")
    # Pattern: `if (isCorrect && isQuestionPanel) { setTimeout(...) }`
    assert re.search(
        r"if\s*\(\s*isCorrect\s*&&\s*isQuestionPanel\s*\)\s*\{[^}]*setTimeout",
        body, flags=re.DOTALL,
    ), (
        "auto-advance must be gated on (isCorrect && isQuestionPanel) and use "
        "setTimeout — direct synchronous advance would cut off the feedback line"
    )


# ---- Invariant 5: edge-swipe phase-skip bypasses the answer lock ----------

def test_reading_edge_swipe_calls_oncontinue_with_force_true():
    """skipCurrentPhase for stage 4.7 invokes readingState.onContinue(true)."""
    body = _slice_function("skipCurrentPhase")
    assert "s === 4.7" in body
    assert "readingState.onContinue(true)" in body, (
        "edge-swipe phase-skip on Reading must call onContinue(true) to bypass "
        "the readingIsComplete() check inside finishReading. Without `true`, the "
        "skip gesture fails on any unanswered checkpoint and the user is stuck."
    )


def test_reading_finish_function_accepts_force_param_to_bypass_completion_check():
    """finishReading(force) — force=true skips the readingIsComplete guard."""
    # finishReading is defined inside showReadingScreen as a const arrow fn,
    # not at top level — so search the whole template, not via _slice_function.
    assert "const finishReading = (force) =>" in TEMPLATE, (
        "finishReading must accept the `force` parameter for edge-swipe phase-skip"
    )
    # The guard line: `if (!force && !readingIsComplete(...))` — force bypasses it.
    assert re.search(
        r"if\s*\(\s*!force\s*&&\s*!readingIsComplete",
        TEMPLATE,
    ), (
        "the readingIsComplete guard must be wrapped in `!force && ...` so "
        "force=true skips it"
    )


# ---- Invariant 6: within-phase swipe-left advances reading panels ---------

def test_reading_swipe_handler_does_not_block_non_edge_swipes_on_stage_4_7():
    """Stage 4.7 (Reading) is excluded from the wave-2 no-swipe filter."""
    # Pre-fix the comparison was `state.stage === 4.7 || state.stage === 6.5 || state.stage === 7.7`
    # and any non-edge swipe on 4.7 returned early. Post-fix Reading is removed
    # from that exclusion list.
    assert "isInterstitialNoSwipe = state.stage === 6.5 || state.stage === 7.7" in TEMPLATE, (
        "Reading (4.7) must NOT be in the no-non-edge-swipe interstitial list — "
        "it now accepts within-phase swipe-left for panel advance"
    )


def test_reading_swipe_left_advances_panel_when_unlocked():
    """Pointerup on stage 4.7 with leftward dx >= threshold advances the panel."""
    # The new branch checks `state.stage === 4.7`, computes isLockedQuestion,
    # and either advances via readingGoToPage or calls onContinue.
    assert re.search(
        r"absDx\s*>\s*50\s*&&\s*state\.stage\s*===\s*4\.7",
        TEMPLATE,
    ), "pointerup must dispatch a stage-4.7 branch for within-phase swipes"
    assert "isLockedQuestion =" in TEMPLATE
    assert "readingGoToPage(readingState.page + 1)" in TEMPLATE


def test_reading_swipe_left_blocked_by_unanswered_checkpoint():
    """A leftward swipe on a question panel with no answer yet is a no-op."""
    # The isLockedQuestion check must gate the readingGoToPage(advance) call.
    assert re.search(
        r"isLockedQuestion\s*=\s*\n?\s*currentPage\.kind\s*===\s*'question'\s*&&\s*\n?"
        r"\s*typeof\s+currentPage\.cpIndex\s*===\s*'number'\s*&&\s*\n?"
        r"\s*!readingState\.answered\[currentPage\.cpIndex\]",
        TEMPLATE,
    ), (
        "isLockedQuestion must be true exactly when the current panel is a "
        "question panel whose checkpoint hasn't been answered yet"
    )


# ---- Invariant 7: backward-compat for legacy READING shape ----------------

def test_reading_legacy_passage_field_still_consumed():
    """The legacy `passage` (or `text`) field is still read when segments is absent."""
    body = _slice_function("renderReading")
    assert "READING.passage || READING.text" in body, (
        "legacy fixtures use READING.passage or READING.text — those must still "
        "be the source for the chunker-fallback path"
    )


def test_reading_legacy_geometric_checkpoint_distribution_still_used():
    """Legacy chunker pages still get checkpoints geometrically distributed."""
    body = _slice_function("renderReading")
    assert "readingCheckpointPage(i, readingState.pages.length, checkpoints.length)" in body, (
        "legacy mode falls back to the existing geometric checkpoint→page mapping; "
        "removing this would break old homework rows that don't have segments[]"
    )


# ---- Injector pass-through (Bug #3 server-side fix) -----------------------

def _inject_reading(reading_payload):
    """Helper: run inject() with a content_json carrying just `reading` + `meta`,
    return the resulting `const READING = {...};` text."""
    from server.services.injector import inject
    cj = {
        "meta": {"title": "T", "subject_display": "english", "section": "", "cefr_level": "B1"},
        "gate_quote": {"mode": "auto"},
        "panels": [], "flashcards": [], "memory_sprint": [],
        "gb_adaptive_quiz": [], "gb_why_chain": [], "gb_memory_match": [],
        "gb_puzzle_lock": [], "gb_mystery_box": [], "gb_ttt": [],
        "boss_questions": [],
        "real_life": {}, "consolidation": {}, "reflection": {},
        "reading": reading_payload,
    }
    html = inject(cj, runtime_context={"lang": "uz", "subject": "english", "grade": 8, "hwId": "X", "homeworkSummary": ""})
    import re
    m = re.search(r"const READING\s*=\s*(\{.*?\});", html, flags=re.DOTALL)
    assert m, "const READING block not found in injected HTML"
    return m.group(1)


def test_injector_passes_segments_through_to_reading_const():
    """The new segments[] array survives injection into READING JS const."""
    src = _inject_reading({
        "title": "T",
        "passage": "<p>seg1</p><p>seg2</p>",
        "segments": [
            {"text": "<p>seg1</p>"},
            {"text": "<p>seg2</p>"},
        ],
        "checkpoints": [
            {"prompt": "Q1?", "ans": "a", "fb": ""},
            {"prompt": "Q2?", "ans": "b", "fb": ""},
        ],
    })
    assert '"segments":' in src, "injector must pass `segments` through; without it the runtime falls back to the chunker and the bug returns"
    # _safe_js_json escapes `</` to `<\/` to keep the const safe inside <script>;
    # check segment markers via their unique text token instead of the raw HTML.
    assert "seg1" in src and "seg2" in src


def test_injector_passes_media_through_to_reading_const():
    """The reading context-picture SVG survives injection."""
    src = _inject_reading({
        "title": "T",
        "passage": "<p>x</p>",
        "media": {"type": "svg", "html": "<svg id='ctx-pic'></svg>"},
        "checkpoints": [],
    })
    assert '"media":' in src, "injector must pass `media` through to READING"
    assert "ctx-pic" in src


def test_injector_splits_list_ans_into_ans_plus_acceptable():
    """When the adapter ships ans as a list, head→ans, tail→acceptable[]."""
    src = _inject_reading({
        "title": "T",
        "passage": "<p>x</p>",
        "checkpoints": [
            {"prompt": "How many?", "ans": ["seven", "7", "Seven"], "fb": ""},
        ],
    })
    # Canonical ans is the first element
    assert '"ans":' in src and '"seven"' in src
    # Tail elements migrate to `acceptable[]`
    assert '"acceptable":' in src
    assert '"7"' in src and '"Seven"' in src


def test_injector_keeps_legacy_string_ans_unchanged():
    """An old fixture with ans-as-string still gets ans:"..." in the output."""
    src = _inject_reading({
        "title": "T",
        "passage": "<p>x</p>",
        "checkpoints": [
            {"prompt": "Q?", "ans": "single answer", "fb": ""},
        ],
    })
    assert '"ans":' in src
    assert '"single answer"' in src


def test_injector_omits_segments_key_when_no_segments_authored():
    """Legacy fixtures (no segments[] in content_json) don't get a stray segments:[] in const."""
    src = _inject_reading({
        "title": "T",
        "passage": "<p>x</p>",
        "checkpoints": [{"prompt": "Q?", "ans": "a", "fb": ""}],
    })
    assert '"segments"' not in src, (
        "injector should NOT emit a `segments` key when content_json has none — "
        "otherwise the runtime's `Array.isArray(READING.segments)` check fires "
        "with an empty array, suppressing the chunker fallback for legacy data"
    )
