// frontend/js/library.js
// Library page — Apple-style subject blocks with FLIP-expand panels.
//
// Layout (replaces the pre-2026-04-30 <details> grouping):
//
//   [ Til: All UZ RU EN ]      [ search… ]   [ Clear ]
//
//   ┌ Total ┐ ┌ Subj ┐ ┌ Hard ┐ ┌ UZ ┐
//
//   ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐
//   │ Algebra│ │ Geom   │ │ Eng    │ │ Phys   │   ← .subject-tile buttons
//   └────────┘ └────────┘ └────────┘ └────────┘
//
//   On click → tile expands into a 3-column-wide .subject-panel that
//   FLIPs from the tile's exact position. Esc / × closes.
//
// Persistence: language + per-subject grade selection live in
// localStorage. Open-panel state is NOT persisted (too disruptive on
// reload).
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

  // Apple-system colors (locked by spec) ─ aligned with the CSS agent.
  const FAMILY_COLORS = {
    "aniq-fanlar":     "#0a84ff", // Apple blue
    "tabiy-fanlar":    "#30d158", // Apple green
    "til-fanlar":      "#bf5af2", // Apple purple
    "ijtimoiy-fanlar": "#ff9f0a", // Apple orange
  };

  // Stat accent colors — blue / green / red / purple per spec.
  const STAT_COLORS = {
    total:    "#0a84ff",
    subjects: "#30d158",
    hard:     "#ff453a",
    uz:       "#bf5af2",
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
  // Per-render cache so the panel can re-filter without re-fetch.
  let lastGroups = {};
  // FLIP engine state
  let openPanel  = null;
  let sourceTile = null;
  let sourceRect = null;
  let activeSubjectId = null;

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
  function show(el) { if (el) el.classList.remove("hidden"); }
  function hide(el) { if (el) el.classList.add("hidden"); }
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

  function isHardItem(hw) {
    // Primary: explicit difficulty / mode field.
    const diff = (hw && hw.difficulty || "").toString().toLowerCase();
    if (diff === "hard") return true;
    const mode = (hw && hw.mode || "").toString().toLowerCase();
    if (mode === "hard") return true;
    // Heuristic fallback when neither field is present: senior-grade
    // content (grade ≥ 9) is typically the "needs review" cohort.
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
  function renderTile(subjectId, items) {
    const accent = subjectFamilyColor(subjectId);
    const name = subjectDisplayName(subjectId);
    const glyph = subjectIcon(subjectId);
    const count = items.length;
    const tagline = subjectTagline(subjectId) || formatCount(count);
    const ariaLabel = t("library.subject_open_label", "Open {name}").replace("{name}", name);
    const openLabel = t("library.tile_open", "Open");

    const tile = document.createElement("button");
    tile.type = "button";
    tile.className = "subject-tile";
    tile.style.setProperty("--accent", accent);
    tile.dataset.subjectId = subjectId;
    tile.setAttribute("aria-label", ariaLabel);
    tile.innerHTML = `
      <div class="tile-orb" aria-hidden="true"></div>
      <div class="tile-icon">${escapeHtml(glyph)}</div>
      <div class="tile-copy">
        <h3>${escapeHtml(name)}</h3>
        <p>${escapeHtml(tagline)}</p>
        <div class="tile-footer">
          <span>${escapeHtml(formatCount(count))}</span>
          <span class="tile-pill">${escapeHtml(openLabel)} ↗</span>
        </div>
      </div>
    `;
    tile.addEventListener("click", () => openSubject(tile, subjectId));
    return tile;
  }

  function renderTiles(groups) {
    while (gridEl.firstChild) gridEl.removeChild(gridEl.firstChild);
    const ids = sortedSubjectIds(Object.keys(groups));
    const frag = document.createDocumentFragment();
    ids.forEach(sid => frag.appendChild(renderTile(sid, groups[sid])));
    gridEl.appendChild(frag);
  }

  // ── Homework card ────────────────────────────────────────────────────────
  function renderHomeworkCard(hw, index) {
    const subjectName = subjectDisplayName(hw.subject);
    const language = hw.language ? hw.language.toUpperCase() : "";
    const mode = (hw.mode || "").toString().toLowerCase();
    const modeLabel = hw.mode ? hw.mode.toUpperCase() : "";
    const num = String(index + 1).padStart(2, "0");
    const chapter = hw.chapter || "";
    const title = hw.title || hw.id;
    const idShort = hw.id ? String(hw.id).slice(0, 8) : "";

    const card = document.createElement("a");
    card.className = "homework-card";
    card.href = `/h/${encodeURIComponent(hw.id)}`;
    card.target = "_blank";
    card.rel = "noreferrer";
    card.setAttribute("aria-label", title);

    const showBadge = !!hw.mode;
    const badgeHtml = showBadge
      ? `<span class="hw-badge ${escapeHtml(mode)}">${escapeHtml(modeLabel)}</span>`
      : "";

    const subjectTag = subjectName
      ? `<span class="hw-tag blue">${escapeHtml(subjectName)}</span>`
      : "";
    const gradeTag = (hw.grade != null)
      ? `<span class="hw-tag purple">${escapeHtml(t("common.grade", "Grade"))} ${escapeHtml(String(hw.grade))}</span>`
      : "";
    const langTag = language
      ? `<span class="hw-tag cyan">${escapeHtml(language)}</span>`
      : "";

    card.innerHTML = `
      <div class="hw-head">
        <span class="hw-num">${escapeHtml(num)}</span>
        ${badgeHtml}
      </div>
      <h4 class="hw-title">${escapeHtml(title)}</h4>
      <div class="hw-subtopic">${escapeHtml(chapter)}</div>
      <div class="hw-tags">
        ${subjectTag}${gradeTag}${langTag}
      </div>
      <div class="hw-bottom">
        <span>ⓘ ${escapeHtml(idShort || formatCount(1))}</span>
        <span>▣ ${escapeHtml(formatDate(hw.updated_at))}</span>
      </div>
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

  // ── FLIP engine ──────────────────────────────────────────────────────────
  function rectRelativeToGrid(rect) {
    const gridRect = gridEl.getBoundingClientRect();
    return {
      left:   rect.left - gridRect.left,
      top:    rect.top  - gridRect.top,
      width:  rect.width,
      height: rect.height,
    };
  }

  // 4-col grid → 3-col-wide expanded panel anchored adjacent to the
  // origin tile. Tablet (≤1030) collapses to full-width 2-row, mobile
  // (≤650) likewise but taller.
  function getExpandedTarget(tile) {
    const gridRect = gridEl.getBoundingClientRect();
    const origin = rectRelativeToGrid(tile.getBoundingClientRect());
    const isMobile = window.innerWidth <= 650;
    const isTablet = window.innerWidth <= 1030;

    if (isMobile) {
      return { left: 0, top: origin.top, width: gridRect.width, height: 690 };
    }
    if (isTablet) {
      return { left: 0, top: origin.top, width: gridRect.width, height: 520 };
    }

    const cardGap = 14;
    const cardWidth = (gridRect.width - cardGap * 3) / 4;
    const originColumn = Math.round(origin.left / (cardWidth + cardGap));
    const width = cardWidth * 3 + cardGap * 2;
    let left;
    if (originColumn === 0) {
      // Origin in column 0 → panel covers cols 1–3.
      left = cardWidth + cardGap;
    } else if (originColumn === 3) {
      // Origin in column 3 → panel covers cols 0–2.
      left = 0;
    } else {
      // Columns 1 or 2 → bias toward right so panel covers cols 1–3.
      left = cardWidth + cardGap;
    }
    return { left, top: origin.top, width, height: 420 };
  }

  function setPanelBox(panel, rect) {
    panel.style.setProperty("--panel-left",   `${rect.left}px`);
    panel.style.setProperty("--panel-top",    `${rect.top}px`);
    panel.style.setProperty("--panel-width",  `${rect.width}px`);
    panel.style.setProperty("--panel-height", `${rect.height}px`);
  }

  function panelMarkup(subjectId, items) {
    const accent = subjectFamilyColor(subjectId);
    const name = subjectDisplayName(subjectId);
    const glyph = subjectIcon(subjectId);
    const count = items.length;

    // Grade range header — min..max present in items.
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

    // Grade chips — only grades present in this subject's items.
    const gradesPresent = Array.from(new Set(grades));
    const persisted = state.gradeBySubject[subjectId] || "all";
    const selected = (persisted === "all" || gradesPresent.includes(Number(persisted))) ? persisted : "all";
    const chipsHtml = [
      `<button class="lib-grade-chip${selected === "all" ? " is-active" : ""}" data-grade="all">${escapeHtml(t("library.section_grade_all", "All"))}</button>`,
    ].concat(gradesPresent.map(g => {
      const active = String(selected) === String(g);
      return `<button class="lib-grade-chip${active ? " is-active" : ""}" data-grade="${escapeHtml(String(g))}">${escapeHtml(String(g))}</button>`;
    })).join("");

    return `
      <div class="panel-content">
        <div class="panel-top">
          <div class="panel-title">
            <div class="panel-glyph">${escapeHtml(glyph)}</div>
            <div>
              <h2>${escapeHtml(name)}</h2>
              <p>${subline}</p>
            </div>
          </div>
          <button class="panel-close" aria-label="${escapeHtml(t("common.close", "Close"))}" data-i18n-aria-label="common.close">×</button>
        </div>
        <div class="panel-actions">${chipsHtml}</div>
        <div class="panel-cards"></div>
      </div>
    `;
  }

  function paintPanelCards(panel, subjectId, items) {
    const cardsHost = panel.querySelector(".panel-cards");
    if (!cardsHost) return;
    while (cardsHost.firstChild) cardsHost.removeChild(cardsHost.firstChild);

    const grade = state.gradeBySubject[subjectId] || "all";
    const filtered = grade === "all"
      ? items
      : items.filter(hw => String(hw.grade) === String(grade));

    if (!filtered.length) {
      const empty = document.createElement("div");
      empty.className = "lib-section-empty";
      empty.textContent = t("library.section_empty", "No homeworks for this grade.");
      cardsHost.appendChild(empty);
      return;
    }

    const frag = document.createDocumentFragment();
    filtered.forEach((hw, idx) => frag.appendChild(renderHomeworkCard(hw, idx)));
    cardsHost.appendChild(frag);
  }

  function openSubject(tile, subjectId) {
    if (openPanel) closePanel(false);

    const items = lastGroups[subjectId] || [];
    sourceTile = tile;
    activeSubjectId = subjectId;
    sourceRect = rectRelativeToGrid(tile.getBoundingClientRect());
    const targetRect = getExpandedTarget(tile);

    const panel = document.createElement("section");
    panel.className = "subject-panel animating";
    panel.style.setProperty("--accent", subjectFamilyColor(subjectId));
    setPanelBox(panel, targetRect);
    panel.innerHTML = panelMarkup(subjectId, items);

    gridEl.appendChild(panel);
    openPanel = panel;
    gridEl.classList.add("has-panel");
    if (stageEl) stageEl.classList.add("has-panel");
    tile.classList.add("is-origin");

    // FLIP — animate from source rect to target rect.
    const dx = sourceRect.left - targetRect.left;
    const dy = sourceRect.top  - targetRect.top;
    const sx = sourceRect.width  / targetRect.width;
    const sy = sourceRect.height / targetRect.height;

    const animation = panel.animate([
      {
        transform: `translate(${dx}px, ${dy}px) scale(${sx}, ${sy})`,
        opacity: 1,
        borderRadius: "31px",
        filter: "brightness(1.14) saturate(1.12)",
      },
      {
        transform: "translate(0, 0) scale(1, 1)",
        opacity: 1,
        borderRadius: "31px",
        filter: "brightness(1) saturate(1)",
      },
    ], {
      duration: 640,
      easing: "cubic-bezier(.16, 1, .3, 1)",
      fill: "both",
    });
    animation.onfinish = () => panel.classList.remove("animating");

    // Render cards immediately so the staggered CSS animation can play.
    paintPanelCards(panel, subjectId, items);

    // Wire close + escape + grade chips.
    const closeBtn = panel.querySelector(".panel-close");
    if (closeBtn) closeBtn.addEventListener("click", () => closePanel(true));

    const actions = panel.querySelector(".panel-actions");
    if (actions) {
      actions.addEventListener("click", (ev) => {
        const chip = ev.target.closest(".lib-grade-chip");
        if (!chip) return;
        const grade = chip.dataset.grade || "all";
        state.gradeBySubject[subjectId] = grade;
        persist();
        actions.querySelectorAll(".lib-grade-chip").forEach(c => {
          c.classList.toggle("is-active", c.dataset.grade === grade);
        });
        paintPanelCards(panel, subjectId, items);
      });
    }

    document.addEventListener("keydown", escHandler);
  }

  function escHandler(event) {
    if (event.key === "Escape") closePanel(true);
  }

  function closePanel(animate) {
    if (animate === undefined) animate = true;
    if (!openPanel) return;

    const panel = openPanel;
    const originRect = sourceTile
      ? rectRelativeToGrid(sourceTile.getBoundingClientRect())
      : sourceRect;
    const currentRect = rectRelativeToGrid(panel.getBoundingClientRect());
    panel.classList.add("animating");
    document.removeEventListener("keydown", escHandler);

    const finish = () => {
      if (panel && panel.parentNode) panel.parentNode.removeChild(panel);
      if (sourceTile) sourceTile.classList.remove("is-origin");
      if (gridEl) gridEl.classList.remove("has-panel");
      if (stageEl) stageEl.classList.remove("has-panel");
      openPanel = null;
      sourceTile = null;
      sourceRect = null;
      activeSubjectId = null;
    };

    if (!animate || !originRect) {
      finish();
      return;
    }

    const dx = originRect.left - currentRect.left;
    const dy = originRect.top  - currentRect.top;
    const sx = originRect.width  / currentRect.width;
    const sy = originRect.height / currentRect.height;

    const animation = panel.animate([
      { transform: "translate(0, 0) scale(1, 1)",                                    opacity: 1,   borderRadius: "31px" },
      { transform: `translate(${dx}px, ${dy}px) scale(${sx}, ${sy})`,                opacity: .98, borderRadius: "31px" },
    ], {
      duration: 500,
      easing: "cubic-bezier(.22, 1, .36, 1)",
      fill: "both",
    });
    animation.onfinish = finish;
  }

  // Reposition open panel on resize.
  window.addEventListener("resize", () => {
    if (!openPanel || !sourceTile) return;
    setPanelBox(openPanel, getExpandedTarget(sourceTile));
  });

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
    // Close any open panel before re-rendering — its source tile is
    // about to be removed.
    if (openPanel) closePanel(false);

    hide(errorEl);
    hide(emptyEl);
    show(loadingEl);
    conceal(stageEl);
    conceal(statsEl);
    while (gridEl.firstChild) gridEl.removeChild(gridEl.firstChild);

    try {
      const { items } = await fetchAllItems();
      hide(loadingEl);

      if (!items.length) {
        show(emptyEl);
        return;
      }

      const groups = groupBySubject(items);
      lastGroups = groups;
      renderStats(items);
      renderTiles(groups);
      reveal(statsEl);
      reveal(stageEl);
    } catch (err) {
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
    searchInput.addEventListener("input", () => onFilterChange(true));
  }

  if (clearBtn) {
    clearBtn.addEventListener("click", () => {
      if (searchInput) searchInput.value = "";
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
