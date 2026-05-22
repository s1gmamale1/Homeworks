"""Regression guard for the 'click the card to start Memory Check' UX fix.

Before the fix: the card always called `onFlip` — students had to find the
disabled grey 'Start Memory Check' button to advance, which was a hidden
affordance. Owner reported it directly:

    "why I can not move forward to Memory check?"
    "By clicking flashcard move to Memory check part"

After the fix: when `allViewed === true`, the card's onClick switches to
`startMemoryCheck`, `data-ready="true"` flips on for the CSS ring cue, and
the flipHint copy changes to "Tap to start Memory Check →".

This is a source-level guard — it reads Flashcards.tsx as text and asserts
the contract. If a future refactor reverts the card's onClick back to
unconditional `onFlip`, this test fails immediately, before any human
notices the disabled-button confusion is back.

PR #261 review (https://github.com/s1gmamale1/Homeworks/pull/261) explicitly
requested this guard.
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_card_click_switches_to_start_memory_check_when_all_viewed():
    src = (ROOT / "frontend/app/src/runtime/Flashcards.tsx").read_text(encoding="utf-8")

    # Card's onClick must be conditional on allViewed → startMemoryCheck
    assert re.search(r"onClick=\{allViewed\s*\?\s*startMemoryCheck", src), (
        "Card onClick must be: onClick={allViewed ? startMemoryCheck : ...} "
        "so tapping the card after all cards are viewed advances to Memory Check. "
        "Reverting to unconditional onFlip re-introduces the 'why I can not move "
        "forward to Memory Check' confusion."
    )

    # data-ready attribute exposes the state so the CSS can paint the ready cue
    assert re.search(r'data-ready=\{allViewed', src), (
        'Card must expose data-ready={allViewed ? "true" : "false"} so the CSS '
        "can paint the ready state (.cardReady teal ring + halo)."
    )

    # aria-label communicates the navigation when ready (screen-reader contract)
    assert '"Start Memory Check"' in src, (
        "Card aria-label must announce 'Start Memory Check' when allViewed; "
        "otherwise screen-reader users hear a 'show back of card' affordance "
        "that doesn't match the actual click behaviour."
    )

    # The CSS ready class is applied to the card
    assert "s.cardReady" in src, (
        "Card className must conditionally apply s.cardReady when allViewed — "
        "this drives the teal ring + halo visual cue."
    )

    # The hint copy switches so the affordance is visible without screen-reader
    assert "Tap to start Memory Check" in src, (
        "flipHint copy must change to 'Tap to start Memory Check →' when "
        "allViewed, so the visual affordance matches the click behaviour."
    )
