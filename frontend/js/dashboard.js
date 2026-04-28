// frontend/js/dashboard.js
// NETS Builder dashboard: library grid, filters, create flow, trash, versions, duplicate.

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

  const SUBJECT_ICONS = {
    "math-algebra": "∑",
    "geometriya-g7-11": "△",
    physics: "⚛",
    biology: "🧬",
    "kimyo-g7-11": "⚗",
    english: "Aa",
    history: "🏛",
  };

  const DEFAULT_FAMILY_COLORS = {
    "aniq-fanlar": "#007AFF",
    "tabiy-fanlar": "#34C759",
    "til-fanlar": "#AF52DE",
    "ijtimoiy-fanlar": "#FF9500",
  };

  const POLL_INTERVAL_MS = 5000;
  const PAGE_SIZE = 50;

  const state = {
    subjects: [],
    families: { ...DEFAULT_FAMILY_COLORS },
    homeworks: [],
    trash: [],
    view: "library", // "library" | "trash"
    filters: {
      search: "",
      subject: "all",
      status: "all",
      mode: "all",
    },
    // Pagination + server-side search state
    offset: 0,
    total: 0,
    q: "",
    subject: "",
    grade: "",
    mode: "",
    loading: false,
    lastError: null,
    pollTimer: null,
    searchDebounceTimer: null,
    openMenuId: null,
  };

  const els = {};

  function $(id) {
    return document.getElementById(id);
  }

  function cacheElements() {
    Object.assign(els, {
      healthPill: $("health-pill"),
      healthLabel: $("health-label"),
      newHomeworkBtn: $("new-homework-btn"),
      emptyNewBtn: $("empty-new-btn"),
      refreshBtn: $("refresh-btn"),
      retryBtn: $("retry-btn"),
      searchInput: $("search-input"),
      subjectFilter: $("subject-filter"),
      statusFilter: $("status-filter"),
      modeFilter: $("mode-filter"),
      loadingState: $("loading-state"),
      emptyState: $("empty-state"),
      errorState: $("error-state"),
      errorStateTitle: $("error-state-title"),
      errorStateMessage: $("error-state-message"),
      homeworkGrid: $("homework-grid"),
      statTotal: $("stat-total"),
      statReady: $("stat-ready"),
      statDraft: $("stat-draft"),
      tabLibrary: $("tab-library"),
      tabTrash: $("tab-trash"),
      tabCountLibrary: $("tab-count-library"),
      tabCountTrash: $("tab-count-trash"),
      libraryTitle: $("library-title"),
      modal: $("create-modal"),
      form: $("create-form"),
      closeCreateModal: $("close-create-modal"),
      cancelCreate: $("cancel-create"),
      titleInput: $("homework-title"),
      subjectSelect: $("homework-subject"),
      gradeSelect: $("homework-grade"),
      modeSelect: $("homework-mode"),
      modeNote: $("mode-note"),
      submitCreate: $("submit-create"),
      versionsModal: $("versions-modal"),
      versionsList: $("versions-list"),
      versionsSubtitle: $("versions-subtitle"),
      closeVersionsModal: $("close-versions-modal"),
      closeVersionsBtn: $("close-versions-btn"),
      toastRegion: $("toast-region"),
      paginationBar: $("pagination-bar"),
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

  function normalize(value) {
    return String(value ?? "").trim().toLowerCase();
  }

  function getSubject(subjectId) {
    return state.subjects.find((subject) => subject.id === subjectId) || null;
  }

  function getSubjectLabel(subjectId) {
    return SUBJECT_LABELS[subjectId] || subjectId || "Unknown";
  }

  function getSubjectIcon(subjectId) {
    return SUBJECT_ICONS[subjectId] || "N";
  }

  function getFamilyColor(family) {
    return state.families[family] || DEFAULT_FAMILY_COLORS[family] || DEFAULT_FAMILY_COLORS["aniq-fanlar"];
  }

  function titleCase(value) {
    const clean = String(value || "").replaceAll("_", " ").replaceAll("-", " ");
    return clean.charAt(0).toUpperCase() + clean.slice(1);
  }

  function formatAbsolute(value) {
    if (!value) return "No date";
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return "No date";
    return new Intl.DateTimeFormat("uz-UZ", {
      year: "numeric",
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    }).format(date);
  }

  function formatRelative(value) {
    if (!value) return "never";
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return "never";
    const diffMs = Date.now() - date.getTime();
    const sec = Math.max(1, Math.round(diffMs / 1000));
    if (sec < 60) return `${sec}s ago`;
    const min = Math.round(sec / 60);
    if (min < 60) return `${min} minute${min === 1 ? "" : "s"} ago`;
    const hr = Math.round(min / 60);
    if (hr < 24) return `${hr} hour${hr === 1 ? "" : "s"} ago`;
    const day = Math.round(hr / 24);
    if (day < 30) return `${day} day${day === 1 ? "" : "s"} ago`;
    const mo = Math.round(day / 30);
    if (mo < 12) return `${mo} month${mo === 1 ? "" : "s"} ago`;
    const yr = Math.round(mo / 12);
    return `${yr} year${yr === 1 ? "" : "s"} ago`;
  }

  function setLoading(isLoading) {
    state.loading = isLoading;
    els.loadingState.classList.toggle("hidden", !isLoading);
    els.refreshBtn.disabled = isLoading;
    if (isLoading) {
      els.errorState.classList.add("hidden");
    }
  }

  function setHealth(status, label) {
    const dot = els.healthPill.querySelector(".status-dot");
    dot.className = `status-dot ${status}`;
    els.healthLabel.textContent = label;
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

  function renderStats() {
    const total = state.view === "library" ? state.total : state.homeworks.length;
    const ready = state.homeworks.filter((item) => item.status === "ready").length;
    const drafts = state.homeworks.filter((item) => item.status === "draft").length;

    els.statTotal.textContent = state.view === "library" ? state.total : state.homeworks.length;
    els.statReady.textContent = ready;
    els.statDraft.textContent = drafts;

    els.tabCountLibrary.textContent = state.total;
    els.tabCountTrash.textContent = state.trash.length;
  }

  function renderPaginationBar() {
    if (!els.paginationBar) return;
    const total = state.total;
    const limit = PAGE_SIZE;
    const offset = state.offset;

    if (total <= limit) {
      els.paginationBar.hidden = true;
      return;
    }

    els.paginationBar.hidden = false;
    const start = offset + 1;
    const end = Math.min(offset + limit, total);
    const hasPrev = offset > 0;
    const hasNext = offset + limit < total;

    els.paginationBar.innerHTML = `
      <button class="btn btn-ghost js-page-prev" type="button" ${hasPrev ? "" : "disabled"}>← Previous</button>
      <span class="pagination-label">Showing ${start}–${end} of ${total}</span>
      <button class="btn btn-ghost js-page-next" type="button" ${hasNext ? "" : "disabled"}>Next →</button>
    `;

    els.paginationBar.querySelector(".js-page-prev")?.addEventListener("click", () => {
      if (state.offset > 0) {
        state.offset = Math.max(0, state.offset - PAGE_SIZE);
        loadHomeworks();
      }
    });

    els.paginationBar.querySelector(".js-page-next")?.addEventListener("click", () => {
      if (state.offset + PAGE_SIZE < state.total) {
        state.offset += PAGE_SIZE;
        loadHomeworks();
      }
    });
  }

  function renderSubjectOptions() {
    const filterCurrent = els.subjectFilter.value || "all";
    const createCurrent = els.subjectSelect.value || "";

    els.subjectFilter.innerHTML = '<option value="all">All subjects</option>';
    els.subjectSelect.innerHTML = '<option value="" disabled selected>Select subject</option>';

    for (const subject of state.subjects) {
      const label = getSubjectLabel(subject.id);

      els.subjectFilter.insertAdjacentHTML(
        "beforeend",
        `<option value="${escapeHtml(subject.id)}">${escapeHtml(label)}</option>`
      );

      els.subjectSelect.insertAdjacentHTML(
        "beforeend",
        `<option value="${escapeHtml(subject.id)}">${escapeHtml(label)}</option>`
      );
    }

    els.subjectFilter.value = [...els.subjectFilter.options].some((option) => option.value === filterCurrent)
      ? filterCurrent
      : "all";

    els.subjectSelect.value = [...els.subjectSelect.options].some((option) => option.value === createCurrent)
      ? createCurrent
      : "";
  }

  function renderGradeOptions(subjectId) {
    const subject = getSubject(subjectId);
    els.gradeSelect.innerHTML = '<option value="" disabled selected>Select grade</option>';
    els.gradeSelect.disabled = !subject;

    if (!subject) return;

    for (const grade of subject.grades || []) {
      els.gradeSelect.insertAdjacentHTML("beforeend", `<option value="${grade}">${grade}-sinf</option>`);
    }
  }

  function applyModeRules(subjectId) {
    const subject = getSubject(subjectId);

    if (!subject) {
      els.modeSelect.disabled = false;
      els.modeSelect.value = "easy";
      els.modeNote.textContent = "Choose a subject to see available grades and mode rules.";
      return;
    }

    if (subject.always_hard) {
      els.modeSelect.value = "hard";
      els.modeSelect.disabled = true;
      els.modeNote.textContent = `${getSubjectLabel(subject.id)} is locked to Hard mode by contract.`;
      return;
    }

    els.modeSelect.disabled = false;
    els.modeNote.textContent = `${getSubjectLabel(subject.id)} supports Easy and Hard modes.`;
  }

  function getActiveList() {
    return state.view === "trash" ? state.trash : state.homeworks;
  }

  function getFilteredHomeworks() {
    const q = normalize(state.filters.search);
    const list = getActiveList();

    return list.filter((homework) => {
      const title = normalize(homework.title);
      const id = normalize(homework.id);
      const subjectId = normalize(homework.subject);
      const subjectLabel = normalize(getSubjectLabel(homework.subject));

      const matchesSearch = !q || title.includes(q) || id.includes(q) || subjectId.includes(q) || subjectLabel.includes(q);
      const matchesSubject = state.filters.subject === "all" || homework.subject === state.filters.subject;
      const matchesStatus = state.filters.status === "all" || homework.status === state.filters.status;
      const matchesMode = state.filters.mode === "all" || homework.mode === state.filters.mode;

      return matchesSearch && matchesSubject && matchesStatus && matchesMode;
    });
  }

  function openBuilder(id) {
    window.location.href = `/builder.html?id=${encodeURIComponent(id)}`;
  }

  function renderHomeworkCard(homework) {
    const familyColor = getFamilyColor(homework.family);
    const subjectLabel = getSubjectLabel(homework.subject);
    const subjectIcon = getSubjectIcon(homework.subject);
    const status = homework.status || "draft";
    const mode = homework.mode || "easy";
    const isTrash = state.view === "trash";
    const shareUrl = `/h/${encodeURIComponent(homework.id)}`;
    const updatedLabel = formatRelative(homework.updated_at || homework.created_at);
    const updatedAbs = formatAbsolute(homework.updated_at || homework.created_at);
    const deletedLabel = homework.deleted_at ? formatRelative(homework.deleted_at) : "";
    const menuOpen = state.openMenuId === homework.id ? "is-open" : "";

    const trashActions = `
      <div class="card-actions">
        <button class="btn btn-primary js-restore" type="button">Restore</button>
        <button class="btn btn-ghost danger js-hard-delete" type="button">Delete forever</button>
      </div>
    `;

    const liveActions = `
      <div class="card-actions">
        <button class="btn btn-primary js-open" type="button">Open</button>
        <div class="card-menu ${menuOpen}">
          <button class="icon-btn js-menu-toggle" type="button" title="More actions" aria-label="More actions" aria-expanded="${menuOpen ? "true" : "false"}">⋯</button>
          <div class="menu-dropdown" role="menu">
            <a class="menu-item" href="${escapeHtml(shareUrl)}" target="_blank" rel="noreferrer" role="menuitem">Open preview</a>
            <button class="menu-item js-duplicate" type="button" role="menuitem">Duplicate</button>
            <button class="menu-item js-versions" type="button" role="menuitem">Version history</button>
            <button class="menu-item danger js-delete" type="button" role="menuitem">Move to trash</button>
          </div>
        </div>
      </div>
    `;

    const metaLine = isTrash
      ? `Trashed ${escapeHtml(deletedLabel)}`
      : `Updated <span title="${escapeHtml(updatedAbs)}">${escapeHtml(updatedLabel)}</span>`;

    return `
      <article class="homework-card glass-card" style="--family-color: ${escapeHtml(familyColor)}" data-id="${escapeHtml(homework.id)}">
        <div class="homework-card-top">
          <div class="subject-icon" aria-hidden="true">${escapeHtml(subjectIcon)}</div>
          <span class="status-pill" data-status="${escapeHtml(status)}">
            <span class="status-dot ${escapeHtml(status)}"></span>
            ${escapeHtml(titleCase(status))}
          </span>
        </div>

        <div>
          <h3 class="homework-title">${escapeHtml(homework.title || "Untitled homework")}</h3>
          <p class="homework-id muted-text">${escapeHtml(homework.id || "")}</p>
        </div>

        <div class="homework-meta">
          <span>${escapeHtml(subjectLabel)} · ${escapeHtml(String(homework.grade))}-sinf</span>
          <span>${metaLine}</span>
        </div>

        <div class="pill-row">
          <span class="mode-pill" data-mode="${escapeHtml(mode)}">${escapeHtml(titleCase(mode))}</span>
          <span class="grade-pill">Grade ${escapeHtml(String(homework.grade))}</span>
        </div>

        ${isTrash ? trashActions : liveActions}
      </article>
    `;
  }

  function renderHomeworks() {
    const filtered = getFilteredHomeworks();
    renderStats();

    els.homeworkGrid.innerHTML = filtered.map(renderHomeworkCard).join("");

    const activeList = getActiveList();
    const hasAny = activeList.length > 0;
    const hasFiltered = filtered.length > 0;

    const showError = Boolean(state.lastError) && !state.loading;
    els.errorState.classList.toggle("hidden", !showError);

    els.emptyState.classList.toggle("hidden", showError || state.loading || hasFiltered);
    els.homeworkGrid.classList.toggle("hidden", showError || state.loading || !hasFiltered);

    const emptyHeading = els.emptyState.querySelector("h3");
    const emptyBody = els.emptyState.querySelector("p");
    const emptyBtn = els.emptyNewBtn;

    if (state.view === "trash") {
      if (!hasAny) {
        emptyHeading.textContent = "Trash is empty";
        emptyBody.textContent = "Deleted homeworks show up here and can be restored.";
        emptyBtn.hidden = true;
      } else if (!hasFiltered) {
        emptyHeading.textContent = "No matching trashed items";
        emptyBody.textContent = "Try clearing search or filters.";
        emptyBtn.hidden = true;
      }
    } else {
      emptyBtn.hidden = false;
      if (!hasAny && !state.loading) {
        emptyHeading.textContent = "No homework yet";
        emptyBody.textContent = "Create your first NETS homework to begin the builder flow.";
      } else if (hasAny && !hasFiltered && !state.loading) {
        emptyHeading.textContent = "No matching homework";
        emptyBody.textContent = "Try clearing search or filters.";
      }
    }
  }

  function setView(view) {
    state.view = view;
    state.openMenuId = null;

    els.tabLibrary.classList.toggle("is-active", view === "library");
    els.tabTrash.classList.toggle("is-active", view === "trash");
    els.tabLibrary.setAttribute("aria-selected", view === "library" ? "true" : "false");
    els.tabTrash.setAttribute("aria-selected", view === "trash" ? "true" : "false");

    els.libraryTitle.textContent = view === "trash" ? "Trash" : "Homeworks";
    renderHomeworks();
  }

  async function loadHealth() {
    try {
      const health = await API.getHealth();
      const geminiText = health.gemini ? "Gemini ready" : "Gemini off";
      setHealth(health.status === "ok" ? "ok" : "warn", `API ok · ${geminiText}`);
    } catch (error) {
      setHealth("error", "API offline");
    }
  }

  async function loadSubjects() {
    const payload = await API.getSubjects();
    state.subjects = Array.isArray(payload.subjects) ? payload.subjects : [];
    state.families = { ...DEFAULT_FAMILY_COLORS, ...(payload.families || {}) };
    renderSubjectOptions();
  }

  async function loadHomeworks() {
    setLoading(true);
    state.lastError = null;

    try {
      const searchParams = {};
      if (state.q)       searchParams.q = state.q;
      if (state.subject) searchParams.subject = state.subject;
      if (state.grade)   searchParams.grade = Number(state.grade);
      if (state.mode)    searchParams.mode = state.mode;
      searchParams.limit  = PAGE_SIZE;
      searchParams.offset = state.offset;

      const [listResult, trashResult] = await Promise.allSettled([
        API.getHomeworks(searchParams),
        API.listTrash(),
      ]);

      if (listResult.status === "fulfilled") {
        const payload = listResult.value || {};
        state.homeworks = Array.isArray(payload.items) ? payload.items : [];
        state.total = typeof payload.total === "number" ? payload.total : state.homeworks.length;
      } else {
        throw listResult.reason;
      }

      if (trashResult.status === "fulfilled") {
        const trashPayload = trashResult.value || {};
        state.trash = Array.isArray(trashPayload.items) ? trashPayload.items : [];
      } else {
        state.trash = [];
      }
    } catch (error) {
      state.lastError = error.message || "Unable to reach the API.";
      state.homeworks = [];
      state.total = 0;
      state.trash = [];
      els.errorStateMessage.textContent = state.lastError;
      showToast("Could not load library", state.lastError, "error");
    } finally {
      setLoading(false);
      renderHomeworks();
      renderPaginationBar();
      schedulePollIfNeeded();
    }
  }

  function schedulePollIfNeeded() {
    if (state.pollTimer) {
      window.clearTimeout(state.pollTimer);
      state.pollTimer = null;
    }

    const generating = state.homeworks.filter((hw) => hw.status === "generating");
    if (generating.length === 0) return;

    state.pollTimer = window.setTimeout(async () => {
      try {
        const results = await Promise.allSettled(
          generating.map((hw) => API.getHomework(hw.id))
        );
        let changed = false;
        for (const r of results) {
          if (r.status !== "fulfilled" || !r.value) continue;
          const idx = state.homeworks.findIndex((hw) => hw.id === r.value.id);
          if (idx === -1) continue;
          if (state.homeworks[idx].status !== r.value.status) changed = true;
          // Don't mutate content_json shape; just pull the status-relevant meta.
          state.homeworks[idx] = {
            ...state.homeworks[idx],
            status: r.value.status,
            updated_at: r.value.updated_at,
            title: r.value.title,
          };
        }
        if (changed) renderHomeworks();
      } catch (_) {
        /* ignore transient polling errors */
      } finally {
        schedulePollIfNeeded();
      }
    }, POLL_INTERVAL_MS);
  }

  function openCreateModal() {
    els.form.reset();
    els.gradeSelect.innerHTML = '<option value="" disabled selected>Select grade</option>';
    els.gradeSelect.disabled = true;
    applyModeRules("");

    if (typeof els.modal.showModal === "function") {
      els.modal.showModal();
    } else {
      els.modal.setAttribute("open", "");
    }

    window.setTimeout(() => els.titleInput.focus(), 40);
  }

  function closeCreateModal() {
    if (typeof els.modal.close === "function") {
      els.modal.close();
    } else {
      els.modal.removeAttribute("open");
    }
  }

  async function handleCreate(event) {
    event.preventDefault();

    const title = els.titleInput.value.trim();
    const subject = els.subjectSelect.value;
    const grade = Number(els.gradeSelect.value);
    const mode = els.modeSelect.value;

    if (!title || !subject || !grade || !mode) {
      showToast("Missing fields", "Fill title, subject, grade, and mode.", "warning");
      return;
    }

    els.submitCreate.disabled = true;
    els.submitCreate.textContent = "Creating...";

    try {
      const homework = await API.createHomework({ title, subject, grade, mode });
      showToast("Homework created", "Opening builder now.", "success");
      closeCreateModal();
      openBuilder(homework.id);
    } catch (error) {
      showToast("Could not create homework", error.message, "error");
    } finally {
      els.submitCreate.disabled = false;
      els.submitCreate.textContent = "Create and open";
    }
  }

  async function handleDelete(homeworkId) {
    const homework = state.homeworks.find((item) => item.id === homeworkId);
    const title = homework?.title || homeworkId;

    const confirmed = window.confirm(`Move "${title}" to trash?`);
    if (!confirmed) return;

    try {
      await API.deleteHomework(homeworkId);
      state.homeworks = state.homeworks.filter((item) => item.id !== homeworkId);
      if (homework) {
        state.trash = [{ ...homework, deleted_at: new Date().toISOString() }, ...state.trash];
      }
      renderHomeworks();
      showToast("Moved to trash", `"${title}" can be restored from Trash.`, "success");
    } catch (error) {
      showToast("Could not delete", error.message, "error");
    }
  }

  async function handleRestore(homeworkId) {
    const homework = state.trash.find((item) => item.id === homeworkId);
    const title = homework?.title || homeworkId;
    try {
      await API.restoreHomework(homeworkId);
      state.trash = state.trash.filter((item) => item.id !== homeworkId);
      if (homework) {
        const { deleted_at: _deleted, ...rest } = homework;
        state.homeworks = [rest, ...state.homeworks];
      }
      renderHomeworks();
      showToast("Restored", `"${title}" is back in the library.`, "success");
    } catch (error) {
      showToast("Could not restore", error.message, "error");
    }
  }

  async function handleHardDelete(homeworkId) {
    const homework = state.trash.find((item) => item.id === homeworkId);
    const title = homework?.title || homeworkId;
    const confirmed = window.confirm(`Permanently delete "${title}"? This wipes the homework and its version history. It cannot be undone.`);
    if (!confirmed) return;

    try {
      await API.hardDeleteHomework(homeworkId);
      state.trash = state.trash.filter((item) => item.id !== homeworkId);
      renderHomeworks();
      showToast("Deleted forever", `"${title}" has been permanently removed.`, "success");
    } catch (error) {
      showToast("Could not delete forever", error.message, "error");
    }
  }

  async function handleDuplicate(homeworkId) {
    const homework = state.homeworks.find((item) => item.id === homeworkId);
    const title = homework?.title || homeworkId;
    try {
      const copy = await API.duplicateHomework(homeworkId);
      state.homeworks = [copy, ...state.homeworks];
      renderHomeworks();
      showToast("Duplicated", `"${title}" cloned as a draft.`, "success");
    } catch (error) {
      showToast("Could not duplicate", error.message, "error");
    }
  }

  function openVersionsModal() {
    if (typeof els.versionsModal.showModal === "function") {
      els.versionsModal.showModal();
    } else {
      els.versionsModal.setAttribute("open", "");
    }
  }

  function closeVersionsModal() {
    if (typeof els.versionsModal.close === "function") {
      els.versionsModal.close();
    } else {
      els.versionsModal.removeAttribute("open");
    }
  }

  async function handleVersions(homeworkId) {
    els.versionsList.innerHTML = "";
    els.versionsSubtitle.textContent = "Loading versions...";
    openVersionsModal();

    try {
      const payload = await API.listVersions(homeworkId);
      const versions = Array.isArray(payload.versions) ? payload.versions : [];
      if (!versions.length) {
        els.versionsSubtitle.textContent = "No snapshots yet. Versions are captured automatically as you edit.";
        els.versionsList.innerHTML = "";
        return;
      }
      els.versionsSubtitle.textContent = `${versions.length} snapshot${versions.length === 1 ? "" : "s"} for ${homeworkId}. Newest first.`;
      els.versionsList.innerHTML = versions
        .map((v) => `
          <div class="version-row" data-version-id="${escapeHtml(String(v.id))}" data-homework-id="${escapeHtml(homeworkId)}">
            <div class="version-meta">
              <strong>${escapeHtml(v.title || "Untitled")}</strong>
              <span class="muted-text" title="${escapeHtml(formatAbsolute(v.saved_at))}">
                Saved ${escapeHtml(formatRelative(v.saved_at))} · ${escapeHtml(String(v.size_bytes || 0))} bytes
              </span>
            </div>
            <button class="btn btn-ghost js-version-restore" type="button">Restore this version</button>
          </div>
        `)
        .join("");
    } catch (error) {
      els.versionsSubtitle.textContent = `Failed to load versions: ${error.message}`;
      els.versionsList.innerHTML = "";
    }
  }

  async function handleVersionRestore(homeworkId, versionId) {
    const confirmed = window.confirm(`Restore this version? Your current content will be saved as a snapshot before being overwritten.`);
    if (!confirmed) return;
    try {
      await API.restoreVersion(homeworkId, versionId);
      showToast("Version restored", "Homework reverted to the selected snapshot.", "success");
      closeVersionsModal();
      await loadHomeworks();
    } catch (error) {
      showToast("Could not restore version", error.message, "error");
    }
  }

  function toggleCardMenu(homeworkId) {
    state.openMenuId = state.openMenuId === homeworkId ? null : homeworkId;
    renderHomeworks();
  }

  function closeAllMenus() {
    if (state.openMenuId !== null) {
      state.openMenuId = null;
      renderHomeworks();
    }
  }

  function bindEvents() {
    els.newHomeworkBtn.addEventListener("click", openCreateModal);
    els.emptyNewBtn.addEventListener("click", openCreateModal);
    els.closeCreateModal.addEventListener("click", closeCreateModal);
    els.cancelCreate.addEventListener("click", closeCreateModal);
    els.refreshBtn.addEventListener("click", loadHomeworks);
    els.retryBtn.addEventListener("click", loadHomeworks);
    els.form.addEventListener("submit", handleCreate);
    els.closeVersionsModal.addEventListener("click", closeVersionsModal);
    els.closeVersionsBtn.addEventListener("click", closeVersionsModal);

    els.tabLibrary.addEventListener("click", () => setView("library"));
    els.tabTrash.addEventListener("click", () => setView("trash"));

    els.modal.addEventListener("click", (event) => {
      if (event.target === els.modal) closeCreateModal();
    });

    els.versionsModal.addEventListener("click", (event) => {
      if (event.target === els.versionsModal) closeVersionsModal();
    });

    els.subjectSelect.addEventListener("change", () => {
      renderGradeOptions(els.subjectSelect.value);
      applyModeRules(els.subjectSelect.value);
    });

    els.searchInput.addEventListener("input", () => {
      // Keep local filter in sync (used by getFilteredHomeworks for trash view)
      state.filters.search = els.searchInput.value;
      // Debounced server-side search — reset offset on new query
      if (state.searchDebounceTimer) window.clearTimeout(state.searchDebounceTimer);
      state.searchDebounceTimer = window.setTimeout(() => {
        state.q = els.searchInput.value.trim();
        state.offset = 0;
        if (state.view === "library") loadHomeworks();
        else renderHomeworks();
      }, 300);
    });

    els.subjectFilter.addEventListener("change", () => {
      state.filters.subject = els.subjectFilter.value;
      // Map "all" to empty string for server-side filter
      state.subject = els.subjectFilter.value === "all" ? "" : els.subjectFilter.value;
      state.offset = 0;
      if (state.view === "library") loadHomeworks();
      else renderHomeworks();
    });

    els.statusFilter.addEventListener("change", () => {
      state.filters.status = els.statusFilter.value;
      renderHomeworks();
    });

    els.modeFilter.addEventListener("change", () => {
      state.filters.mode = els.modeFilter.value;
      // Map "all" to empty string for server-side filter
      state.mode = els.modeFilter.value === "all" ? "" : els.modeFilter.value;
      state.offset = 0;
      if (state.view === "library") loadHomeworks();
      else renderHomeworks();
    });

    els.homeworkGrid.addEventListener("click", (event) => {
      const card = event.target.closest(".homework-card");
      if (!card) return;
      const id = card.dataset.id;

      if (event.target.closest(".js-menu-toggle")) {
        event.stopPropagation();
        toggleCardMenu(id);
        return;
      }

      if (event.target.closest(".js-delete")) {
        handleDelete(id);
        return;
      }

      if (event.target.closest(".js-duplicate")) {
        handleDuplicate(id);
        return;
      }

      if (event.target.closest(".js-versions")) {
        handleVersions(id);
        return;
      }

      if (event.target.closest(".js-restore")) {
        handleRestore(id);
        return;
      }

      if (event.target.closest(".js-hard-delete")) {
        handleHardDelete(id);
        return;
      }

      if (event.target.closest(".js-open")) {
        openBuilder(id);
        return;
      }

      // Clicking inside a menu-dropdown link (Open preview <a>) — let the default handler run.
      if (event.target.closest(".menu-dropdown a")) {
        return;
      }
    });

    els.versionsList.addEventListener("click", (event) => {
      const btn = event.target.closest(".js-version-restore");
      if (!btn) return;
      const row = btn.closest(".version-row");
      if (!row) return;
      const homeworkId = row.dataset.homeworkId;
      const versionId = row.dataset.versionId;
      handleVersionRestore(homeworkId, versionId);
    });

    document.addEventListener("click", (event) => {
      if (!event.target.closest(".card-menu")) {
        closeAllMenus();
      }
    });
  }

  async function init() {
    cacheElements();
    bindEvents();
    setLoading(true);

    await Promise.allSettled([loadHealth(), loadSubjects()]);
    await loadHomeworks();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
