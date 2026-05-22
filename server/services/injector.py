"""HTML injector — stamps content_json into perfect_homework.html template.

Pure functions, no side effects. Template is read ONCE at module import and
cached in memory. See CONTRACTS.md §5 for the injector contract.
"""

import json
import random
import re
from typing import Optional

from ..config import TEMPLATE_PATH
from . import quotes as quotes_service


# --------------------------------------------------------------------------- #
# Boss-name resolution — subject-aware defaults, author override wins.
# Used by the runtime template's data-boss-name / data-boss-name-label hooks
# so each homework's final-boss section reads naturally for its subject.
# --------------------------------------------------------------------------- #

_BOSS_NAME_DEFAULTS = {
    # Subject-id → default boss name (Uzbek primary; aliases for both
    # English-style and Latin-Uzbek subject ids observed in DB rows).
    "algebra":     "Algebra Boshlig'i",
    "geometry":    "Geometriya Boshlig'i",
    "geometriya":  "Geometriya Boshlig'i",
    "physics":     "Fizika Boshlig'i",
    "fizika":      "Fizika Boshlig'i",
    "chemistry":   "Kimyo Boshlig'i",
    "kimyo":       "Kimyo Boshlig'i",
    "biology":     "Biologiya Boshlig'i",
    "biologiya":   "Biologiya Boshlig'i",
    "english":     "English Boss",
    "russian":     "Русский Босс",
    "history":     "Tarix Boshlig'i",
    "tarix":       "Tarix Boshlig'i",
    "literature":  "Adabiyot Boshlig'i",
    "uzbek":       "O'zbek tili Boshlig'i",
}


def boss_name_for(subject_id: Optional[str], explicit: Optional[str]) -> str:
    """Resolve the boss name for a homework. Explicit override wins;
    falls back to subject default; otherwise generic 'Boss'."""
    if explicit and explicit.strip():
        return explicit.strip()
    if subject_id:
        sid = subject_id.strip().lower()
        if sid in _BOSS_NAME_DEFAULTS:
            return _BOSS_NAME_DEFAULTS[sid]
    return "Boss"

# Read template ONCE at module load (not per request)
with open(TEMPLATE_PATH, "r", encoding="utf-8") as _f:
    _TEMPLATE = _f.read()

# Mapping: content_json key -> JS constant name in template
_ARRAY_CONSTANTS = [
    ("panels",           "PANELS"),
    ("quotes",           "QUOTES"),
    ("flashcards",       "FLASHCARDS"),
    ("memory_sprint",    "MS_QUESTIONS"),
    ("gb_adaptive_quiz", "GB_ADAPTIVE_QUIZ"),
    ("gb_why_chain",     "GB_WHY_CHAIN"),
    ("gb_memory_match",  "GB_MEMORY_MATCH"),
    ("gb_puzzle_lock",   "GB_PUZZLE_LOCK"),
    ("gb_mystery_box",   "GB_MYSTERY_BOX"),
    ("gb_ttt",           "GB_TTT"),
    # boss_questions removed from _ARRAY_CONSTANTS — handled by _serialize_boss_questions
    # (side-disjoint, answer-leak prevention). See inject() below.
]

# Mapping: content_json key -> JS constant name in template, for OBJECT (non-array) constants.
# Wave 2: reading/consolidation/reflection are objects, like RL_SCENARIO.
_OBJECT_CONSTANTS = [
    ("reading",       "READING"),
    ("consolidation", "CONSOLIDATION"),
    ("reflection",    "REFLECTION"),
]


def _esc(s) -> str:
    """Escape text for safe insertion into HTML content."""
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _safe_js_json(value) -> str:
    """Serialize JSON for inline <script> assignment contexts."""
    return (
        json.dumps(value, ensure_ascii=False)
        .replace("</", "<\\/")
        .replace("\u2028", "\\u2028")
        .replace("\u2029", "\\u2029")
    )


# Per-game server-only field sets now live in redaction_constants.py so the
# injector (legacy HTML runtime) and runtime_redactor.py (React hydration API)
# share ONE source of truth and cannot drift. Imported as sets for the existing
# in-place `.discard()` / membership usage below.
from .redaction_constants import (  # noqa: E402
    TM_SERVER_ONLY as _TM_SERVER_ONLY_FZ,
    SF_SERVER_ONLY as _SF_SERVER_ONLY_FZ,
    RLC_SERVER_ONLY as _RLC_SERVER_ONLY_FZ,
    BOSS_SERVER_ONLY as _BOSS_SERVER_ONLY_FZ,
)

_TM_SERVER_ONLY = set(_TM_SERVER_ONLY_FZ)
_SF_SERVER_ONLY = set(_SF_SERVER_ONLY_FZ)
_RLC_SERVER_ONLY = set(_RLC_SERVER_ONLY_FZ)
_BOSS_SERVER_ONLY = set(_BOSS_SERVER_ONLY_FZ)

# Transitional flag for legacy compatibility tests only.
# Set to True ONLY for transitional legacy compatibility tests; default False closes
# the answer-leak by stripping accepted[] and aliases from the client JS global.
# When False (default): strip — closes the leak.
# When True: keep accepted[] so test/replay paths that depend on the old shape still work.
_BOSS_LEGACY_CLIENT_MATCH = False

# Memory Palace — server-side defaults. Applied when gb_memory_palace_config omits
# a key or when gb_memory_palace_config is absent entirely.
_MP_DEFAULTS = {
    "concept_count": 5,
    "min_palace_options": 4,
    "enable_reverse_recall": False,
    "concept_count_grade_overrides": {"low": 3, "high": 7},
}


def _serialize_memory_palace(game, config, grade, tier) -> str:
    """Build the client-side GB_MEMORY_PALACE JS global.

    No side-disjoint stripping applies (per plan §2.2). Author content (palace
    locations, concept terms, imagery cues) is pedagogical hint material, not
    an author-supplied answer key. The "answer" for the recall test is the
    student's own placement map, submitted in the POST body and validated
    server-side.

    Args:
        game:   content_json["gb_memory_palace"] — raw dict or Pydantic model.
                May be None (mechanic not authored).
        config: content_json["gb_memory_palace_config"] — raw dict or None.
        grade:  hw grade (int or str, e.g. 7). None → default band.
        tier:   hw tier ("basic" | "premium"). Default "basic".

    Returns _safe_js_json(None) when the game is absent or has no palaces.
    Returns _safe_js_json({palaces, concepts, config}) otherwise.
    """
    # Normalise game to dict.
    if game is None:
        return _safe_js_json(None)
    if not isinstance(game, dict):
        try:
            game = game.model_dump()
        except AttributeError:
            try:
                game = dict(game)
            except Exception:
                return _safe_js_json(None)
    if not game:
        return _safe_js_json(None)

    palaces_raw = game.get("palaces") or []
    concepts_raw = game.get("concepts") or []

    # Empty palaces → signal "not authored" to runtime.
    if not palaces_raw:
        return _safe_js_json(None)

    # Normalise config to dict.
    if config is not None and not isinstance(config, dict):
        try:
            config = config.model_dump()
        except AttributeError:
            try:
                config = dict(config)
            except Exception:
                config = {}
    config_in = config or {}

    # Resolve effective config: defaults + authored overrides (None values skipped).
    cfg = dict(_MP_DEFAULTS)
    for k, v in config_in.items():
        if v is not None:
            cfg[k] = v

    # Resolve grade band → concept_count.
    hw_tier = (tier or "basic").strip().lower()
    try:
        grade_int = int(grade)
    except (TypeError, ValueError):
        grade_int = None

    overrides = cfg.get("concept_count_grade_overrides") or {}
    if grade_int is not None and 1 <= grade_int <= 4:
        concept_count = int(overrides.get("low", cfg["concept_count"]))
    elif grade_int is not None and 8 <= grade_int <= 11 and hw_tier == "premium":
        concept_count = int(overrides.get("high", cfg["concept_count"]))
    else:
        concept_count = int(cfg["concept_count"])

    # Slice concepts (front-load — author writes 7, basic G6 sees first 5).
    concepts_out = []
    for idx, c in enumerate(concepts_raw[:concept_count]):
        if not isinstance(c, dict):
            try:
                c = dict(c)
            except Exception:
                continue
        # Defensive auto-fill of id (schema validator already does this,
        # but raw dict payloads from legacy routes may skip validation).
        cid = c.get("id") or f"mp-c{idx + 1}"
        concepts_out.append({
            "id":          cid,
            "term":        c.get("term", ""),
            "description": c.get("description"),
            "image_cue":   c.get("image_cue"),
        })

    # Filter palaces: skip premium palaces when homework tier is basic.
    palaces_out = []
    for p in palaces_raw:
        if not isinstance(p, dict):
            try:
                p = dict(p)
            except Exception:
                continue
        palace_tier = (p.get("tier") or "basic").strip().lower()
        if palace_tier == "premium" and hw_tier != "premium":
            continue
        locations_out = []
        for loc in (p.get("locations") or []):
            if not isinstance(loc, dict):
                try:
                    loc = dict(loc)
                except Exception:
                    continue
            locations_out.append({
                "name":        loc.get("name", ""),
                "sensory_cue": loc.get("sensory_cue"),
                "icon":        loc.get("icon"),
            })
        palaces_out.append({
            "key":            p.get("key", ""),
            "name":           p.get("name", ""),
            "icon":           p.get("icon"),
            "description":    p.get("description"),
            "subject_family": p.get("subject_family"),
            "tier":           palace_tier,
            "locations":      locations_out,
        })

    wire = {
        "palaces":  palaces_out,
        "concepts": concepts_out,
        "config": {
            "concept_count":       concept_count,
            "min_palace_options":  int(cfg["min_palace_options"]),
            "enable_reverse_recall": bool(cfg["enable_reverse_recall"]),
        },
    }
    return _safe_js_json(wire)


def _serialize_boss_questions(items, boss_meta=None) -> str:
    """Build the client-side BOSS_QUESTIONS array (side-disjoint, answer-leak prevention).

    Runs the existing boss shape-adapter logic (editor shape → template shape),
    then strips every key in _BOSS_SERVER_ONLY from each adapted question.

    Strips (default, _BOSS_LEGACY_CLIENT_MATCH=False):
      - accepted[] (legacy deterministic match list — now server-only)
      - acceptable[] (template-shape deterministic match list — server-only)
      - ans / accepted_answers (legacy aliases)
      - answer_spec (the full grading contract — server uses, client never needs)

    Preserves student-visible fields: id, tier, damage, bloom, pisa, prompt, hints[].
    Hints stay client-side (spec §8: hints are pre-written for Sub Basic).

    Legacy flag: if _BOSS_LEGACY_CLIENT_MATCH is True, accepted/acceptable are NOT
    stripped. Use only for back-compat tests; never in production.

    Returns _safe_js_json output so </script> injection vectors are escaped.
    """
    if not items:
        return _safe_js_json([])

    # Normalise items to list of dicts.
    data = []
    for i, item in enumerate(items):
        if isinstance(item, dict):
            data.append(item)
        else:
            try:
                data.append(item.model_dump())
            except AttributeError:
                try:
                    data.append(dict(item))
                except Exception:
                    continue

    # Run the existing boss shape adapter (editor shape → template shape).
    # Mirrors the logic in the _ARRAY_CONSTANTS loop for key=="boss_questions".
    adapted = []
    for i, item in enumerate(data):
        if not isinstance(item, dict):
            continue
        # Already template shape? pass through (but still strip server-only keys below).
        if "prompt" in item and "acceptable" in item:
            adapted.append(item)
            continue
        dmg = int(item.get("dmg", 10) or 10)
        tier = "easy" if dmg <= 10 else "medium" if dmg <= 20 else "hard"
        bloom, pisa = _parse_bloom_pisa(item.get("tags", ""), "L3", "L3")
        ans_list = item.get("ans") or [""]
        if not isinstance(ans_list, list):
            ans_list = [str(ans_list)]
        hint_raw = item.get("hint") or ""
        hint_plain = _strip_html(hint_raw)
        hint_parts = [p.strip() for p in re.split(r"\n|\s\|\s|•", hint_plain) if p.strip()]
        if not hint_parts:
            hint_parts = [hint_plain or "—"]
        while len(hint_parts) < 3:
            hint_parts.append(hint_parts[-1])
        adapted.append({
            # Synthetic id matches the route's recognized format in
            # routes/ai.py::_fb_find_boss_question (bq_{i}); keeping these in
            # sync is what stops boss grading from silently 404-ing on rows
            # that lack an authored id. See migrate_boss_question_ids.py
            # for the one-time backfill of pre-existing rows.
            "id":         item.get("id") or f"bq_{i}",
            "tier":       tier,
            "damage":     dmg,
            "bloom":      bloom,
            "pisa":       pisa,
            "prompt":     item.get("q", ""),
            "acceptable": [a for a in ans_list if a],
            "hints":      hint_parts[:3],
            # Forward-compat: carry through new optional fields if present.
            **({"pisa_level": item["pisa_level"]} if item.get("pisa_level") else {}),
            **({"bloom_level": item["bloom_level"]} if item.get("bloom_level") else {}),
            **({"hint_cost_per_use": item["hint_cost_per_use"]} if item.get("hint_cost_per_use") is not None else {}),
        })

    # Strip server-only fields. The full _BOSS_SERVER_ONLY set covers both the
    # editor-shape keys (ans, accepted_answers, answer_spec) and the template-shape
    # key (acceptable). When _BOSS_LEGACY_CLIENT_MATCH=True we keep acceptable for
    # back-compat (test/replay only — never production).
    strip_set = _BOSS_SERVER_ONLY
    if _BOSS_LEGACY_CLIENT_MATCH:
        # Legacy: keep accepted[] alias; still strip ans/accepted_answers/answer_spec
        strip_set = _BOSS_SERVER_ONLY - {"accepted", "acceptable"}
    else:
        # Default: also strip the template-shape list
        strip_set = _BOSS_SERVER_ONLY | {"acceptable"}

    cleaned = []
    for item in adapted:
        cleaned.append({k: v for k, v in item.items() if k not in strip_set})

    return _safe_js_json(cleaned)


def _serialize_boss_meta(meta) -> str:
    """Build the client-side BOSS_META object.

    If meta is None, returns 'null' (JS literal).
    Otherwise serialises the BossMeta model dict.
    Anti-cheat fields are included — they're config the client reads (not answers).
    """
    if meta is None:
        return _safe_js_json(None)
    # Normalise: accept Pydantic model or raw dict.
    if not isinstance(meta, dict):
        try:
            meta = meta.model_dump()
        except AttributeError:
            try:
                meta = dict(meta)
            except Exception:
                return _safe_js_json(None)
    return _safe_js_json(meta)


def _serialize_real_life_challenge(case) -> str:
    """Build the client-side RLC_CASE JS global (side-disjoint, answer-leak prevention).

    Strips from every nested level:
      - options[].is_correct, options[].consequence  (decision answer keys)
      - concept_chips[].is_correct                   (concept answer key)
      - steps[].acceptable_keywords                  (AI grading anchor; server-only)

    The client never sees which option is correct, which chip is correct, or what
    keywords trigger reasoning credit. All grading goes through the
    /api/ai/check-answer endpoint with phase=real-life-challenge.

    Returns _safe_js_json output so </script> injection vectors are escaped.
    """
    if case is None:
        return _safe_js_json(None)

    # Normalise to dict — accept Pydantic model or raw dict from content_json.
    if not isinstance(case, dict):
        try:
            case = case.model_dump()
        except AttributeError:
            try:
                case = dict(case)
            except Exception:
                return _safe_js_json(None)

    if not case:
        return _safe_js_json(None)

    # Deep-copy the top-level dict; we'll rebuild nested lists in place.
    clean = {k: v for k, v in case.items()}

    # Strip server-only fields from each step.
    raw_steps = clean.get("steps") or []
    clean_steps = []
    for step in raw_steps:
        if not isinstance(step, dict):
            continue
        # Strip acceptable_keywords from the step.
        clean_step = {k: v for k, v in step.items() if k not in _RLC_SERVER_ONLY}

        # Strip is_correct + consequence from each option within the step.
        if clean_step.get("options"):
            clean_step["options"] = [
                {k: v for k, v in opt.items() if k not in _RLC_SERVER_ONLY}
                for opt in clean_step["options"]
                if isinstance(opt, dict)
            ]

        # Strip is_correct from each concept chip within the step.
        if clean_step.get("concept_chips"):
            clean_step["concept_chips"] = [
                {k: v for k, v in chip.items() if k not in _RLC_SERVER_ONLY}
                for chip in clean_step["concept_chips"]
                if isinstance(chip, dict)
            ]

        clean_steps.append(clean_step)

    clean["steps"] = clean_steps
    return _safe_js_json(clean)


def _serialize_sentence_fill(items: list) -> str:
    """Strip server-only fields from gb_sentence_fill items before JSON-encoding.

    - `answers` and `explanations` are always stripped (answer-leak prevention).
    - `word_bank` is also stripped for free_recall items (it's null anyway, but
      belt-and-suspenders in case an author accidentally set it on a free_recall item).

    Uses _safe_js_json for the final encoding so </script> injection vectors
    are escaped consistently with all other inline constants.
    """
    cleaned = []
    for item in (items or []):
        if not isinstance(item, dict):
            continue
        clean_item = {k: v for k, v in item.items() if k not in _SF_SERVER_ONLY}
        # word_bank is null in free_recall mode \u2014 strip too
        if clean_item.get("mode") == "free_recall":
            clean_item.pop("word_bank", None)
        cleaned.append(clean_item)
    return _safe_js_json(cleaned)


def _serialize_tile_match(
    items: "list | None",
    legacy_pairs: "list | None" = None,
) -> str:
    """Build the client-side GB_TILE_MATCH flat array.

    Priority: `items` (gb_tile_match) wins over `legacy_pairs` (gb_memory_match).

    Output shape — SIDE-DISJOINT (answer-leak prevention).  Each pair
    contributes exactly TWO entries; left entries never carry the right text
    and vice versa.  The runtime sends both IDs to the server check-answer
    endpoint and receives ``correct: bool`` back — the client never holds
    both sides of a pair simultaneously.

    [
        {"id": "tm_001", "side": "left",  "text": "F = ma"},
        {"id": "tm_001", "side": "right", "text": "Newton's 2nd"},
        ...
    ]

    Legacy shim: ``gb_memory_match`` rows (list of [a, b] 2-tuples) are
    converted on-the-fly to the new shape so old DB records render correctly
    without a schema migration.
    """
    source: list = []

    if items:
        # New gb_tile_match — strip server-only fields, then split sides.
        for item in items:
            if not isinstance(item, dict):
                # Accept Pydantic models too (model_dump via dict protocol).
                try:
                    item = dict(item)
                except Exception:
                    continue
            pair_id = item.get("id", "tm_unknown")
            source.append({"id": pair_id, "side": "left",  "text": item.get("left", "")})
            source.append({"id": pair_id, "side": "right", "text": item.get("right", "")})
            # NOTE: _TM_SERVER_ONLY fields (e.g. `explanation`) are intentionally
            # omitted — they travel only in the check-answer endpoint response.
    elif legacy_pairs:
        # Legacy shim — [[a, b], ...] → new side-disjoint shape.
        for i, pair in enumerate(legacy_pairs):
            if not (isinstance(pair, (list, tuple)) and len(pair) >= 2):
                continue
            pair_id = f"tm_legacy_{i:03d}"
            source.append({"id": pair_id, "side": "left",  "text": str(pair[0])})
            source.append({"id": pair_id, "side": "right", "text": str(pair[1])})

    return _safe_js_json(source)


# --------------------------------------------------------------------------- #
# TTT — side-disjoint serialization (answer-leak prevention).
# --------------------------------------------------------------------------- #

# In-memory answer key: {hw_id: {item_id: correct_str}}.
# Populated each time inject() processes a gb_ttt array.
# Same in-memory scar-tissue pattern as _TM_ATTEMPTS / _RLC_ATTEMPTS.
_TTT_ANSWER_KEY: dict = {}


def _is_grade8_math_demo_context(runtime_context: dict | None) -> bool:
    """Temporary showcase rule: Grade 8 algebra/geometriya demos avoid text-heavy games."""
    if not isinstance(runtime_context, dict):
        return False
    subject = str(runtime_context.get("subject") or "").strip().lower()
    try:
        grade = int(runtime_context.get("grade") or 0)
    except (TypeError, ValueError):
        grade = 0
    return grade == 8 and subject in {"math-algebra", "geometriya-g7-11"}


def _ttt_from_why_chain(items: list) -> list:
    """Convert legacy Why Chain fill-items into TTT items for the G8 math demo.

    Why Chain is visually close to sentence filling ("Zanjir"), which is too
    writing-heavy for the current math showcase. The original items are kept
    in content_json, but the rendered demo gets quick multiple-choice TTT
    questions instead.
    """
    symbol_bank = ["/", "×", "+", "−", "=", "%", "|x − a|", "|a|", "a"]
    authored_answers: list[str] = []
    for raw in items or []:
        if not isinstance(raw, dict):
            continue
        ans = raw.get("inv") or raw.get("correct") or raw.get("answer")
        if ans is not None and str(ans).strip():
            authored_answers.append(str(ans).strip())

    out: list[dict] = []
    for idx, raw in enumerate(items or []):
        if not isinstance(raw, dict):
            continue
        q = str(raw.get("q") or raw.get("prompt") or "").strip()
        correct = str(raw.get("inv") or raw.get("correct") or raw.get("answer") or "").strip()
        if not q or not correct:
            continue
        q = q.replace("___", "_____")
        distractors: list[str] = []
        for candidate in [*authored_answers, *symbol_bank]:
            candidate = str(candidate).strip()
            if candidate and candidate != correct and candidate not in distractors:
                distractors.append(candidate)
            if len(distractors) >= 3:
                break
        if len(distractors) < 3:
            continue
        out.append(
            {
                "id": f"demo-ttt-{idx + 1}",
                "q": q,
                "correct": correct,
                "distractors": distractors[:3],
            }
        )
    return out[:6]


def _serialize_ttt(items: list, config: dict) -> tuple:
    """Build the client-side GB_TTT wire format (side-disjoint, answer-leak prevention).

    Returns (wire_items, answer_key):
      - wire_items: list of {id, q, options[]} — client-visible; correct+distractors stripped.
      - answer_key: {item_id: correct_str} — server-only; stashed in _TTT_ANSWER_KEY[hw_id].

    Options are deterministically shuffled by item_id seed so re-renders are stable
    (random.Random(item_id).shuffle is deterministic across processes for the same seed).

    Items with empty q or empty correct are silently dropped.
    Auto-assigns id = "ttt-{idx}" (1-based) when item.id is absent.
    """
    wire: list = []
    answer_key: dict = {}
    for idx, raw in enumerate(items or []):
        if not isinstance(raw, dict):
            continue
        item_id = (raw.get("id") or "").strip() or f"ttt-{idx + 1}"
        q = (raw.get("q") or "").strip()
        correct = (raw.get("correct") or "").strip()
        if not q or not correct:
            continue
        distractors = [
            d for d in (raw.get("distractors") or [])
            if isinstance(d, str) and d.strip()
        ]
        opts = [correct, *distractors]
        rng = random.Random(item_id)
        rng.shuffle(opts)
        wire.append({"id": item_id, "q": q, "options": opts})
        answer_key[item_id] = correct
    return wire, answer_key


def get_ttt_answer_key(hw_id: str) -> dict:
    """Return the answer key for a previously injected homework.

    Returns {item_id: correct_str} or {} if the homework has not been rendered.
    Called by the /api/ai/check-answer?phase=ttt route handler.
    """
    return _TTT_ANSWER_KEY.get(hw_id) or {}


def _find_js_const_statement_end(src: str, literal_start: int) -> int:
    opener = src[literal_start]
    closer = {"[": "]", "{": "}"}[opener]
    depth = 0
    quote: str | None = None
    escaped = False
    line_comment = False
    block_comment = False
    i = literal_start

    while i < len(src):
        ch = src[i]
        nxt = src[i + 1] if i + 1 < len(src) else ""

        if line_comment:
            if ch in "\r\n":
                line_comment = False
        elif block_comment:
            if ch == "*" and nxt == "/":
                block_comment = False
                i += 1
        elif quote:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == quote:
                quote = None
        elif ch in ("'", '"', "`"):
            quote = ch
        elif ch == "/" and nxt == "/":
            line_comment = True
            i += 1
        elif ch == "/" and nxt == "*":
            block_comment = True
            i += 1
        elif ch == opener:
            depth += 1
        elif ch == closer:
            depth -= 1
            if depth == 0:
                end = i + 1
                while end < len(src) and src[end].isspace():
                    end += 1
                if end < len(src) and src[end] == ";":
                    return end + 1
                raise ValueError("JS const literal is not terminated with a semicolon")
        i += 1

    raise ValueError("JS const literal did not terminate")


def _replace_js_const(html: str, const_name: str, replacement: str) -> str:
    match = re.search(rf"\bconst\s+{re.escape(const_name)}\s*=", html)
    if not match:
        return html
    literal_start = match.end()
    while literal_start < len(html) and html[literal_start].isspace():
        literal_start += 1
    if literal_start >= len(html) or html[literal_start] not in "[{":
        return html
    end = _find_js_const_statement_end(html, literal_start)
    return html[: match.start()] + replacement + html[end:]


def _strip_html(s) -> str:
    """Strip HTML tags + decode common entities. Used for plain-text fields like
    flashcard front terms, which the template renders via textContent."""
    if not s:
        return ""
    text = str(s)
    text = re.sub(r"<[^>]+>", " ", text)
    text = (
        text.replace("&nbsp;", " ")
            .replace("&amp;", "&")
            .replace("&lt;", "<")
            .replace("&gt;", ">")
            .replace("&quot;", '"')
            .replace("&#039;", "'")
            .replace("&apos;", "'")
    )
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _split_answers(value) -> list:
    """Normalize an answer field (string or list) into a list of accepted strings."""
    if value is None:
        return []
    if isinstance(value, list):
        return [str(v).strip() for v in value if str(v).strip()]
    s = str(value).strip()
    if not s:
        return []
    # Accept common separators so authors can cram multiple answers into one input.
    parts = [p.strip() for p in re.split(r"\s*(?:\|\||;|\n)\s*", s) if p.strip()]
    return parts or [s]


def _rl_adapt_to_template(rl: dict) -> dict:
    """Convert builder-shape real_life ({badge, story, q1..q6, endTitle, endSub})
    into the template-shape {title, story, questions:[...], closure:{...}}."""
    out = dict(rl)
    badge = rl.get("badge") or "VAZIFA"
    title = rl.get("title") or badge
    story = rl.get("story") or ""

    def make_text_q(key: str, bloom: str, pisa: str) -> dict:
        q = rl.get(key) or {}
        capture = bool(q.get("capture"))
        answers = _split_answers(q.get("ans"))
        fb_html = q.get("fb") or ""
        hint = _strip_html(fb_html) or ""
        q_type = "text-with-capture" if capture else "text"
        out_q = {
            "id":                key.upper(),
            "type":              q_type,
            "bloom":             bloom,
            "pisa":              pisa,
            "capture":           capture,
            "prompt":            q.get("prompt") or "",
            "acceptableAnswers": answers or ["—"],
            "hint":              hint,
        }
        if capture:
            out_q["expectedWork"] = hint
        return out_q

    def make_fields_q(key: str, bloom: str, pisa: str) -> dict:
        q = rl.get(key) or {}
        # If author provided no fields[] but did provide ans, fall through to a
        # single-input text question — otherwise the player gets a phantom
        # multi-input box that only accepts "—".
        fields_in = q.get("fields") or []
        if not fields_in and (q.get("ans") or q.get("prompt")):
            return make_text_q(key, bloom, pisa)
        capture = bool(q.get("capture"))
        fields_out = []
        for f in fields_in:
            if not isinstance(f, dict):
                continue
            fields_out.append({
                "label":      f.get("label") or f.get("id") or "",
                "acceptable": _split_answers(f.get("ans")) or ["—"],
            })
        if not fields_out:
            fields_out = [{"label": "Javob", "acceptable": ["—"]}]
        return {
            "id":      key.upper(),
            "type":    "multi-input",
            "bloom":   bloom,
            "pisa":    pisa,
            "capture": capture,
            "prompt":  q.get("prompt") or "",
            "fields":  fields_out,
        }

    def make_open_q(key: str, bloom: str, pisa: str) -> dict:
        q = rl.get(key) or {}
        return {
            "id":       key.upper(),
            "type":     "textarea",
            "bloom":    bloom,
            "pisa":     pisa,
            "capture":  bool(q.get("capture")),
            "prompt":   q.get("prompt") or "",
            "accepted": "open-ended",
        }

    # Only emit a question slot if the author actually provided content for it.
    # Phantom empty questions (acceptableAnswers: ["—"], no prompt) make the
    # runtime un-completable.
    def _has(key: str) -> bool:
        q = rl.get(key) or {}
        return bool((q.get("prompt") or "").strip()) or bool(q.get("ans")) or bool(q.get("fields"))

    questions = []
    if _has("q1"): questions.append(make_text_q("q1", "L3", "P2"))
    if _has("q2"): questions.append(make_fields_q("q2", "L2", "P2"))
    if _has("q3"): questions.append(make_text_q("q3", "L4", "P3"))
    if _has("q4"): questions.append(make_text_q("q4", "L4", "P3"))
    if _has("q5"):
        questions.append(make_open_q("q5", "L5", "P4")
                         if (rl.get("q5") or {}).get("open")
                         else make_text_q("q5", "L3", "P2"))
    if _has("q6"): questions.append(make_text_q("q6", "L3", "P2"))

    out["title"] = title
    out["story"] = story
    out["questions"] = questions
    out["closure"] = {
        "title":   rl.get("endTitle") or "Loyiha tugadi ✓",
        "message": rl.get("endSub")   or "Ajoyib ish! Siz vazifani muvaffaqiyatli yakunladingiz.",
    }
    return out


def _parse_bloom_pisa(tags: str, default_bloom: str = "L2", default_pisa: str = "L2"):
    """Extract Bloom and PISA level codes from a tags string like
    ``[Bloom: L3 | PISA: L2 | Damage: -20 HP]``. Returns (bloom, pisa)."""
    if not tags:
        return default_bloom, default_pisa
    src = str(tags)
    bm = re.search(r"bloom\s*:\s*([A-Za-z]?\d+)", src, flags=re.IGNORECASE)
    pm = re.search(r"pisa\s*:\s*([A-Za-z]?\d+)", src, flags=re.IGNORECASE)
    bloom = (bm.group(1) if bm else default_bloom).upper()
    pisa = (pm.group(1) if pm else default_pisa).upper()
    if not bloom.startswith("L"):
        bloom = "L" + bloom.lstrip("Ll")
    if not pisa.startswith("L"):
        pisa = "L" + pisa.lstrip("Ll")
    return bloom, pisa


def _strip_text_tags_keep_media(s) -> str:
    """Strip formatting tags (p/b/i/br/span/div/strong/em/u/h1-h6) but PRESERVE
    inline <img ...> and <svg>...</svg> elements. Used for the flashcard front
    term, which now renders via innerHTML so users can embed visuals via the
    RichField toolbar. NBSP/whitespace normalized; other entities left intact
    so &amp; etc. survive into innerHTML correctly."""
    if not s:
        return ""
    text = str(s)
    # 1. Extract <img ...> and <svg>...</svg> into placeholders so the tag
    #    stripper below doesn't eat them.
    placeholders: list[str] = []

    def _stash(match):
        placeholders.append(match.group(0))
        return f"\x00MEDIA{len(placeholders) - 1}\x00"

    # SVG first (multiline body), then img.
    text = re.sub(r"<svg\b[^>]*>.*?</svg>", _stash, text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<img\b[^>]*?/?>", _stash, text, flags=re.IGNORECASE)
    # 2. Strip all remaining tags (formatting only — p, b, i, br, span, div, etc.).
    text = re.sub(r"<[^>]+>", " ", text)
    # 3. Normalize whitespace + nbsp.
    text = text.replace("&nbsp;", " ")
    text = re.sub(r"\s+", " ", text).strip()
    # 4. Restore stashed media.
    def _restore(match):
        idx = int(match.group(1))
        return placeholders[idx] if 0 <= idx < len(placeholders) else ""

    text = re.sub(r"\x00MEDIA(\d+)\x00", _restore, text)
    return text


def _normalize_reading_checkpoint(cp) -> dict:
    """Normalize a reading checkpoint to the runtime's
    {prompt, ans, acceptable[], fb} shape.

    Accepts both:
      - top-level checkpoints[] entries (canonical {prompt, ans, fb} or
        legacy {q, ans, fb})
      - segment-nested s["checkpoint"] entries ({q, ans[], tags?, fb?})

    `ans` may be a string (legacy fixtures) or a list (segment-aware
    adapter output). When it's a list, the head is the canonical answer
    and the tail goes into `acceptable[]` for the runtime's multi-answer
    matcher (cp.ans + cp.acceptable[] is the existing contract). Authors
    can also supply `acceptable[]` explicitly.
    """
    if not isinstance(cp, dict):
        return {"prompt": "", "ans": "", "acceptable": [], "fb": ""}
    raw_ans = cp.get("ans")
    if isinstance(raw_ans, list):
        ans_str = str(raw_ans[0]) if raw_ans else ""
        acceptable = [str(a) for a in raw_ans[1:]]
    else:
        ans_str = str(raw_ans or "")
        acceptable = []
    extra_acc = cp.get("acceptable")
    if isinstance(extra_acc, list):
        acceptable = acceptable + [str(a) for a in extra_acc]
    return {
        "prompt":     str(cp.get("prompt") or cp.get("q") or ""),
        "ans":        ans_str,
        "acceptable": acceptable,
        "fb":         str(cp.get("fb") or ""),
    }


def inject(
    content_json: dict,
    meta_override: dict | None = None,
    *,
    runtime_context: dict,
) -> str:
    """Inject content_json into the Perfect Homework HTML template.

    content_json: full schema per CONTRACTS §1
    meta_override: optional {title, subject_display, section, cefr_level} to force
                   specific values. If None, uses content_json['meta'].
    runtime_context: required keyword-only dict — AI tutor runtime hook context
                     (window.NETS_CTX + runtime.js). Always injected before </body>.

    Returns: rendered HTML string.
    """
    html = _TEMPLATE
    meta = meta_override or content_json.get("meta") or {}

    # Boss name — author override (content_json.boss_name) wins over the
    # subject-aware default. Stamped onto the runtime context so the inline
    # template script (which reads window.NETS_CTX.boss_name on
    # DOMContentLoaded) can populate the data-boss-name hooks T1 added.
    if runtime_context is not None and "boss_name" not in runtime_context:
        runtime_context = dict(runtime_context)
        runtime_context["boss_name"] = boss_name_for(
            runtime_context.get("subject"),
            content_json.get("boss_name") if isinstance(content_json, dict) else None,
        )

    # 0. Stamp <html lang> with the resolved runtime language so the runtime
    # i18n layer (RUNTIME_LABELS / PHASE_LABELS) and any assistive tech
    # see the correct locale. Falls back to 'uz' if runtime_context omits lang.
    _lang = (runtime_context.get("lang") if runtime_context else None) or "uz"
    if not isinstance(_lang, str) or len(_lang) > 8:
        _lang = "uz"
    html = re.sub(
        r'<html\s+lang="[^"]*"',
        f'<html lang="{_esc(_lang)}"',
        html,
        count=1,
    )

    # 1. Replace title h1 (first occurrence only)
    title = meta.get("title", "Homework")
    subject_display = meta.get("subject_display", "")
    section = meta.get("section", "")

    html = re.sub(
        r"<h1>.*?</h1>",
        f"<h1>NETS · {_esc(title)}</h1>",
        html,
        count=1,
    )

    # 1b. Bug #3: Replace browser <title> tag inside <head> so the tab text
    # tracks the homework's meta.title (with row-level fallback already
    # applied by render_homework). The template ships with a literal
    # default ("NETS · Kvadrat tenglama") that otherwise stays stale across
    # all rendered homeworks.
    #
    # Scope to the <head>...</head> window so we don't accidentally rewrite
    # any inline <title> element inside an SVG glyph that may live in body
    # markup. The replacement is idempotent — running it again on the
    # already-rendered HTML yields the same string.
    head_match = re.search(r"<head\b[^>]*>.*?</head>", html, flags=re.DOTALL | re.IGNORECASE)
    if head_match:
        head_block = head_match.group(0)
        new_head = re.sub(
            r"<title>.*?</title>",
            f"<title>NETS · {_esc(title)}</title>",
            head_block,
            count=1,
            flags=re.DOTALL | re.IGNORECASE,
        )
        if new_head != head_block:
            html = html[:head_match.start()] + new_head + html[head_match.end():]

    # 2. Replace caption div (first occurrence — the one at top of homework)
    if subject_display or section:
        caption_text = f"{subject_display}"
        if section:
            caption_text += f" · {section}"
        html = re.sub(
            r'<div class="caption">.*?</div>',
            f'<div class="caption">{_esc(caption_text)}</div>',
            html,
            count=1,
        )

    # 3. Replace each array constant
    for (key, const_name) in _ARRAY_CONSTANTS:
        data = content_json.get(key, [])
        if data is None:
            data = []
        # Quote/fact sequence: pick the opening quote and mid-homework break
        # cards per inject call. Source is the new
        # `gate_quote` envelope ({mode, pinned_id?, custom?}); falls back to the
        # legacy `quotes` array for in-flight rows. Slot 0 is quote-only before
        # preview, slot 1 is mixed after preview, slot 2 is fact-only after
        # flashcards.
        if key == "quotes":
            envelope = content_json.get("gate_quote")
            if envelope is None:
                envelope = content_json.get("quotes")
            data = quotes_service.select_sequence(envelope)

        # Shape adapter: Memory Sprint editor emits type codes MC|TF|YNNG, but the
        # template renders item.type directly as a human label in "Savol X / Y · {type}".
        # Map codes to Uzbek labels so the runtime UI reads naturally. Legacy values
        # (KO, full-label strings) are accepted and passed through.
        if key == "memory_sprint":
            _MS_LABELS = {
                "MC":   "Ko'p variantli",
                "TF":   "To'g'ri / Noto'g'ri",
                "YNNG": "Ha / Yo'q / Aniq emas",
                "KO":   "Ko'p variantli",  # legacy
            }
            adapted = []
            for q in data:
                if not isinstance(q, dict):
                    continue
                q2 = dict(q)
                raw_type = q2.get("type", "MC")
                q2["type"] = _MS_LABELS.get(raw_type, raw_type)
                # Template expects options, correct, prompt, subtitle, tags, explain.
                q2.setdefault("options", ["", "", "", ""])
                q2.setdefault("correct", 0)
                q2.setdefault("prompt", "")
                q2.setdefault("subtitle", "")
                q2.setdefault("tags", "[Bloom: L1 | PISA: L1]")
                q2.setdefault("explain", "")
                adapted.append(q2)
            data = adapted

        # Shape adapter: Adaptive Quiz editor emits {q, tags, tier: "EASY", ans[], capture, hint, media}
        # but the template expects {id, tier: "easy", bloom, pisa, prompt, answer, work}.
        # The template filters by lowercase tier strings in gbAQPickItem, so we lowercase tier.
        # We also parse Bloom/PISA out of the tags string.
        if key == "gb_adaptive_quiz":
            adapted = []
            for i, item in enumerate(data):
                if not isinstance(item, dict):
                    continue
                # Already in template shape? pass through.
                if "prompt" in item and "answer" in item:
                    adapted.append(item)
                    continue
                tier = str(item.get("tier", "easy")).lower()
                if tier not in ("easy", "medium", "hard"):
                    tier = "easy"
                bloom, pisa = _parse_bloom_pisa(item.get("tags", ""), "L2", "L2")
                ans_list = item.get("ans") or [""]
                if not isinstance(ans_list, list):
                    ans_list = [str(ans_list)]
                # Strip empties; preserve order; primary answer = first non-empty.
                acceptable = [str(a).strip() for a in ans_list if str(a).strip()]
                if not acceptable:
                    acceptable = [""]
                answer = acceptable[0]
                hint_text = item.get("hint") or ""
                adapted.append({
                    "id":     item.get("id", f"A{i+1}"),
                    "tier":   tier,
                    "bloom":  bloom,
                    "pisa":   pisa,
                    "prompt": item.get("q", ""),
                    "answer": answer,
                    # Wave 2 fix: runtime checks acceptable[] first, falls back to answer.
                    "acceptable": acceptable,
                    # work = author-provided hint/explanation only. Don't default
                    # to "Javob: X" — the runtime already shows the correct answer
                    # in the wrong-answer feedback, and a default that just repeats
                    # the answer prints it twice (see Unit 19 regression 2026-04-29).
                    "work":   hint_text,
                    # Preserve extras for future use
                    "capture": bool(item.get("capture", False)),
                    "ans_all": acceptable,
                })
            # Ensure each tier has at least one DISTINCT item so the picker never
            # returns undefined and the student never sees the same question twice
            # in different tiers. If the source data collapses everything into one
            # tier (common when an importer hardcodes "tier": "MEDIUM"), redistribute
            # real items across easy/medium/hard by Bloom level — fall back to index
            # buckets when Bloom is missing.
            if adapted:
                tiers_present = {x["tier"] for x in adapted}
                missing = [t for t in ("easy", "medium", "hard") if t not in tiers_present]
                if missing and len(adapted) >= 2:
                    def _bloom_to_tier(b: str) -> str:
                        # L1-L2 → easy, L3 → medium, L4+ → hard. Default medium.
                        m = re.search(r"L(\d)", str(b or ""))
                        if not m:
                            return "medium"
                        n = int(m.group(1))
                        return "easy" if n <= 2 else ("hard" if n >= 4 else "medium")

                    have_bloom = any(re.search(r"L\d", str(x.get("bloom") or "")) for x in adapted)
                    if have_bloom:
                        # Bloom-driven redistribution
                        for x in adapted:
                            x["tier"] = _bloom_to_tier(x.get("bloom"))
                    else:
                        # Index buckets: first third → easy, middle → medium, last third → hard
                        n = len(adapted)
                        for i, x in enumerate(adapted):
                            if   i < n / 3:        x["tier"] = "easy"
                            elif i < 2 * n / 3:    x["tier"] = "medium"
                            else:                  x["tier"] = "hard"

                    # If a tier is still empty, fill it with the item whose Bloom
                    # is *closest to* that tier's target band — never with the most
                    # advanced item demoted to easy or vice-versa.
                    def _bloom_n(x):
                        m = re.search(r"L(\d)", str(x.get("bloom") or ""))
                        return int(m.group(1)) if m else 3
                    target = {"easy": 1, "medium": 3, "hard": 5}
                    by_tier = {"easy": [], "medium": [], "hard": []}
                    for x in adapted:
                        by_tier.setdefault(x["tier"], []).append(x)
                    for t in ("easy", "medium", "hard"):
                        if by_tier[t]:
                            continue
                        # Find a donor tier with > 1 item; among its items pick the
                        # one whose Bloom level is closest to target[t].
                        donors = [k for k in ("easy", "medium", "hard") if k != t and len(by_tier[k]) >= 2]
                        if not donors:
                            continue
                        # Choose donor whose pool has an item closest to target[t]
                        best = None  # (donor_key, item_index, distance)
                        for d in donors:
                            for i, item in enumerate(by_tier[d]):
                                dist = abs(_bloom_n(item) - target[t])
                                if best is None or dist < best[2]:
                                    best = (d, i, dist)
                        if best:
                            d, i, _ = best
                            moved = by_tier[d].pop(i)
                            moved["tier"] = t
                            by_tier[t].append(moved)
            data = adapted

        # Shape adapter: Sentence Fill editor emits {q, inv, reprompts[]} but the
        # template expects {id, bloom, pisa, chain:[{level, probe, expect}], invariant}.
        # We wrap the single q into a 3-level chain (using reprompts as levels 2-3 probes),
        # and invariant = inv.
        if key == "gb_why_chain":
            adapted = []
            for i, item in enumerate(data):
                if not isinstance(item, dict):
                    continue
                # Already nested? pass through.
                if isinstance(item.get("chain"), list) and item["chain"]:
                    if "invariant" not in item and "inv" in item:
                        item = dict(item); item["invariant"] = item.get("inv", "")
                    adapted.append(item)
                    continue
                q = item.get("q", "")
                inv = item.get("inv", "") or item.get("invariant", "")
                reprompts = item.get("reprompts") or []
                if not isinstance(reprompts, list):
                    reprompts = []
                # Wave 2: per-level expects. If author provides expects[], use them; else
                # fall back to invariant (legacy behavior).
                expects = item.get("expects") or []
                if not isinstance(expects, list):
                    expects = []
                # Build a chain of up to 3 levels from [q] + reprompts, expect = per-level
                # keyword (or invariant fallback).
                levels = [q] if q else []
                for rp in reprompts:
                    if len(levels) >= 3:
                        break
                    if rp:
                        levels.append(rp)
                while len(levels) < 3:
                    levels.append(q or "Keyingi qadam?")
                chain = []
                for li, probe in enumerate(levels[:3]):
                    per_level_expect = ""
                    if li < len(expects):
                        per_level_expect = str(expects[li] or "").strip()
                    chain.append({
                        "level":  li + 1,
                        "probe":  probe,
                        "expect": per_level_expect or inv,
                    })
                adapted.append({
                    "id":        item.get("id", f"C{i+1}"),
                    "bloom":     "L3",
                    "pisa":      "L3",
                    "chain":     chain,
                    "invariant": inv or "—",
                })
            data = adapted

        # Shape adapter: builder stores flashcards as flat {term, def, cluster, hint?, media?}.
        # Template expects {cluster, front:{term, term_html?, media?, formula?}, back:{definition, bullets?, hook}}.
        if key == "flashcards":
            adapted = []
            for card in data:
                if not isinstance(card, dict):
                    continue
                # Already nested shape — pass through.
                if isinstance(card.get("front"), dict) or isinstance(card.get("back"), dict):
                    adapted.append(card)
                    continue
                cluster = card.get("cluster") or "QOIDA"
                # Plain-text fallback (used for side-peek cards via textContent).
                term_plain = _strip_html(card.get("term") or "")
                # Mixed HTML — formatting stripped but inline <img>/<svg> preserved
                # so users can embed visuals inside the term RichField.
                term_html = _strip_text_tags_keep_media(card.get("term") or "")
                definition = card.get("def") or ""
                # Structured front media (dedicated builder zone above the term).
                media = card.get("media") if isinstance(card.get("media"), dict) else None
                front_media_html = ""
                if media:
                    if media.get("type") == "image" and media.get("src"):
                        front_media_html = (
                            f'<img src="{_esc(media["src"])}" '
                            f'alt="{_esc(media.get("alt") or "")}" />'
                        )
                    elif media.get("type") == "svg" and media.get("html"):
                        front_media_html = media["html"]
                adapted.append({
                    "cluster": cluster,
                    "front": {
                        "term": term_plain,
                        "term_html": term_html,
                        "media": front_media_html,
                    },
                    "back": {
                        "definition": definition,
                        "bullets": [],
                        "hook": card.get("hint") or "",
                    },
                })
            data = adapted

        # Shape adapter: Mystery Box — contract uses [{category, q, a}] objects.
        # Pre-compute the shared picker label list (union of all items' categories,
        # in original first-occurrence order) and stamp it onto every box so the
        # runtime can render the ID step without rescanning. Empty/missing
        # categories are dropped from the picker; if the union is empty, the
        # runtime should fall back to a confirmation-only ID step.
        if key == "gb_mystery_box":
            seen = []
            for item in data:
                if not isinstance(item, dict):
                    continue
                cat = (item.get("category") or "").strip()
                if cat and cat not in seen:
                    seen.append(cat)
            adapted = []
            for item in data:
                if not isinstance(item, dict):
                    continue
                adapted.append({
                    "category": str(item.get("category") or ""),
                    "q":        str(item.get("q") or ""),
                    "a":        str(item.get("a") or ""),
                    "labels":   list(seen),
                })
            data = adapted

        # Shape adapter: Puzzle Lock — contract uses [{content, q, a}] objects.
        # Template reads same shape. Normalize string fields to be safe and accept
        # legacy aliases (text→content, question→q, answer→a).
        if key == "gb_puzzle_lock":
            adapted = []
            for tile in data:
                if not isinstance(tile, dict):
                    continue
                content_html = tile.get("content") or tile.get("text") or ""
                q_text = tile.get("q") or tile.get("question") or ""
                a_text = tile.get("a") or tile.get("answer") or ""
                adapted.append({
                    "content": str(content_html),
                    "q": str(q_text),
                    "a": str(a_text),
                })
            data = adapted

        # Shape adapter: contract uses [[left, right]] arrays; template expects
        # [{a, b, confirmQ, correct}] objects. Convert + back-fill missing fields.
        if key == "gb_memory_match":
            adapted = []
            for pair in data:
                if isinstance(pair, dict):
                    # Already object-shaped — ensure required fields exist.
                    a = pair.get("a") or pair.get("left") or ""
                    b = pair.get("b") or pair.get("right") or ""
                    adapted.append({
                        "a": a,
                        "b": b,
                        "confirmQ": pair.get("confirmQ") or f"{a} ↔ ?",
                        "correct": pair.get("correct") or b,
                    })
                elif isinstance(pair, list) and len(pair) >= 2:
                    a, b = pair[0], pair[1]
                    adapted.append({
                        "a": a,
                        "b": b,
                        "confirmQ": f"{a} ↔ ?",
                        "correct": b,
                    })
            data = adapted

        # Empty-array placeholders to prevent template runtime crashes on new homeworks
        if not data:
            if key == "panels":
                data = [{
                    "id": 1,
                    "title": "PANEL 1 — Ko'rib chiqish",
                    "pages": [{"blocks": [{"type": "p", "text": "Bu bosqich hali to'ldirilmagan."}]}]
                }]
            elif key == "flashcards":
                data = [{
                    "cluster": "QOIDA",
                    "front": {"term": "Joylashtirilmagan", "term_html": "Joylashtirilmagan", "media": ""},
                    "back": {"definition": "Kontent tayyorlanishi kutilmoqda.", "bullets": [], "hook": ""},
                }]
            elif key == "memory_sprint":
                data = [{
                    "type": "KO",
                    "prompt": "Bu bosqich hali to'ldirilmagan.",
                    "subtitle": "",
                    "tags": "[Bloom: L1 | PISA: L1]",
                    "explain": "Builder'da savollarni qo'shing.",
                    "options": ["OK"],
                    "correct": 0,
                }]
            # Game-break placeholders intentionally absent: gb_adaptive_quiz,
            # gb_why_chain, gb_memory_match, gb_puzzle_lock, gb_mystery_box keep
            # their empty arrays when the author didn't fill them in. The runtime
            # registry (gbActiveGameOrder in perfect_homework.html) walks only the
            # games whose array has content and skips empty ones — including
            # skipping Stage 5 entirely when all five games are empty.
            #
            # Rule: never re-introduce placeholder fallbacks for game-break keys.
            # Showing fake "Bu bosqich hali to'ldirilmagan" content to a real
            # student is worse than silently skipping the game. This rule applies
            # to every new game added in the future too.
            elif key == "boss_questions":
                # Template shape.
                data = [{
                    "id":         "QF",
                    "tier":       "easy",
                    "damage":     10,
                    "bloom":      "L3",
                    "pisa":       "L3",
                    "prompt":     "Bu bosqich hali to'ldirilmagan.",
                    "acceptable": ["ok"],
                    "hints":      ["Builder'dan savollarni qo'shing.", "Savollar shu yerda paydo bo'ladi.", "Kontent tayyorlanishi kutilmoqda."],
                }]
        # TTT — side-disjoint serialization (answer-leak prevention).
        # Strips correct/distractors from the wire format; stashes answer key
        # in _TTT_ANSWER_KEY[hw_id] for the /api/ai/check-answer?phase=ttt handler.
        if key == "gb_ttt":
            hw_id = (runtime_context or {}).get("hwId") or (runtime_context or {}).get("hw_id") or ""
            if _is_grade8_math_demo_context(runtime_context) and not data:
                data = _ttt_from_why_chain(content_json.get("gb_why_chain") or [])
            wire, key_map = _serialize_ttt(data, content_json.get("gb_ttt_config") or {})
            if hw_id:
                _TTT_ANSWER_KEY[hw_id] = key_map
            replacement = f"const {const_name} = {_safe_js_json(wire)};"
            html = _replace_js_const(html, const_name, replacement)
            continue

        replacement = f"const {const_name} = {_safe_js_json(data)};"
        html = _replace_js_const(html, const_name, replacement)

    # 4. Replace RL_SCENARIO (object, not array). Fallback if missing to avoid template crash.
    rl = content_json.get("real_life")
    if not rl:
        rl = {
            "badge": "VAZIFA · Joylashtirilmagan",
            "story": "Bu bosqich hali to'ldirilmagan. Builder orqali ssenariy qo'shing.",
            "q1": {"prompt": "Savol kutilmoqda.", "ans": "ok", "fb": "OK"},
            "q2": {"prompt": "Savol kutilmoqda.", "fields": [{"id": "x", "label": "Javob", "ans": "ok"}], "fb": "OK"},
            "q3": {"prompt": "Savol kutilmoqda.", "ans": "ok", "fb": "OK"},
            "q4": {"prompt": "Savol kutilmoqda.", "fields": [{"id": "y", "label": "Javob", "ans": "ok"}], "fb": "OK"},
            "q5": {"prompt": "Savol kutilmoqda.", "open": True, "fb": "OK"},
            "q6": {"prompt": "Savol kutilmoqda.", "ans": "ok", "fb": "OK"},
            "endTitle": "Vazifa bajarildi!",
            "endSub": "Kontent builder'da to'ldirilgandan keyin to'liq tajriba paydo bo'ladi.",
        }
    if rl:
        # Shape adapter: builder stores {badge, story, q1..q6, endTitle, endSub}
        # but the template expects {title, story, questions:[{...}], closure:{title, message}}.
        # Convert if the template shape isn't already present.
        if "questions" not in rl or "closure" not in rl:
            rl = _rl_adapt_to_template(rl)
        rl_json = f"const RL_SCENARIO = {_safe_js_json(rl)};"
        html = _replace_js_const(html, "RL_SCENARIO", rl_json)

    # 5. Replace OBJECT constants — reading / consolidation / reflection.
    # Authors edit these via dedicated editors; builder routes them straight into
    # content_json under their own keys. Empty/missing → empty placeholder object
    # (template auto-skips empty phases at runtime).
    for (key, const_name) in _OBJECT_CONSTANTS:
        obj = content_json.get(key)
        if not isinstance(obj, dict):
            obj = {}
        # Normalize per-phase known fields (strings → strings; lists → lists).
        if key == "reading":
            top_checkpoints = obj.get("checkpoints") or []
            if not isinstance(top_checkpoints, list):
                top_checkpoints = []
            top_out_cps = [_normalize_reading_checkpoint(cp) for cp in top_checkpoints]

            # Pass through segment-aware reading fields. When `segments` is
            # present, the runtime renders an interleaved text→question stream
            # via these objects (see perfect_homework.html::readingBuildPages).
            # Legacy fixtures (no segments key) keep the chunker fallback path.
            #
            # Bug #1: when each segment carries a nested `checkpoint` dict and
            # the top-level `checkpoints[]` array is empty, auto-populate the
            # flat checkpoints[] from the per-segment ones (preserving order).
            # We ALSO keep the nested `checkpoint` on each segment in the
            # output, so the runtime's _buildReadingCheckpointBlock can read
            # either source.
            raw_segments = obj.get("segments")
            segments_out = None
            seg_derived_cps: list = []
            if isinstance(raw_segments, list):
                segments_out = []
                for s in raw_segments:
                    if not isinstance(s, dict):
                        continue
                    seg_entry = {"text": str(s.get("text") or s.get("html") or "")}
                    seg_cp_raw = s.get("checkpoint")
                    if isinstance(seg_cp_raw, dict):
                        seg_cp_norm = _normalize_reading_checkpoint(seg_cp_raw)
                        seg_entry["checkpoint"] = seg_cp_norm
                        seg_derived_cps.append(seg_cp_norm)
                    segments_out.append(seg_entry)

            # Author-supplied top-level checkpoints take precedence over
            # segment-derived ones. Only fall back to segment-derived when
            # top-level is empty/missing — that way explicit authoring isn't
            # silently overwritten by segment metadata.
            if top_out_cps:
                out_cps = top_out_cps
            else:
                out_cps = seg_derived_cps

            normalized = {
                "title":       str(obj.get("title") or ""),
                "passage":     str(obj.get("passage") or ""),
                "checkpoints": out_cps,
            }
            if segments_out:
                normalized["segments"] = segments_out
            media = obj.get("media")
            if isinstance(media, dict):
                normalized["media"] = {
                    "type": str(media.get("type") or ""),
                    "html": str(media.get("html") or ""),
                }
        elif key == "consolidation":
            bullets = obj.get("bullets") or []
            if not isinstance(bullets, list):
                bullets = []
            normalized = {
                "title":        str(obj.get("title") or ""),
                "mnemonic":     str(obj.get("mnemonic") or ""),
                "bullets":      [str(b or "") for b in bullets if str(b or "").strip()],
                "check_prompt": str(obj.get("check_prompt") or ""),
                "check_answer": str(obj.get("check_answer") or ""),
                # Legacy alias used by the parity report
                "recap":        str(obj.get("recap") or obj.get("mnemonic") or ""),
            }
            # Bug #7: pass through the new panels[] + check shape used by the
            # wave2 sliding-panel renderer. Generic across mnemonic techniques
            # (Radiant Summary branches, Memory Palace stations, Link System
            # steps, etc.) — each entry is {title?, html, media?, kind?}.
            # Legacy fixtures (no panels[] in content_json) keep rendering via
            # the existing single-panel path above.
            raw_panels = obj.get("panels")
            if isinstance(raw_panels, list):
                panels_out = []
                for p in raw_panels:
                    if not isinstance(p, dict):
                        continue
                    panel_entry = {
                        "title": str(p.get("title") or ""),
                        "html":  str(p.get("html") or ""),
                        "kind":  str(p.get("kind") or ""),
                    }
                    pmedia = p.get("media")
                    if isinstance(pmedia, dict):
                        panel_entry["media"] = {
                            "type": str(pmedia.get("type") or ""),
                            "html": str(pmedia.get("html") or ""),
                        }
                    panels_out.append(panel_entry)
                if panels_out:
                    normalized["panels"] = panels_out
            check = obj.get("check")
            if isinstance(check, dict):
                normalized["check"] = {
                    "prompt": str(check.get("prompt") or ""),
                    "answer": str(check.get("answer") or ""),
                }
        elif key == "reflection":
            normalized = {
                "summary":    str(obj.get("summary") or ""),
                "question":   str(obj.get("question") or ""),
                "spaced_rep": str(obj.get("spaced_rep") or ""),
                "closing":    str(obj.get("closing") or ""),
            }
        else:
            normalized = obj

        replacement = f"const {const_name} = {_safe_js_json(normalized)};"
        html = _replace_js_const(html, const_name, replacement)

    # Sentence Fill — strip answers/explanations/word_bank(free_recall) before
    # JSON-encoding into __GB_SENTENCE_FILL__.  This constant is handled
    # separately from _ARRAY_CONSTANTS because it needs custom field-stripping.
    html = html.replace(
        "__GB_SENTENCE_FILL__",
        _serialize_sentence_fill(content_json.get("gb_sentence_fill")),
    )

    # Tile Match — side-disjoint serialization (answer-leak prevention).
    # Prefers gb_tile_match; falls back to legacy gb_memory_match shim.
    html = html.replace(
        "__GB_TILE_MATCH__",
        _serialize_tile_match(
            content_json.get("gb_tile_match"),
            content_json.get("gb_memory_match"),
        ),
    )

    # Real-Life Challenge (new, split-and-coexist with legacy RL_SCENARIO).
    # Side-disjoint serialization strips is_correct / consequence /
    # acceptable_keywords — client never sees answer keys.
    # NOTE: legacy RL_SCENARIO path above is UNTOUCHED; both globals coexist.
    html = html.replace(
        "__RLC_CASE__",
        _serialize_real_life_challenge(content_json.get("real_life_challenge")),
    )

    # Memory Palace — full author content (no side-disjoint stripping; the
    # "answer" is student-generated placement state, not an author key).
    # Ships null when gb_memory_palace is absent or has no palaces so the
    # runtime can detect "not authored" and skip the panel.
    # grade + hw_tier come from runtime_context; tier defaults "basic" when absent.
    html = html.replace(
        "__GB_MEMORY_PALACE__",
        _serialize_memory_palace(
            content_json.get("gb_memory_palace"),
            content_json.get("gb_memory_palace_config"),
            (runtime_context or {}).get("grade"),
            (runtime_context or {}).get("tier", "basic"),
        ),
    )

    # Final Boss — side-disjoint serialization (answer-leak prevention).
    # _serialize_boss_questions strips accepted[], ans, accepted_answers, answer_spec,
    # and the template-shape acceptable[] from the client JS global.
    # _BOSS_LEGACY_CLIENT_MATCH=False (default) closes the leak; True keeps acceptable[]
    # for transitional back-compat tests only.
    html = _replace_js_const(
        html,
        "BOSS_QUESTIONS",
        "const BOSS_QUESTIONS = " + _serialize_boss_questions(
            content_json.get("boss_questions"),
            boss_meta=content_json.get("boss_meta"),
        ) + ";",
    )

    # BOSS_META — null when boss_meta absent; populated otherwise.
    html = html.replace(
        "__BOSS_META__",
        _serialize_boss_meta(content_json.get("boss_meta")),
    )

    # Always inject the AI tutor runtime hook before </body>.
    ctx_json = _safe_js_json(runtime_context)
    runtime_snippet = (
        f'<script>window.NETS_CTX = {ctx_json};</script>\n'
        f'<script src="/static/runtime/runtime.js"></script>\n'
    )
    html = html.replace('</body>', runtime_snippet + '</body>', 1)

    return html


def verify_template() -> dict:
    """Check that all expected JS constants exist in the template. For startup validation."""
    missing = []
    for (_, const_name) in _ARRAY_CONSTANTS:
        if not re.search(rf"const {const_name}\s*=\s*\[", _TEMPLATE):
            missing.append(const_name)
    if not re.search(r"const RL_SCENARIO\s*=\s*\{", _TEMPLATE):
        missing.append("RL_SCENARIO")
    if "__RLC_CASE__" not in _TEMPLATE:
        missing.append("RLC_CASE")
    for (_, const_name) in _OBJECT_CONSTANTS:
        if not re.search(rf"const {const_name}\s*=\s*\{{", _TEMPLATE):
            missing.append(const_name)
    return {"ok": len(missing) == 0, "missing": missing}
