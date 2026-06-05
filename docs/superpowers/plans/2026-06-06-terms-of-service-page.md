# Terms of Service Page — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a public, fully-trilingual (UZ/RU/EN) Terms of Service page at `/terms` that is a visual + behavioral twin of the already-built `/privacy` page, rendered "final look" (placeholders filled, internal/draft blocks stripped) per the owner's decisions.

**Architecture:** Static HTML served by FastAPI (`server/app.py` `_HTML_PAGES`) with `__VERSION__` cache-bust substitution. The page renders the ToS three times — one `.legal-doc[data-lang-panel]` per language — and CSS shows the active panel via `html[data-lang]`. Language + styling infra (`legal.css`, `legal.js`) is shared with the privacy page after a rename, and the privacy page's wrong localStorage key (`landing_lang` → `nets-landing-lang`) is corrected so all pages sync.

**Tech Stack:** Vanilla HTML/CSS/JS, FastAPI (Python), the existing `landing.css` `--landing-*` token system, `theme.js` (dark mode), shared `legal.js` (language toggle).

**Spec:** `docs/superpowers/specs/2026-06-06-terms-of-service-page-design.md`
**Source content:** `/Users/aisigma/projects/SigmaDevelopment/docs/legal/Terms_of_Service.md`

**Verification server:** the launchd `:8000` serves a *different* copy (`~/nets-builder`). To verify THIS repo, run a throwaway server on a free port:
```bash
./.venv/bin/python -m uvicorn server.app:app --host 127.0.0.1 --port 8011
```
Use `http://127.0.0.1:8011` for all curl checks. Stop it when done.

---

## Task 1: Extract shared `legal.css` / `legal.js` + fix the privacy lang key

**Files:**
- Rename: `frontend/css/privacy.css` → `frontend/css/legal.css`
- Rename: `frontend/js/privacy.js` → `frontend/js/legal.js`
- Modify: `frontend/js/legal.js` (lang key + comment)
- Modify: `frontend/css/legal.css` (header comment only)
- Modify: `frontend/privacy.html` (3 references)

- [ ] **Step 1: Rename the two files with git**

```bash
cd "/Users/aisigma/projects/SigmaDevelopment/Class A Education/Homeworks"
git mv frontend/css/privacy.css frontend/css/legal.css
git mv frontend/js/privacy.js  frontend/js/legal.js
```
(If the files are untracked, use plain `mv` instead — check `git status` first.)

- [ ] **Step 2: Fix the localStorage key in `legal.js`**

In `frontend/js/legal.js`, change line 10:
```js
  var LANG_KEY = 'landing_lang';
```
to:
```js
  var LANG_KEY = 'nets-landing-lang';
```
And update the top comment (lines 1-8) `landing_lang` → `nets-landing-lang`, and "Privacy page" → "Legal pages (Privacy + Terms)".

- [ ] **Step 3: Update the `legal.css` header comment**

In `frontend/css/legal.css`, change the comment block (lines 1-5) from "Privacy Policy (legal long-form)" to "Legal long-form (Privacy + Terms) — loaded after landing.css; inherits --landing-* tokens."

- [ ] **Step 4: Re-point `privacy.html` to the shared files + fix its inline key**

In `frontend/privacy.html`:
- Line 13: `/css/privacy.css` → `/css/legal.css`
- Line 19 (inline head script): `localStorage.getItem('landing_lang')` → `localStorage.getItem('nets-landing-lang')`
- Line 1042 (end of body): `/js/privacy.js` → `/js/legal.js`

- [ ] **Step 5: Verify no stale references remain**

```bash
grep -rn "privacy\.css\|privacy\.js\|landing_lang" frontend/ server/
```
Expected: **no matches** (every reference now points to `legal.css` / `legal.js` / `nets-landing-lang`). The only `legal.js`/`legal.css` consumers so far are `privacy.html`.

- [ ] **Step 6: Verify `/privacy` still renders (regression)**

Start the test server (see header), then:
```bash
curl -fsS "http://127.0.0.1:8011/privacy" | grep -c "legal.css\|legal.js"
```
Expected: `2` (both shared assets linked). And:
```bash
curl -fsS "http://127.0.0.1:8011/css/legal.css" | head -1
curl -fsS "http://127.0.0.1:8011/js/legal.js"  | grep "nets-landing-lang"
```
Expected: CSS comment line prints; the grep finds the corrected key.

- [ ] **Step 7: Commit**

```bash
git add -A frontend/css/legal.css frontend/js/legal.js frontend/privacy.html
git commit -m "refactor(legal): share legal.css/legal.js across legal pages; fix lang-sync key

Co-Authored-By: RuFlo <ruv@ruv.net>"
```

---

## Task 2: Register the `/terms` route

**Files:**
- Modify: `server/app.py` (`_HTML_PAGES` dict, ~lines 137-146)

- [ ] **Step 1: Add the two route entries**

In `server/app.py`, inside the `_HTML_PAGES` dict, add (next to the `/privacy` lines):
```python
    "/terms":         "terms.html",
    "/terms.html":    "terms.html",
```

- [ ] **Step 2: Verify the route is registered**

```bash
grep -n '"/terms"' server/app.py
```
Expected: one match. (Route will 404 until `terms.html` exists — built in Task 4. That is fine.)

- [ ] **Step 3: Commit**

```bash
git add server/app.py
git commit -m "feat(server): route /terms and /terms.html to terms.html

Co-Authored-By: RuFlo <ruv@ruv.net>"
```

---

## Task 3: Fix the landing footer i18n key + add the Terms link

**Files:**
- Modify: `frontend/landing.html` (footer, ~lines 374-382)

Context: `landing.js` already defines `footer: { privacy, terms }` (lines 60/177/294), but the HTML uses the non-existent flat key `footerPrivacy`. Fix the path and add the Terms link beside it.

- [ ] **Step 1: Correct the privacy link key and add the Terms link**

In `frontend/landing.html`, replace line 380:
```html
        <a href="/privacy" class="nav-link" data-i18n="footerPrivacy">Maxfiylik siyosati</a>
```
with:
```html
        <a href="/terms" class="nav-link" data-i18n="footer.terms">Foydalanish shartlari</a>
        <span class="landing-footer__sep" aria-hidden="true">·</span>
        <a href="/privacy" class="nav-link" data-i18n="footer.privacy">Maxfiylik siyosati</a>
```

- [ ] **Step 2: Verify**

```bash
grep -n 'data-i18n="footer\.\(privacy\|terms\)"' frontend/landing.html
grep -n 'footer: { privacy' frontend/js/landing.js
```
Expected: the HTML grep finds both `footer.terms` and `footer.privacy`; the JS grep finds all three language blocks (no JS edit needed).

- [ ] **Step 3: Visual check (optional, after Task 4)**

Load `http://127.0.0.1:8011/` and toggle UZ/RU/EN — both footer links must translate (Foydalanish shartlari / Условия использования / Terms of Service) and navigate to `/terms` and `/privacy`.

- [ ] **Step 4: Commit**

```bash
git add frontend/landing.html
git commit -m "fix(landing): correct footer i18n key path + add Terms of Service link

Co-Authored-By: RuFlo <ruv@ruv.net>"
```

---

## Task 4: Build `terms.html` shell + the full English panel

**Files:**
- Create: `frontend/terms.html`
- Reference (read for footer/structure parity): `frontend/privacy.html` (lines 1-55, 1034-1044)

**Conversion rules (apply to every section of the source `Terms_of_Service.md`):**
1. Include only the publishable document: the intro paragraphs (source lines 36-38) and **§§1–19** (incl. §19 contact). **Exclude** the YAML front-matter, the "⚠️ DRAFT — NOT YET IN EFFECT" blockquote, the "Placeholders to confirm" table, and the "✅ Before Publishing — Open Items" checklist.
2. Each `##` heading → `<section id="en-s{N}"><h2>{N}. {Title}</h2> … </section>`. Each `###`/bold sub-lead → `<h3>`. Bullet lists → `<ul><li>`. Bold runs → `<strong>`. The two inline tables (the role-tier table in §1's "Who is bound" is prose, not a table; there are no markdown tables in the ToS body — render the role tiers as a `<ul>`).
3. **Fill placeholders** (no `[brackets]`, no `.legal-ph`):
   - `[Class-A-Technologies MCHJ]` → `Class A Technologies MCHJ`
   - `[legal@classa.education]` → `legal@classa.education` · `[support@classa.education]` → `support@classa.education` · `[privacy@classa.education]` → `privacy@classa.education`
   - `[registered address, Tashkent, Uzbekistan]` → `Tashkent, Uzbekistan`
   - `[Tashkent]` → `Tashkent`
   - `[PUBLICATION DATE]`/`[1.0]` → `June 6, 2026` / `Version 1.0`
4. **§13:** drop the bracketed floor — render the cap as "limited to the fees paid by the Customer for the Services in the twelve (12) months before the event giving rise to the claim." (Remove "the greater of (a) … or (b) [a nominal floor amount]".)
5. Every mention of "Privacy Policy" / `[[Privacy_Policy]]` → `<a href="/privacy">Privacy Policy</a>`.
6. Proper nouns verbatim: ZRU-547, GDPR, COPPA, FERPA, Hermes, the emails.

- [ ] **Step 1: Create `frontend/terms.html` with the shell + EN panel**

Use this exact shell (head, inline flash-free script with the corrected key, reused header, `legal.css`/`legal.js`, footer mirrored from privacy):

```html
<!DOCTYPE html>
<html lang="uz" data-page="terms">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Homeworks · Terms of Service</title>
  <meta name="description" content="Terms of Service for the Class A Education / Homeworks learning platform." />
  <meta name="robots" content="index, follow" />
  <link rel="icon" type="image/png" sizes="32x32" href="/img/favicon-32.png?v=__VERSION__" />
  <link rel="apple-touch-icon" href="/img/classa-logo.png?v=__VERSION__" />
  <link rel="preload" href="/css/landing.css?v=__VERSION__" as="style" />
  <link rel="stylesheet" href="/css/landing.css?v=__VERSION__" />
  <link rel="stylesheet" href="/css/legal.css?v=__VERSION__" />
  <script src="/js/theme.js?v=__VERSION__"></script>
  <script>
    /* Phase A — set language synchronously before paint (flash-free). */
    (function () {
      try {
        var l = localStorage.getItem('nets-landing-lang');
        var s = ['uz', 'ru', 'en'];
        document.documentElement.setAttribute('data-lang', s.indexOf(l) !== -1 ? l : 'uz');
      } catch (e) {
        document.documentElement.setAttribute('data-lang', 'uz');
      }
    })();
  </script>
</head>
<body class="landing-body">
  <a class="skip-link" href="#terms-main">Skip to content</a>

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

  <main id="terms-main" class="legal-wrap">

    <!-- ===================== EN ===================== -->
    <div class="legal-doc" lang="en" data-lang-panel="en">
      <div class="legal-layout">
        <aside class="legal-toc" aria-label="Contents">
          <p class="legal-toc__title">Contents</p>
          <ol>
            <li><a href="#en-s1">1. Acceptance &amp; who is bound</a></li>
            <li><a href="#en-s2">2. Definitions</a></li>
            <li><a href="#en-s3">3. Eligibility &amp; accounts</a></li>
            <li><a href="#en-s4">4. Licence to use the Services</a></li>
            <li><a href="#en-s5">5. Acceptable use &amp; academic integrity</a></li>
            <li><a href="#en-s6">6. School licensing (B2B terms)</a></li>
            <li><a href="#en-s7">7. Fees, payment &amp; subscription</a></li>
            <li><a href="#en-s8">8. Intellectual property</a></li>
            <li><a href="#en-s9">9. AI features &amp; disclaimer</a></li>
            <li><a href="#en-s10">10. Student data &amp; privacy</a></li>
            <li><a href="#en-s11">11. Third-party services</a></li>
            <li><a href="#en-s12">12. Warranties &amp; disclaimers</a></li>
            <li><a href="#en-s13">13. Limitation of liability</a></li>
            <li><a href="#en-s14">14. Indemnification</a></li>
            <li><a href="#en-s15">15. Term, termination &amp; suspension</a></li>
            <li><a href="#en-s16">16. Changes</a></li>
            <li><a href="#en-s17">17. Governing law &amp; dispute resolution</a></li>
            <li><a href="#en-s18">18. Miscellaneous</a></li>
            <li><a href="#en-s19">19. Contact us</a></li>
          </ol>
        </aside>

        <article class="legal-body">
          <header class="legal-head">
            <p class="legal-eyebrow">Class A Education</p>
            <h1>Terms of Service</h1>
            <p class="legal-updated">Last updated: June 6, 2026 · Version 1.0</p>
          </header>

          <section id="en-intro">
            <p>These Terms of Service ("<strong>Terms</strong>") are a binding agreement between Class A Technologies MCHJ ("<strong>Class A</strong>", "<strong>we</strong>", "<strong>us</strong>", "<strong>our</strong>") and the people and institutions that use the <strong>Class A Education</strong> learning platform — a web platform for schools and teachers, and a mobile application for students and parents (together, the "<strong>Services</strong>"). They govern access to and use of the Services, alongside our <a href="/privacy">Privacy Policy</a>, which is incorporated by reference.</p>
            <p>We design the Services for <strong>schools and their students</strong>, most of whom are <strong>children</strong>, so these Terms place responsibility where it belongs: the <strong>School</strong> is the licensee that enables and oversees use, <strong>we</strong> keep the platform safe and honest about what it can and cannot do, and <strong>AI features assist learning — they do not replace teachers.</strong></p>
          </section>

          <section id="en-s1">
            <h2>1. Acceptance &amp; who is bound</h2>
            <p><strong>Acceptance.</strong> You accept these Terms by clicking to accept, by signing an order form or licence that references them, or by accessing or using the Services. If you do not agree, do not use the Services.</p>
            <p><strong>Who is bound (two tiers).</strong></p>
            <ul>
              <li><strong>The School</strong> (or other institution that licenses the Services) is the "<strong>Customer</strong>" — it accepts these Terms <strong>on behalf of, and is responsible for,</strong> the teachers, students, and parents it enables ("<strong>Authorized Users</strong>"). Where a School and Class A sign a separate licence, order form, or data-processing agreement, <strong>that agreement controls</strong> over these Terms on any conflict.</li>
              <li><strong>Authorized Users</strong> (teachers, students, parents) are bound by these Terms when they use the Services. A person who accepts on behalf of a School or other organisation represents that they are <strong>authorised to bind it</strong>.</li>
            </ul>
            <p><strong>Minors.</strong> A student who is a minor is bound through their <strong>School and/or parent or guardian</strong>, not by their own independent acceptance. Students do not create unsupervised accounts (see §3).</p>
            <p><strong>Direct (home) use.</strong> Where a parent registers a student directly (outside a School licence), the <strong>parent</strong> accepts these Terms, consents on the child's behalf, and is responsible for the child's use.</p>
          </section>

          <!-- §§2–12, 14–16, 18: straight conversion per the rules above. -->

          <section id="en-s13">
            <h2>13. Limitation of liability</h2>
            <p>To the fullest extent permitted by law: neither party is liable for <strong>indirect, incidental, special, consequential, or punitive</strong> damages, or for lost profits, data, or goodwill; and Class A's <strong>total aggregate liability</strong> arising out of or relating to the Services is <strong>limited to the fees paid by the Customer for the Services in the twelve (12) months before the event giving rise to the claim.</strong> Because some AI Features are provided by third parties we do not control, our liability for their Output is further limited as set out in §9. <strong>These limits do not apply to liability that cannot be limited under applicable law</strong>, including mandatory consumer-protection rights (see §17).</p>
          </section>

          <section id="en-s17">
            <h2>17. Governing law &amp; dispute resolution</h2>
            <p>These Terms are governed by the <strong>laws of the Republic of Uzbekistan</strong>, without regard to conflict-of-laws rules. The parties will first try to resolve any dispute <strong>amicably by negotiation</strong>; if they cannot, the dispute is subject to the <strong>courts of the Republic of Uzbekistan</strong> at Tashkent, except where mandatory law gives an individual consumer a different forum.</p>
            <p><strong>Consumer rights preserved.</strong> Nothing in these Terms (including §§12–13) <strong>waives or limits any non-waivable right</strong> a parent or other individual consumer has under <strong>Uzbekistan's Law on Protection of Consumer Rights</strong> or other mandatory law.</p>
            <p><strong>Language.</strong> The <strong>Uzbek-language</strong> version of these Terms is the authoritative version; any <strong>Russian or English</strong> version is a convenience translation and does not control on conflict, except where mandatory law provides otherwise.</p>
          </section>

          <section id="en-s19">
            <h2>19. Contact us</h2>
            <p><strong>Class A Technologies MCHJ</strong> — Legal</p>
            <ul>
              <li>Email: <strong>legal@classa.education</strong> · Support: <strong>support@classa.education</strong> · Privacy: <strong>privacy@classa.education</strong></li>
              <li>Postal: Tashkent, Uzbekistan</li>
            </ul>
          </section>
        </article>
      </div>
    </div>

    <!-- UZ panel inserted in Task 5; RU panel inserted in Task 6 -->

  </main>

  <footer class="landing-footer" role="contentinfo">
    <div class="legal-footer__inner">
      <span>Homeworks</span>
      <span class="landing-footer__sep" aria-hidden="true">·</span>
      <a href="/privacy" class="legal-footer__link" data-i18n-uz="Maxfiylik siyosati" data-i18n-ru="Политика конфиденциальности" data-i18n-en="Privacy Policy">Maxfiylik siyosati</a>
      <span class="landing-footer__sep" aria-hidden="true">·</span>
      <a href="/" class="legal-footer__link" data-i18n-uz="← Bosh sahifa" data-i18n-ru="← На главную" data-i18n-en="← Home">← Bosh sahifa</a>
    </div>
  </footer>

  <script src="/js/legal.js?v=__VERSION__" defer></script>
</body>
</html>
```

- [ ] **Step 2: Fill in §§2–12, 14–16, 18 of the EN panel**

Convert each remaining section from `Terms_of_Service.md` using the conversion rules. Insert them in order (the `<!-- §§2–12 … -->` placeholder marks the spot; §13, §17, §19 are already written above as worked examples). Do not leave any section out — the TOC lists all 19.

- [ ] **Step 3: Verify the route serves and content is clean**

```bash
curl -fsS "http://127.0.0.1:8011/terms" -o /tmp/terms.html
grep -c "Terms of Service" /tmp/terms.html            # > 0
grep -c "en-s19" /tmp/terms.html                      # 2 (TOC link + section id) → all 19 present
grep -c "\[Class-A-Technologies\|\[PUBLICATION DATE\|DRAFT — NOT YET\|Before Publishing\|nominal floor" /tmp/terms.html  # 0 — no leaked internals/placeholders
grep -c "legal.css\|legal.js" /tmp/terms.html         # 2
```
Expected values as noted in comments.

- [ ] **Step 4: Visual check (light + dark)**

Open `http://127.0.0.1:8011/terms`. Confirm: header/nav/footer match `/privacy`; reading column + sticky TOC look right; toggle the theme — dark mode renders cleanly. EN panel visible by default only if `nets-landing-lang` is `en` or unset; otherwise it's hidden (UZ default) — that's expected until Task 5.

- [ ] **Step 5: Commit**

```bash
git add frontend/terms.html
git commit -m "feat(legal): add Terms of Service page — English panel + shell

Co-Authored-By: RuFlo <ruv@ruv.net>"
```

---

## Task 5: Add the Uzbek (default) panel

**Files:**
- Modify: `frontend/terms.html` (insert UZ `.legal-doc` panel before the EN panel so UZ is first/default in source order)
- Reference: `frontend/privacy.html` — reuse its established Uzbek legal terminology (controller→"nazoratchi", processor→"qayta ishlovchi", "Authorized User", ZRU-547 phrasing, etc.)

- [ ] **Step 1: Produce the Uzbek translation via a sub-agent**

Dispatch a translation sub-agent with this brief:
> Translate the English Terms of Service panel in `frontend/terms.html` (the `<div class="legal-doc" data-lang-panel="en">` block) into **Uzbek (Latin script)**. Output a complete `<div class="legal-doc" lang="uz" data-lang-panel="uz">…</div>` block with **identical structure** to the English one. Rules: (a) change every `id="en-…"` to `id="uz-…"` and every TOC `href="#en-…"` to `href="#uz-…"`; (b) translate the TOC title ("Contents"→"Mundarija"), `.legal-eyebrow` stays "Class A Education", `<h1>`→"Foydalanish shartlari", `.legal-updated`→"Oxirgi yangilanish: 2026-yil 6-iyun · Versiya 1.0"; (c) keep proper nouns verbatim (Class A Technologies MCHJ, ZRU-547, GDPR, COPPA, FERPA, Hermes, the emails, "Tashkent"); (d) keep `<a href="/privacy">` links, translating only the visible text ("Privacy Policy"→"Maxfiylik siyosati"); (e) **reuse the exact Uzbek legal terminology already used in `frontend/privacy.html`** for consistency (read it first). Return only the HTML block.

- [ ] **Step 2: Insert the UZ panel**

Place the returned `<div class="legal-doc" … data-lang-panel="uz">` block immediately after `<main id="terms-main" class="legal-wrap">` and before the EN panel.

- [ ] **Step 3: Verify**

```bash
curl -fsS "http://127.0.0.1:8011/terms" -o /tmp/terms.html
grep -c 'data-lang-panel="uz"' /tmp/terms.html   # 1
grep -c "uz-s19" /tmp/terms.html                 # 2 (all 19 UZ sections + TOC)
grep -c "Foydalanish shartlari" /tmp/terms.html  # >= 1
```
Visual: load `/terms` with no stored language (or pick UZ) → Uzbek panel shows by default; no English leaks through.

- [ ] **Step 4: Commit**

```bash
git add frontend/terms.html
git commit -m "feat(legal): add Uzbek panel to Terms of Service (authoritative language)

Co-Authored-By: RuFlo <ruv@ruv.net>"
```

---

## Task 6: Add the Russian panel

**Files:**
- Modify: `frontend/terms.html` (insert RU `.legal-doc` panel after the EN panel)
- Reference: `frontend/privacy.html` — reuse its established Russian legal terminology.

- [ ] **Step 1: Produce the Russian translation via a sub-agent**

Dispatch a translation sub-agent with the same brief as Task 5 Step 1, but target **Russian**, with: `id="en-…"`→`id="ru-…"`, `href="#en-…"`→`href="#ru-…"`, TOC title "Contents"→"Содержание", `<h1>`→"Условия использования", `.legal-updated`→"Последнее обновление: 6 июня 2026 г. · Версия 1.0", "Privacy Policy"→"Политика конфиденциальности", and reuse the Russian legal terminology from `frontend/privacy.html`. Return only the `<div class="legal-doc" lang="ru" data-lang-panel="ru">…</div>` block.

- [ ] **Step 2: Insert the RU panel** immediately after the EN panel.

- [ ] **Step 3: Verify**

```bash
curl -fsS "http://127.0.0.1:8011/terms" -o /tmp/terms.html
grep -c 'data-lang-panel="ru"' /tmp/terms.html   # 1
grep -c "ru-s19" /tmp/terms.html                 # 2
grep -c "Условия использования" /tmp/terms.html  # >= 1
```

- [ ] **Step 4: Commit**

```bash
git add frontend/terms.html
git commit -m "feat(legal): add Russian panel to Terms of Service

Co-Authored-By: RuFlo <ruv@ruv.net>"
```

---

## Task 7: Full verification + cross-page regression

**Files:** none (verification only)

- [ ] **Step 1: Route + content fidelity**

```bash
curl -fsS "http://127.0.0.1:8011/terms.html" -o /dev/null && echo "terms.html OK"
curl -fsS "http://127.0.0.1:8011/terms" -o /tmp/t.html
for p in en uz ru; do echo -n "$p sections: "; grep -oc "id=\"$p-s" /tmp/t.html; done   # each 19
grep -c "DRAFT — NOT YET\|Before Publishing\|\[PUBLICATION DATE\]\|\[Class-A-Technologies\]" /tmp/t.html  # 0
```

- [ ] **Step 2: Language toggle + cross-page sync (browser)**

Using the browser MCP (or manually) at `http://127.0.0.1:8011`:
1. On `/` pick **RU** → footer shows "Условия использования" / "Политика конфиденциальности".
2. Click Terms → `/terms` opens already in **RU** (panel + chrome), proving `nets-landing-lang` sync.
3. On `/terms` switch to **UZ**, then open `/privacy` → privacy now also shows **UZ** (confirms Task 1 key fix).
4. Reload `/terms` → language persists.
5. Toggle **dark mode** on `/terms` → renders cleanly; reload → persists (`nets_theme`).

- [ ] **Step 3: Accessibility spot-check**

- Skip-link (`Tab` on load) focuses "Skip to content" → jumps to `#terms-main`.
- `:focus-visible` rings on lang pills, theme toggle, TOC links, footer links.
- Headings ordered h1 → h2 (→ h3); lang `<html lang>` updates on toggle.
- With `prefers-reduced-motion`, TOC smooth-scroll degrades to instant (inherited).

- [ ] **Step 4: Privacy regression**

```bash
curl -fsS "http://127.0.0.1:8011/privacy" -o /dev/null && echo "privacy OK"
```
Confirm `/privacy` still renders and its language now persists under `nets-landing-lang`.

- [ ] **Step 5: Stop the test server** (Ctrl-C the uvicorn on :8011).

- [ ] **Step 6: Final commit (if any verification fixes were needed)**

```bash
git add -A && git commit -m "test(legal): verify ToS page, toggle sync, and privacy regression

Co-Authored-By: RuFlo <ruv@ruv.net>"
```

---

## Self-Review (done by plan author)

- **Spec coverage:** Goal/§1 → Tasks 2,4–6; trilingual/§3,§6 → Tasks 4–6; shared infra + lang-key fix/§4 → Task 1; footer link/§4 → Task 3; placeholder fills/§5 → Task 4 rules; styling/§7 → reused (Task 1); behavior/§8 → Task 1 (legal.js); verification/§11 → Task 7; privacy regression → Tasks 1,7. All spec sections mapped.
- **Placeholder scan:** Mechanical tasks (1,2,3) carry exact diffs; Task 4 carries the full shell + worked example sections + explicit conversion rules; translation tasks carry exact sub-agent briefs. The only non-inlined content is the bulk legal prose (the deliverable itself), produced by the stated rules/briefs.
- **Consistency:** key `nets-landing-lang`, files `legal.css`/`legal.js`, ids `{lang}-s{N}`, and `data-lang-panel` used identically across all tasks; matches the privacy page's actual conventions.
