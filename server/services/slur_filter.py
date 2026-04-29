"""Severity classifier for student messages — replaces the old binary
detector that returned a single canned callout per language.

The classifier loads two markdown sources at import time:

  * ``docs/Naughty_words.md`` — terms grouped into 4 sections (Mild Uzbek,
    Strong Uzbek vulgar, Russian-mixed profanity, English profanity). Each
    table row gives ``(term, severity_label, meaning, safer_rewrite)``.
  * ``docs/Slangs.md``        — casual register that must NEVER trigger a
    warning. These populate ``SAFE_LIST``.

Public API:

  * :func:`classify`            — main entry point, returns
    :class:`SlurClassification`.
  * :func:`detect_slurs`        — backward-compat shim that returns the raw
    matched terms (severity ≥ ``insult_mild``).
  * :func:`callout_for`         — DEPRECATED no-op stub. T2 of Wave J will
    delete it after the route layer is rewritten to consume :func:`classify`
    directly.

The LLM tutor owns the actual response wording now; this module's job is to
hand the route layer a structured signal it can splice into the system
prompt.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Literal, Optional, Set, Tuple

from server.config import BASE_DIR

# ---------------------------------------------------------------------------
# Public types
# ---------------------------------------------------------------------------

Severity = Literal[
    "casual_safe",
    "casual_negative",
    "insult_mild",
    "profanity_mild",
    "profanity_strong",
    "slur_or_hate",
    "sexual_vulgar",
]

# Ordered weakest → strongest. Used when a term fires under more than one
# pattern: the strongest tier wins. Also used by ``detect_slurs`` to filter
# anything below ``insult_mild``.
_SEVERITY_ORDER: Tuple[Severity, ...] = (
    "casual_safe",
    "casual_negative",
    "insult_mild",
    "profanity_mild",
    "profanity_strong",
    "slur_or_hate",
    "sexual_vulgar",
)
_SEVERITY_RANK: Dict[Severity, int] = {s: i for i, s in enumerate(_SEVERITY_ORDER)}

# Section name → category label exposed on the result.
_CATEGORY_BY_SECTION: Dict[str, str] = {
    "1": "uz_mild_insult",
    "2": "uz_strong_vulgar",
    "3": "ru_mixed_profanity",
    "4": "en_profanity",
}


@dataclass(frozen=True)
class SlurClassification:
    severity: Severity
    category: str
    lang: str
    matched_terms: List[str] = field(default_factory=list)
    is_clean: bool = True


# ---------------------------------------------------------------------------
# File paths
# ---------------------------------------------------------------------------

_NAUGHTY_PATH = BASE_DIR / "docs" / "Naughty_words.md"
_SLANGS_PATH = BASE_DIR / "docs" / "Slangs.md"

_MIN_TERM_LEN = 3


# ---------------------------------------------------------------------------
# Severity-label mapping
# ---------------------------------------------------------------------------


_SEXUAL_MEANING_HINTS = (
    "sexual", "genital", "misogyn", "fuck", "obscene genital",
)


def _map_severity(raw_label: str, section: str, meaning: str = "") -> Severity:
    """Map the human-readable severity column from Naughty_words.md to one of
    the 7 ``Severity`` literals. The ``meaning`` cell is consulted as a
    secondary signal for sexual content.

    Strategy:

    * Meaning column carries explicit sexual / genital framing → ``sexual_vulgar``.
    * Severity label ``very vulgar`` or contains ``sexual`` → ``sexual_vulgar``.
    * Slurs / ableist / homophobic → ``slur_or_hate``.
    * ``strong`` label → ``profanity_strong``.
    * Plain ``vulgar`` → ``profanity_strong`` (body-part insults, obscene fillers).
    * ``profanity`` (without ``strong``) → ``profanity_mild``.
    * ``mild`` / ``rude`` / ``mocking`` / ``disrespectful`` / ``dismissive`` /
      ``insult`` / ``context-dependent`` → ``insult_mild``.
    * Otherwise → section default:
      sec 1 ``insult_mild``, sec 2 ``profanity_strong``,
      sec 3 ``profanity_strong``, sec 4 ``profanity_mild``.

    When in doubt we round UP to the safer (higher) tier.
    """
    label = raw_label.lower().strip()
    meaning_l = meaning.lower()

    # Sexual / genital framing in either column wins outright.
    if "very vulgar" in label or "sexual" in label:
        return "sexual_vulgar"
    if any(h in meaning_l for h in _SEXUAL_MEANING_HINTS):
        # Don't let "fuck" inside an English-profanity meaning column pull
        # ordinary "fuck"-glossed strong profanity into sexual territory if
        # the severity says only "strong profanity" (e.g. "wtf"). Require
        # genital/sexual/misogynistic framing for that.
        if any(h in meaning_l for h in ("sexual", "genital", "misogyn")):
            return "sexual_vulgar"

    # Slur / ableist / homophobic.
    if "slur" in label or "ableist" in label or "homophobic" in label:
        return "slur_or_hate"

    # Strong tiers — distinguish profanity vs insult.
    if "strong" in label:
        return "profanity_strong"

    # Plain "vulgar" → profanity_strong (body-part insults, obscene fillers).
    if "vulgar" in label:
        return "profanity_strong"

    # Mild profanity / profanity / abbreviation → profanity_mild.
    if "profanity" in label:
        return "profanity_mild"

    # Mild insults / rude / mocking / disrespectful / dismissive / context.
    if any(k in label for k in ("mild", "rude", "mocking", "disrespect", "dismissive", "insult", "context")):
        return "insult_mild"

    # Final fallback: section default.
    if section == "1":
        return "insult_mild"
    if section == "2":
        return "profanity_strong"
    if section == "3":
        return "profanity_strong"
    if section == "4":
        return "profanity_mild"
    return "insult_mild"


# ---------------------------------------------------------------------------
# Markdown parsing
# ---------------------------------------------------------------------------

# Matches a section header like "## 1. Mild Uzbek..." — captures the digit.
_SECTION_RE = re.compile(r"^##\s+(\d+)\.\s", re.MULTILINE)

# Matches a markdown table row: `| col1 | col2 | col3 | col4 |`. We accept
# any number of cells ≥ 2 so the parser is tolerant of formatting drift.
_TABLE_ROW_RE = re.compile(r"^\|(.+)\|\s*$")

# Header-separator row (`|---|---:|---|---|`). Skip these.
_TABLE_SEP_RE = re.compile(r"^\|[\s\-:|]+\|\s*$")


def _split_term_variants(cell: str) -> List[str]:
    """A term cell can hold multiple variants separated by ' / '. Strip
    backticks, asterisks, and whitespace; reject anything shorter than
    ``_MIN_TERM_LEN`` or containing characters we don't expect in a real
    term."""
    cell = cell.replace("`", "").replace("*", "").strip()
    raw_parts = re.split(r"\s*/\s*", cell)
    out: List[str] = []
    for part in raw_parts:
        token = part.strip().lower()
        # Drop parentheticals like "(refuse to use)" if they leaked in.
        token = re.sub(r"\s*\(.*?\)\s*", "", token).strip()
        if len(token) < _MIN_TERM_LEN:
            continue
        # Allow letters (Latin + Cyrillic), apostrophes, hyphens, spaces.
        if not re.match(r"^[a-zà-ÿа-яёўғқҳ' \-]+$", token, re.IGNORECASE):
            continue
        out.append(token)
    return out


def _parse_naughty(text: str) -> Dict[str, Tuple[Severity, str]]:
    """Walk the naughty-words file. Track the current ``## N.`` section so
    each term gets the right category label and a sane fallback severity.

    Returns ``{term: (severity, category)}``."""
    terms: Dict[str, Tuple[Severity, str]] = {}
    current_section: Optional[str] = None

    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        m = _SECTION_RE.match(line)
        if m:
            current_section = m.group(1)
            continue

        # Only parse rows inside one of the four data sections.
        if current_section not in _CATEGORY_BY_SECTION:
            continue

        # Skip the policy/example sections (5, 6, 7) — handled by the
        # condition above, but we also want to skip code fences inside the
        # active section.
        if line.startswith("```"):
            continue

        if _TABLE_SEP_RE.match(line):
            continue

        row_match = _TABLE_ROW_RE.match(line)
        if not row_match:
            continue

        cells = [c.strip() for c in row_match.group(1).split("|")]
        if len(cells) < 2:
            continue

        # Skip the header row (cells like "Word / phrase", "Severity").
        first_cell_l = cells[0].lower()
        if "word" in first_cell_l and ("phrase" in first_cell_l or "variant" in first_cell_l):
            continue

        term_cell, severity_cell = cells[0], cells[1]
        meaning_cell = cells[2] if len(cells) > 2 else ""
        variants = _split_term_variants(term_cell)
        if not variants:
            continue

        category = _CATEGORY_BY_SECTION[current_section]
        severity = _map_severity(severity_cell, current_section, meaning_cell)

        for term in variants:
            existing = terms.get(term)
            # If a term shows up in multiple rows, keep the stronger severity.
            if existing is None or _SEVERITY_RANK[severity] > _SEVERITY_RANK[existing[0]]:
                terms[term] = (severity, category)
    return terms


def _parse_slangs(text: str) -> Set[str]:
    """Pull every term-like cell out of Slangs.md and add it to the safe
    list. We only need the first column of each table row — that's the
    ``Casual form`` / ``Slang`` / ``Term`` / ``Abbrev`` / ``Mixed phrase``
    column depending on the section, all of which list student-side text."""
    safe: Set[str] = set()
    in_table = False
    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        if line.startswith("```"):
            in_table = False
            continue
        if _TABLE_SEP_RE.match(line):
            in_table = True
            continue
        m = _TABLE_ROW_RE.match(line)
        if not m:
            in_table = False
            continue
        if not in_table:
            # Could still be the header row — pick up subsequent rows once
            # the separator is seen.
            continue
        cells = [c.strip() for c in m.group(1).split("|")]
        if not cells:
            continue
        for term in _split_term_variants(cells[0]):
            safe.add(term)
    return safe


# ---------------------------------------------------------------------------
# Module-level cache: load + compile once at import.
# ---------------------------------------------------------------------------


def _load() -> Tuple[Dict[str, Tuple[Severity, str]], Set[str]]:
    naughty: Dict[str, Tuple[Severity, str]] = {}
    safe: Set[str] = set()
    if _NAUGHTY_PATH.exists():
        naughty = _parse_naughty(_NAUGHTY_PATH.read_text(encoding="utf-8"))
    if _SLANGS_PATH.exists():
        safe = _parse_slangs(_SLANGS_PATH.read_text(encoding="utf-8"))
    # Safe list wins over naughty list for casual register collisions
    # (e.g. "jinni" appears in both — Slangs treats it as positive slang,
    # Naughty marks it context-dependent). The classifier still flags it
    # at the module level so explicit insulting use is detected, but if a
    # term is ALSO in the safe list the classifier downgrades the result
    # at scoring time.
    return naughty, safe


_NAUGHTY: Dict[str, Tuple[Severity, str]]
_SAFE_LIST: Set[str]
_NAUGHTY, _SAFE_LIST = _load()

# One compiled regex per severity tier, so we know which tier each match
# belongs to without re-checking the dict.
_PATTERNS_BY_SEVERITY: Dict[Severity, Optional[re.Pattern]] = {}
for _sev in _SEVERITY_ORDER:
    _terms_for_sev = [t for t, (s, _) in _NAUGHTY.items() if s == _sev]
    if _terms_for_sev:
        _PATTERNS_BY_SEVERITY[_sev] = re.compile(
            r"(?<![\w'])(?:" + "|".join(re.escape(t) for t in _terms_for_sev) + r")(?![\w'])",
            re.IGNORECASE,
        )
    else:
        _PATTERNS_BY_SEVERITY[_sev] = None

# Backward-compat: the old test suite asserts a non-empty ``_SLURS`` list
# exists at module scope. Keep it as a sorted snapshot of every naughty
# term (regardless of tier) so the legacy assertion still holds.
_SLURS: List[str] = sorted(_NAUGHTY.keys())


# ---------------------------------------------------------------------------
# Per-message language detection
# ---------------------------------------------------------------------------

# Cyrillic letters that only appear in Uzbek-Cyrillic, not standard Russian.
_UZ_CYRILLIC_HINTS = re.compile(r"[ўғқҳЎҒҚҲ]")
# Russian Cyrillic block (covers Russian + Uzbek Cyrillic).
_CYRILLIC_BLOCK = re.compile(r"[Ѐ-ӿ]")

# Latin words that are heavily Uzbek-leaning; pulled from Slangs.md.
_UZ_LATIN_HINTS = {
    "uka", "opa", "aka", "salom", "rahmat", "tushundim", "tushunmadim",
    "ovqat", "yaxshi", "yomon", "qanday", "qalay", "qalaysiz", "qalaysan",
    "nima", "kerak", "bilan", "uchun", "xop", "mayli", "bo'pti", "bopti",
    "bo'ldi", "rahmat", "iltimos", "javob", "savol", "vazifa", "darsda",
    "darsdamiz", "ustoz", "uka", "jo'ra", "og'a", "sherik", "yaxwi",
    "bowqa", "wunaqa",
}


def _detect_message_lang(text: str) -> str:
    """Return ``"uz"``, ``"ru"``, or ``"en"`` based on what's in ``text``.

    Heuristic order:

    1. Uzbek-specific Cyrillic letters (ў, ғ, қ, ҳ) → ``uz``.
    2. Generic Cyrillic only → ``ru``.
    3. Latin with at least one Uzbek-leaning word → ``uz``.
    4. Otherwise → ``en``.
    """
    if not text:
        return "en"
    if _UZ_CYRILLIC_HINTS.search(text):
        return "uz"
    if _CYRILLIC_BLOCK.search(text):
        return "ru"
    lowered = text.lower()
    # Token split that survives apostrophes inside words like bo'pti.
    tokens = re.findall(r"[a-z']+", lowered)
    for tok in tokens:
        if tok in _UZ_LATIN_HINTS:
            return "uz"
    return "en"


# ---------------------------------------------------------------------------
# Classifier
# ---------------------------------------------------------------------------


def _safe_clean_classification(lang: str) -> SlurClassification:
    return SlurClassification(
        severity="casual_safe",
        category="clean",
        lang=lang,
        matched_terms=[],
        is_clean=True,
    )


def classify(message: str) -> SlurClassification:
    """Single source of truth.

    Walks each severity tier from strongest to weakest, collects every match,
    discards any match that's also in ``SAFE_LIST`` for that exact form, and
    returns the strongest surviving tier.
    """
    if not message:
        return _safe_clean_classification(lang="en")

    lang = _detect_message_lang(message)

    # Search strongest first so we can short-circuit on the worst tier.
    matched_per_tier: Dict[Severity, List[str]] = {}
    for sev in reversed(_SEVERITY_ORDER):  # sexual_vulgar → casual_safe
        pat = _PATTERNS_BY_SEVERITY.get(sev)
        if pat is None:
            continue
        hits = []
        for m in pat.finditer(message):
            term = m.group(0).lower()
            # Suppress matches that are ALSO listed as casual register up
            # through profanity_mild. Genuine mild profanity (shit, blin,
            # damn, fuck, wtf, ass) is verified not to appear in the safe
            # list, so the only collisions we rescue here are the
            # context-dependent terms (jinni, cooked, npc, opp, cringe,
            # washed, yapping) where Slangs.md explicitly says the casual
            # use is tolerated. Anything profanity_strong+ is never
            # rescued.
            if term in _SAFE_LIST and _SEVERITY_RANK[sev] <= _SEVERITY_RANK["profanity_mild"]:
                continue
            hits.append(term)
        if hits:
            matched_per_tier[sev] = list(dict.fromkeys(hits))  # dedupe, keep order

    if not matched_per_tier:
        return _safe_clean_classification(lang=lang)

    # Pick the strongest tier that actually fired.
    top_sev = max(matched_per_tier.keys(), key=lambda s: _SEVERITY_RANK[s])
    matched_terms = matched_per_tier[top_sev]
    # Pull category from the first matched term's lookup record.
    category = _NAUGHTY.get(matched_terms[0], (top_sev, "unknown"))[1]
    return SlurClassification(
        severity=top_sev,
        category=category,
        lang=lang,
        matched_terms=matched_terms,
        is_clean=False,
    )


# ---------------------------------------------------------------------------
# Backward-compat shims
# ---------------------------------------------------------------------------


def detect_slurs(message: str) -> List[str]:
    """Return matched terms whose severity is ``insult_mild`` or higher.

    Preserved verbatim so the existing ``tests/test_security_hardening.py``
    and ``tests/test_tutor_security.py`` keep working until they get
    rewritten in T2.
    """
    if not message:
        return []
    result = classify(message)
    if result.is_clean:
        return []
    if _SEVERITY_RANK[result.severity] < _SEVERITY_RANK["insult_mild"]:
        return []
    return list(result.matched_terms)


def callout_for(message: str, lang: str = "uz") -> Optional[str]:  # pragma: no cover
    """DEPRECATED — see :func:`classify`. The LLM tutor owns response wording
    now; this stub stays only so import sites in ``server/routes/ai.py``
    don't break before T2 wires the new state machine. Always returns
    ``None``.
    """
    return None
