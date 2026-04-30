"""Focused regression tests for English prompt guardrails.

These tests verify that:
- instruction.md does not reference flow.md and lists the 9 phase prompts in order
- flashcards.md has no-answer-leak hint rules
- flashcards.md locks to textbook-only content
- flashcards.md requires concept-related SVG media
- flashcards.md requires Buzan-style mnemonic technique (always visible, not optional)
- game-breaks.md drops Speed Sort and locks to always-3-games
- memory-sprint.md has gated hint with anti-leak + Uzbek YNNG/TF labels + count fallback
- final-challenge.md tags drop the legacy ID prefix and Hint Ladder bans literal-answer leaks
- reflection.md documents the 6-body-to-4-schema-keys mapping and is mode-locked HARD
- All non-flashcard phases share the #93 media-hardening clause + BAD/GOOD anti-pattern examples
- No prompt file leaks runtime / homework-builder internals
"""
import re
from pathlib import Path

import pytest

PROMPTS_DIR = Path(__file__).resolve().parents[1] / "server" / "prompts" / "english"


def _read(name: str) -> str:
    return (PROMPTS_DIR / name).read_text(encoding="utf-8")


def test_instruction_no_flow_md_and_phase_order():
    """instruction.md must not reference flow.md, must declare always-HARD mode,
    and must list the 9 phase prompts in strictly increasing order."""
    text = (PROMPTS_DIR / "instruction.md").read_text(encoding="utf-8")

    # Must NOT contain flow.md reference
    assert "flow.md" not in text, "instruction.md must not reference flow.md"

    # Must declare always-HARD mode
    assert "**Mode:** always HARD for English." in text, (
        "instruction.md must contain '**Mode:** always HARD for English.'"
    )

    # 9 phase-prompt filenames must appear in strictly increasing order
    phase_prompts = [
        "preview-hard.md",
        "flashcards.md",
        "memory-sprint.md",
        "reading.md",
        "game-breaks.md",
        "real-life.md",
        "consolidation.md",
        "final-challenge.md",
        "reflection.md",
    ]
    positions = []
    for name in phase_prompts:
        idx = text.find(name)
        assert idx != -1, f"instruction.md must contain '{name}'"
        positions.append(idx)

    for i in range(1, len(positions)):
        assert positions[i] > positions[i - 1], (
            f"Phase prompts must appear in order: '{phase_prompts[i]}' "
            f"(pos {positions[i]}) must come after '{phase_prompts[i-1]}' "
            f"(pos {positions[i-1]})"
        )


def test_flashcards_no_answer_leak_hint_rules():
    """flashcards.md must contain all no-answer-leak hint rules."""
    text = (PROMPTS_DIR / "flashcards.md").read_text(encoding="utf-8")

    required = [
        "Hint must never expose the answer",
        "Hint cannot repeat the target term",
        "Hint cannot include the exact definition",
        "Hint cannot translate the target into Uzbek",
        "Hint cannot give a sentence where the target word is the obvious missing answer",
    ]
    for phrase in required:
        assert phrase in text, f"flashcards.md must contain: {phrase!r}"


def test_flashcards_textbook_only_fidelity():
    """flashcards.md must lock content to textbook-only sources."""
    text = (PROMPTS_DIR / "flashcards.md").read_text(encoding="utf-8")

    required = [
        "Textbook fidelity",
        "No invented examples",
        "No dictionary padding",
        "No out-of-topic facts",
    ]
    for phrase in required:
        assert phrase in text, f"flashcards.md must contain: {phrase!r}"


def test_flashcards_concept_related_media_rules():
    """flashcards.md must require concept-related SVG media and ban decorative media."""
    text = (PROMPTS_DIR / "flashcards.md").read_text(encoding="utf-8")

    required = [
        "concept-related visual",
        "inline SVG",
        "200",  # loose check that 200×150 size guidance is present
        "No decorative, generic, stock-like, or out-of-topic media",
        "omit `media`",  # literal backtick-quoted media
    ]
    for phrase in required:
        assert phrase in text, f"flashcards.md must contain: {phrase!r}"


def test_english_flow_md_is_removed():
    """flow.md is orphaned after #93 inlined the phase order — must stay
    deleted to prevent two-sources-of-truth drift."""
    flow_path = PROMPTS_DIR / "flow.md"
    assert not flow_path.exists(), (
        "server/prompts/english/flow.md must not exist — instruction.md inlines the "
        "phase-prompt order; keeping flow.md creates a conflicting orphan."
    )


# --- T1: instruction.md path prefix --------------------------------------


def test_instruction_no_stale_06_prompts_path_prefix():
    """instruction.md must not reference the stale `06-prompts/` path prefix.

    The actual prompt directory is `server/prompts/english/`. Any
    `06-prompts/...` reference is dead doc that confuses operators.
    """
    text = _read("instruction.md")
    assert "06-prompts/" not in text, (
        "instruction.md must not reference the stale 06-prompts/ path prefix"
    )


# --- T3: game-breaks.md (Speed Sort + always-3-games) --------------------


def test_game_breaks_speed_sort_not_in_available_table():
    """Speed Sort was removed from the English roster; it must not return to the
    Available Games table or have a Construction-per-game block.
    """
    text = _read("game-breaks.md")
    assert "**Speed Sort**" not in text, (
        "Speed Sort must not return as a row in the Available Games table"
    )
    assert "### Speed Sort" not in text, (
        "Speed Sort must not return as a Construction-per-game block"
    )


def test_game_breaks_always_3_games_no_easy_branch():
    """English is always-HARD per classify.md; game-breaks must reflect 3 games
    always, with no EASY-mode branch in selection guidance.
    """
    text = _read("game-breaks.md")
    assert "3 games" in text, "game-breaks.md must declare 3 games"
    assert "2 or 3 games" not in text, "the legacy 2-or-3 framing must be gone"
    assert "**EASY (2 games):**" not in text, "EASY-mode game-count branch must be gone"
    assert "**HARD (3 games):**" not in text, "HARD-mode game-count branch must be gone"


def test_game_breaks_no_memory_match_in_available_table():
    """Memory Match is not a real game in the editor catalog (no memory-match.js
    exists; tile-match.js writes to gb_memory_match storage). It must not return
    to the Available Games table or have a Construction-per-game block.
    """
    text = _read("game-breaks.md")
    assert "**Memory Match**" not in text, (
        "Memory Match must not return as a row in the Available Games table"
    )
    assert "### Memory Match" not in text, (
        "Memory Match must not return as a Construction-per-game block"
    )


def test_game_breaks_puzzle_lock_in_available_table():
    """Puzzle Lock replaces Memory Match in the English roster — must appear in
    both the Available Games table and the Construction-per-game section.
    """
    text = _read("game-breaks.md")
    assert "**Puzzle Lock**" in text, (
        "Puzzle Lock must appear as a row in the Available Games table"
    )
    assert "### Puzzle Lock" in text, (
        "Puzzle Lock must have a Construction-per-game block"
    )


def test_game_breaks_schema_includes_puzzle_lock_key():
    """OUTPUT REQUIREMENT schema must include a `puzzle_lock` key so authored
    Puzzle Lock content has a landing slot.
    """
    text = _read("game-breaks.md")
    assert '"puzzle_lock":' in text, (
        "OUTPUT REQUIREMENT schema must include `puzzle_lock` key"
    )


# --- T4: memory-sprint.md (hint + anti-leak + Uzbek labels + count fallback)


def test_memory_sprint_has_gated_hint_section_and_anti_leak():
    """memory-sprint.md must have a Hint section with explicit anti-leak rules and
    a `hint` field in the OUTPUT REQUIREMENT schema.
    """
    text = _read("memory-sprint.md")
    assert "## Hint" in text, "memory-sprint.md must have a Hint section"
    assert "must NEVER expose the answer" in text, (
        "memory-sprint hint section must contain the never-expose-answer rule"
    )
    # hint field must be present in OUTPUT REQUIREMENT JSON schema
    assert '"hint":' in text, "memory-sprint OUTPUT REQUIREMENT must include `hint` field"


def test_memory_sprint_no_legacy_no_hints_rule():
    """The legacy `**No hints.**` rule contradicts the new gated-hint design and must
    not return.
    """
    text = _read("memory-sprint.md")
    assert "**No hints.**" not in text, (
        "memory-sprint.md must not re-introduce the `**No hints.**` rule"
    )


def test_memory_sprint_uses_uzbek_ynng_labels_in_examples():
    """YNNG examples must use Uzbek runtime labels (Ha / Yo'q / Ma'lum emas), not
    the English-language framing — the runtime renders Uzbek buttons.
    """
    text = _read("memory-sprint.md")
    assert "Ha / Yo'q / Ma'lum emas" in text, (
        "YNNG cue must use Uzbek 'Ha / Yo'q / Ma'lum emas'"
    )
    # English-only framing must not appear in BAD/GOOD examples or section body
    assert "Yes / No / Not Given" not in text, (
        "English YNNG framing must not be used — runtime renders Uzbek buttons"
    )


def test_memory_sprint_uses_uzbek_tf_label_in_examples():
    """T/F BAD/GOOD examples must use the Uzbek runtime cue."""
    text = _read("memory-sprint.md")
    assert "To'g'ri yoki Noto'g'ri" in text, (
        "T/F examples must use Uzbek 'To'g'ri yoki Noto'g'ri?'"
    )


def test_memory_sprint_count_fallback_rule_present():
    """Ranged counts (4-5, 5-6) need an explicit rule for what the +1 item is.
    Otherwise the LLM has to guess at the upper bound.
    """
    text = _read("memory-sprint.md")
    assert "extra MC item" in text, (
        "memory-sprint must specify the +1 fallback item for ranged counts (extra MC item)"
    )


# --- T5: flashcards.md Buzan extension -----------------------------------


def test_flashcards_hint_required_not_optional():
    """flashcards.md hint must be a required Buzan-style mnemonic (always visible),
    not an optional add-on.
    """
    text = _read("flashcards.md")
    assert "Always-visible Buzan-style mnemonic" in text, (
        "flashcards.md hint must be declared always-visible Buzan-style mnemonic"
    )
    assert "Optional mnemonic" not in text, (
        "the legacy 'Optional mnemonic' wording must be gone"
    )
    assert "Every card must include a `hint`" in text, (
        "flashcards.md must require `hint` on every card"
    )
    # Schema reflects the requirement
    assert "required Buzan-style mnemonic" in text, (
        "flashcards OUTPUT REQUIREMENT must mark hint as required"
    )


@pytest.mark.parametrize(
    "technique",
    ["Link / Story", "Peg / Number", "Major system", "Substitute word", "MIG"],
)
def test_flashcards_lists_buzan_technique(technique):
    """All five Buzan techniques must be listed by name in flashcards.md."""
    text = _read("flashcards.md")
    assert technique in text, f"flashcards.md must list Buzan technique: {technique}"


# --- T6: final-challenge.md (tag format + tier note + Hint Ladder anti-leak)


def test_final_challenge_tag_format_drops_id_prefix():
    """Boss tags must use the schema format only — the legacy
    [UZ-ENG{G}-UNIT{N}-{SEQ}] | ... prefix breaks the schema.
    """
    text = _read("final-challenge.md")
    bad_pattern = re.compile(r"\[UZ-ENG\d?\{?G?\}?-?UNIT")
    matches = bad_pattern.findall(text)
    assert not matches, (
        f"Boss tags must not include the UZ-ENG{{G}}-UNIT{{N}} ID prefix "
        f"(found {len(matches)} occurrences)"
    )


def test_final_challenge_has_tier_disambiguation_note():
    """A note distinguishing per-question tier (Easy/Medium/Hard) from homework
    mode must appear under the Damage Table, since English mode is always HARD.
    """
    text = _read("final-challenge.md")
    assert "Tier disambiguation" in text, (
        "final-challenge.md must contain a Tier disambiguation note"
    )
    assert "always HARD" in text, (
        "Tier disambiguation note must reaffirm English homework mode is always HARD"
    )


def test_final_challenge_hint_ladder_bans_literal_answer():
    """The Hint Ladder must explicitly ban literal-answer leakage at any level —
    even Hint 3 only shows the frame, never the answer text.
    """
    text = _read("final-challenge.md")
    assert "Anti-leak rules" in text, (
        "final-challenge Hint Ladder must include an Anti-leak rules block"
    )
    assert "literal answer" in text.lower(), (
        "Hint Ladder must mention literal-answer ban"
    )
    # BAD/GOOD pair must be present
    assert "BAD Hint" in text and "GOOD Hint" in text, (
        "Hint Ladder must include BAD/GOOD example pairs"
    )


# --- T7: reflection.md (mode strip + 6→4 schema mapping) -----------------


def test_reflection_no_easy_mode_reference():
    """reflection.md must not reference EASY mode — English is always HARD."""
    text = _read("reflection.md")
    assert "Mode (EASY or HARD)" not in text, (
        "reflection.md must not reference EASY/HARD as a mode choice"
    )
    assert "always HARD" in text, (
        "reflection.md must affirm Mode is always HARD per classify.md"
    )


def test_reflection_documents_6_to_4_schema_mapping():
    """reflection.md must explicitly document the 6-body-section → 4-schema-key
    mapping so the LLM knows where each part lands in the JSON output.
    """
    text = _read("reflection.md")
    assert "Schema mapping" in text, (
        "reflection.md must contain a 'Schema mapping' section"
    )
    # All four schema keys must be referenced in the mapping section
    for key in ("summary", "question", "spaced_rep", "closing"):
        assert f"`{key}`" in text, (
            f"reflection.md schema mapping must reference key `{key}`"
        )


# --- T8: media hardening sweep across non-flashcard prompts --------------

_MEDIA_HARDENED_FILES = [
    "memory-sprint.md",
    "preview-hard.md",
    "reading.md",
    "real-life.md",
    "consolidation.md",
    "final-challenge.md",
]


@pytest.mark.parametrize("filename", _MEDIA_HARDENED_FILES)
def test_media_rule_hardened_across_non_flashcard_phases(filename):
    """Every non-flashcard prompt that allows media must include the #93 hardening
    clause `No decorative, generic, stock-like, or out-of-topic media`.
    Catches a future PR that softens one file's wording back to 'aim to include'.
    """
    text = _read(filename)
    assert "No decorative, generic, stock-like, or out-of-topic media" in text, (
        f"{filename} missing the standard media-hardening clause"
    )


@pytest.mark.parametrize("filename", _MEDIA_HARDENED_FILES)
def test_media_rule_has_bad_good_examples(filename):
    """Every non-flashcard prompt with media guidance must include a BAD/GOOD
    anti-pattern pair so the LLM has a concrete contrast.
    """
    text = _read(filename)
    assert "BAD:" in text and "GOOD:" in text, (
        f"{filename} must include BAD/GOOD media examples"
    )


def test_media_hardening_parametrize_list_not_empty():
    """Meta-sanity: the parametrize surface list must be non-empty so the
    hardening tests above cannot pass vacuously by zeroing out the list.
    """
    assert len(_MEDIA_HARDENED_FILES) >= 6, (
        "non-flashcard media-hardening sweep must cover at least 6 files"
    )


# --- T9: no homework-builder / runtime references ------------------------

_FORBIDDEN_BUILDER_PHRASES = [
    "stored and resurfaced",
    "is pulled from Preview",
    "string pulled from Preview",
    "perfect_homework",
    "content_json",
    "the injector",
]


@pytest.mark.parametrize("phrase", _FORBIDDEN_BUILDER_PHRASES)
def test_no_homework_builder_references_in_english_prompts(phrase):
    """Prompts must be content-only guidance to the LLM — no runtime / builder /
    injector internals. Catches a future PR that sneaks a 'pulled from runtime'
    phrase into any English prompt file.
    """
    for path in PROMPTS_DIR.glob("*.md"):
        text = path.read_text(encoding="utf-8")
        assert phrase not in text, (
            f"{path.name} contains forbidden homework-builder reference: {phrase!r}"
        )


def test_forbidden_builder_phrases_list_not_empty():
    """Meta-sanity: the forbidden-phrase list must be non-empty."""
    assert len(_FORBIDDEN_BUILDER_PHRASES) >= 6
