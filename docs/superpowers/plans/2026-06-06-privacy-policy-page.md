# Privacy Policy Page Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a public, trilingual (UZ/RU/EN) Privacy Policy page at `/privacy` that renders `docs/legal/Privacy_Policy.md` verbatim in the existing landing-page design system.

**Architecture:** A single self-contained `frontend/privacy.html` holds the full policy three times — one `.legal-doc` block per language — toggled by CSS keyed on `html[data-lang]`. A tiny inline head script sets the initial language synchronously (flash-free, mirroring `theme.js`); `frontend/js/privacy.js` wires the `.lang-pill` clicks. Long-form legal typography lives in a new `frontend/css/privacy.css` built entirely on landing.css's `--landing-*` tokens. One route row is added to `server/app.py`; a Privacy link is added to the landing footer.

**Tech Stack:** Vanilla HTML/CSS/JS, FastAPI static-page routing (`_HTML_PAGES` + `__VERSION__` substitution), existing `theme.js` (dark mode) + `landing_lang` localStorage convention.

---

## File structure

| File | Action | Responsibility |
|------|--------|----------------|
| `frontend/css/privacy.css` | Create | Long-form legal typography, TOC, tables, callouts, dark-mode parity, language-panel CSS switching. Built on `--landing-*` tokens. |
| `frontend/js/privacy.js` | Create | Language toggle: read/persist `landing_lang`, set `html[data-lang]`, sync `.lang-pill` active state. |
| `frontend/privacy.html` | Create | Page: reused header/footer chrome + inline lang head-script + 3 `.legal-doc` panels (uz/ru/en), each = TOC + body. |
| `server/app.py` | Modify | Add `/privacy` + `/privacy.html` to `_HTML_PAGES`. |
| `frontend/landing.html` | Modify | Add Privacy link to `.landing-footer`. |
| `frontend/js/landing.js` | Modify | Add `footerPrivacy` i18n key to uz/ru/en dicts. |

**Conventions locked in:**
- Section IDs are language-prefixed: `uz-s1`…`uz-s15`, `uz-intro`, `uz-meta`, `uz-appendix-a`, `uz-appendix-b`, `uz-checklist` (and `ru-*`, `en-*`). Prevents duplicate-ID collisions across panels.
- Default language is `uz` (matches `landing.html`).
- `[BRACKETED]` placeholders are kept visible, wrapped in `<span class="legal-ph">…</span>`.
- No new JS test framework (repo's frontend JS — `theme.js`, `landing.js`, `apply.js` — has none). Verification is route-check (curl) + browser screenshots in light/dark × 3 languages.

---

## Task 1: Add the `/privacy` route

**Files:**
- Modify: `server/app.py:137-146`

- [ ] **Step 1: Add the two route rows to `_HTML_PAGES`**

In the `_HTML_PAGES` dict, add `/privacy` and `/privacy.html` (keep alphabeticalish grouping next to apply):

```python
_HTML_PAGES: dict[str, str] = {
    "/":              "landing.html",
    "/index.html":    "index.html",
    "/apply":         "apply.html",
    "/apply.html":    "apply.html",
    "/builder.html":  "builder.html",
    "/library.html":  "library.html",
    "/landing.html":  "landing.html",
    "/privacy":       "privacy.html",
    "/privacy.html":  "privacy.html",
    "/taskboard.html": "taskboard.html",
}
```

- [ ] **Step 2: Commit** (route only; page comes next)

```bash
git add server/app.py
git commit -m "feat(privacy): register /privacy route"
```

---

## Task 2: Create `frontend/css/privacy.css`

**Files:**
- Create: `frontend/css/privacy.css`

- [ ] **Step 1: Write the full stylesheet** (complete — paste verbatim)

```css
/* ============================================================
   Homeworks — Privacy Policy (legal long-form)
   Loaded AFTER landing.css; inherits --landing-* tokens.
   Trilingual: panels toggled via html[data-lang]; see privacy.js.
   ============================================================ */

/* -------- Language panel switching -------- */
.legal-doc { display: none; }
html[data-lang="uz"] .legal-doc[data-lang-panel="uz"],
html[data-lang="ru"] .legal-doc[data-lang-panel="ru"],
html[data-lang="en"] .legal-doc[data-lang-panel="en"] { display: block; }
html:not([data-lang]) .legal-doc[data-lang-panel="uz"] { display: block; }

/* -------- Page shell -------- */
.legal-wrap {
  max-inline-size: 1120px;
  margin-inline: auto;
  padding-inline: 16px;
  padding-block: 40px 96px;
}
@media (min-width: 640px) { .legal-wrap { padding-inline: 24px; padding-block: 64px 120px; } }

/* -------- Title header -------- */
.legal-head { margin-block-end: 32px; }
.legal-eyebrow {
  margin: 0 0 10px;
  font-size: 13px;
  font-weight: 600;
  letter-spacing: 0.18em;
  text-transform: uppercase;
  color: var(--landing-blue-600);
}
.legal-head h1 {
  margin: 0;
  font-size: clamp(30px, 5vw, 46px);
  font-weight: 600;
  letter-spacing: -0.02em;
  line-height: 1.08;
  color: var(--landing-zinc-950);
}
.legal-updated { margin: 14px 0 0; font-size: 14px; color: var(--landing-zinc-500); }

/* -------- Layout: TOC + body -------- */
.legal-layout { display: block; }
@media (min-width: 1024px) {
  .legal-layout {
    display: grid;
    grid-template-columns: 248px minmax(0, 1fr);
    gap: 48px;
    align-items: start;
  }
}

/* -------- Table of contents -------- */
.legal-toc {
  margin-block-end: 32px;
  border: 1px solid var(--landing-ring);
  border-radius: 18px;
  background: var(--landing-card);
  padding: 18px 20px;
  box-shadow: var(--landing-shadow-soft);
}
@media (min-width: 1024px) {
  .legal-toc {
    position: sticky;
    top: 76px;
    margin-block-end: 0;
    max-block-size: calc(100vh - 100px);
    overflow-y: auto;
  }
}
.legal-toc__title {
  margin: 0 0 12px;
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--landing-zinc-500);
}
.legal-toc ol { margin: 0; padding: 0; list-style: none; display: grid; gap: 2px; }
.legal-toc a {
  display: block;
  padding: 6px 8px;
  border-radius: 8px;
  font-size: 13px;
  line-height: 1.4;
  color: var(--landing-zinc-600);
  transition: background 160ms var(--landing-spring), color 160ms var(--landing-spring);
}
.legal-toc a:hover { background: var(--landing-zinc-100); color: var(--landing-zinc-950); }

/* -------- Body typography -------- */
.legal-body { max-inline-size: 760px; min-inline-size: 0; }
.legal-body section { scroll-margin-top: 76px; }
.legal-body h2 {
  margin: 44px 0 14px;
  font-size: clamp(21px, 2.6vw, 27px);
  font-weight: 600;
  letter-spacing: -0.015em;
  line-height: 1.2;
  color: var(--landing-zinc-950);
  scroll-margin-top: 76px;
}
.legal-body h3 {
  margin: 26px 0 8px;
  font-size: 17px;
  font-weight: 600;
  letter-spacing: -0.01em;
  color: var(--landing-zinc-950);
}
.legal-body p { margin: 0 0 14px; font-size: 15.5px; line-height: 1.72; color: var(--landing-zinc-700); }
.legal-body a { color: var(--landing-blue-600); text-decoration: underline; text-underline-offset: 2px; }
.legal-toc a { text-decoration: none; }
.legal-body strong { color: var(--landing-zinc-950); font-weight: 600; }
.legal-body ul, .legal-body ol { margin: 0 0 16px; padding-inline-start: 22px; }
.legal-body li { margin: 0 0 8px; font-size: 15.5px; line-height: 1.7; color: var(--landing-zinc-700); }
.legal-body li strong { color: var(--landing-zinc-950); }

/* -------- Tables -------- */
.legal-table-wrap {
  margin: 0 0 18px;
  overflow-x: auto;
  border: 1px solid var(--landing-ring);
  border-radius: 14px;
}
.legal-body table { inline-size: 100%; border-collapse: collapse; font-size: 14px; min-inline-size: 560px; }
.legal-body thead th {
  text-align: start;
  font-weight: 600;
  color: var(--landing-zinc-950);
  background: var(--landing-zinc-100);
  padding: 10px 14px;
  border-block-end: 1px solid var(--landing-ring);
}
.legal-body tbody td {
  padding: 10px 14px;
  vertical-align: top;
  line-height: 1.55;
  color: var(--landing-zinc-700);
  border-block-end: 1px solid var(--landing-ring);
}
.legal-body tbody tr:last-child td { border-block-end: 0; }

/* -------- Callouts (draft notice / open items / notes) -------- */
.legal-meta {
  margin: 0 0 24px;
  border: 1px solid var(--landing-ring);
  border-radius: 14px;
  background: var(--landing-card);
  padding: 16px 18px;
  font-size: 13px;
  line-height: 1.6;
  color: var(--landing-zinc-500);
}
.legal-meta dl { margin: 0; display: grid; grid-template-columns: max-content 1fr; gap: 4px 14px; }
.legal-meta dt { font-weight: 600; color: var(--landing-zinc-700); }
.legal-meta dd { margin: 0; }
.legal-callout {
  margin: 0 0 24px;
  border: 1px solid var(--landing-ring);
  border-inline-start: 3px solid var(--landing-zinc-400);
  border-radius: 14px;
  background: var(--landing-card-tinted);
  padding: 16px 18px;
}
.legal-callout > :first-child { margin-block-start: 0; }
.legal-callout > :last-child { margin-block-end: 0; }
.legal-callout h2, .legal-callout h3 { margin-block: 0 8px; font-size: 16px; }
.legal-callout p, .legal-callout li { font-size: 14px; }
.legal-callout--warn { border-inline-start-color: #d97706; background: #fffbeb; }
.legal-callout--warn strong, .legal-callout--warn h2, .legal-callout--warn h3 { color: #92400e; }

/* Inline placeholder tokens like [BRACKETED] kept visible but subtle */
.legal-ph {
  font-style: normal;
  color: var(--landing-zinc-500);
  background: var(--landing-zinc-100);
  border-radius: 4px;
  padding: 0 4px;
  font-size: 0.92em;
}

/* -------- Footer (reuses .landing-footer chrome) -------- */
.legal-footer__inner {
  max-inline-size: 1120px;
  margin-inline: auto;
  padding-inline: 16px;
  padding-block: 20px 28px;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
  font-size: 13px;
  color: var(--landing-zinc-500);
}
.legal-footer__link { color: var(--landing-zinc-700); }
.legal-footer__link:hover { color: var(--landing-zinc-950); }

/* -------- Dark mode parity -------- */
[data-theme="dark"] .legal-head h1 { color: rgba(244,244,245,0.96); }
[data-theme="dark"] .legal-updated { color: rgba(244,244,245,0.5); }
[data-theme="dark"] .legal-eyebrow { color: var(--landing-blue-400); }
[data-theme="dark"] .legal-toc { background: var(--landing-zinc-900); border-color: rgba(63,63,70,0.6); }
[data-theme="dark"] .legal-toc a { color: rgba(244,244,245,0.62); }
[data-theme="dark"] .legal-toc a:hover { background: rgba(63,63,70,0.4); color: rgba(244,244,245,0.96); }
[data-theme="dark"] .legal-body h2, [data-theme="dark"] .legal-body h3 { color: rgba(244,244,245,0.96); }
[data-theme="dark"] .legal-body p, [data-theme="dark"] .legal-body li { color: rgba(244,244,245,0.72); }
[data-theme="dark"] .legal-body strong, [data-theme="dark"] .legal-body li strong { color: rgba(244,244,245,0.96); }
[data-theme="dark"] .legal-meta { background: var(--landing-zinc-900); border-color: rgba(63,63,70,0.6); color: rgba(244,244,245,0.55); }
[data-theme="dark"] .legal-meta dt { color: rgba(244,244,245,0.78); }
[data-theme="dark"] .legal-table-wrap { border-color: rgba(63,63,70,0.6); }
[data-theme="dark"] .legal-body thead th { background: var(--landing-zinc-800); color: rgba(244,244,245,0.96); border-block-end-color: rgba(63,63,70,0.6); }
[data-theme="dark"] .legal-body tbody td { color: rgba(244,244,245,0.72); border-block-end-color: rgba(63,63,70,0.6); }
[data-theme="dark"] .legal-callout { background: var(--landing-zinc-900); border-color: rgba(63,63,70,0.6); border-inline-start-color: var(--landing-zinc-500); }
[data-theme="dark"] .legal-callout--warn { background: rgba(217,119,6,0.12); border-inline-start-color: #f59e0b; }
[data-theme="dark"] .legal-callout--warn strong, [data-theme="dark"] .legal-callout--warn h2, [data-theme="dark"] .legal-callout--warn h3 { color: #fcd34d; }
[data-theme="dark"] .legal-ph { background: rgba(63,63,70,0.5); color: rgba(244,244,245,0.6); }
[data-theme="dark"] .legal-footer__inner { color: rgba(244,244,245,0.5); }
[data-theme="dark"] .legal-footer__link { color: rgba(244,244,245,0.78); }
[data-theme="dark"] .legal-footer__link:hover { color: rgba(244,244,245,0.96); }

@media (prefers-reduced-motion: reduce) {
  .legal-toc a { transition: none; }
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/css/privacy.css
git commit -m "feat(privacy): add legal long-form stylesheet"
```

---

## Task 3: Create `frontend/js/privacy.js`

**Files:**
- Create: `frontend/js/privacy.js`

- [ ] **Step 1: Write the language toggle** (complete — paste verbatim)

```javascript
/* Homeworks — Privacy page language toggle.
 * Shares the `landing_lang` localStorage key with landing.js so the choice
 * carries across pages. The initial language is set synchronously by a small
 * inline <head> script (see privacy.html) to avoid a flash; this file wires the
 * .lang-pill click handlers and keeps the active state in sync. Theme stays
 * owned by theme.js.
 */
(function () {
  var LANG_KEY = 'landing_lang';
  var SUPPORTED = ['uz', 'ru', 'en'];
  var DEFAULT = 'uz';

  function readLang() {
    try {
      var v = localStorage.getItem(LANG_KEY);
      if (v && SUPPORTED.indexOf(v) !== -1) return v;
    } catch (e) { /* private mode */ }
    return DEFAULT;
  }

  function applyLang(lang) {
    if (SUPPORTED.indexOf(lang) === -1) lang = DEFAULT;
    document.documentElement.setAttribute('data-lang', lang);
    document.documentElement.lang = lang;
    try { localStorage.setItem(LANG_KEY, lang); } catch (e) { /* private mode */ }
    var pills = document.querySelectorAll('.lang-pill');
    for (var i = 0; i < pills.length; i++) {
      var on = pills[i].getAttribute('data-lang') === lang;
      pills[i].classList.toggle('is-active', on);
      pills[i].setAttribute('aria-pressed', on ? 'true' : 'false');
    }
  }

  function wire() {
    var pills = document.querySelectorAll('.lang-pill');
    for (var i = 0; i < pills.length; i++) {
      pills[i].addEventListener('click', function () {
        var lang = this.getAttribute('data-lang');
        if (lang) applyLang(lang);
      });
    }
    applyLang(readLang());
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', wire);
  } else {
    wire();
  }
})();
```

- [ ] **Step 2: Commit**

```bash
git add frontend/js/privacy.js
git commit -m "feat(privacy): add language toggle script"
```

---

## Task 4: Create the `privacy.html` shell (chrome + 3 empty panels)

Build the page skeleton first and verify it serves, toggles, and themes — *before* pouring in 4,200 words × 3. Use a one-line placeholder per panel; real content lands in Tasks 5–7.

**Files:**
- Create: `frontend/privacy.html`

- [ ] **Step 1: Write the shell** (complete — paste verbatim; content panels filled later)

```html
<!DOCTYPE html>
<html lang="uz" data-page="privacy">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Homeworks · Privacy Policy</title>
  <meta name="description" content="Privacy Policy for the Class A Education / Homeworks learning platform." />
  <meta name="robots" content="index, follow" />
  <link rel="icon" type="image/png" sizes="32x32" href="/img/favicon-32.png?v=__VERSION__" />
  <link rel="apple-touch-icon" href="/img/classa-logo.png?v=__VERSION__" />
  <link rel="preload" href="/css/landing.css?v=__VERSION__" as="style" />
  <link rel="stylesheet" href="/css/landing.css?v=__VERSION__" />
  <link rel="stylesheet" href="/css/privacy.css?v=__VERSION__" />
  <script src="/js/theme.js?v=__VERSION__"></script>
  <script>
    /* Phase A — set language synchronously before paint (flash-free). */
    (function () {
      try {
        var l = localStorage.getItem('landing_lang');
        var s = ['uz', 'ru', 'en'];
        document.documentElement.setAttribute('data-lang', s.indexOf(l) !== -1 ? l : 'uz');
      } catch (e) {
        document.documentElement.setAttribute('data-lang', 'uz');
      }
    })();
  </script>
</head>
<body class="landing-body">
  <a class="skip-link" href="#privacy-main">Skip to content</a>

  <header class="landing-header" role="banner">
    <nav class="landing-nav" aria-label="Primary">
      <a href="/" class="brand-link" aria-label="Homeworks home">
        <span class="brand-mark" aria-hidden="true">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M3 8l9-5 9 5-9 5Zm5 5v4c2.5 2 5.5 2 8 0v-4M19 10v6"></path></svg>
        </span>
        <span class="brand-text">Homeworks</span>
      </a>

      <div class="nav-links" role="navigation" aria-label="Sections">
        <a href="/" class="nav-link" data-i18n-uz="← Bosh sahifa" data-i18n-ru="← На главную" data-i18n-en="← Home">← Bosh sahifa</a>
      </div>

      <div class="nav-actions">
        <div class="lang-toggle" role="group" aria-label="Language">
          <button type="button" class="lang-pill" data-lang="uz">UZ</button>
          <button type="button" class="lang-pill" data-lang="ru">RU</button>
          <button type="button" class="lang-pill" data-lang="en">EN</button>
        </div>
        <button type="button" class="theme-toggle" data-theme-toggle aria-label="Switch to dark mode" aria-pressed="false">🌙</button>
      </div>
    </nav>
  </header>

  <main id="privacy-main" class="legal-wrap">

    <!-- ===================== UZ ===================== -->
    <div class="legal-doc" lang="uz" data-lang-panel="uz">
      <p>UZ panel placeholder</p>
    </div>

    <!-- ===================== RU ===================== -->
    <div class="legal-doc" lang="ru" data-lang-panel="ru">
      <p>RU panel placeholder</p>
    </div>

    <!-- ===================== EN ===================== -->
    <div class="legal-doc" lang="en" data-lang-panel="en">
      <p>EN panel placeholder</p>
    </div>

  </main>

  <footer class="landing-footer" role="contentinfo">
    <div class="legal-footer__inner">
      <span>Homeworks</span>
      <span class="landing-footer__sep" aria-hidden="true">·</span>
      <a href="/" class="legal-footer__link" data-i18n-uz="← Bosh sahifa" data-i18n-ru="← На главную" data-i18n-en="← Home">← Bosh sahifa</a>
    </div>
  </footer>

  <script src="/js/privacy.js?v=__VERSION__" defer></script>
</body>
</html>
```

> **Note on the back-link text:** the `← Home` link and footer use `data-i18n-uz/ru/en` attributes. These are translated by a 3-line loop appended to `privacy.js` in Task 5 Step 2 (kept out of the panel system because they live in shared chrome). For the shell smoke-test they simply show the `uz` default.

- [ ] **Step 2: Smoke-test the route + serving**

Start a throwaway server from the Homeworks dir on a spare port (does NOT touch the live :8000), then curl:

```bash
cd "/Users/aisigma/projects/SigmaDevelopment/Class A Education/Homeworks"
.venv/bin/python -m uvicorn server.app:app --port 8011 >/tmp/priv.log 2>&1 &
sleep 3
curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8011/privacy
curl -s http://127.0.0.1:8011/privacy | grep -c 'data-lang-panel'
```

Expected: `200`, and grep count `3`. (If `.venv` is absent, fall back to `python3 -m http.server 8011 --directory frontend` and hit `http://127.0.0.1:8011/privacy.html`.)

- [ ] **Step 3: Browser check — toggle + theme** (playwright MCP)

Navigate to `http://127.0.0.1:8011/privacy`, screenshot. Click `.lang-pill[data-lang="en"]` → only EN placeholder visible. Click `.theme-toggle` → dark mode applies (page bg dark). Reload → language persists. Screenshot light+dark.

- [ ] **Step 4: Stop the throwaway server**

```bash
kill %1 2>/dev/null; pkill -f 'uvicorn server.app:app --port 8011' 2>/dev/null; true
```

- [ ] **Step 5: Commit**

```bash
git add frontend/privacy.html
git commit -m "feat(privacy): add page shell with trilingual panels + chrome"
```

---

## Task 5: Fill the EN panel (faithful HTML conversion of the source)

Convert the **entire** `docs/legal/Privacy_Policy.md` into the EN panel — nothing omitted (YAML frontmatter → metadata block; the ⚠️ DRAFT blockquote; all 15 sections; both appendices; the "Before Publishing" checklist).

**Files:**
- Modify: `frontend/privacy.html` (EN panel)
- Modify: `frontend/js/privacy.js` (append chrome-i18n loop)

**Conversion rules (apply consistently):**
1. Panel body wrapper:
   ```html
   <div class="legal-layout">
     <aside class="legal-toc" aria-label="Contents">
       <p class="legal-toc__title">Contents</p>
       <ol> … one <li><a href="#en-sN">N. Title</a></li> per section … </ol>
     </aside>
     <article class="legal-body">
       <header class="legal-head">
         <p class="legal-eyebrow">Class A Education</p>
         <h1>Privacy Policy</h1>
         <p class="legal-updated">Last updated: <span class="legal-ph">[PUBLICATION DATE]</span> · Version: <span class="legal-ph">[1.0]</span></p>
       </header>
       … meta block, draft callout, sections …
     </article>
   </div>
   ```
2. **YAML frontmatter** → a `<div class="legal-meta" id="en-meta"><dl>…</dl></div>` with one `dt/dd` pair per field (title, status, version, drafted, effective, owner, compliance target, source/Trello). Renders the owner (`Leo (GTM)`) and Trello card verbatim, per the verbatim decision.
3. **`> ## ⚠️ DRAFT — NOT YET IN EFFECT`** blockquote → `<aside class="legal-callout legal-callout--warn">` with an `<h2>⚠️ DRAFT — NOT YET IN EFFECT</h2>` + the two paragraphs.
4. **`## N. Title`** → `<section id="en-sN"><h2>N. Title</h2>…</section>`. **`### 4.x`** → `<h3>`.
5. **Tables** → `<div class="legal-table-wrap"><table><thead>…</thead><tbody>…</tbody></table></div>`.
6. **`> **Note…` / `> **Open item…`** blockquotes → `<aside class="legal-callout">`.
7. **`**bold**`** → `<strong>`; **`** `[X]` ``** inline placeholders → `<span class="legal-ph">[X]</span>`; bullet lists → `<ul>`, the numbered checklist → `<ol>`.
8. IDs for TOC targets: `en-s1`…`en-s15`, `en-appendix-a`, `en-appendix-b`, `en-checklist`.

- [ ] **Step 1: Worked example — §2 (proves the style)**

Section 2 with its 4-column table renders exactly like this (use as the pattern for all sections):

```html
<section id="en-s2">
  <h2>2. Who We Are &amp; Our Two Roles</h2>
  <p><strong>Controller:</strong> <span class="legal-ph">[Class-A-Technologies MCHJ]</span>, <span class="legal-ph">[registered address, Tashkent, Uzbekistan]</span>, registration No. <span class="legal-ph">[•]</span>. Contact: <span class="legal-ph">[privacy@classa.education]</span>. Data Protection Officer / Privacy Lead: <span class="legal-ph">[NAME / privacy@classa.education]</span>.</p>
  <p>We act in <strong>two different roles</strong> depending on how you use the Services. This distinction matters because it determines who decides how data is used and how you exercise your rights.</p>
  <div class="legal-table-wrap">
    <table>
      <thead>
        <tr><th>Scenario</th><th>School-provided (institutional)</th><th>Direct (home / individual)</th></tr>
      </thead>
      <tbody>
        <tr><td><strong>How it's used</strong></td><td>A school or teacher licenses the Services and enrols students</td><td>A parent registers a student directly</td></tr>
        <tr><td><strong>Who is the "controller"</strong></td><td>The <strong>school</strong> is the controller; <strong>Class A is the processor</strong>, acting on the school's documented instructions</td><td><strong>Class A is the controller</strong></td></tr>
        <tr><td><strong>Consent for a child</strong></td><td>The <strong>school provides consent on behalf of parents</strong> for in-school use (COPPA "school authorisation"); we act as a <strong>FERPA "school official"</strong> with a legitimate educational interest</td><td>The <strong>parent provides verifiable consent</strong> directly</td></tr>
        <tr><td><strong>How to exercise rights</strong></td><td>Requests are <strong>routed through the school</strong></td><td>Requests come <strong>directly to us</strong></td></tr>
      </tbody>
    </table>
  </div>
  <p>Where we are a <strong>processor</strong>, we only process student data to provide the Services to the school, never for our own purposes, and our agreement with the school (the <strong>Data Processing Agreement</strong>, Appendix B) governs.</p>
</section>
```

- [ ] **Step 2: Append the chrome-i18n loop to `privacy.js`**

So the `← Home` back-link + footer link translate with the toggle. Add inside `applyLang(lang)`, after the pill loop:

```javascript
    var nodes = document.querySelectorAll('[data-i18n-uz]');
    for (var n = 0; n < nodes.length; n++) {
      var t = nodes[n].getAttribute('data-i18n-' + lang);
      if (t !== null) nodes[n].textContent = t;
    }
```

- [ ] **Step 3: Convert and paste the full EN document** into the EN panel using the rules + worked example. Build the TOC `<ol>` to match the section IDs.

- [ ] **Step 4: Verify EN renders** — restart the throwaway server (Task 4 Step 2), navigate `http://127.0.0.1:8011/privacy`, switch to EN, screenshot full page (light + dark). Confirm: all 15 sections present, all 5 tables render inside scroll wrappers, TOC links jump to sections (offset clears the sticky header), placeholders show as subtle chips, draft callout is amber.

- [ ] **Step 5: Commit**

```bash
git add frontend/privacy.html frontend/js/privacy.js
git commit -m "feat(privacy): render full English policy + chrome i18n"
```

---

## Task 6: Fill the UZ panel (translation)  ·  Task 7: Fill the RU panel (translation)

These run in parallel (one translation sub-agent each). Each produces the panel's inner HTML mirroring the EN structure exactly — same tags, same table shapes, same callouts, same section order — translating only human-readable text.

**Files:** Modify `frontend/privacy.html` (UZ panel / RU panel respectively).

**Translation rules:**
- Translate all prose, headings, list items, table cells, TOC labels, the metadata `dt` labels, and the draft/notice callouts.
- **Do NOT translate / keep verbatim:** `[BRACKETED]` placeholders (inside `.legal-ph`), the email/entity placeholders, proper nouns and legal references — `Class A`, `Homeworks`, `ZRU-547`, `GDPR`, `COPPA`, `FERPA`, `ISO 27001`, `NIST CSF`, `Expo / EAS`, `Apple App Store`, `Google Play`, `Firebase Cloud Messaging`, `Trello`, `Leo (GTM)`, `edu.jakhongir.dev`, `Standard Contractual Clauses`.
- Change every `id="en-…"` to `id="uz-…"` (Task 6) / `id="ru-…"` (Task 7), and update the TOC `href`s to match.
- Keep `data-lang-panel` and the `lang="uz"`/`lang="ru"` attribute on the panel root.
- Glossary anchors (consistent terms):
  - UZ: Privacy Policy → "Maxfiylik siyosati"; data → "ma'lumotlar"; student → "o'quvchi"; parent → "ota-ona"; teacher → "o'qituvchi"; school → "maktab"; consent → "rozilik"; rights → "huquqlar".
  - RU: Privacy Policy → "Политика конфиденциальности"; data → "данные"; student → "ученик"; parent → "родитель"; teacher → "учитель"; school → "школа"; consent → "согласие"; rights → "права".

- [ ] **Step 1 (each):** Produce the translated panel HTML (sub-agent), keeping structure identical to EN.
- [ ] **Step 2 (each):** Paste into the matching panel in `frontend/privacy.html`.
- [ ] **Step 3 (each):** Verify — switch the toggle to UZ / RU, screenshot light+dark, confirm structure matches EN (same tables/sections), no leaked English in prose, placeholders intact.
- [ ] **Step 4:** Commit

```bash
git add frontend/privacy.html
git commit -m "feat(privacy): add Uzbek + Russian policy translations"
```

---

## Task 8: Add the footer Privacy link on the landing page

**Files:**
- Modify: `frontend/landing.html:365-371`
- Modify: `frontend/js/landing.js` (uz/ru/en `footerPrivacy` key)

- [ ] **Step 1: Add the link to the landing footer**

Replace the footer inner with (adds a separator + link after `footerNote`):

```html
    <footer class="landing-footer" role="contentinfo">
      <div class="section-inner landing-footer__inner">
        <span data-i18n="brand">Homeworks</span>
        <span class="landing-footer__sep" aria-hidden="true">·</span>
        <span data-i18n="footerNote">Beta loyiha — interaktiv darslar uchun.</span>
        <span class="landing-footer__sep" aria-hidden="true">·</span>
        <a href="/privacy" class="nav-link" data-i18n="footerPrivacy">Maxfiylik siyosati</a>
      </div>
    </footer>
```

- [ ] **Step 2: Add the `footerPrivacy` i18n key** to each language block in `frontend/js/landing.js`, immediately after that block's `footerNote:` line:

- uz block: `footerPrivacy: "Maxfiylik siyosati",`
- ru block: `footerPrivacy: "Политика конфиденциальности",`
- en block: `footerPrivacy: "Privacy Policy",`

(Locate each with `grep -n "footerNote:" frontend/js/landing.js` — there are three, one per language.)

- [ ] **Step 3: Verify** — serve, load `/` (landing), confirm the footer shows a "Maxfiylik siyosati" link, clicking it navigates to `/privacy`; switch language pills and confirm the footer label translates (uz/ru/en).

- [ ] **Step 4: Commit**

```bash
git add frontend/landing.html frontend/js/landing.js
git commit -m "feat(landing): link Privacy Policy in footer (trilingual)"
```

---

## Task 9: Full verification pass

- [ ] **Step 1: Route** — `curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8011/privacy` → `200`; same for `/privacy.html`. Confirm `__VERSION__` is substituted (no literal `__VERSION__` in `curl http://127.0.0.1:8011/privacy | grep VERSION`).
- [ ] **Step 2: Visual matrix** (playwright MCP screenshots) — 3 languages × 2 themes = 6 screenshots. Header/footer match landing; reading column, tables, callouts, TOC all look Apple-grade; mobile width (resize to 390px) intact; tables scroll, don't overflow.
- [ ] **Step 3: Behavior** — language persists across reload and carries to `/` and back; theme toggle works and persists; skip-link focuses content; TOC anchors land below the sticky header; `:focus-visible` rings on pills/links.
- [ ] **Step 4: Fidelity** — every EN section/table/list/checklist item from the `.md` is present; UZ and RU mirror the same structure with no leaked English in prose.
- [ ] **Step 5: Stop the throwaway server** (Task 4 Step 4).
- [ ] **Step 6: Final commit** (if any verification fixes were made).

---

## Self-review (done at write time)

- **Spec coverage:** verbatim full doc → Tasks 5/6/7 (incl. frontmatter meta block, draft callout, checklist); trilingual + default uz → CSS panel switch + privacy.js + inline head script; landing.css aesthetic → privacy.css on `--landing-*` tokens; footer link → Task 8; route → Task 1; dark mode + a11y + reduced-motion → privacy.css + verify Task 9. All covered.
- **Placeholder scan:** infra steps (CSS/JS/HTML shell/server/footer) contain complete code. Content tasks are rule-based + a fully-worked section example (the only honest way to plan a 12k-word trilingual transform) — not "TODO".
- **Type/name consistency:** classes (`.legal-doc`, `.legal-layout`, `.legal-toc`, `.legal-body`, `.legal-callout`, `.legal-meta`, `.legal-ph`, `.legal-footer__*`), the `html[data-lang]` switch, `landing_lang` key, `data-lang-panel` values, and `en-/uz-/ru-` ID prefixes are consistent across CSS, JS, and HTML.
