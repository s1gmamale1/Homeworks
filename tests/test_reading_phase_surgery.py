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

_JS_PATH = Path(__file__).resolve().parent.parent / "server" / "template" / "js" / "perfect_homework.js"
_CSS_PATH = Path(__file__).resolve().parent.parent / "server" / "template" / "static" / "css" / "perfect_homework.css"
_HTML_PATH = Path(__file__).resolve().parent.parent / "server" / "template" / "perfect_homework.html"
TEMPLATE = _HTML_PATH.read_text(encoding="utf-8") + "\n" + _JS_PATH.read_text(encoding="utf-8") + "\n" + _CSS_PATH.read_text(encoding="utf-8")


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
    """Per Bug #2 — segments with a checkpoint now emit ONE combined
    `kind:'segment_with_question'` page (passage on top, question below
    in the same panel) instead of two separate pages.

    Segments without a checkpoint still emit a plain `kind:'text'` page.
    Either way the cpIndex must be explicit on the page object so the
    renderer can grab the right checkpoint."""
    body = _slice_function("readingBuildPages")
    assert "Array.isArray(segments) && segments.length" in body
    assert "kind: 'text'" in body
    # Combined page kind for segment-with-checkpoint, with an explicit
    # cpIndex so the renderer knows which checkpoint belongs to which page.
    assert "kind: 'segment_with_question'" in body, (
        "segments with a checkpoint must emit a combined "
        "kind:'segment_with_question' page (Bug #2 fix)"
    )
    assert "cpIndex: i" in body, (
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


# ---- Invariant 3: Keyingi button — created in both modes, gated reveal ----
#
# Contract change (PR #231): the per-checkpoint manual Next button is now
# created UNCONDITIONALLY for both modes. The old design ("nextBtn only when
# mode === 'legacy'") stranded students in segment mode on a wrong answer —
# auto-advance only fires on correct, and the wrong-answer branch left them
# with the verdict on screen and no visible advance affordance.
#
# New contract:
#   - nextBtn always exists (created unconditionally, hidden by default)
#   - Revealed when (mode === 'legacy' || !isCorrect) — i.e. legacy mode
#     always, or segment-mode-wrong-answer as an escape hatch
#   - Correct + segment still auto-advances at 1.1s; button being also
#     visible during that 1.1s is harmless (click triggers same advance)


def test_reading_per_checkpoint_next_button_created_unconditionally():
    """The Next button must be created for BOTH modes — no `if (mode === 'legacy')`
    gate around the createElement call. Pre-fix that gate left segment-mode
    wrong-answer panels with no manual advancer at all (HW-20260514-007 repro).
    """
    body = _slice_function("_buildReadingCheckpointBlock")
    # The old broken gate must be gone.
    bad = re.search(
        r"if\s*\(\s*mode\s*===\s*'legacy'\s*\)\s*\{[^}]*?nextBtn\s*=\s*document\.createElement",
        body, flags=re.DOTALL,
    )
    assert bad is None, (
        "_buildReadingCheckpointBlock must NOT gate nextBtn creation on "
        "mode === 'legacy'. That's the regressed bug — segment-mode wrong "
        "answers had no button at all. Create the button unconditionally; "
        "gate visibility instead."
    )
    # And the new unconditional creation must be present.
    assert re.search(
        r"const\s+nextBtn\s*=\s*document\.createElement\(\s*['\"]button['\"]\s*\)",
        body,
    ), (
        "_buildReadingCheckpointBlock must create nextBtn unconditionally "
        "(`const nextBtn = document.createElement('button')`) so the same "
        "DOM node can be hidden/shown by the gate logic below."
    )


def test_reading_segment_mode_reveals_next_button_on_wrong_answer():
    """Segment mode + wrong answer: nextBtn must be revealed inside the
    check handler so the student can advance manually after reading the
    feedback. Auto-advance only fires for correct answers in segment mode,
    so this is the escape hatch that fixes the user-reported stranded
    state on HW-20260514-007.
    """
    body = _slice_function("_buildReadingCheckpointBlock")
    # The reveal condition: `if (mode === 'legacy' || !isCorrect) nextBtn.style.display = ''`
    assert re.search(
        r"if\s*\(\s*mode\s*===\s*'legacy'\s*\|\|\s*!isCorrect\s*\)\s*\{"
        r"\s*nextBtn\.style\.display\s*=\s*['\"]['\"]",
        body, flags=re.DOTALL,
    ), (
        "_buildReadingCheckpointBlock must reveal nextBtn inside "
        "`if (mode === 'legacy' || !isCorrect)`. Without the `|| !isCorrect` "
        "clause, segment-mode wrong answers regress to the stranded state."
    )


def test_reading_no_bottom_page_nav_in_segment_mode():
    """Post-wave2 the bottom prev/next page-nav row is gone entirely.

    Pre-wave2 each chunker page rendered a `screen-reading-btn-row` with a
    Back button + a `pageNextBtn`. Now the wave2 stream + dot indicator
    handle navigation via swipe; no bottom nav buttons exist anywhere in
    the renderReading function.
    """
    body = _slice_function("renderReading")
    assert "pageNextBtn" not in body, (
        "renderReading must NOT create pageNextBtn anymore — wave2 swipe "
        "navigation replaces the bottom page-nav row"
    )


# ---- Invariant 4: auto-advance after correct answer -----------------------

def test_reading_correct_answer_auto_advances_in_segment_mode():
    """A correct answer in segment mode auto-advances via wave2SlideNavigate.

    The auto-advance path now lives inside `_buildReadingCheckpointBlock`'s
    checkBtn handler, gated on (isCorrect && mode === 'segment'), and calls
    wave2SlideNavigate on the reading-stream after a 1100ms beat.
    """
    body = _slice_function("_buildReadingCheckpointBlock")
    assert re.search(
        r"if\s*\(\s*isCorrect\s*&&\s*mode\s*===\s*'segment'\s*\)\s*\{[^}]*setTimeout",
        body, flags=re.DOTALL,
    ), (
        "auto-advance must be gated on (isCorrect && mode === 'segment') and "
        "use setTimeout for the read-the-feedback beat"
    )
    assert "wave2SlideNavigate('reading-stream', +1)" in body, (
        "auto-advance must dispatch through the wave2 helper, not call any "
        "internal go-to-page function directly"
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
    """Stage 4.7 (Reading) AND 6.5 (Consolidation) accept non-edge swipes.

    Post-Bug-#7: both are removed from the interstitial-no-swipe list and
    the only remaining "edge-only" Wave-2 stage is 7.7 (Reflection).
    """
    assert "isInterstitialNoSwipe = state.stage === 7.7" in TEMPLATE, (
        "only Reflection (7.7) should be in the interstitial-no-swipe filter; "
        "Reading (4.7) and Consolidation (6.5) both run wave2 streams now"
    )


def test_reading_swipe_dispatches_to_wave2_helper():
    """Pointerup on stage 4.7 calls wave2SlideNavigate with ±1.

    The bespoke isLockedQuestion / readingGoToPage path is replaced by a
    single `wave2SlideNavigate('reading-stream', dir)` call. The helper's
    canAdvance hook (declared inside renderReading) handles the question
    lock; we don't repeat that logic at the swipe-handler level.
    """
    assert re.search(
        r"absDx\s*>\s*50\s*&&\s*state\.stage\s*===\s*4\.7",
        TEMPLATE,
    ), "pointerup must still dispatch a stage-4.7 branch"
    assert "wave2SlideNavigate('reading-stream'," in TEMPLATE, (
        "Reading swipe handling must route through wave2SlideNavigate so the "
        "shared helper owns the slide animation + dot updates"
    )


def test_reading_can_advance_hook_blocks_unanswered_question_panels():
    """canAdvance returns false when leaving an unanswered question panel.

    The lock invariant (no skipping a question without answering it) is
    moved out of the swipe handler and into the canAdvance callback the
    consumer passes to wave2SlideInit.
    """
    body = _slice_function("renderReading")
    # canAdvance hook is registered with the helper
    assert "canAdvance:" in body
    # The hook reads from readingState.pages[fromIdx] and gates on
    # !readingState.answered[fromPage.cpIndex] for question panels.
    assert "fromPage.kind === 'question'" in body
    assert "!readingState.answered[fromPage.cpIndex]" in body, (
        "canAdvance must return false when the current question panel's "
        "checkpoint hasn't been answered — that's the lock invariant"
    )
    # Back-swipe (toIdx < fromIdx) must be unconditionally allowed.
    assert "if (toIdx < fromIdx) return true" in body, (
        "canAdvance must allow back-swipe unconditionally (toIdx < fromIdx); "
        "the lock only gates forward motion"
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
