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
    "real_life",
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
    return (window.BUILDER_STATE.meta && window.BUILDER_STATE.meta.phase_names) || PHASE_NAMES;
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

      if (["real_life", "reflection"].includes(key)) {
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
      textEl.textContent = "Saving...";
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
      textEl.textContent = `⚠ Save failed — retrying (${attempt}/${max})`;
    } else if (state === "offline") {
      textEl.textContent = "⚠ Offline — changes queued";
    } else {
      // "idle" — cleanest neutral state before first save.
      if (relativeTicker) {
        window.clearInterval(relativeTicker);
        relativeTicker = null;
      }
      textEl.textContent = window.BUILDER_STATE?.dirty ? "Unsaved" : "Idle";
    }
  }

  function updateRelativeTime() {
    if (!lastSavedAt) return;
    const el = document.querySelector("#save-indicator .save-text");
    if (!el) return;
    const secs = Math.floor((Date.now() - lastSavedAt) / 1000);
    if (secs < 5) el.textContent = "Saved";
    else if (secs < 60) el.textContent = `Saved ${secs}s ago`;
    else if (secs < 3600) el.textContent = `Saved ${Math.floor(secs / 60)}m ago`;
    else el.textContent = `Saved ${Math.floor(secs / 3600)}h ago`;
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
    banner.textContent =
      "⚠ Cannot save — check connection. Changes kept in memory — do NOT close this tab.";
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

  function renderMeta() {
    const homework = window.BUILDER_STATE.homework;
    if (!homework) return;

    const subject = getSubjectLabel(homework.subject);
    const status = homework.status || "draft";

    els.sidebarTitle.textContent = homework.title || "Untitled homework";
    els.builderTitle.textContent = homework.title || "Untitled homework";
    els.builderSubtitle.textContent = `${subject} · ${homework.grade}-sinf · ${titleCase(homework.mode)}`;

    els.sidebarMeta.innerHTML = `
      <span class="status-pill" data-status="${escapeHtml(status)}">
        <span class="status-dot ${escapeHtml(status)}"></span>
        ${escapeHtml(titleCase(status))}
      </span>
      <span class="mode-pill">${escapeHtml(titleCase(homework.mode))}</span>
      <span class="grade-pill">${escapeHtml(homework.grade)}-sinf</span>
    `;
  }

  function renderPhases() {
    const active = window.BUILDER_STATE.activePhase;
    const phases = getPipeline();
    const phaseNames = getPhaseNames();
    const phaseIcons = getPhaseIcons();

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
      };
    }

    if (phase === "real_life") return clone(content.real_life);
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
    } else if (phase === "real_life") {
      content.real_life = nextData || null;
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
      showToast("Not saved", `${phaseNames[phase] || PHASE_NAMES[phase] || phase} is not contract-backed yet.`, "warning");
      return;
    }

    markDirty();
  }

  function renderPlaceholderEditor(phase) {
    const data = getPhaseData(phase);
    const dataPreview = data === null ? "No contract-backed data key for this phase yet." : JSON.stringify(data, null, 2);
    const phaseNames = getPhaseNames();

    els.editorRoot.innerHTML = `
      <div class="editor-card">
        <div class="editor-header">
          <div>
            <p class="eyebrow">Wave 1 stub</p>
            <h3>${escapeHtml(phaseNames[phase] || PHASE_NAMES[phase] || titleCase(phase))}</h3>
          </div>
        </div>
        <p class="muted-text">
          Editor module for this phase will plug in here during Wave 2. Current data shape is shown below for contract checking.
        </p>
        <pre class="json-preview">${escapeHtml(dataPreview)}</pre>
      </div>
    `;
  }

  function renderActiveEditor() {
    const phase = window.BUILDER_STATE.activePhase;
    const phaseNames = getPhaseNames();
    const phaseName = phaseNames[phase] || PHASE_NAMES[phase] || titleCase(phase);
    const editorKey = PHASE_EDITOR_KEYS[phase];
    const editor = window.Editors?.[editorKey];

    els.activePhaseKicker.textContent = "Active phase";
    els.activePhaseTitle.textContent = phaseName;
    if (els.addItemBtn) els.addItemBtn.hidden = true;

    if (editor && typeof editor.render === "function") {
      editor.render(els.editorRoot, getPhaseData(phase), (nextData) => applyPhaseChange(phase, nextData));
    } else {
      renderPlaceholderEditor(phase);
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
    setSaveState("Unsaved changes", "dirty");

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
      setSaveState("Offline — queued", "dirty");
      return;
    }

    window.clearTimeout(autosaveTimer);
    setSaveState("Saving...", "dirty");
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

      setSaveState("Saved", "saved");
      updateSaveState("saved");
      renderMeta();
      refreshPreview();
    } catch (error) {
      setSaveState("Save failed", "error");
      updateSaveState("error", {
        attempt: retryCount + 1,
        maxAttempts: RETRY_DELAYS.length,
      });
      showToast("Autosave failed", error.message, "error");
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
    els.togglePreviewBtn.textContent = previewVisible ? "Hide preview" : "Show preview";
    els.togglePreviewBtn.setAttribute("aria-pressed", String(previewVisible));

    if (previewVisible) refreshPreview();
  }

  async function loadHomework() {
    const id = getHomeworkId();

    if (!id) {
      els.editorRoot.innerHTML = `
        <div class="empty-state glass-card">
          <div class="empty-orb" aria-hidden="true">⚠️</div>
          <h3>No homework ID</h3>
          <p>Open a homework from the dashboard so the builder receives ?id=HW-...</p>
          <a class="btn btn-primary" href="/index.html">Back to dashboard</a>
        </div>
      `;
      return;
    }

    setSaveState("Loading...", "");

    try {
      const homework = await API.getHomework(id);
      homework.content_json = normalizeContent(homework.content_json || {}, homework);

      window.BUILDER_STATE.homework = homework;
      window.BUILDER_STATE.activePhase = getPipeline()[0] || "preview";
      window.BUILDER_STATE.dirty = false;

      setSaveState("Loaded", "saved");
      updateSaveState("saved");
      renderAll();
    } catch (error) {
      els.editorRoot.innerHTML = `
        <div class="empty-state glass-card">
          <div class="empty-orb" aria-hidden="true">🧯</div>
          <h3>Could not load homework</h3>
          <p>${escapeHtml(error.message)}</p>
          <a class="btn btn-primary" href="/index.html">Back to dashboard</a>
        </div>
      `;
      setSaveState("Load failed", "error");
      updateSaveState("error", { attempt: 1, maxAttempts: RETRY_DELAYS.length });
      showToast("Load failed", error.message, "error");
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
    setSaveState("Loading template...", "dirty");

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

      showToast("Template loaded", `${name}.json was applied and saved.`, "success");
      closeTemplateModal(true);
    } catch (error) {
      setSaveState("Template load failed", "error");
      showToast("Template load failed", error.message, "error");
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
    if (baseBtn) { baseBtn.disabled = true; baseBtn.textContent = "Testing..."; }

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
        "AI backend",
        `${status.backend || "?"} · ${status.model_fast || ""}${status.project ? " · " + status.project : ""}`,
        status.backend === "none" ? "error" : "success",
      );
    } catch (e) {
      showToast("AI status failed", String(e), "error");
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

    if (baseBtn) { baseBtn.disabled = false; baseBtn.textContent = "Test Tutor"; }
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
      setSaveState("Offline — queued", "dirty");
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

  function syncFab() {
    const fab = document.getElementById("fab-add");
    if (!fab) return;
    const target = findPrimaryAddButton();
    if (!target) {
      fab.hidden = true;
      fab.dataset.label = "";
      return;
    }
    // Derive a short label from the target button text ("Add panel" -> "Panel").
    const raw = (target.textContent || "").trim();
    const short = raw.replace(/^add\s*/i, "").trim() || "Item";
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
    await loadSubjectsMeta();
    loadHomework();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
