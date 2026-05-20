# Design Patterns — Reusable UI Recipes

Living document for design patterns that worked and should be reused. Add to it when a pattern lands; remove only when it's superseded.

---

## In-grid expansion (Apple-style "tile grows in place")

**Where it shipped:** Library page (`frontend/library.html` + `frontend/css/library.css` + `frontend/js/library.js`). PR #89 (`402514c`), 2026-04-30. User feedback: *"This is truly Apple-like design."*

**The problem it solves:** A clickable tile in a grid needs to "open into" a detail view. The naive solution is a modal, lightbox, or absolutely-positioned overlay panel. All three break the user's spatial model — the new content appears OVER existing content, hiding everything else, and the user loses sense of where the tile was. Apple's macOS Launchpad / iOS Photos pull off the trick where the source element morphs into the detail view AND siblings flow around it. That's the pattern below.

### Visual contract

```
COMPACT STATE                              EXPANDED STATE
┌─────┬─────┬─────┬─────┐                  ┌────────────────────────┐
│  A  │  B  │  C  │  D  │                  │   A (expanded)         │
└─────┴─────┴─────┴─────┘                  │   ┌──┬──┬──┬──┐        │
┌─────┬─────┬─────┬─────┐                  │   │ items │           │
│  E  │  F  │  G  │  H  │     click  →     │   └──┴──┴──┴──┘        │
└─────┴─────┴─────┴─────┘                  └────────────────────────┘
                                           ┌─────┬─────┬─────┬─────┐
                                           │  B  │  C  │  D  │  E  │   ← reflowed
                                           ├─────┼─────┼─────┴─────┘
                                           │  F  │  G  │  H            ← still flowing
```

The expanded tile occupies a full row (`grid-column: 1 / -1`). All siblings shift forward in document order to fill the freed cells. CSS Grid does the layout; the browser's View Transitions API tweens the visual change.

### Architectural rule

**One DOM node per tile.** The compact card and the expanded card are the SAME `<button>` / `<section>` element. Only its `innerHTML` and a class name change. This is what unlocks the View Transitions morph — the browser sees "same identity, different appearance" and animates between them.

Reject these alternatives:
- ❌ Two stacked DOM nodes (compact + expanded) toggled with `display: none`. View Transitions can't morph across an identity change.
- ❌ Absolute-positioned overlay panel that covers neighbors. This is the anti-pattern this recipe replaces.
- ❌ FLIP via `Element.animate()` with manual rect math. Works but ~150 LOC vs ~40 with View Transitions, and you have to manually animate every neighbor too.

### CSS recipe

```css
/* Outer grid that holds the tiles */
.subject-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 14px;
}

/* Compact tile — base state */
.subject-tile {
  display: flex;
  flex-direction: column;
  gap: 12px;
  min-height: 140px;
  padding: 16px 18px;
  border-radius: 22px;
  /* tile-specific gradient, border, etc. */
}

/* The magic: expanded modifier spans the full row */
.subject-tile.is-expanded {
  grid-column: 1 / -1;       /* full row width */
  min-height: 480px;          /* taller for content */
  cursor: default;
  padding: 24px;
}

/* Per-tile view-transition-name (set by JS dynamically) */
.subject-tile {
  view-transition-name: var(--vt-name);  /* JS sets --vt-name inline */
}

/* Tweak the morph easing — default 250ms ease is too snappy */
::view-transition-old(*),
::view-transition-new(*) {
  animation-duration: 480ms;
  animation-timing-function: cubic-bezier(.16, 1, .3, 1);  /* Apple spring */
}
```

**View transition name uniqueness:** the browser uses the name to match "old" and "new" frames. Each tile needs its own name; otherwise two simultaneous transitions clash. Generate from a stable id:

```js
function vtNameForTile(subjectId) {
  // Sanitize so any id (including punctuation) becomes a valid CSS ident
  return "library-tile-" + String(subjectId).replace(/[^a-zA-Z0-9]+/g, "-");
}
tileEl.style.setProperty("--vt-name", vtNameForTile(subjectId));
```

### JS recipe

```js
let currentExpanded = null;

function expandSubject(tileEl, subject, items) {
  if (currentExpanded && currentExpanded !== tileEl) {
    collapseSubject(currentExpanded, /* animate */ false);
  }
  const apply = () => {
    tileEl.classList.add("is-expanded");
    tileEl.innerHTML = expandedMarkup(subject, items);
    wireExpandedHandlers(tileEl, subject, items);
    currentExpanded = tileEl;
  };
  if (typeof document.startViewTransition === "function") {
    document.startViewTransition(apply);
  } else {
    apply();   // graceful fallback for browsers without the API
  }
}

function collapseSubject(tileEl, animate = true) {
  const apply = () => {
    tileEl.classList.remove("is-expanded");
    tileEl.innerHTML = compactMarkup(tileEl._subject);
    wireCompactHandlers(tileEl);
    currentExpanded = null;
  };
  if (animate && typeof document.startViewTransition === "function") {
    document.startViewTransition(apply);
  } else {
    apply();
  }
}
```

That's the whole engine. ~30 LOC of state. CSS Grid does the layout reflow. View Transitions does the animation.

### Why this is "Apple-like"

1. **Spatial continuity** — the source tile and the expanded surface are the SAME element, so the user's mental model never breaks.
2. **Siblings flow naturally** — neighbors don't disappear, they shift. This is exactly what macOS Launchpad does when you click a folder.
3. **No overlay, no blackout** — the page never goes modal. You can still see other tiles, the topbar, the search.
4. **One spring curve** — `cubic-bezier(.16, 1, .3, 1)` is the no-overshoot Apple curve used across macOS Big Sur+. ~480ms is the right duration for content this size (smaller tiles → 320ms; full app windows → 640ms).
5. **Native-driven** — View Transitions API is the browser's own snapshot-and-tween engine. It handles edge cases (font swap mid-anim, scrollbar appearing, layout shift) better than any JS implementation.

### Browser support (as of 2026-04)

- **Chromium 111+** (Chrome, Edge, Opera, Brave) — full support
- **Safari 18+** — full support
- **Firefox** — partial support behind a flag, but the synchronous `apply()` fallback path renders correctly without animation. Acceptable degradation.

### When to reach for this pattern

✅ Good fit:
- Grid of cards where one expands to show details (library subjects, photo album, file folder)
- Settings panel where a row reveals sub-settings inline
- Reading list where one article expands to show preview
- Any "drill-in" interaction that doesn't need a full route change

❌ Bad fit:
- Modal forms (use a dialog)
- Multi-step wizards (use a route)
- Anything that needs the URL to change
- Detail views with > 80% viewport content (use a route — modal feel breaks down)

### Reference implementation

- `frontend/css/library.css` — `.subject-tile`, `.subject-tile.is-expanded`, view-transition rules
- `frontend/js/library.js` — `expandSubject()`, `collapseSubject()`, `vtNameForTile()`
- PR #89 — full diff with the rationale

### What got deleted to make room

The "before" was a ~150-LOC FLIP engine using `Element.animate()` and `getBoundingClientRect()` math (`getExpandedTarget`, `setPanelBox`, `rectRelativeToGrid`). It worked, but:
- Hardcoded geometry (panel height, column widths) drifted from the actual layout on resize
- Required an `is-origin` ghost state to hide the source tile
- Created an absolute-positioned overlay that covered neighbors (the visual bug we set out to fix)
- ~4× more code than the View Transitions equivalent

The lesson: when the browser has a native primitive for what you're trying to animate, use it. Reach for FLIP only when you need to coordinate animations across DOM trees the View Transitions API can't capture together.

---

## Pattern catalog

| Pattern | File | First shipped |
|---|---|---|
| In-grid expansion (Apple-style) | This file, above | PR #89 |
| (add more as they ship) | | |
