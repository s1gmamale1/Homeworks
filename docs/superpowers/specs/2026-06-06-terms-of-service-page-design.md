# Terms of Service Page — Design Spec

- **Date:** 2026-06-06
- **Status:** Approved (brainstorming gate passed)
- **Source content:** `/Users/aisigma/projects/SigmaDevelopment/docs/legal/Terms_of_Service.md`
- **Sibling page:** `docs/superpowers/specs/2026-06-06-privacy-policy-page-design.md` (already built — this page is its structural twin)
- **Design system:** reuse `frontend/css/landing.css` (Apple-inspired, light-first, `--landing-*` tokens, `[data-theme="dark"]` parity) via the shared `legal.css` extracted from the privacy build.

## 1. Goal

Add a public **Terms of Service** page to the Homeworks / Class A Education landing site that:

1. Renders the full 19-section ToS document, **polished for publication** (see §2 — owner decisions).
2. Is fully **trilingual** (UZ / RU / EN) with full Uzbek + Russian translations, using the
   same language toggle and the same CSS-only panel mechanism as the privacy page, defaulting to Uzbek.
3. Looks and behaves like the existing landing + privacy pages — same header/nav, footer chrome,
   theme toggle, fonts, tokens, dark mode, and motion language.
4. Is reachable from a **Terms of Service** link in the landing-page footer, and cross-links to `/privacy`.

## 2. Owner decisions (flagged — differ from the privacy page on purpose)

Confirmed at the design gate over four rounds of Q&A:

| Decision | Choice | Consequence |
|---|---|---|
| Draft presentation | **Final look, no draft notice** | Strip the YAML front-matter, the "⚠️ DRAFT — NOT YET IN EFFECT" banner, the "Placeholders to confirm" table, and the "Before Publishing — Open Items" checklist. The page reads as a finished ToS. (Owner accepts publishing before formal legal sign-off.) |
| Placeholders | **Fill them** | No visible `[BRACKETED]` tokens / no `.legal-ph` styling. Values in §5. |
| Languages | **Full UZ + RU translations** | All 19 sections translated, matching the privacy page's bar. The ToS itself (§17) names the **Uzbek version authoritative**, so real Uzbek matters here. |
| Privacy cross-links | **Link to `/privacy`** | Every "Privacy Policy" reference links to `/privacy` (page already built). |
| Lang-key bug | **Fix it + share `legal.css`** | Correct the privacy page's `landing_lang` → `nets-landing-lang`; extract a shared stylesheet + JS. |

> **Note on sibling consistency:** the privacy page currently publishes its document *verbatim*
> (draft banner, internal checklist, raw placeholders all visible). The ToS page is deliberately
> the more polished of the two per the owner's explicit choice. If the two should later match, the
> cheaper path is to polish privacy up to this bar — no structural change to either page.

## 3. Chosen approach

**Three language "panels" in one self-contained page**, identical to the privacy page:
the full ToS is rendered three times — one `<div class="legal-doc" data-lang-panel="en|uz|ru" lang="…">`
per language — and the shared `legal.js` shows the active panel via `html[data-lang]` (pure CSS),
synced to the `nets-landing-lang` localStorage key and the `.lang-pill` toggle.

Rejected alternatives are the same as the privacy spec (a `data-i18n` key dictionary is unusable for
long-form legal prose; server-assembled partials add backend cost for no benefit). Accepted trade-off:
`terms.html` is a large **content** file (the document ×3 languages); the repo's "under 500 lines"
*code* guideline is relaxed for this one content page, exactly as it was for `privacy.html`.

## 4. Architecture & components

### New files

| File | Purpose | Depends on |
|------|---------|-----------|
| `frontend/terms.html` | The page: reused header/footer chrome + reading layout + 3 language panels (full EN/UZ/RU). | `landing.css`, `legal.css`, `theme.js`, `legal.js` |

### Renamed (extract shared legal infra from the privacy build — owner-approved)

| From | To | Why |
|------|----|-----|
| `frontend/css/privacy.css` | `frontend/css/legal.css` | Classes are already generic `.legal-*`; both pages share one stylesheet. Update header comment. |
| `frontend/js/privacy.js` | `frontend/js/legal.js` | Behavior is generic (panel toggle + chrome translation); both pages share one script. Fix the lang key (below) in this single place. |

### Edited files

| File | Change |
|------|--------|
| `frontend/js/legal.js` | Fix `LANG_KEY`: `'landing_lang'` → `'nets-landing-lang'` (match `landing.js:410`). Update header comment. |
| `frontend/privacy.html` | Re-point links: `/css/privacy.css` → `/css/legal.css`; `/js/privacy.js` → `/js/legal.js`. Fix the inline `<head>` flash-free script key: `localStorage.getItem('landing_lang')` → `'nets-landing-lang'`. |
| `server/app.py` | Add `"/terms": "terms.html"` and `"/terms.html": "terms.html"` to `_HTML_PAGES`. |
| `frontend/landing.html` | Add a **Terms of Service** link to `.landing-footer` (beside the existing Privacy link), with a `data-i18n` key. |
| `frontend/js/landing.js` | Add the `footerTerms` i18n key (uz/ru/en) to the translation dict. (`footerPrivacy` already added by the privacy build.) |

### Page anatomy (`terms.html`) — mirrors `privacy.html`

```
<html lang="uz" data-page="terms">
<head>  — favicon, apple-touch-icon, preload+link landing.css, link legal.css,
          sync <script> theme.js, all ?v=__VERSION__; title + meta description;
          inline flash-free <script> that sets html[data-lang] from nets-landing-lang
<body class="landing-body">
  skip-link → #terms-main
  <header class="landing-header"> … reused nav:
      brand-link → "/"; one nav-link "← Home" (data-i18n-uz/ru/en);
      .lang-toggle (UZ/RU/EN .lang-pill); .theme-toggle  (no CTA pill)
  <main id="terms-main" class="legal-wrap">
      <div class="legal-doc" data-lang-panel="uz" lang="uz"> … full UZ ToS … </div>
      <div class="legal-doc" data-lang-panel="ru" lang="ru" hidden-by-css> … full RU … </div>
      <div class="legal-doc" data-lang-panel="en" lang="en" hidden-by-css> … full EN … </div>
  <footer> mirror privacy.html's footer (legal-footer chrome) with Terms·Privacy·Home links
  <script src="/js/legal.js?v=__VERSION__"></script>
```

Each panel contains `.legal-layout` (sticky `.legal-toc` + `.legal-body` article). Each article:
`.legal-head` (eyebrow "Class A Education" + `<h1>` title + `.legal-updated` line) → §§1–19 as
`<section id="{lang}-s{n}">` → contact. **No** `.legal-meta` draft block, **no** `.legal-callout--warn`
banner, **no** checklist (those are the stripped internal bits).

- Anchors/IDs are **language-prefixed** (`id="uz-s1"`, `id="ru-s1"`, `id="en-s1"`) so the three
  panels don't collide; each panel's TOC links to its own anchors. (Same convention as privacy.)
- Default visible panel = `uz` (CSS `html:not([data-lang])` fallback + inline head script).

## 5. Placeholder fills (final-look values)

| Placeholder | Filled value |
|---|---|
| `[Class-A-Technologies MCHJ]` | **Class A Technologies MCHJ** (short form "Class A"); page eyebrow/brand "Class A Education" |
| `[legal@classa.education]` | legal@classa.education |
| `[support@classa.education]` | support@classa.education |
| `[privacy@classa.education]` | privacy@classa.education |
| `[registered address, Tashkent, Uzbekistan]` | **Tashkent, Uzbekistan** (omit unknown street; don't fabricate) |
| `[Tashkent]` (court venue) | Tashkent |
| `[PUBLICATION DATE]` / `[1.0]` | **June 6, 2026** / Version 1.0 (localized date format per language) |
| §13 `[a nominal floor amount]` | **Dropped** — render §13 with the 12-month-fees cap only; do not invent a figure |

Proper nouns kept verbatim across all languages: ZRU-547, GDPR, COPPA, FERPA, "Hermes", and the
email addresses. The §17 "language clause" (Uzbek authoritative; RU/EN convenience) is rendered in all three.

## 6. Content & translation

- **EN:** faithful HTML conversion of §§1–19 + intro + contact (H2/H3 hierarchy, lists, the few inline
  tables/role-tiers as needed, bold key terms). Internal/draft blocks excluded (§2). Placeholders filled (§5).
- **UZ + RU:** full, careful translations of the same structure. Legal/technical terminology handled
  carefully and kept consistent with the **already-translated privacy page** (reuse its renderings of
  controller/processor, "Authorized User", ZRU-547 phrasing, etc. for cross-document consistency).
- Execution fans out **one translation sub-agent per language** (UZ, RU), then a fidelity/terminology review.

## 7. Styling (`legal.css`)

No new CSS authored — the privacy build's `.legal-*` system already covers everything (reading column
~760px, heading scale, lists, `.legal-table-wrap`, sticky TOC ≥1024px, full `[data-theme="dark"]` parity,
`prefers-reduced-motion`). The only change is the file rename + comment. The ToS simply won't use the
`.legal-callout--warn` / `.legal-meta` / `.legal-ph` classes (they remain available, harmless).

## 8. Behavior (`legal.js`)

- On load: read `nets-landing-lang` (`uz` default; `uz|ru|en`); set `html[data-lang]`; mark the active
  `.lang-pill`. Inline head script does the same synchronously to avoid a flash.
- On `.lang-pill` click: switch `data-lang`, persist to `nets-landing-lang`, update pills, retranslate
  `data-i18n-<lang>` chrome nodes.
- Same storage key as `landing.js` and (post-fix) `privacy.html` → choice carries across all pages.
- No dependency on `landing.js`; theme owned by `theme.js`.

## 9. Data flow

Static file → FastAPI handler substitutes `__VERSION__` (git short SHA) at request time → served via
Caddy. Language + theme toggles are pure client-side. No backend logic beyond the one route entry; no new deps.

## 10. Error handling / edge cases

- `localStorage` blocked (private mode): fall back to default `uz`; never throw (mirror existing `try/catch`).
- Unknown/missing `nets-landing-lang`: clamp to `uz`.
- JS disabled: default `uz` panel visible via CSS; page fully readable, just not switchable.
- Wide content on small screens: any table wrapped in `.legal-table-wrap` (overflow-x).

## 11. Testing / verification

- Route: `GET /terms` and `/terms.html` return 200 with `__VERSION__` substituted.
- Visual: header/footer/nav match landing + privacy; light **and** dark render correctly; reading column
  Apple-grade; mobile intact.
- Language: UZ↔RU↔EN swaps panels, persists across reload, and **carries to/from `landing.html` AND
  `/privacy`** (shared `nets-landing-lang` after the fix). Verify the privacy page now syncs too.
- Footer: landing footer shows Terms + Privacy, both translated in all three languages, both navigating correctly.
- Accessibility: skip-link, ordered headings, labelled toggles, `:focus-visible`, reduced-motion respected.
- Content fidelity: every §1–19 + contact present in EN; UZ/RU mirror the same structure; placeholders
  filled per §5; no draft/checklist/meta blocks leaked.
- Regression: `/privacy` still renders after the css/js rename (links re-pointed); privacy language now
  persists under the corrected key.

## 12. Out of scope

- Filling the remaining legal substance that needs counsel (e.g., the §13 nominal floor amount — dropped, not invented).
- Re-polishing the privacy page's content presentation to match the ToS (only the lang-key + file-rename touch privacy).
- Any change to existing landing sections beyond the single footer link + its i18n key.
