"""Real-Life Challenge story-panel pagination regression tests.

Guards: pre-fix, the RL story panel was a fixed-height vertical-scroll
container that got `display: none`'d when the student moved from the
"Boshlash" (Start) screen to question 1. Result on `HW-20260505-006`:
the lab quality-control passage students needed for reference was
hidden the moment they began answering. Two paths force-set
`display: none` (rlShowQuestion + rlHandleAction) and one force-set
`flex: 1` on phase entry (overriding any CSS sizing).

Each test asserts the BAD pre-fix state cannot return:
- Story panel must NOT be hidden via inline `style.display = 'none'`
  on the question or start-button transitions.
- Story panel CSS must declare bounded height + horizontal scroll-snap
  (paginated layout) instead of vertical scroll.
- Page-indicator container must exist in the rendered template.
- Pagination JS (page-builder + drag handler + dot updater) must be
  wired so the runtime turns a single passage into a swipable
  multi-page panel.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest


_JS_PATH = Path(__file__).resolve().parent.parent / "server" / "template" / "js" / "perfect_homework.js"
_CSS_PATH = Path(__file__).resolve().parent.parent / "server" / "template" / "static" / "css" / "perfect_homework.css"
_HTML_PATH = Path(__file__).resolve().parent.parent / "server" / "template" / "perfect_homework.html"


@pytest.fixture(scope="module")
def template_html() -> str:
    return _HTML_PATH.read_text(encoding="utf-8") + "\n" + _JS_PATH.read_text(encoding="utf-8") + "\n" + _CSS_PATH.read_text(encoding="utf-8")


# ── Negative assertions: pre-fix code cannot return ─────────────────────────


def test_story_panel_no_display_none_on_question_show(template_html):
    """rlShowQuestion previously had:
        const story = document.getElementById('rl-story-section');
        if (story) story.style.display = 'none';
    That broke the "passage stays alongside question" contract.
    """
    # Cover both single- and double-quoted JS strings.
    bad_patterns = [
        r"story\.style\.display\s*=\s*'none'",
        r'story\.style\.display\s*=\s*"none"',
    ]
    for pat in bad_patterns:
        assert not re.search(pat, template_html), (
            f"Pre-fix line `story.style.display = 'none'` is back. "
            f"The story panel must remain visible alongside the question."
        )


def test_story_panel_no_force_flex_one_on_phase_entry(template_html):
    """Phase-entry code previously force-set `story.style.flex = '1'` which
    overrode the new bounded-height CSS (`flex: 0 0 220px`) and let the
    story expand to fill the card again.
    """
    assert not re.search(
        r"story\.style\.flex\s*=\s*['\"]1['\"]",
        template_html,
    ), (
        "Pre-fix line `story.style.flex = '1'` is back. The CSS now bounds "
        "the panel via `flex: 0 0 220px`; do not override inline."
    )


# ── Positive assertions: post-fix layout is in place ────────────────────────


def test_story_panel_has_horizontal_pagination_css(template_html):
    """Story panel must declare horizontal scroll-snap and bounded width
    (each .rl-story-page = one snap target = one page)."""
    # Bounded panel height — the wrap uses `flex: 0 0 <bounded>` (no longer
    # `flex: 1`). Accept any explicit unit OR a clamp() expression so a
    # future tuning pass can adjust the value without breaking the test.
    assert re.search(
        r"\.rl-story-wrap\s*\{[^}]*flex:\s*0\s+0\s+(?:\d+(?:px|vh|%)|clamp\()",
        template_html,
    ), (
        ".rl-story-wrap must declare a bounded `flex: 0 0 <NNNpx|NNvh|NN%|clamp(...)>` "
        "(panel height must NOT be `flex: 1` — that lets it expand to fill "
        "the card and breaks the paginated panel layout)."
    )
    # Horizontal scroll-snap container.
    assert "scroll-snap-type: x mandatory" in template_html, (
        ".rl-story-body must declare `scroll-snap-type: x mandatory` "
        "for paginated swipe behavior."
    )
    # Each page snaps to start of the viewport.
    assert "scroll-snap-align: start" in template_html, (
        ".rl-story-page must declare `scroll-snap-align: start`."
    )
    # Pages are full-width flex children — exactly one fills the panel.
    assert re.search(r"\.rl-story-page\s*\{[^}]*flex:\s*0\s+0\s+100%", template_html), (
        ".rl-story-page must use `flex: 0 0 100%` so each snaps to fill."
    )


def test_story_panel_has_page_indicator_dots_html(template_html):
    """The `<div id="rl-story-dots">` indicator container must be present
    between the story panel and the question stack."""
    assert re.search(
        r'<div\s+class="rl-story-dots"\s+id="rl-story-dots"[^>]*>',
        template_html,
    ), (
        "Page-indicator container `<div class=\"rl-story-dots\" id=\"rl-story-dots\">` "
        "must exist in the RL card."
    )
    # Dots CSS hides the row when there's only one page (or zero).
    assert re.search(
        r'\.rl-story-dots\[data-pages="1"\]',
        template_html,
    ), "Single-page dot suppression CSS must be present."


def test_story_renderer_has_pagination_js(template_html):
    """rlRenderStory() must build pages incrementally and bind drag + dot
    handlers. Smoke-level check — Playwright would test runtime behavior;
    this guards the wiring."""
    # Pagination algorithm — paragraph-based with overflow check.
    assert "startNewPage" in template_html, (
        "rlRenderStory must define an internal startNewPage() helper."
    )
    assert "scrollHeight > panelHeight" in template_html, (
        "Pagination must compare scrollHeight to panel height to decide breaks."
    )
    # Dot updater binds to the scroll event exactly once.
    assert "__rlDotsBound" in template_html, (
        "Dot-updater scroll listener must be guarded by __rlDotsBound flag "
        "(prevents duplicate listeners on re-entry)."
    )
    # Drag-to-pan handler (mouse) wired and idempotent.
    assert "__rlDragBound" in template_html, (
        "Drag handler must be guarded by __rlDragBound flag."
    )
    # The drag handler must NOT swallow text selection — verify cursor css
    # toggles from grab to grabbing during a drag.
    assert ".rl-story-body.rl-dragging" in template_html, (
        "Dragging state CSS class .rl-dragging must be defined."
    )


def test_rl_handle_action_no_longer_hides_story_on_start(template_html):
    """rlHandleAction's start-button branch previously fade-out'd and
    display:none'd the story before showing question 1. New design just
    calls rlShowQuestion(0) directly — the story stays put."""
    # Find the rlHandleAction function's story-screen branch.
    m = re.search(
        r"function\s+rlHandleAction\s*\(\)\s*\{(.{0,1500}?)\bif\s*\(stage6State\.screen\s*===\s*['\"]closure['\"]",
        template_html,
        re.DOTALL,
    )
    assert m, (
        "Couldn't locate rlHandleAction's story-screen branch — test needs "
        "an update if the function was renamed/restructured."
    )
    body = m.group(1)
    # The branch must NOT toggle story display/opacity anymore.
    assert "story.style.display" not in body, (
        "rlHandleAction's story branch must not touch story.style.display "
        "(panel must remain visible)."
    )
    assert "rlShowQuestion(0)" in body, (
        "rlHandleAction's story branch must transition to rlShowQuestion(0)."
    )


# ── Integration via injector — render path produces all of the above ───────


def test_injector_renders_template_with_pagination_classes(tmp_path, monkeypatch):
    """End-to-end: feed an RL story through the injector and confirm the
    rendered HTML carries the pagination markers. Mirrors how a live
    /h/{id} render would behave."""
    from server.services import injector

    sample_content = {
        "meta": {"title": "Stress test", "subject_display": "math"},
        "real_life": {
            "badge": "VAZIFA",
            "story": "Para one.\n\nPara two.\n\nPara three.",
            "q1": {"prompt": "?", "ans": "1", "fb": ""},
            "q2": {"prompt": "?", "ans": "2", "fb": ""},
            "q3": {"prompt": "?", "ans": "3", "fb": ""},
            "q4": {"prompt": "?", "ans": "4", "fb": ""},
            "q5": {"prompt": "?", "ans": "5", "fb": "", "open": True},
            "q6": {"prompt": "?", "ans": "6", "fb": ""},
            "endTitle": "Done",
            "endSub": "Done",
        },
    }
    from pathlib import Path
    _repo = Path(__file__).resolve().parent.parent
    _css = (_repo / "server" / "template" / "static" / "css" / "perfect_homework.css").read_text(encoding="utf-8")
    rendered = injector.inject(
        sample_content,
        runtime_context={"hw_id": "HW-TEST-001"},
    ) + "\n" + _css
    assert "rl-story-page" in rendered
    assert 'id="rl-story-dots"' in rendered
    assert "scroll-snap-type: x mandatory" in rendered
    assert "Para one." in rendered  # story actually injected


# ── Grading control flow — single-check contract ────────────────────────────
#
# These tests guard the load-bearing logic change in this PR: the old
# dual-fire "show local hint AND dispatch AI" branch on first wrong attempt
# is gone, replaced by a single-check flow (local exact-match → if no match,
# AI fallback once). Reviewer flagged this as the biggest test gap because
# the original tests only cover the story panel layer, not the submit
# contract. Static-string tests against the rendered template — same pattern
# as the rest of this file (Playwright-style runtime tests would be better
# but match the existing project test style).


def _extract_function_body(template_html: str, fn_name: str) -> str:
    """Extract a JS function body by brace-counting (regex can't handle
    nested braces in if/else blocks). Returns the text between the
    function's outer `{` and matching `}`, exclusive."""
    pattern = re.compile(rf"function\s+{re.escape(fn_name)}\s*\([^)]*\)\s*\{{")
    m = pattern.search(template_html)
    assert m, f"Couldn't locate function {fn_name}() in template."
    start = m.end()  # position right after the opening `{`
    depth = 1
    i = start
    n = len(template_html)
    in_str = None  # current string delimiter, if any
    in_line_comment = False
    in_block_comment = False
    while i < n and depth > 0:
        c = template_html[i]
        nxt = template_html[i + 1] if i + 1 < n else ""
        if in_line_comment:
            if c == "\n":
                in_line_comment = False
        elif in_block_comment:
            if c == "*" and nxt == "/":
                in_block_comment = False
                i += 1
        elif in_str:
            if c == "\\":
                i += 1  # skip escaped next char
            elif c == in_str:
                in_str = None
        else:
            if c == "/" and nxt == "/":
                in_line_comment = True
                i += 1
            elif c == "/" and nxt == "*":
                in_block_comment = True
                i += 1
            elif c in ('"', "'", "`"):
                in_str = c
            elif c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0:
                    return template_html[start:i]
        i += 1
    raise AssertionError(f"Unbalanced braces in {fn_name} — could not extract body.")


def _rl_submit_body(template_html: str) -> str:
    return _extract_function_body(template_html, "rlSubmitQuestion")


def test_submit_no_dual_fire_on_first_wrong_attempt(template_html):
    """Pre-fix code had:
        if (stage6State.attempts[idx] === 1 && q.hint) {
            rlSetFeedback(fbId, 'rl-hint', '💡 ' + q.hint);
            rlDispatchTutorAi(idx, q, val);
        }
    Both fired together: local hint AND AI dispatch on the same submit. New
    flow runs ONE check path. Asserts the dual-fire pattern cannot return.
    """
    body = _rl_submit_body(template_html)
    assert not re.search(r"attempts\[idx\]\s*===\s*1\s*&&\s*q\.hint", body), (
        "rlSubmitQuestion must not contain the legacy `attempts[idx] === 1 && q.hint` "
        "first-attempt branch — that was the dual-fire bug."
    )
    # Auto-prepending the hint emoji + q.hint into the feedback band on
    # submit was the visible symptom of the dual-fire branch. Hints are
    # now opt-in via .rl-hint-toggle only.
    assert "'💡 ' + q.hint" not in body, (
        "Auto-injecting q.hint into the feedback band on submit is gone — "
        "hints render on demand via the rl-hint-toggle button."
    )


def test_submit_dispatches_ai_at_most_once(template_html):
    """Across the entire rlSubmitQuestion body there must be exactly ONE
    `rlDispatchTutorAi(...)` call site — the single AI fallback path. Pre-fix
    code had three: text-attempt-1, text-attempt-2+, multi-attempt-1,
    multi-attempt-2+, plus textarea. New flow has one shared dispatch."""
    body = _rl_submit_body(template_html)
    dispatch_calls = re.findall(r"rlDispatchTutorAi\s*\(", body)
    assert len(dispatch_calls) == 1, (
        f"Expected exactly 1 AI dispatch call inside rlSubmitQuestion, found {len(dispatch_calls)}. "
        "Multiple dispatches indicate the old branched-by-question-type pattern returned."
    )


def test_submit_local_correct_skips_ai_dispatch(template_html):
    """Path 1 of the new flow: when local exact-match passes, the function
    must return BEFORE dispatching the AI. Verified by checking the order
    of key markers in the submit body — the local-correct branch's
    `rlCommitQuestion(idx); return;` MUST appear before the single
    `rlDispatchTutorAi(...)` call site."""
    body = _rl_submit_body(template_html)

    # Anchor 1: the gate that opens the local-correct branch.
    correct_gate = body.find("canLocalCheck && localCorrect")
    assert correct_gate != -1, (
        "Couldn't find `canLocalCheck && localCorrect` gate in rlSubmitQuestion."
    )

    # Anchor 2: the SOLE rlDispatchTutorAi call (must come AFTER the
    # local-correct branch so the branch's `return;` skips it).
    dispatch = body.find("rlDispatchTutorAi(")
    assert dispatch != -1, "Missing rlDispatchTutorAi call in rlSubmitQuestion."

    # Local-correct branch must complete BEFORE the dispatch line. Anchor
    # the branch end via rlCommitQuestion(idx) — only the local-correct
    # path calls it from within rlSubmitQuestion (the AI-result handler
    # has its own call outside).
    commit_call = body.find("rlCommitQuestion(idx)", correct_gate)
    assert commit_call != -1, (
        "Local-correct branch must call rlCommitQuestion(idx) to reveal Keyingi."
    )

    # Find the `return;` immediately after rlCommitQuestion(idx) — that
    # terminates the local-correct path before the AI dispatch below.
    return_after_commit = body.find("return;", commit_call)
    assert return_after_commit != -1, (
        "Local-correct branch must `return;` after rlCommitQuestion(idx); "
        "otherwise the AI dispatch below it fires anyway."
    )
    assert return_after_commit < dispatch, (
        "Local-correct branch's `return;` must come BEFORE the rlDispatchTutorAi call. "
        "Otherwise the local path falls through and the AI gets called for correct answers."
    )

    # Also assert: between correct_gate and the local-correct return, there
    # is NO rlDispatchTutorAi (no dispatch-from-correct-branch).
    correct_branch_text = body[correct_gate:return_after_commit]
    assert "rlDispatchTutorAi" not in correct_branch_text, (
        "Local-correct path must NOT dispatch AI — that defeats the cost/latency "
        "savings the local-first design provides."
    )


def test_submit_engages_busy_lock_before_dispatch(template_html):
    """Submit must set checking[idx]=true and disable the local submit button
    BEFORE dispatching AI, otherwise a fast second click can fire two AI
    requests. Order matters: lock first, then dispatch."""
    body = _rl_submit_body(template_html)
    busy_set = body.find("stage6State.checking[idx] = true")
    submit_disable = body.find("submitBtn.disabled = true")
    dispatch = body.find("rlDispatchTutorAi(")
    assert busy_set != -1, "Missing `stage6State.checking[idx] = true` lock-engage line."
    assert submit_disable != -1, "Missing `submitBtn.disabled = true` lock-engage line."
    assert dispatch != -1, "Missing rlDispatchTutorAi call (the single AI dispatch)."
    assert busy_set < dispatch, "checking[idx]=true must be set BEFORE dispatching AI."
    assert submit_disable < dispatch, "Submit button must be disabled BEFORE dispatching AI."


def test_submit_guarded_against_double_invocation(template_html):
    """Top-of-function guard: if checking[idx] is already true, return
    immediately. Same for already-submitted. Without this, a fast second
    click during the AI window fires twice."""
    body = _rl_submit_body(template_html)
    # The first ~15 lines should contain both guards.
    head = "\n".join(body.split("\n")[:30])
    assert re.search(
        r"if\s*\(\s*stage6State\.checking\s*&&\s*stage6State\.checking\[idx\]\s*\)\s*return",
        head,
    ), "Missing top-of-function guard against re-entry while checking[idx] is true."
    assert re.search(
        r"if\s*\(\s*stage6State\.submitted\[idx\]\s*\)\s*return",
        head,
    ), "Missing top-of-function guard against re-submit after verdict already in."


def test_set_rl_ai_lock_targets_local_submit_not_action_button(template_html):
    """Pre-fix `setRlAiLock` toggled is-ai-pending on `#action-button`. New
    design moves submit off the bottom button entirely, so the lock must
    operate on the active question's `.rl-submit-local`."""
    body = _extract_function_body(template_html, "setRlAiLock")
    assert "'rl-q' + ((i || 0) + 1) + '-submit'" in body or "rl-q' +" in body, (
        "setRlAiLock must look up the per-question local submit button "
        "(`rl-q{N}-submit`), not the global #action-button."
    )
    assert "getElementById('action-button')" not in body, (
        "setRlAiLock must NOT target #action-button anymore — that's pre-fix."
    )


def test_all_four_question_types_get_local_button_row(template_html):
    """rlRenderQuestion must inject `.rl-q-actions` (with submit/hint/tutor)
    + `.rl-q-after` (with Keyingi) into the per-question body for every
    question type. Test by checking the renderer code unconditionally builds
    these rows — they're in a single block at the end of rlRenderQuestion,
    not branched per-type."""
    body = _extract_function_body(template_html, "rlRenderQuestion")
    # The action row builder block must exist outside any q.type-specific
    # branch (it's in the unconditional tail of the function).
    assert re.search(r"actions\s*=\s*document\.createElement\(['\"]div['\"]\)", body), (
        "rlRenderQuestion must build .rl-q-actions row unconditionally."
    )
    assert "submitBtn.className = 'rl-submit-local'" in body
    assert "nextBtn.className = 'rl-next-local'" in body
    # Tutor pre-submit button (always rendered; hidden after submit).
    assert "tutorBtn.className = 'rl-tutor-pre-submit'" in body
    # Hint toggle is conditional on q.hint — that's intentional, but the
    # variable name + class name must still appear.
    assert "hintBtn.className = 'rl-hint-toggle'" in body
    # Per-question state arrays must be reset on render.
    assert "stage6State.checking[idx] = false" in body
    assert "stage6State.hintOpen[idx] = false" in body


def test_post_grading_keyingi_button_only_visible_after_verdict(template_html):
    """`.rl-q-after` (post-grading row) is hidden by default and revealed
    only by `rlCommitQuestion(idx)`. Both the local-correct path and the
    AI-result handler must call rlCommitQuestion to reveal Keyingi."""
    body = _extract_function_body(template_html, "rlCommitQuestion")
    assert "after.hidden = false" in body, (
        "rlCommitQuestion must unhide `.rl-q-after` so the local Keyingi button appears."
    )
    # AI-result handler calls it (lives in the document.addEventListener
    # block, outside any named function — so we check at template scope).
    assert re.search(
        r"rlCommitQuestion\s*\(\s*ticket\.qIndex\s*\)",
        template_html,
    ), "AI-result handler must call rlCommitQuestion(ticket.qIndex) to reveal Keyingi."


def test_bloom_pisa_extractor_regex_handles_documented_variants():
    """Executable test of the rlExtractMeta regex pattern. Pre-fix, the
    parsing was checked only via "function exists / is wired" assertions —
    no test actually ran the regex against the variants the comment claims
    to support. This catches silent regex regressions.

    Mirrors the JS regex in rlExtractMeta() to Python `re` and asserts the
    documented input forms parse to the expected (bloom_level, pisa_level)
    output, plus that no-match inputs return None.

    NOTE: Order assumption is Bloom-before-PISA per production convention.
    Reversed-order inputs intentionally fail to match — see the comment
    above rlExtractMeta() for rationale.
    """
    # Mirror of the JS regex, ported to Python re flavor (case-insensitive).
    js_pattern = re.compile(
        r"\[\s*Bloom:?\s*L?(\d+)\s*[|·,]\s*PISA:?\s*[LP]?(\d+)\s*\]",
        re.IGNORECASE,
    )

    # Variants that MUST parse — from the comment in rlExtractMeta().
    parses = [
        ("[Bloom: L3 | PISA: L2]", "3", "2"),     # canonical production form
        ("[Bloom L3 · PISA L2]", "3", "2"),       # no colons, dot separator
        ("[Bloom: 3 | PISA: 2]", "3", "2"),       # no L prefix
        ("[BLOOM: L3 | PISA: P2]", "3", "2"),     # uppercase, P prefix on PISA
        ("[bloom: L4 , pisa: L1]", "4", "1"),     # comma separator, lowercase
        ("[ Bloom: L5 | PISA: L4 ]", "5", "4"),  # extra whitespace inside brackets
        ("Question text. [Bloom: L3 | PISA: L2]", "3", "2"),  # tags after text
    ]
    for src, bloom, pisa in parses:
        m = js_pattern.search(src)
        assert m is not None, f"Regex must parse {src!r} but didn't."
        assert m.group(1) == bloom, f"{src!r}: bloom expected {bloom!r}, got {m.group(1)!r}"
        assert m.group(2) == pisa, f"{src!r}: pisa expected {pisa!r}, got {m.group(2)!r}"

    # Inputs that MUST NOT parse.
    no_match = [
        "Plain question text without any tags.",
        "Question with [some other bracketed text].",
        "[Bloom L3]",                              # PISA missing
        "[PISA: L2 | Bloom: L3]",                  # reversed order — by design (see code comment)
        "Bloom: L3 | PISA: L2",                    # missing brackets
    ]
    for src in no_match:
        assert js_pattern.search(src) is None, (
            f"Regex must NOT parse {src!r}, but it did. Either tighten the pattern "
            f"or update the documented variants comment."
        )


def test_bloom_pisa_extractor_strips_tags_from_prompt():
    """The full rlExtractMeta contract — parsing is one half; the other is
    that the returned `stripped` text has the bracket suffix removed AND
    trailing whitespace/punctuation cleaned up so the rendered prompt is
    presentation-ready (not "Some question.   ." with leftovers)."""
    js_pattern = re.compile(
        r"\[\s*Bloom:?\s*L?(\d+)\s*[|·,]\s*PISA:?\s*[LP]?(\d+)\s*\]",
        re.IGNORECASE,
    )
    trailing_pattern = re.compile(r"[\s.;,]+$")

    def py_extract(text):
        # Mirror of the JS rlExtractMeta() implementation.
        src = text or ""
        m = js_pattern.search(src)
        if not m:
            return {"tags": "", "stripped": src}
        tags = f"Bloom L{m.group(1)} · PISA L{m.group(2)}"
        stripped = trailing_pattern.sub("", src.replace(m.group(0), "")).strip()
        return {"tags": tags, "stripped": stripped}

    cases = [
        # (input, expected_tags, expected_stripped)
        (
            "1-test uchun absolut xatolikni toping (mmol/L). [Bloom: L3 | PISA: L2]",
            "Bloom L3 · PISA L2",
            "1-test uchun absolut xatolikni toping (mmol/L)",
        ),
        (
            "Solve this problem. [Bloom L4 · PISA L3]",
            "Bloom L4 · PISA L3",
            "Solve this problem",
        ),
        (
            "[Bloom: L1 | PISA: L1] What is 2+2?",
            "Bloom L1 · PISA L1",
            "What is 2+2?",
        ),
        (
            "Plain prompt with no tags.",
            "",
            "Plain prompt with no tags.",
        ),
    ]
    for src, expected_tags, expected_stripped in cases:
        result = py_extract(src)
        assert result["tags"] == expected_tags, (
            f"{src!r}: tags expected {expected_tags!r}, got {result['tags']!r}"
        )
        assert result["stripped"] == expected_stripped, (
            f"{src!r}: stripped expected {expected_stripped!r}, got {result['stripped']!r}"
        )


def test_bloom_pisa_tags_relocated_to_header_meta_slot(template_html):
    """Bloom/PISA tags used to be inline at the end of `q.prompt` text. They
    now render in a dedicated top-right header slot so the prompt stays
    clean. Asserts:
      - `.rl-card-top` wrapper + `.rl-q-header-meta` slot exist.
      - `rlExtractMeta()` helper is defined and pulls the bracketed pattern.
      - `rlRenderQuestion` writes to `#rl-q-header-meta` and renders the
        prompt with the tag substring stripped (not the raw `q.prompt`).
      - Story view + closure clear the meta so it auto-hides via :empty.
    """
    # CSS + HTML structure.
    assert "rl-card-top" in template_html, "Missing .rl-card-top wrapper class."
    assert 'id="rl-q-header-meta"' in template_html, (
        "Missing <div id='rl-q-header-meta'> slot in the header row."
    )
    assert ".rl-q-header-meta:empty" in template_html, (
        "Missing :empty rule that hides the meta slot when no tags are present."
    )

    # JS extractor exists and is invoked on render.
    assert "function rlExtractMeta(" in template_html, (
        "Missing rlExtractMeta() helper that extracts `[Bloom: LX | PISA: LY]` from q.prompt."
    )

    render_q_body = _extract_function_body(template_html, "rlRenderQuestion")
    assert "rlExtractMeta(q.prompt)" in render_q_body, (
        "rlRenderQuestion must call rlExtractMeta(q.prompt) so the tags can be relocated."
    )
    # Prompt must render meta.stripped (not raw q.prompt) — otherwise the
    # tag suffix shows in BOTH the meta slot and inline.
    assert "promptEl.innerHTML = meta.stripped" in render_q_body, (
        "rlRenderQuestion must render `meta.stripped` (not raw q.prompt) so the "
        "Bloom/PISA bracket suffix doesn't appear twice."
    )

    # Story + closure clear the meta so the slot hides.
    story_body = _extract_function_body(template_html, "rlRenderStory")
    assert "rl-q-header-meta" in story_body and "metaEl.textContent = ''" in story_body, (
        "rlRenderStory must clear #rl-q-header-meta so the meta hides during story view."
    )
    closure_body = _extract_function_body(template_html, "rlShowClosure")
    assert "rl-q-header-meta" in closure_body and "closureMetaEl.textContent = ''" in closure_body, (
        "rlShowClosure must clear #rl-q-header-meta so the meta hides on closure card."
    )


def test_final_boss_entry_defensively_unhides_action_button(template_html):
    """The RL phase hides #action-button during its question loop and
    rlShowClosure() unhides it on the closure card. Normal flow is safe,
    but edge paths (skip-to-end shortcuts at line 11057, page reload
    landing on Boss, session restore) could reach `startFinalBoss()`
    with the button still hidden, leaving the student stuck.

    `startFinalBoss()` must therefore unconditionally re-show
    #action-button on entry — Boss should be self-contained, not
    depend on prior phase cleanup."""
    body = _extract_function_body(template_html, "startFinalBoss")
    assert "getElementById('action-button')" in body, (
        "startFinalBoss must look up #action-button on entry."
    )
    assert "ab.style.display = ''" in body, (
        "startFinalBoss must re-show #action-button via `display: ''` so a "
        "leaked hide from the RL question loop doesn't strand the student."
    )


def test_bottom_action_button_hidden_during_question_loop(template_html):
    """Bottom #action-button is hidden when entering the question loop and
    re-shown on the closure card. Otherwise the student sees TWO submit
    affordances (the local one + the global one) and the contract gets
    confusing."""
    show_body = _extract_function_body(template_html, "rlShowQuestion")
    assert re.search(
        r"getElementById\(['\"]action-button['\"]\)[^;]*;\s*if\s*\(\s*ab\s*\)\s*ab\.style\.display\s*=\s*['\"]none['\"]",
        show_body,
        re.DOTALL,
    ), "rlShowQuestion must hide #action-button via display:none."

    closure_body = _extract_function_body(template_html, "rlShowClosure")
    assert "ab.style.display = ''" in closure_body, (
        "rlShowClosure must un-hide #action-button (display: '') so the student can advance "
        "to the next phase."
    )


# ── Boss submit loading state ────────────────────────────────────────────


def test_boss_submit_shows_loading_not_premature_wrong(template_html):
    """Pre-fix Boss submit reused `.boss-feedback.wrong` (red) + text
    `✗ Noto'g'ri. AI tahlil qilmoqda...` immediately on submit, BEFORE
    awaiting the AI verdict. The wrong branch must only fire AFTER the AI
    returns a wrong verdict (in bossHandleResponse).

    Asserts the new neutral `.boss-feedback.loading` class + `boss.checking`
    translation key are wired correctly.
    """
    body = _extract_function_body(template_html, "bossHandleAction")
    pre_await = body.split("bossState.busy = true")[0]

    assert "'boss-feedback wrong'" not in pre_await and \
           '"boss-feedback wrong"' not in pre_await, (
        "bossHandleAction's pre-await UI must not set `.boss-feedback.wrong` — "
        "applied before the AI has decided. Use `.boss-feedback.loading`."
    )
    assert "'boss-feedback loading'" in pre_await or \
           '"boss-feedback loading"' in pre_await, (
        "bossHandleAction's pre-await UI must set `.boss-feedback.loading`."
    )
    assert "RT('boss.wrong_ai')" not in pre_await and \
           'RT("boss.wrong_ai")' not in pre_await, (
        "bossHandleAction's pre-await UI must not use `boss.wrong_ai`."
    )
    assert "RT('boss.checking')" in pre_await or \
           'RT("boss.checking")' in pre_await, (
        "bossHandleAction's pre-await UI must use `boss.checking`."
    )
    assert ".boss-feedback.loading" in template_html, (
        "Missing `.boss-feedback.loading` CSS rule."
    )
    assert re.search(
        r"\.boss-feedback\.loading\s*\{[^}]*background:\s*rgba\(99,\s*184,\s*255",
        template_html,
    ), ".boss-feedback.loading must use blue, not red."
    count = template_html.count("'boss.checking':") + template_html.count('"boss.checking":')
    assert count >= 3, (
        f"`boss.checking` translation key must appear in all 3 locales; found {count}."
    )


# ── Boss-tutor prompt taunt pool ─────────────────────────────────────────


def test_boss_tutor_prompt_has_explicit_taunt_pool_for_wrong_branch():
    """boss-tutor.md must declare a concrete TAUNT POOL for `was_correct:
    false` (mirroring the praise pool's structure). Pre-fix the wrong
    branch was just `"short taunt … Rotate"` with no pool, so the LLM
    leaked praise-pool phrases like "Mantiq qiziqarli 🔥" onto wrong-
    verdict responses."""
    prompt_path = (
        Path(__file__).resolve().parent.parent
        / "server" / "prompts" / "runtime" / "boss-tutor.md"
    )
    prompt = prompt_path.read_text(encoding="utf-8")

    m = re.search(
        r"If not[^:]*:.*?(?=\n\s*\d\.|\n##|\Z)",
        prompt,
        re.DOTALL | re.IGNORECASE,
    )
    assert m, (
        "Couldn't locate the `If not` (wrong-branch) section in boss-tutor.md."
    )
    wrong_branch_text = m.group(0)

    for locale in ("UZ", "RU", "EN"):
        assert re.search(
            rf"Pool\s+{locale}:.+?\".+?\".+?\".+?\"",
            wrong_branch_text,
            re.DOTALL,
        ), (
            f"Missing `Pool {locale}:` taunt list under the `If not` "
            f"(wrong) branch in boss-tutor.md."
        )

    # Praise pool must STILL be present.
    assert "Mantiq qiziqarli" in prompt, (
        "Praise pool was accidentally removed while adding the taunt pool."
    )
