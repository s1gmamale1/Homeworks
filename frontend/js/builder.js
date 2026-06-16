// frontend/js/builder.js
// NETS Builder workspace logic: load homework, render phase sidebar, autosave, preview, fixture loading.

(function () {
  "use strict";

  const SUBJECT_LABELS = {
    "math-algebra": "Algebra",
    "geometriya-g7-11": "Geometriya",
    physics: "Fizika",
    biology: "Biologiya",
    "kimyo-g7-11": "Kimyo",
    english: "English",
    history: "Tarix",
  };

  const FIXTURE_NAMES = [
    "math-algebra-g8-hard",
    "physics-g9-hard",
    "biology-g10-hard",
    "english-g11-b2",
    "history-g8",
    "kimyo-g9-hard",
    "geometriya-g8-hard",
  ];

  const PHASE_PIPELINE = {
    "aniq-fanlar:easy": ["preview", "flashcards", "memory_sprint", "game_breaks", "reflection"],
    "aniq-fanlar:hard": [
      "preview",
      "flashcards",
      "memory_sprint",
      "game_breaks",
      "real_life",
      "real_life_challenge",
      "consolidation",
      "final_challenge",
      "reflection",
    ],
    "tabiy-fanlar:easy": ["preview", "flashcards", "memory_sprint", "game_breaks", "reflection"],
    "tabiy-fanlar:hard": [
      "preview",
      "flashcards",
      "memory_sprint",
      "game_breaks",
      "real_life",
      "real_life_challenge",
      "consolidation",
      "final_challenge",
      "reflection",
    ],
    "til-fanlar:hard": [
      "preview",
      "flashcards",
      "memory_sprint",
      "reading",
      "game_breaks",
      "real_life",
      "real_life_challenge",
      "consolidation",
      "final_challenge",
      "reflection",
    ],
    "ijtimoiy-fanlar:hard": [
      "preview",
      "flashcards",
      "memory_sprint",
      "game_breaks",
      "consolidation",
      "final_challenge",
      "reflection",
    ],
  };

  const PHASE_NAMES = {
    preview: "Ko'rib chiqish",
    flashcards: "Flesh-kartalar",
    memory_sprint: "Xotira Sprint",
    reading: "O'qish",
    game_breaks: "O'yin tanaffus",
    real_life: "Hayotiy vazifa",
    real_life_challenge: "Hayotiy chaqiruv",
    consolidation: "Mustahkamlash",
    final_challenge: "Yakuniy jang",
    reflection: "Xulosa",
  };

  const PHASE_ICONS = {
    preview: "📋",
    flashcards: "🃏",
    memory_sprint: "⚡",
    reading: "📖",
    game_breaks: "🎮",
    real_life: "🌍",
    real_life_challenge: "🧭",
    consolidation: "🧠",
    final_challenge: "👾",
    reflection: "💭",
  };

  const PHASE_EDITOR_KEYS = {
    preview: "preview",
    flashcards: "flashcards",
    memory_sprint: "memorySprint",
    reading: "reading",
    game_breaks: "gameBreaks",
    real_life: "realLife",
    real_life_challenge: "realLifeChallenge",
    consolidation: "consolidation",
    final_challenge: "boss",
    reflection: "reflection",
  };

  const CONTRACT_KEYS = [
    "meta",
    "quotes",
    "panels",
    "flashcards",
    "memory_sprint",
    "gb_adaptive_quiz",
    "gb_why_chain",
    "gb_memory_match",
    "gb_puzzle_lock",
    "gb_mystery_box",
    "gb_ttt",
    "real_life",
    "real_life_challenge",
    "boss_questions",
    "reflection",
  ];

  const els = {};
  let autosaveTimer = null;
  let previewVisible = true;
  let loadingTemplate = false;

  // --- Save-state indicator + retry state ---
  const RETRY_DELAYS = [3000, 9000, 27000, 60000, 120000];
  let retryCount = 0;
  let retryTimer = null;
  let lastSavedAt = null;
  let relativeTicker = null;
  let isOffline = typeof navigator !== "undefined" && navigator.onLine === false;

  window.BUILDER_STATE = window.BUILDER_STATE || {
    homework: null,
    activePhase: "preview",
    dirty: false,
    meta: null,
  };

  async function loadSubjectsMeta() {
    try {
      const payload = await API.getSubjects();
      if (payload && typeof payload === "object") {
        window.BUILDER_STATE.meta = {
          subjects: Array.isArray(payload.subjects) ? payload.subjects : [],
          families: payload.families || {},
          statuses: payload.statuses || null,
          phase_names: payload.phase_names || null,
          phase_icons: payload.phase_icons || null,
          pipelines: payload.pipelines || null,
        };
      }
    } catch (error) {
      // Silent fallback: hardcoded constants remain in effect.
      window.BUILDER_STATE.meta = null;
    }
  }

  function getPhaseNames() {
    // Prefer i18n strings so the sidebar phase tabs respond to language changes.
    // Backend-supplied phase_names and the hardcoded PHASE_NAMES (Uzbek) remain
    // as fallbacks when an i18n key is missing.
    const backend = (window.BUILDER_STATE.meta && window.BUILDER_STATE.meta.phase_names) || {};
    const out = {};
    Object.keys(PHASE_NAMES).forEach((phase) => {
      const i18nKey = `builder.phase_${phase}`;
      const translated = t(i18nKey, "");
      out[phase] = translated && translated !== i18nKey
        ? translated
        : (backend[phase] || PHASE_NAMES[phase]);
    });
    return out;
  }

  function getPhaseIcons() {
    return (window.BUILDER_STATE.meta && window.BUILDER_STATE.meta.phase_icons) || PHASE_ICONS;
  }

  function getPhasePipelines() {
    return (window.BUILDER_STATE.meta && window.BUILDER_STATE.meta.pipelines) || PHASE_PIPELINE;
  }

  function $(id) {
    return document.getElementById(id);
  }

  // i18n helper — falls back to the literal string if i18n hasn't loaded yet.
  function t(key, fallback) {
    if (window.i18n && typeof window.i18n.t === "function") {
      return window.i18n.t(key, fallback);
    }
    return fallback != null ? fallback : key;
  }

  function cacheElements() {
    Object.assign(els, {
      sidebarTitle: $("sidebar-title"),
      sidebarMeta: $("sidebar-meta"),
      phaseList: $("phase-list"),
      saveState: $("save-state"),
      builderSubtitle: $("builder-subtitle"),
      builderTitle: $("builder-title"),
      refreshBtn: $("refresh-homework-btn"),
      togglePreviewBtn: $("toggle-preview-btn"),
      loadTemplateBtn: $("load-template-btn"),
      testTutorBtn: $("test-tutor-btn"),
      builderContent: $("builder-content"),
      activePhaseKicker: $("active-phase-kicker"),
      activePhaseTitle: $("active-phase-title"),
      addItemBtn: $("add-item-btn"),
      editorRoot: $("editor-root"),
      previewPanel: $("preview-panel"),
      previewFrame: $("preview-frame"),
      templateModal: $("template-modal"),
      closeTemplateModal: $("close-template-modal"),
      cancelTemplate: $("cancel-template"),
      fixtureList: $("fixture-list"),
      toastRegion: $("toast-region"),
      migrateContentBtn: $("migrate-content-btn"),
    });
  }

  function escapeHtml(value) {
    return String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#039;");
  }

  function clone(value) {
    if (value === undefined) return undefined;
    return JSON.parse(JSON.stringify(value));
  }

  function titleCase(value) {
    const clean = String(value || "").replaceAll("_", " ").replaceAll("-", " ");
    return clean.charAt(0).toUpperCase() + clean.slice(1);
  }

  function getHomeworkId() {
    const params = new URLSearchParams(window.location.search);
    return params.get("id") || params.get("homework_id") || "";
  }

  function getSubjectLabel(subjectId) {
    return SUBJECT_LABELS[subjectId] || subjectId || "Unknown";
  }

  function getContent() {
    const homework = window.BUILDER_STATE.homework || {};
    homework.content_json = normalizeContent(homework.content_json || {}, homework);
    return homework.content_json;
  }

  function normalizeContent(content, homework) {
    const safe = content && typeof content === "object" ? { ...content } : {};

    safe.meta = {
      title: safe.meta?.title || homework?.title || "",
      subject_display: safe.meta?.subject_display || getSubjectLabel(homework?.subject),
      section: safe.meta?.section || "",
      cefr_level: safe.meta?.cefr_level || "",
    };

    for (const key of CONTRACT_KEYS) {
      if (key === "meta") continue;

      if (["real_life", "real_life_challenge", "reflection"].includes(key)) {
        safe[key] = safe[key] ?? null;
      } else {
        safe[key] = Array.isArray(safe[key]) ? safe[key] : [];
      }
    }

    return safe;
  }

  function getPipeline() {
    const homework = window.BUILDER_STATE.homework;
    if (!homework) return ["preview"];

    const family = homework.family || "aniq-fanlar";
    const mode = homework.mode || "easy";
    const key = `${family}:${mode}`;
    const pipelines = getPhasePipelines();

    return (
      pipelines[key] ||
      pipelines[`${family}:hard`] ||
      PHASE_PIPELINE[key] ||
      PHASE_PIPELINE[`${family}:hard`] ||
      PHASE_PIPELINE["aniq-fanlar:easy"]
    );
  }

  function setSaveState(label, type = "") {
    if (!els.saveState) return;
    els.saveState.textContent = label;
    els.saveState.className = `save-state ${type}`.trim();
    els.saveState.dataset.state = type || "idle";
  }

  // --- Top-bar save indicator ---
  // state: "idle" | "saving" | "saved" | "error" | "offline"
  function updateSaveState(state, extra) {
    const el = document.getElementById("save-indicator");
    if (!el) return;

    el.dataset.state = state;
    const textEl = el.querySelector(".save-text");
    if (!textEl) return;

    if (state === "saving") {
      textEl.textContent = t("builder.saving");
    } else if (state === "saved") {
      lastSavedAt = Date.now();
      if (relativeTicker) window.clearInterval(relativeTicker);
      relativeTicker = window.setInterval(updateRelativeTime, 10000);
      updateRelativeTime();
      // Tear down persistent error banner if present — connection recovered.
      document.getElementById("save-failed-banner")?.remove();
    } else if (state === "error") {
      const attempt = (extra && extra.attempt) || 1;
      const max = (extra && extra.maxAttempts) || 5;
      textEl.textContent = `${t("builder.save_failed_retry")} (${attempt}/${max})`;
    } else if (state === "offline") {
      textEl.textContent = t("builder.offline_queued");
    } else {
      // "idle" — cleanest neutral state before first save.
      if (relativeTicker) {
        window.clearInterval(relativeTicker);
        relativeTicker = null;
      }
      textEl.textContent = window.BUILDER_STATE?.dirty ? t("builder.unsaved") : t("builder.idle");
    }
  }

  function updateRelativeTime() {
    if (!lastSavedAt) return;
    const el = document.querySelector("#save-indicator .save-text");
    if (!el) return;
    const secs = Math.floor((Date.now() - lastSavedAt) / 1000);
    if (secs < 5) el.textContent = t("builder.saved");
    else if (secs < 60) el.textContent = `${t("builder.saved")} · ${secs}s`;
    else if (secs < 3600) el.textContent = `${t("builder.saved")} · ${Math.floor(secs / 60)}m`;
    else el.textContent = `${t("builder.saved")} · ${Math.floor(secs / 3600)}h`;
  }

  function scheduleRetry() {
    if (retryCount >= RETRY_DELAYS.length) {
      showPersistentErrorBanner();
      return;
    }
    const delay = RETRY_DELAYS[retryCount] || 120000;
    retryCount += 1;
    if (retryTimer) window.clearTimeout(retryTimer);
    retryTimer = window.setTimeout(() => {
      retryTimer = null;
      saveNow().catch(() => {
        /* handled inside saveNow — next tick will reschedule */
      });
    }, delay);
  }

  function showPersistentErrorBanner() {
    if (document.getElementById("save-failed-banner")) return;
    const banner = document.createElement("div");
    banner.id = "save-failed-banner";
    banner.className = "save-banner-error";
    banner.textContent = t("builder.save_banner_error");
    document.body.appendChild(banner);
  }

  // Fire-and-forget PUT flush for beforeunload / visibilitychange=hidden.
  // Uses fetch+keepalive (survives tab close). Falls back to sendBeacon inside API.flushHomework.
  function flushPendingSave() {
    if (autosaveTimer) {
      window.clearTimeout(autosaveTimer);
      autosaveTimer = null;
    }
    const state = window.BUILDER_STATE;
    if (!state || !state.dirty || !state.homework || !state.homework.id) return;

    const payload = {
      content_json: getContent(),
    };
    if (state.homework.title) payload.title = state.homework.title;
    if (state.homework.status) payload.status = state.homework.status;

    try {
      if (window.API && typeof window.API.flushHomework === "function") {
        window.API.flushHomework(state.homework.id, payload);
      }
    } catch (_err) {
      /* best effort — page is unloading */
    }
  }

  function showToast(title, message, type = "success") {
    const toast = document.createElement("div");
    toast.className = `toast ${type}`;
    toast.innerHTML = `
      <span class="status-dot ${type === "error" ? "error" : type === "warning" ? "warn" : "ok"}"></span>
      <div>
        <strong>${escapeHtml(title)}</strong>
        <p>${escapeHtml(message)}</p>
      </div>
    `;

    els.toastRegion.appendChild(toast);
    window.setTimeout(() => {
      toast.style.opacity = "0";
      toast.style.transform = "translateY(8px) scale(0.98)";
      window.setTimeout(() => toast.remove(), 180);
    }, 3200);
  }

  function setMigrationButton(status) {
    if (!els.migrateContentBtn) return;
    const needsMigration = Boolean(status && status.needs_migration);
    els.migrateContentBtn.hidden = !needsMigration;
    els.migrateContentBtn.disabled = false;
    els.migrateContentBtn.textContent = needsMigration
      ? t("builder.migrate_data", "Update data")
      : t("builder.data_current", "Data current");
    const keys = []
      .concat((status && status.added_keys) || [])
      .concat((status && status.changed_keys) || []);
    els.migrateContentBtn.title = keys.length
      ? `${t("builder.migrate_data_title", "Stored data needs compatibility updates")}: ${keys.slice(0, 6).join(", ")}`
      : t("builder.migrate_data_title", "Stored data needs compatibility updates");
  }

  async function checkMigrationStatus() {
    const homework = window.BUILDER_STATE.homework;
    if (!homework || !homework.id || !API.getHomeworkMigrationStatus) return;
    try {
      const status = await API.getHomeworkMigrationStatus(homework.id);
      setMigrationButton(status);
    } catch (_error) {
      setMigrationButton(null);
    }
  }

  async function migrateStoredContent() {
    const homework = window.BUILDER_STATE.homework;
    if (!homework || !homework.id || !API.migrateHomeworkContent || !els.migrateContentBtn) return;

    els.migrateContentBtn.disabled = true;
    els.migrateContentBtn.textContent = t("builder.migrating_data", "Updating...");

    try {
      if (window.BUILDER_STATE.dirty) {
        await saveNow();
      }
      const result = await API.migrateHomeworkContent(homework.id);
      const nextHomework = result.homework || homework;
      window.BUILDER_STATE.homework = {
        ...homework,
        ...nextHomework,
        content_json: normalizeContent(nextHomework.content_json || homework.content_json || {}, nextHomework),
      };
      window.BUILDER_STATE.dirty = false;
      setMigrationButton({ needs_migration: false });
      renderAll();
      showToast(
        t("builder.data_migrated", "Data migrated"),
        result.migrated
          ? t("builder.data_migrated_message", "This homework now uses the current content format.")
          : t("builder.data_already_current", "This homework was already up to date."),
        "success"
      );
    } catch (error) {
      els.migrateContentBtn.disabled = false;
      els.migrateContentBtn.textContent = t("builder.migrate_data", "Update data");
      showToast(t("builder.data_migration_failed", "Data migration failed"), error.message, "error");
    }
  }

  function renderMeta() {
    const homework = window.BUILDER_STATE.homework;
    if (!homework) return;

    const subject = getSubjectLabel(homework.subject);
    const status = homework.status || "draft";

    const fallbackTitle = t("builder.untitled");
    els.sidebarTitle.textContent = homework.title || fallbackTitle;
    els.builderTitle.textContent = homework.title || fallbackTitle;
    const modeLabel =
      homework.mode === "easy" ? t("common.easy")
      : homework.mode === "hard" ? t("common.hard")
      : titleCase(homework.mode);
    els.builderSubtitle.textContent = `${subject} · ${homework.grade}-sinf · ${modeLabel}`;

    const statusKey = `common.${status}`;
    const statusLabel = t(statusKey, titleCase(status));
    els.sidebarMeta.innerHTML = `
      <span class="status-pill" data-status="${escapeHtml(status)}">
        <span class="status-dot ${escapeHtml(status)}"></span>
        ${escapeHtml(statusLabel)}
      </span>
      <span class="mode-pill">${escapeHtml(modeLabel)}</span>
      <span class="grade-pill">${escapeHtml(homework.grade)}-sinf</span>
    `;
  }

  function renderPhases() {
    const active = window.BUILDER_STATE.activePhase;
    const phases = getPipeline();
    const phaseNames = getPhaseNames();
    const phaseIcons = getPhaseIcons();

    // Real phase buttons are about to replace the loading skeleton.
    els.phaseList.setAttribute("aria-busy", "false");

    els.phaseList.innerHTML = phases
      .map(
        (phase) => `
          <button class="phase-btn ${phase === active ? "active" : ""}" type="button" data-phase="${escapeHtml(phase)}">
            <span class="phase-icon" aria-hidden="true">${escapeHtml(phaseIcons[phase] || PHASE_ICONS[phase] || "•")}</span>
            <span>${escapeHtml(phaseNames[phase] || PHASE_NAMES[phase] || titleCase(phase))}</span>
          </button>
        `
      )
      .join("");
  }

  function getPhaseData(phase) {
    const content = getContent();

    if (phase === "preview") {
      return {
        meta: clone(content.meta),
        panels: clone(content.panels),
        quotes: clone(content.quotes),
      };
    }

    if (phase === "flashcards") return clone(content.flashcards);
    if (phase === "memory_sprint") return clone(content.memory_sprint);

    if (phase === "game_breaks") {
      return {
        adaptive_quiz: clone(content.gb_adaptive_quiz),
        why_chain: clone(content.gb_why_chain),
        memory_match: clone(content.gb_memory_match),
        puzzle_lock: clone(content.gb_puzzle_lock),
        mystery_box: clone(content.gb_mystery_box),
        ttt: clone(content.gb_ttt),
        memory_palace: clone(content.gb_memory_palace) || { palaces: [], concepts: [] },
      };
    }

    if (phase === "real_life") return clone(content.real_life);
    if (phase === "real_life_challenge") return clone(content.real_life_challenge);
    if (phase === "consolidation") return clone(content.consolidation);
    if (phase === "reading") return clone(content.reading);
    if (phase === "final_challenge") return clone(content.boss_questions);
    if (phase === "reflection") return clone(content.reflection);

    return null;
  }

  function applyPhaseChange(phase, nextData) {
    const content = getContent();

    if (phase === "preview") {
      content.meta = { ...content.meta, ...(nextData?.meta || {}) };
      content.panels = Array.isArray(nextData?.panels) ? nextData.panels : content.panels;
      content.quotes = Array.isArray(nextData?.quotes) ? nextData.quotes : content.quotes;
    } else if (phase === "flashcards") {
      content.flashcards = Array.isArray(nextData) ? nextData : [];
    } else if (phase === "memory_sprint") {
      content.memory_sprint = Array.isArray(nextData) ? nextData : [];
    } else if (phase === "game_breaks") {
      content.gb_adaptive_quiz = Array.isArray(nextData?.adaptive_quiz) ? nextData.adaptive_quiz : [];
      content.gb_why_chain = Array.isArray(nextData?.why_chain) ? nextData.why_chain : [];
      content.gb_memory_match = Array.isArray(nextData?.memory_match) ? nextData.memory_match : [];
      content.gb_puzzle_lock = Array.isArray(nextData?.puzzle_lock) ? nextData.puzzle_lock : [];
      content.gb_mystery_box = Array.isArray(nextData?.mystery_box) ? nextData.mystery_box : [];
      content.gb_ttt = Array.isArray(nextData?.ttt) ? nextData.ttt : [];
      content.gb_memory_palace =
        nextData?.memory_palace && typeof nextData.memory_palace === "object"
          ? nextData.memory_palace
          : { palaces: [], concepts: [] };
    } else if (phase === "real_life") {
      content.real_life = nextData || null;
    } else if (phase === "real_life_challenge") {
      content.real_life_challenge = nextData || null;
    } else if (phase === "consolidation") {
      content.consolidation = nextData || null;
    } else if (phase === "reading") {
      content.reading = nextData || null;
    } else if (phase === "final_challenge") {
      content.boss_questions = Array.isArray(nextData) ? nextData : [];
    } else if (phase === "reflection") {
      content.reflection = nextData || null;
    } else {
      const phaseNames = getPhaseNames();
      const name = phaseNames[phase] || PHASE_NAMES[phase] || phase;
      showToast(t("builder.toast_not_saved"), `${name} — ${t("builder.no_contract_data")}`, "warning");
      return;
    }

    markDirty();
  }

  function renderPlaceholderEditor(phase) {
    const data = getPhaseData(phase);
    const dataPreview = data === null ? t("builder.no_contract_data") : JSON.stringify(data, null, 2);
    const phaseNames = getPhaseNames();

    els.editorRoot.innerHTML = `
      <div class="editor-card">
        <div class="editor-header">
          <div>
            <p class="eyebrow">${escapeHtml(t("builder.wave1_stub_eyebrow"))}</p>
            <h3>${escapeHtml(phaseNames[phase] || PHASE_NAMES[phase] || titleCase(phase))}</h3>
          </div>
        </div>
        <p class="muted-text">${escapeHtml(t("builder.wave1_stub_text"))}</p>
        <pre class="json-preview">${escapeHtml(dataPreview)}</pre>
      </div>
    `;
  }

  // Subject → default boss name (mirrors server/services/injector._BOSS_NAME_DEFAULTS).
  // Used only to compute the placeholder hint shown in the builder boss-name field;
  // the runtime resolves the real default server-side, so authors see the same
  // string in the placeholder as the player will see if the field is left blank.
  const BOSS_NAME_DEFAULTS = {
    algebra:    "Algebra Boshlig'i",
    geometry:   "Geometriya Boshlig'i",
    geometriya: "Geometriya Boshlig'i",
    physics:    "Fizika Boshlig'i",
    fizika:     "Fizika Boshlig'i",
    chemistry:  "Kimyo Boshlig'i",
    kimyo:      "Kimyo Boshlig'i",
    biology:    "Biologiya Boshlig'i",
    biologiya:  "Biologiya Boshlig'i",
    english:    "English Boss",
    russian:    "Русский Босс",
    history:    "Tarix Boshlig'i",
    tarix:      "Tarix Boshlig'i",
    literature: "Adabiyot Boshlig'i",
    uzbek:      "O'zbek tili Boshlig'i",
  };

  function defaultBossNameFor(subjectId) {
    const sid = String(subjectId || "").trim().toLowerCase();
    return BOSS_NAME_DEFAULTS[sid] || "Boss";
  }

  function mountBossNameField() {
    // Prepend a top-of-editor card with the boss-name input, bound to
    // content.boss_name. Empty string == use server-side default.
    const content = getContent();
    const homework = window.BUILDER_STATE.homework || {};
    const fallback = defaultBossNameFor(homework.subject);
    const current = String(content.boss_name || "");
    const label = t("builder.boss_name_label", "Boss name");
    const placeholderTpl = t(
      "builder.boss_name_placeholder_template",
      "Boss name (defaults to: {default})",
    );
    const placeholder = placeholderTpl.replace("{default}", fallback);
    const help = t(
      "builder.boss_name_help",
      "Leave blank to use the subject default. Shown on the final-boss screen.",
    );

    const card = document.createElement("section");
    card.className = "editor-card";
    card.dataset.bossNameCard = "true";
    card.innerHTML = `
      <div class="editor-grid">
        <label class="field full-span">
          <span>${escapeHtml(label)}</span>
          <input
            type="text"
            id="boss-name-input"
            value="${escapeHtml(current)}"
            placeholder="${escapeHtml(placeholder)}"
            maxlength="80"
            autocomplete="off" />
          <small class="muted-text">${escapeHtml(help)}</small>
        </label>
      </div>
    `;
    // Insert at the very top of the editor root (above the boss-questions list).
    els.editorRoot.insertBefore(card, els.editorRoot.firstChild);

    const input = card.querySelector("#boss-name-input");
    if (input) {
      input.addEventListener("input", () => {
        const next = input.value.trim();
        const c = getContent();
        if (next) c.boss_name = next;
        else delete c.boss_name;
        markDirty();
      });
    }
  }

  function renderActiveEditor() {
    const phase = window.BUILDER_STATE.activePhase;
    const phaseNames = getPhaseNames();
    const phaseName = phaseNames[phase] || PHASE_NAMES[phase] || titleCase(phase);
    const editorKey = PHASE_EDITOR_KEYS[phase];
    const editor = window.Editors?.[editorKey];

    // The skeleton was the editor-root's initial content; either an editor.render
    // call or renderPlaceholderEditor below will overwrite it. Either way, we
    // are no longer waiting on data — flip aria-busy off.
    els.editorRoot.setAttribute("aria-busy", "false");

    els.activePhaseKicker.textContent = t("builder.active_phase_eyebrow");
    els.activePhaseTitle.textContent = phaseName;
    if (els.addItemBtn) els.addItemBtn.hidden = true;

    if (editor && typeof editor.render === "function") {
      // 4th-arg context — game-break editors (Sentence Fill) use grade for
      // mode defaults, subject for AI-grader hints, tier for premium gating.
      const homework = window.BUILDER_STATE.homework || {};
      const context = {
        grade: typeof homework.grade === "number" ? homework.grade : 8,
        subject: homework.subject || "general",
        tier: homework.tier || (homework.mode === "hard" ? "premium" : "basic"),
      };
      editor.render(
        els.editorRoot,
        getPhaseData(phase),
        (nextData) => applyPhaseChange(phase, nextData),
        context
      );
    } else {
      renderPlaceholderEditor(phase);
    }

    // Boss-phase only: add a top-of-editor input for the dynamic boss name
    // (binds directly to content.boss_name; outside the boss_questions list).
    if (phase === "final_challenge") {
      mountBossNameField();
    }
  }

  function renderAll() {
    renderMeta();
    renderPhases();
    renderActiveEditor();
    refreshPreview();
  }

  function refreshPreview() {
    const homework = window.BUILDER_STATE.homework;
    if (!homework || !els.previewFrame || !previewVisible) return;

    els.previewFrame.src = `${API.getPreviewUrl(homework.id)}?t=${Date.now()}`;
  }

  function markDirty() {
    window.BUILDER_STATE.dirty = true;
    setSaveState(t("builder.unsaved_changes"), "dirty");

    // Show "Saving..." in the top-bar indicator as soon as changes land — the
    // actual PUT happens after the 500ms debounce in saveNow().
    const ind = document.getElementById("save-indicator");
    if (ind && ind.dataset.state !== "error" && ind.dataset.state !== "offline") {
      updateSaveState("saving");
    }

    window.clearTimeout(autosaveTimer);
    autosaveTimer = window.setTimeout(saveNow, 500);
  }

  async function saveNow() {
    const homework = window.BUILDER_STATE.homework;
    if (!homework) return;

    // If the browser says we're offline, don't even try — keep dirty, wait for "online".
    if (isOffline) {
      updateSaveState("offline");
      setSaveState(t("builder.offline_short"), "dirty");
      return;
    }

    window.clearTimeout(autosaveTimer);
    setSaveState(t("builder.saving"), "dirty");
    updateSaveState("saving");

    try {
      const putBody = {
        content_json: getContent(),
      };
      if (homework.title) putBody.title = homework.title;
      if (homework.status) putBody.status = homework.status;

      const updated = await API.updateHomework(homework.id, putBody);

      window.BUILDER_STATE.homework = {
        ...homework,
        ...updated,
        content_json: normalizeContent(updated.content_json || getContent(), updated),
      };
      window.BUILDER_STATE.dirty = false;

      // Clear retry state on success.
      retryCount = 0;
      if (retryTimer) {
        window.clearTimeout(retryTimer);
        retryTimer = null;
      }

      setSaveState(t("builder.saved"), "saved");
      updateSaveState("saved");
      renderMeta();
      refreshPreview();
    } catch (error) {
      setSaveState(t("builder.save_failed"), "error");
      updateSaveState("error", {
        attempt: retryCount + 1,
        maxAttempts: RETRY_DELAYS.length,
      });
      showToast(t("builder.toast_autosave_failed"), error.message, "error");
      scheduleRetry();
      throw error;
    }
  }

  function setActivePhase(phase) {
    const pipeline = getPipeline();
    if (!pipeline.includes(phase)) return;

    window.BUILDER_STATE.activePhase = phase;
    renderPhases();
    renderActiveEditor();
  }

  function togglePreview() {
    previewVisible = !previewVisible;
    els.previewPanel.classList.toggle("hidden", !previewVisible);
    els.builderContent.style.gridTemplateColumns = previewVisible ? "" : "1fr";
    els.togglePreviewBtn.textContent = previewVisible ? t("builder.hide_preview") : t("builder.show_preview");
    els.togglePreviewBtn.setAttribute("aria-pressed", String(previewVisible));

    if (previewVisible) refreshPreview();
  }

  // Skeleton minimum-display floor — keep the loading placeholders
  // visible for at least SKELETON_MIN_MS so a fast (cache-warm) /api/homeworks/:id
  // resolve does not flash the skeleton on/off in a single frame.
  const SKELETON_MIN_MS = 500;
  const _now = () => (typeof performance !== "undefined" && performance.now)
    ? performance.now()
    : Date.now();
  const _skeletonShownAt = _now();
  function waitSkeletonFloor() {
    const elapsed = _now() - _skeletonShownAt;
    if (elapsed >= SKELETON_MIN_MS) return Promise.resolve();
    return new Promise((r) => setTimeout(r, SKELETON_MIN_MS - elapsed));
  }

  async function loadHomework() {
    const id = getHomeworkId();

    if (!id) {
      els.editorRoot.innerHTML = `
        <div class="empty-state glass-card">
          <div class="empty-orb" aria-hidden="true">⚠️</div>
          <h3>${escapeHtml(t("builder.no_homework_id_h3"))}</h3>
          <p>${escapeHtml(t("builder.no_homework_id_text"))}</p>
          <a class="btn btn-primary" href="/index.html">${escapeHtml(t("builder.back_to_dashboard"))}</a>
        </div>
      `;
      return;
    }

    setSaveState(t("common.loading"), "");

    try {
      const homework = await API.getHomework(id);
      homework.content_json = normalizeContent(homework.content_json || {}, homework);

      window.BUILDER_STATE.homework = homework;
      window.BUILDER_STATE.activePhase = getPipeline()[0] || "preview";
      window.BUILDER_STATE.dirty = false;

      setSaveState(t("builder.loaded"), "saved");
      updateSaveState("saved");
      // Hold the skeleton at least SKELETON_MIN_MS before swapping in the
      // real editor so a fast load does not flash the layout.
      await waitSkeletonFloor();
      renderAll();
      checkMigrationStatus();
    } catch (error) {
      // Same floor on the failure path so the user does not see the
      // skeleton blink and then an error card jump in.
      await waitSkeletonFloor();
      els.editorRoot.innerHTML = `
        <div class="empty-state glass-card">
          <div class="empty-orb" aria-hidden="true">🧯</div>
          <h3>${escapeHtml(t("builder.could_not_load_h3"))}</h3>
          <p>${escapeHtml(error.message)}</p>
          <a class="btn btn-primary" href="/index.html">${escapeHtml(t("builder.back_to_dashboard"))}</a>
        </div>
      `;
      setSaveState(t("builder.load_failed"), "error");
      updateSaveState("error", { attempt: 1, maxAttempts: RETRY_DELAYS.length });
      showToast(t("builder.load_failed"), error.message, "error");
    }
  }

  function formatFixtureName(name) {
    return String(name || "")
      .split("-")
      .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
      .join(" ");
  }

  function renderFixtureList() {
    els.fixtureList.innerHTML = FIXTURE_NAMES.map(
      (name) => `
        <button class="fixture-card" type="button" data-fixture="${escapeHtml(name)}">
          <span class="fixture-name">${escapeHtml(formatFixtureName(name))}</span>
          <code>${escapeHtml(name)}.json</code>
        </button>
      `
    ).join("");
  }

  function openTemplateModal() {
    renderFixtureList();

    if (typeof els.templateModal.showModal === "function") {
      els.templateModal.showModal();
    } else {
      els.templateModal.setAttribute("open", "");
    }
  }

  function closeTemplateModal(force = false) {
    if (loadingTemplate && !force) return;

    if (typeof els.templateModal.close === "function") {
      els.templateModal.close();
    } else {
      els.templateModal.removeAttribute("open");
    }
  }

  async function fetchFixture(name) {
    const response = await fetch(`/api/fixtures/${encodeURIComponent(name)}`, {
      headers: { Accept: "application/json" },
    });

    if (!response.ok) {
      throw new Error(`Could not load fixture: ${name}`);
    }

    return response.json();
  }

  async function loadTemplate(name) {
    const homework = window.BUILDER_STATE.homework;
    if (!homework || loadingTemplate) return;

    loadingTemplate = true;
    setSaveState(t("builder.loading_template"), "dirty");

    els.fixtureList.querySelectorAll("button").forEach((button) => {
      button.disabled = true;
    });

    try {
      const fixture = await fetchFixture(name);
      const nextContent = fixture.content_json || fixture;

      homework.content_json = normalizeContent(nextContent, homework);
      window.BUILDER_STATE.homework = homework;
      window.BUILDER_STATE.dirty = true;

      renderAll();
      await saveNow();

      showToast(t("builder.toast_template_loaded"), `${name}.json`, "success");
      closeTemplateModal(true);
    } catch (error) {
      setSaveState(t("builder.template_load_failed"), "error");
      showToast(t("builder.template_load_failed"), error.message, "error");
    } finally {
      loadingTemplate = false;
      els.fixtureList.querySelectorAll("button").forEach((button) => {
        button.disabled = false;
      });
    }
  }

  // --- AI tutor smoke test ---
  async function runTutorSmokeTest() {
    const hw = window.BUILDER_STATE.homework || {};
    const subject = hw.subject || "math-algebra";
    const grade = hw.grade || 8;
    const baseBtn = els.testTutorBtn;
    if (baseBtn) { baseBtn.disabled = true; baseBtn.textContent = t("builder.testing"); }

    async function postJSON(path, body) {
      const t0 = performance.now();
      try {
        const res = await fetch(path, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(body),
        });
        const text = await res.text();
        let data; try { data = JSON.parse(text); } catch { data = { _raw: text.slice(0, 200) }; }
        const ms = Math.round(performance.now() - t0);
        return { ok: res.ok, status: res.status, ms, data };
      } catch (err) {
        return { ok: false, status: 0, ms: 0, data: { error: String(err) } };
      }
    }

    // 0) Backend status
    try {
      const statusRes = await fetch("/api/ai/status");
      const status = await statusRes.json();
      showToast(
        t("builder.toast_ai_backend"),
        `${status.backend || "?"} · ${status.model_fast || ""}${status.project ? " · " + status.project : ""}`,
        status.backend === "none" ? "error" : "success",
      );
    } catch (e) {
      showToast(t("builder.toast_ai_status_failed"), String(e), "error");
    }

    // 1) check-answer
    const r1 = await postJSON("/api/ai/check-answer", {
      question: "2+2 nechaga teng?",
      student_answer: "4",
      expected_answers: ["4"],
      subject, grade, tier: "EASY",
    });
    showToast(
      `check-answer ${r1.status} (${r1.ms}ms)`,
      r1.ok ? `correct=${r1.data.correct} · ${String(r1.data.feedback || "").slice(0, 80)}` : JSON.stringify(r1.data).slice(0, 120),
      r1.ok ? "success" : "error",
    );

    // 2) boss-turn
    const r2 = await postJSON("/api/ai/boss-turn", {
      boss_question: "x+3=10 bo'lsa x ga teng?",
      student_answer: "7",
      expected_answers: ["7"],
      damage_value: 20, hp_remaining: 100, attempt_number: 1,
      subject, grade,
    });
    showToast(
      `boss-turn ${r2.status} (${r2.ms}ms)`,
      r2.ok ? `dmg=${r2.data.damage_dealt} · ${String(r2.data.boss_response || "").slice(0, 80)}` : JSON.stringify(r2.data).slice(0, 120),
      r2.ok ? "success" : "error",
    );

    // 3) reflection
    const r3 = await postJSON("/api/ai/reflection", {
      homework_title: hw.title || "Test",
      homework_summary: subject,
      student_reflection: "Qiziqarli bo'ldi, lekin savollar qiyin edi.",
      performance: { correct: 6, total: 8, time_minutes: 22, weak_phase: "memory_sprint" },
      subject, grade,
    });
    showToast(
      `reflection ${r3.status} (${r3.ms}ms)`,
      r3.ok ? String(r3.data.feedback || "").slice(0, 100) : JSON.stringify(r3.data).slice(0, 120),
      r3.ok ? "success" : "error",
    );

    // 4) tutor
    const r4 = await postJSON("/api/ai/tutor", {
      phase: "real_life",
      question: "Qanday qilib chiziqli tenglamani yechish mumkin?",
      student_input: "Bilmayman",
      subject, grade,
    });
    showToast(
      `tutor ${r4.status} (${r4.ms}ms)`,
      r4.ok ? String(r4.data.response || "").slice(0, 100) : JSON.stringify(r4.data).slice(0, 120),
      r4.ok ? "success" : "error",
    );

    if (baseBtn) { baseBtn.disabled = false; baseBtn.textContent = t("builder.test_tutor"); }
  }

  function bindEvents() {
    els.phaseList.addEventListener("click", (event) => {
      const button = event.target.closest(".phase-btn");
      if (!button) return;
      setActivePhase(button.dataset.phase);
    });

    els.refreshBtn.addEventListener("click", loadHomework);
    els.togglePreviewBtn.addEventListener("click", togglePreview);
    els.loadTemplateBtn.addEventListener("click", openTemplateModal);
    els.closeTemplateModal.addEventListener("click", closeTemplateModal);
    els.cancelTemplate.addEventListener("click", closeTemplateModal);
    if (els.testTutorBtn) els.testTutorBtn.addEventListener("click", runTutorSmokeTest);
    if (els.migrateContentBtn) els.migrateContentBtn.addEventListener("click", migrateStoredContent);

    els.templateModal.addEventListener("click", (event) => {
      if (event.target === els.templateModal) closeTemplateModal();
    });

    els.fixtureList.addEventListener("click", (event) => {
      const button = event.target.closest("[data-fixture]");
      if (!button) return;
      loadTemplate(button.dataset.fixture);
    });

    window.addEventListener("beforeunload", (event) => {
      // Fire the keepalive PUT synchronously BEFORE returning — don't block nav.
      flushPendingSave();
      if (!window.BUILDER_STATE.dirty) return;
      event.preventDefault();
      event.returnValue = "";
    });

    // Mobile browsers (and some desktop cases) fire visibilitychange but not
    // beforeunload when the tab is backgrounded or killed. Catch that too.
    document.addEventListener("visibilitychange", () => {
      if (document.visibilityState === "hidden") {
        flushPendingSave();
      }
    });

    // Network transitions: reflect state and retry immediately when we recover.
    window.addEventListener("offline", () => {
      isOffline = true;
      updateSaveState("offline");
      setSaveState(t("builder.offline_short"), "dirty");
    });

    window.addEventListener("online", () => {
      isOffline = false;
      // Cancel any pending backoff and attempt an immediate save if dirty.
      if (retryTimer) {
        window.clearTimeout(retryTimer);
        retryTimer = null;
      }
      retryCount = 0;
      if (window.BUILDER_STATE && window.BUILDER_STATE.dirty) {
        saveNow().catch(() => {
          /* handled inside saveNow */
        });
      } else {
        updateSaveState("idle");
      }
    });
  }

  // ---------- Floating "Add X" button ----------
  // Follows the viewport so users with many items never need to scroll back
  // up to add another one. Watches the current editor panel for the primary
  // "Add X" button (first button whose class matches js-add-*) and proxies
  // clicks. Hides itself when no Add button exists in the phase.

  function findPrimaryAddButton() {
    const root = document.getElementById("editor-root");
    if (!root) return null;
    // Prefer a primary (blue) add button that's NOT inside a nested card.
    // Strategy: pick the first js-add-* button that isn't inside another
    // .editor-card.nested-card (those are per-item "Add X" buttons that
    // should NOT be shadowed globally).
    const candidates = Array.from(root.querySelectorAll('button[class*="js-add-"]'));
    for (const btn of candidates) {
      // Skip buttons nested inside a per-item card (they're item-local Add actions).
      const nested = btn.closest(".nested-card, [data-index], .flashcard-builder-card");
      // If the button's closest nested/item-card isn't the same as the direct
      // editor-list child, it's local to an item. Skip.
      if (nested) {
        // Check if this nested ancestor itself is the direct editor-list child.
        const list = btn.closest(".editor-list");
        if (list && nested.parentElement !== list) continue;
      }
      // Prefer a .btn-primary over .btn-ghost for the top-level add action.
      if (btn.classList.contains("btn-primary")) return btn;
    }
    // Fallback: first js-add-* we can find
    return candidates[0] || null;
  }

  // Per-phase i18n keys for the FAB short label (singular noun shown after "+").
  // Phases without a single primary "Add X" button (e.g. game_breaks with sub-tabs,
  // reflection) are absent — those fall back to the source-button text.
  const FAB_PHASE_I18N = {
    preview: "builder.fab_short_panel",
    flashcards: "builder.fab_short_card",
    memory_sprint: "builder.fab_short_question",
    reading: "builder.fab_short_checkpoint",
    real_life: "builder.fab_short_field",
    consolidation: "builder.fab_short_bullet",
    final_challenge: "builder.fab_short_boss_question",
  };

  function syncFab() {
    const fab = document.getElementById("fab-add");
    if (!fab) return;
    const target = findPrimaryAddButton();
    if (!target) {
      fab.hidden = true;
      fab.dataset.label = "";
      return;
    }
    // Prefer a per-phase i18n string so the FAB tracks language changes; fall
    // back to deriving from the source button text ("Add panel" -> "panel").
    const phase = window.BUILDER_STATE && window.BUILDER_STATE.activePhase;
    const i18nKey = FAB_PHASE_I18N[phase];
    let short = "";
    if (i18nKey) {
      const translated = t(i18nKey, "");
      if (translated && translated !== i18nKey) short = translated;
    }
    if (!short) {
      const raw = (target.textContent || "").trim();
      short = raw.replace(/^add\s*/i, "").trim() || t("builder.fab_add");
    }
    const labelEl = fab.querySelector(".fab-label");
    if (labelEl) labelEl.textContent = short;
    fab.hidden = false;
    fab.dataset.label = short;
  }

  function setupFab() {
    const fab = document.getElementById("fab-add");
    if (!fab) return;
    fab.addEventListener("click", () => {
      const target = findPrimaryAddButton();
      if (target) target.click();
      // After add, re-sync in case the DOM updated and the new button location moved.
      setTimeout(syncFab, 50);
    });
    // Watch editor-root for DOM mutations (phase switch, repaints) to keep FAB synced.
    const root = document.getElementById("editor-root");
    if (root && "MutationObserver" in window) {
      const obs = new MutationObserver(() => {
        // Debounce — repaints can fire many times in a row.
        clearTimeout(setupFab._rafTimer);
        setupFab._rafTimer = setTimeout(syncFab, 80);
      });
      obs.observe(root, { childList: true, subtree: true });
    }
    // Initial sync + on load
    syncFab();
  }

  async function init() {
    cacheElements();
    bindEvents();
    setupFab();
    // Seed the save indicator so it isn't blank on first paint.
    updateSaveState("idle");

    // Re-render dynamic content on language switch — static [data-i18n] attrs
    // are handled by i18n.js automatically, but the toggle-preview button text,
    // save indicator, and meta pills need a manual repaint.
    if (window.i18n && typeof window.i18n.onChange === "function") {
      window.i18n.onChange(() => {
        if (els.togglePreviewBtn) {
          els.togglePreviewBtn.textContent = previewVisible
            ? t("builder.hide_preview")
            : t("builder.show_preview");
        }
        // Refresh the indicator with the current state in the new language.
        const indicator = document.getElementById("save-indicator");
        const cur = (indicator && indicator.dataset.state) || "idle";
        updateSaveState(cur);
        if (window.BUILDER_STATE && window.BUILDER_STATE.homework) {
          renderMeta();
          renderPhases();
          renderActiveEditor();
        }
        syncFab();
      });
    }

    await loadSubjectsMeta();
    loadHomework();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
