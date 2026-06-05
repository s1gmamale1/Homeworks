# Privacy Policy Page — Design Spec

- **Date:** 2026-06-06
- **Status:** Approved (brainstorming gate passed)
- **Source content:** `/Users/aisigma/projects/SigmaDevelopment/docs/legal/Privacy_Policy.md`
- **Design system:** reuse `frontend/css/landing.css` (Apple-inspired, light-first, `--landing-*` tokens, `[data-theme="dark"]` parity)

## 1. Goal

Add a public **Privacy Policy** page to the Homeworks landing site that:

1. Renders the Privacy Policy document **verbatim** (the full `.md`, including the draft
   notice, internal "Before Publishing" checklist, Trello/owner references, and all
   `[BRACKETED]` placeholders — nothing stripped).
2. Is fully **trilingual** (UZ / RU / EN) with the same language toggle the rest of the
   site uses, defaulting to Uzbek like `landing.html`.
3. Looks and behaves like the existing landing pages — same header/nav, footer, theme
   toggle, fonts, tokens, dark mode, and motion language as `landing.css`.
4. Is reachable from a **Privacy** link in the landing-page footer.

### Explicit owner decision (flagged)

Per the user's choice, the page publishes the document **verbatim** — this means the
internal draft banner, owner name (Leo / GTM), Trello card IDs, and the team
"Before Publishing — Open Items to Confirm" checklist will be **publicly visible and
translated into Uzbek and Russian**. This is intentional and was confirmed at the
design gate. (If this is later reconsidered, the fix is to drop those blocks from all
three language panels — no structural change required.)

## 2. Chosen approach

**Three language "panels" in one self-contained page.** The full policy is rendered
three times — one block per language (`<div class="legal-doc" lang="en|uz|ru">`) — and a
small `privacy.js` shows the active language's block and hides the other two, synced to
the existing `landing_lang` localStorage key and the `.lang-pill` toggle.

Rejected alternatives:
- **`data-i18n` key dictionary** (the `landing.js` pattern): the document has 100+ text
  blocks and 5 tables → hundreds of keys × 3 languages, with tables becoming unreadable.
  Not viable for static long-form legal prose.
- **Server-assembled language partials / fetched fragments**: adds backend code and
  extra requests for no user-visible benefit.

**Accepted trade-off:** `privacy.html` becomes a large content file (~2,000+ lines)
because it holds the same ~4,200-word document three times. This is content, not logic,
so the repo's "keep files under 500 lines" guideline (aimed at code maintainability) is
relaxed for this one content page. Recorded here as a deliberate decision.

## 3. Architecture & components

Each unit has one clear purpose, a defined interface, and can be understood independently.

### New files

| File | Purpose | Depends on |
|------|---------|-----------|
| `frontend/privacy.html` | The page: reused header/footer chrome + reading layout + 3 language panels. | `landing.css`, `privacy.css`, `theme.js`, `privacy.js` |
| `frontend/css/privacy.css` | Long-form legal typography (reading column, heading scale, paragraph rhythm, lists, bordered tables, draft-notice callout, sticky TOC), built on `--landing-*` tokens with `[data-theme="dark"]` parity. | `landing.css` tokens |
| `frontend/js/privacy.js` | Language-panel show/hide synced to `landing_lang` + `.lang-pill` active state; smooth-scroll for the TOC. ~40–60 lines. | DOM only (theme handled by `theme.js`) |

### Edited files

| File | Change |
|------|--------|
| `server/app.py` | Add `"/privacy": "privacy.html"` and `"/privacy.html": "privacy.html"` to the `_HTML_PAGES` dict. |
| `frontend/landing.html` | Add a `Privacy` link to `.landing-footer` (with a `data-i18n` key). |
| `frontend/js/landing.js` | Add the footer link's i18n key (uz/ru/en) to the existing translation dict. |

### Page anatomy (`privacy.html`)

```
<html lang="uz" data-page="privacy">
<head>  — favicon, apple-touch-icon, preload+link landing.css, link privacy.css,
          sync <script> theme.js, all with ?v=__VERSION__; title + meta description
<body class="landing-body">
  skip-link
  <header class="landing-header"> … reused nav:
      brand-link → "/"; minimal nav-links (← Home / back to site);
      .lang-toggle (UZ/RU/EN .lang-pill buttons); .theme-toggle
  <main id="privacy-main" class="legal-wrap">
      <header> doc title + "Last updated / Version" line (per-language)
      <nav> sticky table of contents (desktop) / inline at top (mobile)
      <div class="legal-doc" lang="en" hidden> … full EN policy … </div>
      <div class="legal-doc" lang="uz">         … full UZ policy … </div>
      <div class="legal-doc" lang="ru" hidden> … full RU policy … </div>
  <footer class="landing-footer"> reused
  <script src="/js/privacy.js?v=__VERSION__" defer>
```

- Anchors/IDs are **language-prefixed** (e.g. `id="uz-collection"`) so the three panels
  don't collide on duplicate IDs; each panel's TOC links to its own anchors.
- Only the active language panel is visible (`hidden` on the other two); default = `uz`
  unless `landing_lang` says otherwise.

## 4. Styling rules (`privacy.css`)

- Reuse `--landing-*` tokens for color, shadow, radius, spring curve — **no new palette**.
- Reading column: centered, ~`min(720px, 92vw)`, generous line-height for legal text.
- Heading scale consistent with landing's type feel (H1 ~ `clamp(32px,5vw,48px)`, H2/H3
  stepped down); section spacing rhythm.
- Tables: bordered, zebra-free, token-based borders; horizontal scroll wrapper on mobile.
- Draft notice / callouts: styled `<aside>`/`<blockquote>` using `--landing-card` +
  `--landing-ring`.
- Sticky TOC sidebar on `≥1024px`; collapses to an inline list at the top on mobile.
- Full `[data-theme="dark"]` parity for every element (text, borders, tables, callouts).
- Respect `prefers-reduced-motion` (landing.css already sets the global rule; TOC
  smooth-scroll degrades to instant).

## 5. Behavior (`privacy.js`)

- On load: read `landing_lang` (`uz` default; values `uz|ru|en`); show that language
  panel, hide the others; set the matching `.lang-pill.is-active`.
- On `.lang-pill` click: switch visible panel, persist to `landing_lang`, update active
  pill. (Same storage key as `landing.js` so the choice carries across pages.)
- TOC links: smooth-scroll to the in-panel anchor (instant under reduced-motion).
- No dependency on `landing.js`; theme remains owned by `theme.js`.

## 6. Content & translation

- **EN:** faithful HTML conversion of the entire `.md` — H1/H2/H3 hierarchy, all 5
  tables, every list, bold key terms, the opening draft notice, and the closing
  "Before Publishing" checklist. Placeholders (`[Class-A-Technologies MCHJ]`,
  `[privacy@classa.education]`, `[PUBLICATION DATE]`, retention windows, sub-processor
  rows, etc.) are kept **as-is** — not fabricated.
- **UZ + RU:** full, careful translations of the same structure (headings, tables,
  lists, callouts, checklist). Legal/technical terminology handled carefully.
  Language-neutral placeholders and proper nouns (entity name, email, ZRU-547, GDPR,
  COPPA, FERPA, ISO 27001, NIST CSF, Expo/EAS, Firebase) stay verbatim across languages.
- Execution may fan out one translation sub-agent per language, followed by review for
  fidelity and consistent terminology.

## 7. Data flow

Static file → FastAPI handler substitutes `__VERSION__` (git short SHA) at request time
→ served through Caddy reverse proxy. The language toggle is pure client-side panel
swapping; the theme toggle reuses `theme.js`. No backend logic beyond the one route
entry; no new dependencies.

## 8. Error handling / edge cases

- `localStorage` blocked (private mode): fall back to default `uz`; never throw
  (mirror the existing `try/catch` pattern in `theme.js`/`landing.js`).
- Unknown/missing `landing_lang` value: clamp to `uz`.
- JS disabled: the default (`uz`) panel is visible (others `hidden`); page is still
  fully readable, just not switchable. Footer/skip-link/headings remain semantic.
- Wide tables on small screens: wrapped in an overflow-x container so they never break
  layout.

## 9. Testing / verification

- Route: `GET /privacy` and `/privacy.html` both return the page (200) with `__VERSION__`
  substituted.
- Visual: header/footer/nav match landing; light **and** dark mode render correctly;
  reading column + tables + callouts look Apple-grade; mobile layout intact.
- Language toggle: switching UZ↔RU↔EN swaps the panel, persists across reload, and
  carries to/from `landing.html` (shared `landing_lang`).
- Footer link on `landing.html` navigates to `/privacy` and is translated in all three
  languages.
- Accessibility: skip-link works, headings are ordered, toggle buttons have labels,
  `:focus-visible` rings present, reduced-motion respected.
- Content fidelity: every section/table/list/checklist item from the `.md` is present in
  EN; UZ/RU mirror the same structure.

## 10. Out of scope

- Filling in the legal `[BRACKETED]` placeholders (requires founder/counsel sign-off).
- A separate Terms of Service page (referenced in the doc but not yet drafted).
- Any change to the existing landing sections beyond the single footer link + its i18n key.
