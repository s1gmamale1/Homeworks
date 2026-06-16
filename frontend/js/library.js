// frontend/js/library.js
// Library page — Apple-style subject blocks with in-grid expansion.
//
// Layout (2026-04-30 v2 — replaces FLIP overlay panel):
//
//   [ Til: All UZ RU EN ]      [ search… ]   [ Clear ]
//
//   ┌ Total ┐ ┌ Subj ┐ ┌ Hard ┐ ┌ UZ ┐
//
//   ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐
//   │ Algebra│ │ Geom   │ │ Eng    │ │ Phys   │   ← .subject-tile
//   └────────┘ └────────┘ └────────┘ └────────┘
//
//   On click → tile gets .is-expanded → grid-column: 1 / -1 (full row),
//   other tiles flow to next rows. View Transitions API morphs the
//   layout. Esc / × closes. Same DOM node for compact + expanded —
//   only innerHTML + class changes.
//
// Persistence: language + per-subject grade selection live in
// localStorage. Open-tile state is NOT persisted.
(function () {
  "use strict";

  // ── Subject metadata ─────────────────────────────────────────────────────
  const SUBJECT_ICONS = {
    "math-algebra":     "ƒx",
    "geometriya-g7-11": "△",
    physics:            "⚛",
    biology:            "🧬",
    "kimyo-g7-11":      "⚗",
    english:            "Aa",
    history:            "🏛",
  };

  const SUBJECT_DISPLAY = {
    "math-algebra":     { uz: "Algebra",    ru: "Алгебра",    en: "Algebra" },
    "geometriya-g7-11": { uz: "Geometriya", ru: "Геометрия",  en: "Geometry" },
    physics:            { uz: "Fizika",     ru: "Физика",     en: "Physics" },
    biology:            { uz: "Biologiya",  ru: "Биология",   en: "Biology" },
    "kimyo-g7-11":      { uz: "Kimyo",      ru: "Химия",      en: "Chemistry" },
    english:            { uz: "Ingliz tili", ru: "Английский", en: "English" },
    history:            { uz: "Tarix",      ru: "История",    en: "History" },
  };

  const SUBJECT_TAGLINE = {
    "math-algebra":     { uz: "Tenglamalar, funksiyalar, ifodalar", ru: "Уравнения, функции, выражения", en: "Equations, functions, expressions" },
    "geometriya-g7-11": { uz: "Shakllar, burchaklar, almashtirishlar", ru: "Фигуры, углы, преобразования", en: "Shapes, angles, transformations" },
    physics:            { uz: "Kuchlar, harakat, elektr",          ru: "Силы, движение, электричество", en: "Forces, motion, circuits" },
    biology:            { uz: "Hujayralar, organizmlar, ekologiya", ru: "Клетки, организмы, экология", en: "Cells, organisms, ecology" },
    "kimyo-g7-11":      { uz: "Atomlar, reaksiyalar, birikmalar",  ru: "Атомы, реакции, соединения",  en: "Atoms, reactions, compounds" },
    english:            { uz: "O'qish, grammatika, yozma ish",     ru: "Чтение, грамматика, письмо", en: "Reading, grammar, writing" },
    history:            { uz: "Davlatlar, voqealar, sanalar",      ru: "Государства, события, даты", en: "States, events, dates" },
  };

  const FAMILY_ORDER = [
    "aniq-fanlar",
    "tabiy-fanlar",
    "til-fanlar",
    "ijtimoiy-fanlar",
  ];

  // Production palette — matches app.css --family-* tokens.
  const FAMILY_COLORS = {
    "aniq-fanlar":     "#0066CC", // production blue
    "tabiy-fanlar":    "#34C759", // production green
    "til-fanlar":      "#AF52DE", // production purple
    "ijtimoiy-fanlar": "#FF9500", // production orange
  };

  // Stat accent colors — production palette per spec.
  const STAT_COLORS = {
    total:    "#0066CC",
    subjects: "#34C759",
    hard:     "#FF453A",
    uz:       "#AF52DE",
  };

  // ── DOM refs ─────────────────────────────────────────────────────────────
  const searchInput = document.getElementById("lib-search");
  const clearBtn    = document.getElementById("lib-clear-btn");
  const langChips   = document.getElementById("lib-lang-chips");
  const stageEl     = document.getElementById("lib-stage");
  const gridEl      = document.getElementById("lib-subject-grid");
  const statsEl     = document.getElementById("lib-stats");
  const loadingEl   = document.getElementById("lib-loading");
  const errorEl     = document.getElementById("lib-error");
  const errorMsgEl  = document.getElementById("lib-error-msg");
  const emptyEl     = document.getElementById("lib-empty");
  const retryBtn    = document.getElementById("lib-retry-btn");

  // ── State ────────────────────────────────────────────────────────────────
  const STORAGE_KEY = "nets.library.v3";
  const PAGE_SIZE = 200;

  let subjectMeta = {};
  let debounceTimer = null;

  const state = loadPersistedState();
  // Per-render cache so the expanded tile can re-filter without re-fetch.
  let lastGroups = {};
  // The currently expanded tile element (or null).
  let expandedTile = null;
  let expandedSubjectId = null;

  function loadPersistedState() {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (!raw) return defaultState();
      const parsed = JSON.parse(raw);
      return {
        language: typeof parsed.language === "string" ? parsed.language : "",
        gradeBySubject: parsed.gradeBySubject && typeof parsed.gradeBySubject === "object"
          ? parsed.gradeBySubject
          : {},
      };
    } catch (_) {
      return defaultState();
    }
  }

  function defaultState() {
    return { language: "", gradeBySubject: {} };
  }

  function persist() {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
    } catch (_) {
      // private mode / quota — silent
    }
  }

  // ── Helpers ──────────────────────────────────────────────────────────────
  // Skeleton minimum-display floor. Without this gate, a cache-warm
  // fetch can swap the skeleton off in a single frame and feels like
  // a glitch. We restamp the clock every time show(loadingEl) runs.
  const SKELETON_MIN_MS = 500;
  let _skeletonShownAt = (typeof performance !== "undefined" && performance.now)
    ? performance.now()
    : Date.now();
  function _now() {
    return (typeof performance !== "undefined" && performance.now)
      ? performance.now()
      : Date.now();
  }
  function waitSkeletonFloor() {
    const elapsed = _now() - _skeletonShownAt;
    if (elapsed >= SKELETON_MIN_MS) return Promise.resolve();
    return new Promise((r) => setTimeout(r, SKELETON_MIN_MS - elapsed));
  }

  function show(el) {
    if (!el) return;
    el.classList.remove("hidden");
    // Mirror visual state to assistive tech for the loading skeleton —
    // the container declares aria-busy="true" in HTML; we re-assert here
    // in case the same node was previously toggled to "false".
    if (el === loadingEl) {
      _skeletonShownAt = _now();
      el.setAttribute("aria-busy", "true");
    }
  }
  function hide(el) {
    if (!el) return;
    el.classList.add("hidden");
    if (el === loadingEl) el.setAttribute("aria-busy", "false");
  }
  function reveal(el) { if (el) el.removeAttribute("hidden"); }
  function conceal(el) { if (el) el.setAttribute("hidden", ""); }

  function t(key, fallback) {
    if (window.i18n && typeof window.i18n.t === "function") {
      return window.i18n.t(key, fallback);
    }
    return fallback != null ? fallback : key;
  }

  function activeUiLang() {
    if (window.i18n && typeof window.i18n.getLang === "function") {
      const lang = window.i18n.getLang();
      if (lang === "uz" || lang === "ru" || lang === "en") return lang;
    }
    return "uz";
  }

  function subjectDisplayName(subjectId) {
    const map = SUBJECT_DISPLAY[subjectId];
    if (!map) return subjectId;
    return map[activeUiLang()] || map.uz || subjectId;
  }

  function subjectIcon(subjectId) {
    return SUBJECT_ICONS[subjectId] || "N";
  }

  function subjectTagline(subjectId) {
    const map = SUBJECT_TAGLINE[subjectId];
    if (!map) return "";
    return map[activeUiLang()] || map.uz || "";
  }

  function subjectFamily(subjectId) {
    const m = subjectMeta[subjectId];
    return (m && m.family) || "aniq-fanlar";
  }

  function subjectFamilyColor(subjectId) {
    return FAMILY_COLORS[subjectFamily(subjectId)] || FAMILY_COLORS["aniq-fanlar"];
  }

  function formatDate(iso) {
    if (!iso) return "";
    try {
      return new Intl.DateTimeFormat(navigator.language || "uz", {
        year: "numeric", month: "short", day: "numeric",
      }).format(new Date(iso));
    } catch (_) {
      return iso.slice(0, 10);
    }
  }

  function formatCount(n) {
    const tpl = n === 1
      ? t("library.section_count_one", "1 homework")
      : t("library.section_count_other", "{n} homeworks");
    return tpl.replace("{n}", String(n));
  }

  function escapeHtml(str) {
    return String(str)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }

  // Sanitize the subject id for use as a view-transition-name (must be
  // a valid CSS ident). Replace any non-alphanumeric with `-`.
  function vtNameFor(subjectId) {
    return "library-tile-" + String(subjectId).replace(/[^a-zA-Z0-9]+/g, "-");
  }

  function isHardItem(hw) {
    const diff = (hw && hw.difficulty || "").toString().toLowerCase();
    if (diff === "hard") return true;
    const mode = (hw && hw.mode || "").toString().toLowerCase();
    if (mode === "hard") return true;
    if (typeof hw.grade === "number" && hw.grade >= 9 && !mode && !diff) {
      return true;
    }
    return false;
  }

  // ── Stats ────────────────────────────────────────────────────────────────
  function renderStats(items) {
    const total = items.length;
    const subjectIds = new Set();
    let hard = 0;
    let uz = 0;
    items.forEach(hw => {
      if (hw.subject) subjectIds.add(hw.subject);
      try { if (isHardItem(hw)) hard += 1; } catch (_) { /* swallow */ }
      if ((hw.language || "").toLowerCase() === "uz") uz += 1;
    });

    const cards = [
      { accent: STAT_COLORS.total,    glyph: "▣", num: total,             label: t("library.stat_total",    "Total"),    sub: t("library.stat_total_sub",    "Total content") },
      { accent: STAT_COLORS.subjects, glyph: "⌁", num: subjectIds.size,   label: t("library.stat_subjects", "Subjects"), sub: t("library.stat_subjects_sub", "Expandable blocks") },
      { accent: STAT_COLORS.hard,     glyph: "◆", num: hard,              label: t("library.stat_hard",     "Hard"),     sub: t("library.stat_hard_sub",     "Needs review") },
      { accent: STAT_COLORS.uz,       glyph: "◌", num: uz,                label: t("library.stat_uz",       "Uzbek"),    sub: t("library.stat_uz_sub",       "UZ content") },
    ];

    statsEl.innerHTML = cards.map(c => `
      <article class="lib-stat" style="--accent: ${c.accent}">
        <div class="lib-stat-icon">${escapeHtml(c.glyph)}</div>
        <div>
          <span class="stat-num">${escapeHtml(String(c.num))}</span>
          <strong class="stat-label">${escapeHtml(c.label)}</strong>
          <span class="stat-sub">${escapeHtml(c.sub)}</span>
        </div>
      </article>
    `).join("");
  }

  // ── Subject tiles ────────────────────────────────────────────────────────
  function compactMarkup(subjectId, items) {
    const name = subjectDisplayName(subjectId);
    const glyph = subjectIcon(subjectId);
    const count = items.length;
    const tagline = subjectTagline(subjectId) || formatCount(count);
    const openLabel = t("library.tile_open", "Open");

    return `
      <div class="tile-orb" aria-hidden="true"></div>
      <div class="tile-icon tile-icon-compact">${escapeHtml(glyph)}</div>
      <div class="tile-copy tile-copy-compact">
        <h3>${escapeHtml(name)}</h3>
        <p>${escapeHtml(tagline)}</p>
      </div>
      <div class="tile-footer tile-footer-compact">
        <span>${escapeHtml(formatCount(count))}</span>
        <span class="tile-pill">${escapeHtml(openLabel)} ↗</span>
      </div>
    `;
  }

  function renderTile(subjectId, items) {
    const accent = subjectFamilyColor(subjectId);
    const name = subjectDisplayName(subjectId);
    const ariaLabel = t("library.subject_open_label", "Open {name}").replace("{name}", name);

    // The tile uses <div role="button"> instead of <button> because
    // the expanded state nests <button> (close, grade chips) and <a>
    // (homework cards) inside it — a real <button> would produce invalid
    // HTML5 (interactive content inside interactive content), which
    // misroutes screen reader focus and breaks keyboard nav.
    const tile = document.createElement("div");
    tile.className = "subject-tile";
    tile.setAttribute("role", "button");
    tile.setAttribute("tabindex", "0");
    tile.style.setProperty("--accent", accent);
    tile.style.setProperty("--accent-hover", shade(accent, -12));
    tile.style.setProperty("--accent-glow", hexToRgba(accent, 0.28));
    tile.style.setProperty("--accent-light", hexToRgba(accent, 0.10));
    tile.style.viewTransitionName = vtNameFor(subjectId);
    tile.dataset.subjectId = subjectId;
    tile.setAttribute("aria-label", ariaLabel);
    tile.setAttribute("aria-expanded", "false");
    tile.innerHTML = compactMarkup(subjectId, items);
    wireCompactHandlers(tile, subjectId);
    return tile;
  }

  function wireCompactHandlers(tile, subjectId) {
    tile.onclick = (ev) => {
      // Ignore clicks while already expanded (close handled separately)
      if (tile.classList.contains("is-expanded")) return;
      ev.preventDefault();
      ev.stopPropagation();
      expandSubject(tile, subjectId);
    };
    // Manual keyboard activation — <div role="button"> doesn't get
    // Enter/Space activation for free the way <button> does.
    tile.addEventListener("keydown", (ev) => {
      if (tile.classList.contains("is-expanded")) return;
      if (ev.key === "Enter" || ev.key === " ") {
        // preventDefault on Space stops the page from scrolling.
        ev.preventDefault();
        ev.stopPropagation();
        expandSubject(tile, subjectId);
      }
    });
  }

  function renderTiles(groups) {
    while (gridEl.firstChild) gridEl.removeChild(gridEl.firstChild);
    const ids = sortedSubjectIds(Object.keys(groups));
    const frag = document.createDocumentFragment();
    ids.forEach(sid => frag.appendChild(renderTile(sid, groups[sid])));
    gridEl.appendChild(frag);
  }

  // ── Color helpers (for per-tile accent CSS vars) ────────────────────────
  function hexToRgba(hex, a) {
    const h = hex.replace("#", "");
    const r = parseInt(h.slice(0, 2), 16);
    const g = parseInt(h.slice(2, 4), 16);
    const b = parseInt(h.slice(4, 6), 16);
    return `rgba(${r}, ${g}, ${b}, ${a})`;
  }
  function shade(hex, percent) {
    // negative percent → darken
    const h = hex.replace("#", "");
    let r = parseInt(h.slice(0, 2), 16);
    let g = parseInt(h.slice(2, 4), 16);
    let b = parseInt(h.slice(4, 6), 16);
    const f = (percent + 100) / 100;
    r = Math.max(0, Math.min(255, Math.round(r * f)));
    g = Math.max(0, Math.min(255, Math.round(g * f)));
    b = Math.max(0, Math.min(255, Math.round(b * f)));
    return `#${r.toString(16).padStart(2, "0")}${g.toString(16).padStart(2, "0")}${b.toString(16).padStart(2, "0")}`;
  }

  // ── Homework card (dashboard-parity) ─────────────────────────────────────
  function renderHomeworkCard(hw, index) {
    const accent = subjectFamilyColor(hw.subject || "");
    const subjectName = subjectDisplayName(hw.subject);
    const subjectGlyph = subjectIcon(hw.subject);
    const language = hw.language ? hw.language.toUpperCase() : "";
    const mode = (hw.mode || "").toString().toLowerCase();
    const modeLabel = hw.mode ? hw.mode.toUpperCase() : "";
    const status = (hw.status || "draft").toString().toLowerCase();
    const statusLabel = status.charAt(0).toUpperCase() + status.slice(1);
    const chapter = hw.chapter || "";
    const title = hw.title || hw.id;
    const idShort = hw.id ? String(hw.id).slice(0, 8) : "";
    const openLabel = t("dashboard.btn_open", "Open");

    const card = document.createElement("a");
    card.className = "homework-card";
    card.href = `/h/${encodeURIComponent(hw.id)}`;
    card.target = "_blank";
    card.rel = "noreferrer";
    card.setAttribute("aria-label", title);
    // Per-card accent (top border + icon badge)
    card.style.setProperty("--accent", accent);
    card.style.setProperty("--accent-hover", shade(accent, -12));
    card.style.setProperty("--accent-glow", hexToRgba(accent, 0.28));
    card.style.setProperty("--accent-light", hexToRgba(accent, 0.10));

    const badgeHtml = hw.mode
      ? `<span class="hw-pill" data-mode="${escapeHtml(mode)}">${escapeHtml(modeLabel)}</span>`
      : "";
    const gradePill = (hw.grade != null)
      ? `<span class="hw-pill">${escapeHtml(t("common.grade", "Grade"))} ${escapeHtml(String(hw.grade))}</span>`
      : "";
    const langPill = language
      ? `<span class="hw-pill">${escapeHtml(language)}</span>`
      : "";

    const subjectMeta = subjectName
      ? `${escapeHtml(subjectName)}${hw.grade != null ? ` · ${escapeHtml(String(hw.grade))}-sinf` : ""}`
      : (hw.grade != null ? `${escapeHtml(String(hw.grade))}-sinf` : "");

    const updatedLabel = formatDate(hw.updated_at);

    card.innerHTML = `
      <div class="hw-head">
        <div class="hw-icon" aria-hidden="true">${escapeHtml(subjectGlyph)}</div>
        <span class="hw-status">${escapeHtml(statusLabel)}</span>
      </div>
      <div>
        <h4 class="hw-title">${escapeHtml(title)}</h4>
        <p class="hw-id">${escapeHtml(idShort || "")}</p>
      </div>
      <div class="hw-meta">
        ${subjectMeta ? `<span>${subjectMeta}</span>` : ""}
        ${chapter ? `<span>${escapeHtml(chapter)}</span>` : ""}
        ${updatedLabel ? `<span>${escapeHtml(updatedLabel)}</span>` : ""}
      </div>
      <div class="hw-pills">
        ${badgeHtml}${gradePill}${langPill}
      </div>
      <span class="hw-open">${escapeHtml(openLabel)}</span>
    `;
    return card;
  }

  // ── Group + sort ─────────────────────────────────────────────────────────
  function groupBySubject(items) {
    const groups = {};
    items.forEach(hw => {
      const key = hw.subject || "_unknown";
      (groups[key] = groups[key] || []).push(hw);
    });
    return groups;
  }

  function familyRank(subjectId) {
    const idx = FAMILY_ORDER.indexOf(subjectFamily(subjectId));
    return idx >= 0 ? idx : FAMILY_ORDER.length;
  }

  function sortedSubjectIds(groupKeys) {
    return groupKeys.slice().sort((a, b) => {
      const fa = familyRank(a);
      const fb = familyRank(b);
      if (fa !== fb) return fa - fb;
      return subjectDisplayName(a).localeCompare(subjectDisplayName(b));
    });
  }

  // ── Expanded markup ──────────────────────────────────────────────────────
  function expandedMarkup(subjectId, items) {
    const name = subjectDisplayName(subjectId);
    const glyph = subjectIcon(subjectId);
    const count = items.length;

    const grades = items
      .map(i => i.grade)
      .filter(g => typeof g === "number")
      .sort((a, b) => a - b);
    const gradeRange = grades.length
      ? (grades[0] === grades[grades.length - 1]
          ? `${t("common.grade", "Grade")} ${grades[0]}`
          : `${t("common.grade", "Grade")} ${grades[0]}–${grades[grades.length - 1]}`)
      : "";
    const subline = `${formatCount(count)}${gradeRange ? ` · ${escapeHtml(gradeRange)}` : ""}`;

    const gradesPresent = Array.from(new Set(grades));
    const persisted = state.gradeBySubject[subjectId] || "all";
    const selected = (persisted === "all" || gradesPresent.includes(Number(persisted))) ? persisted : "all";
    const chipsHtml = [
      `<button class="lib-grade-chip${selected === "all" ? " is-active" : ""}" data-grade="all">${escapeHtml(t("library.section_grade_all", "All"))}</button>`,
    ].concat(gradesPresent.map(g => {
      const active = String(selected) === String(g);
      return `<button class="lib-grade-chip${active ? " is-active" : ""}" data-grade="${escapeHtml(String(g))}">${escapeHtml(String(g))}</button>`;
    })).join("");

    const closeLabel = t("common.close", "Close");

    return `
      <div class="tile-expanded-body">
        <div class="expanded-head">
          <div class="expanded-title">
            <div class="expanded-glyph" aria-hidden="true">${escapeHtml(glyph)}</div>
            <div>
              <h2>${escapeHtml(name)}</h2>
              <p>${subline}</p>
            </div>
          </div>
          <button class="expanded-close" type="button" aria-label="${escapeHtml(closeLabel)}" data-i18n-aria-label="common.close">×</button>
        </div>
        <div class="expanded-actions">${chipsHtml}</div>
        <div class="expanded-cards"></div>
      </div>
    `;
  }

  function paintExpandedCards(tile, subjectId, items) {
    const cardsHost = tile.querySelector(".expanded-cards");
    if (!cardsHost) return;
    while (cardsHost.firstChild) cardsHost.removeChild(cardsHost.firstChild);

    const grade = state.gradeBySubject[subjectId] || "all";
    const filtered = grade === "all"
      ? items
      : items.filter(hw => String(hw.grade) === String(grade));

    if (!filtered.length) {
      const empty = document.createElement("div");
      empty.className = "expanded-empty";
      empty.textContent = t("library.section_empty", "No homeworks for this grade.");
      cardsHost.appendChild(empty);
      return;
    }

    const frag = document.createDocumentFragment();
    filtered.forEach((hw, idx) => frag.appendChild(renderHomeworkCard(hw, idx)));
    cardsHost.appendChild(frag);
  }

  function wireExpandedHandlers(tile, subjectId, items) {
    const closeBtn = tile.querySelector(".expanded-close");
    if (closeBtn) {
      closeBtn.addEventListener("click", (ev) => {
        ev.preventDefault();
        ev.stopPropagation();
        collapseSubject(tile, true);
      });
    }

    const actions = tile.querySelector(".expanded-actions");
    if (actions) {
      actions.addEventListener("click", (ev) => {
        const chip = ev.target.closest(".lib-grade-chip");
        if (!chip) return;
        ev.preventDefault();
        ev.stopPropagation();
        const grade = chip.dataset.grade || "all";
        state.gradeBySubject[subjectId] = grade;
        persist();
        actions.querySelectorAll(".lib-grade-chip").forEach(c => {
          c.classList.toggle("is-active", c.dataset.grade === grade);
        });
        paintExpandedCards(tile, subjectId, items);
      });
    }

    // Block bubbling clicks on the expanded body from re-triggering expand.
    const body = tile.querySelector(".tile-expanded-body");
    if (body) {
      body.addEventListener("click", (ev) => ev.stopPropagation());
    }
  }

  // ── Expand / collapse (View Transitions API) ────────────────────────────
  function expandSubject(tile, subjectId) {
    if (expandedTile && expandedTile !== tile) {
      collapseSubject(expandedTile, false);
    }
    const items = lastGroups[subjectId] || [];
    const apply = () => {
      tile.classList.add("is-expanded");
      tile.setAttribute("aria-expanded", "true");
      tile.innerHTML = expandedMarkup(subjectId, items);
      wireExpandedHandlers(tile, subjectId, items);
      paintExpandedCards(tile, subjectId, items);
      expandedTile = tile;
      expandedSubjectId = subjectId;
      document.addEventListener("keydown", escHandler);
    };
    if (typeof document.startViewTransition === "function") {
      document.startViewTransition(apply);
    } else {
      apply();
    }
  }

  function collapseSubject(tile, animate) {
    if (!tile) return;
    const subjectId = tile.dataset.subjectId;
    const items = lastGroups[subjectId] || [];
    const apply = () => {
      tile.classList.remove("is-expanded");
      tile.setAttribute("aria-expanded", "false");
      tile.innerHTML = compactMarkup(subjectId, items);
      wireCompactHandlers(tile, subjectId);
      if (expandedTile === tile) {
        expandedTile = null;
        expandedSubjectId = null;
        document.removeEventListener("keydown", escHandler);
      }
    };
    if (animate && typeof document.startViewTransition === "function") {
      document.startViewTransition(apply);
    } else {
      apply();
    }
  }

  function escHandler(event) {
    if (event.key === "Escape" && expandedTile) {
      collapseSubject(expandedTile, true);
    }
  }

  // ── Fetch ────────────────────────────────────────────────────────────────
  async function fetchAllItems() {
    const params = new URLSearchParams();
    if (state.language) params.set("language", state.language);
    const q = searchInput ? searchInput.value.trim() : "";
    if (q) params.set("q", q);
    params.set("limit", String(PAGE_SIZE));

    let offset = 0;
    let total = 0;
    const items = [];
    while (true) {
      params.set("offset", String(offset));
      const data = await API.request(`/api/library?${params.toString()}`);
      const batch = Array.isArray(data.items) ? data.items : [];
      total = typeof data.total === "number" ? data.total : items.length + batch.length;
      items.push(...batch);
      if (!batch.length || items.length >= total) break;
      offset += PAGE_SIZE;
      if (offset >= PAGE_SIZE * 25) break;
    }
    return { items, total };
  }

  async function loadAndRender() {
    // Drop any expanded state — the tile is about to be removed.
    if (expandedTile) {
      expandedTile = null;
      expandedSubjectId = null;
      document.removeEventListener("keydown", escHandler);
    }

    hide(errorEl);
    hide(emptyEl);
    show(loadingEl);
    conceal(stageEl);
    conceal(statsEl);
    while (gridEl.firstChild) gridEl.removeChild(gridEl.firstChild);

    try {
      const { items } = await fetchAllItems();
      // Hold the skeleton at least SKELETON_MIN_MS before swapping in real
      // tiles, otherwise a fast cache-warm fetch flashes the layout.
      await waitSkeletonFloor();
      hide(loadingEl);

      // Always render the stats — even for an empty result set we want
      // Total / Subjects / Hard / Uzbek to read 0 instead of vanishing
      // (LIB-counter-01: prior code early-returned before renderStats so
      // the whole strip disappeared on a no-results search, leaving the
      // user with no readout that the filter dropped everything to zero).
      renderStats(items);
      reveal(statsEl);

      if (!items.length) {
        show(emptyEl);
        return;
      }

      const groups = groupBySubject(items);
      lastGroups = groups;
      renderTiles(groups);
      reveal(stageEl);
    } catch (err) {
      // Same floor on the error path — the user shouldn't see a skeleton
      // blink for 50ms and then an error card jump in.
      await waitSkeletonFloor();
      hide(loadingEl);
      errorMsgEl.textContent = err && err.message
        ? err.message
        : t("common.check_connection", "Check your connection and try again.");
      show(errorEl);
    }
  }

  // ── Subject metadata ─────────────────────────────────────────────────────
  async function loadSubjectMeta() {
    try {
      const data = await API.request("/api/subjects");
      const out = {};
      (data.subjects || []).forEach(s => {
        out[s.id] = { family: s.family, grades: s.grades || [] };
      });
      subjectMeta = out;
    } catch (_) {
      subjectMeta = {};
    }
  }

  // ── Top-bar wiring ───────────────────────────────────────────────────────
  function syncLangChipUi() {
    if (!langChips) return;
    langChips.querySelectorAll(".lib-chip").forEach(chip => {
      const v = chip.dataset.libLang || "";
      const active = v === state.language;
      chip.classList.toggle("is-active", active);
      chip.setAttribute("aria-pressed", active ? "true" : "false");
    });
  }

  function onFilterChange(reload) {
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(() => {
      if (reload !== false) loadAndRender();
    }, 250);
  }

  if (langChips) {
    langChips.addEventListener("click", (ev) => {
      const chip = ev.target.closest(".lib-chip");
      if (!chip) return;
      state.language = chip.dataset.libLang || "";
      persist();
      syncLangChipUi();
      onFilterChange(true);
    });
  }

  if (searchInput) {
    searchInput.addEventListener("input", () => {
      // LIB-3: Treat an empty input value as an implicit "clear filters"
      // signal so the inline X (data-search-clear, dispatched by
      // search-box.js) has the same semantics as the page-level Clear
      // button — otherwise users would see language/grade chips stay
      // active even though the search query was cleared.
      if (searchInput.value === "") {
        if (state.language || Object.keys(state.gradeBySubject).length) {
          state.language = "";
          state.gradeBySubject = {};
          persist();
          syncLangChipUi();
        }
      }
      onFilterChange(true);
    });
  }

  if (clearBtn) {
    clearBtn.addEventListener("click", () => {
      if (searchInput) {
        searchInput.value = "";
        // LIB-2: Dispatch a synthetic input event so search-box.js's
        // syncFilled re-runs and removes the .is-filled class (the X
        // icon would otherwise stay visible after the clear). The
        // empty-value branch in our own input listener is a no-op
        // here because we reset language/gradeBySubject just below
        // anyway.
        searchInput.dispatchEvent(new Event("input", { bubbles: true }));
        // Belt-and-suspenders: strip .is-filled directly from the
        // wrapper in case search-box.js failed to load.
        const box = searchInput.closest(".search-box");
        if (box) box.classList.remove("is-filled");
      }
      state.language = "";
      state.gradeBySubject = {};
      persist();
      syncLangChipUi();
      loadAndRender();
    });
  }

  if (retryBtn) {
    retryBtn.addEventListener("click", loadAndRender);
  }

  if (window.i18n && typeof window.i18n.onChange === "function") {
    window.i18n.onChange(() => {
      syncLangChipUi();
      loadAndRender();
    });
  }

  // ── Boot ────────────────────────────────────────────────────────────────
  syncLangChipUi();
  loadSubjectMeta().then(loadAndRender);
})();
