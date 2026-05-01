"""
Regression: dashboard homework-card progress bar must reflect a real
pipeline state, not arbitrary magic numbers.

Earlier code in `frontend/js/dashboard.js`:

    case "draft":      return 35;   // every draft homework looked half-done
    case "error":      return 20;

Every homework with `status: "draft"` on the dashboard rendered the
SAME 35% bar — pure cosmetic padding with no real signal. The user
spotted this and asked "why is this hardcoded".

The fix is honest pipeline values:

    draft  → 0 (metadata exists, no content yet)
    generating → 50 (AI building right now)
    ready  → 100 (content done, link shareable)
    error  → 0 (build failed)

Plus: hide the progress bar entirely when value is 0 — the status pill
already shows "Draft" / "Error", a 0% bar adds no information.

These tests pin both the value mapping and the conditional render in
place so a future PR can't quietly slip the magic numbers back in.
"""
from pathlib import Path

import pytest


DASHBOARD_JS = Path(__file__).parent.parent / "frontend" / "js" / "dashboard.js"


@pytest.fixture(scope="module")
def dashboard_source() -> str:
    return DASHBOARD_JS.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Magic numbers must be gone
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "forbidden,reason",
    [
        ('case "draft":      return 35;', "draft must not silently report 35%"),
        ('case "draft": return 35;',     "draft must not silently report 35% (compact form)"),
        ('case "error":      return 20;', "error must not report a fake 20%"),
        ('case "error": return 20;',     "error must not report a fake 20% (compact form)"),
    ],
)
def test_no_magic_numbers_in_progress_status(dashboard_source: str, forbidden: str, reason: str):
    assert forbidden not in dashboard_source, (
        f"{reason} — found leftover magic-number mapping: {forbidden!r}. "
        "The dashboard progress must reflect the build pipeline honestly, "
        "not arbitrary cosmetic numbers."
    )


# ---------------------------------------------------------------------------
# Honest pipeline values must be present
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "expected,why",
    [
        ('case "ready":      return 100;', "ready = 100% (content done, shareable)"),
        ('case "generating": return 50;',  "generating = 50% (AI mid-build)"),
        ('case "draft":      return 0;',   "draft = 0% (metadata only, no content)"),
        ('case "error":      return 0;',   "error = 0% (build failed)"),
    ],
)
def test_honest_pipeline_values(dashboard_source: str, expected: str, why: str):
    assert expected in dashboard_source, f"missing pipeline mapping: {expected!r}  ({why})"


# ---------------------------------------------------------------------------
# Backend `item.progress` override still respected
# ---------------------------------------------------------------------------

def test_explicit_item_progress_override_still_honored(dashboard_source: str):
    """If the backend ever supplies an explicit `progress: number` field
    on a homework, the dashboard must use that value — the pipeline
    fallback is exactly that, a fallback."""
    assert "typeof item.progress" in dashboard_source, (
        "explicit item.progress override branch missing — once the backend "
        "starts shipping real progress, the dashboard would silently ignore it."
    )
    assert "Math.round(item.progress)" in dashboard_source


# ---------------------------------------------------------------------------
# Progress bar is conditional — hidden when 0
# ---------------------------------------------------------------------------

def test_progress_bar_hidden_when_progress_is_zero(dashboard_source: str):
    """A 0% progress bar adds no information beyond the status pill, so the
    `.hw-progress` block must be omitted entirely when progress === 0.
    Otherwise the dashboard shows an empty track for every draft homework
    and looks half-broken."""
    # The conditional render uses a template-literal ternary on `progress`.
    assert "progress > 0 ?" in dashboard_source or "progress > 0?" in dashboard_source, (
        "progress bar render is no longer guarded by `progress > 0` — every "
        "draft homework will show an empty 0% bar."
    )


def test_progress_label_only_inside_conditional(dashboard_source: str):
    """The "Progress: 35%" / "Progress: 0%" text must be inside the
    conditional, not always rendered. (If "0%" leaked outside the
    conditional, every draft card would show a literal "0%" label.)"""
    src = dashboard_source
    # Find the .hw-progress block region.
    start = src.find('class="hw-progress"')
    assert start > 0, "could not locate .hw-progress block in dashboard.js"
    # Walk back ~80 chars to find the opening of the conditional template.
    region = src[max(0, start - 100):start]
    assert "progress > 0" in region, (
        '`<div class="hw-progress">` is no longer wrapped in a `progress > 0` '
        "ternary — the progress label/track will render even for draft cards."
    )
