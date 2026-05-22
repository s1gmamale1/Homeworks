"""Regression guard for the 'card turns right on hover' bug.

The flippable card uses `transform-style: preserve-3d`, and each face carries
its own transform (`rotateY(180deg)` on `.faceBack`). Adding a 2-D transform
on `.face:hover` causes the browser to interpolate through partial-rotation
states — the card appears to twist whenever the cursor moves over it, AND
the back peeks through before the user even clicks. Owner reported it:

    "when you go on the top of flashcard it turns right and it is kinda laggy
     and without pressing showing another side which is not giving to read it
     and not functioning"

The fix: `.face:hover` changes only `box-shadow` and `border-color`. NEVER
transform. The card-level flip transform stays exclusively on `.card`,
toggled by the JS click handler — no preserve-3d collision.

This is a source-level guard — it parses Flashcards.module.css and walks
each rule. Any rule whose selector touches `.face*:hover` is checked to
ensure it carries no `transform:` declaration.

PR #261 review (https://github.com/s1gmamale1/Homeworks/pull/261) explicitly
requested this guard.
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_face_hover_rules_have_no_transform():
    css = (ROOT / "frontend/app/src/runtime/Flashcards.module.css").read_text(
        encoding="utf-8"
    )

    # Walk each CSS rule block: selector { body }
    # (Stops at the next opening brace, so this correctly handles
    # multi-line / multi-selector rules.)
    rule_re = re.compile(r"([^{}]+)\{([^{}]*)\}", re.DOTALL)

    offenders = []
    for selector, body in rule_re.findall(css):
        sel = selector.strip()

        # Only inspect :hover rules that touch a face element
        # (.face, .faceFront, .faceBack, .cardFlipped .faceBack:hover, etc.)
        if ":hover" not in sel:
            continue
        if not re.search(r"\.face", sel):
            continue

        # `transform: none` is the explicit accessibility reset inside the
        # @media (prefers-reduced-motion: reduce) block — it does NOT cause
        # the partial-rotation collision; it prevents it. Allow that exact
        # value; flag everything else.
        for m in re.finditer(r"\btransform\s*:\s*([^;}]+)", body):
            value = m.group(1).strip().rstrip(";").strip().lower()
            if value == "none":
                continue
            offenders.append(
                f"{re.sub(chr(10) + r'\s*', ' ', sel)[:140]}  →  transform: {value[:60]}"
            )

    assert not offenders, (
        "Found `transform:` declarations on .face*:hover rules. These collide "
        "with the back face's rotateY(180deg) inside the preserve-3d context "
        "and cause partial-rotation flicker on hover (the 'card turns right' "
        "bug). Hover feedback must change shadow / border only.\n\n"
        "Offending selectors:\n  - " + "\n  - ".join(offenders)
    )
