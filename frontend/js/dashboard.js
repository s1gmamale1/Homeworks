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
    history: "T",
  };

  // Map subject_id → family. If a subject has explicit `family` from API, that wins
  // (see _subjectFamily). This switch is the fallback / hard-coded assignment.
  const SUBJECT_FAMILY_MAP = {
    "math-algebra": "aniq-fanlar",
    "geometriya-g7-11": "aniq-fanlar",
    physics: "aniq-fanlar",
    biology: "tabiy-fanlar",
    "kimyo-g7-11": "tabiy-fanlar",
    english: "til-fanlar",
    russian: "til-fanlar",
    uzbek: "til-fanlar",
    literature: "til-fanlar",
    history: "ijtimoiy-fanlar",
    social: "ijtimoiy-fanlar",
  };

  // Inline SVG icon library (path strings). Mirrors the JSX prototype.
  const ICON_PATHS = {
    plus:     "M12 5v14M5 12h14",
    search:   "M21 21l-4.3-4.3M10.8 18a7.2 7.2 0 1 1 0-14.4 7.2 7.2 0 0 1 0 14.4Z",
    refresh:  "M20 6v5h-5M4 18v-5h5M19 11a7 7 0 0 0-12.2-4.7L4 9m1 4a7 7 0 0 0 12.2 4.7L20 15",
    library:  "M4 19.5A2.5 2.5 0 0 1 6.5 17H20M4 4.5A2.5 2.5 0 0 1 6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15Z",
    trash:    "M3 6h18M8 6V4h8v2m-9 0 1 15h8l1-15M10 11v6M14 11v6",
    sparkles: "M12 2l1.6 5.2L19 9l-5.4 1.8L12 16l-1.6-5.2L5 9l5.4-1.8L12 2Zm7 12 .8 2.6L22 17l-2.2.4L19 20l-.8-2.6L16 17l2.2-.4L19 14Z",
    arrow:    "M5 12h14M13 5l7 7-7 7",
    copy:     "M8 8h12v12H8zM4 4h12v12",
    eye:      "M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12Zm10 3a3 3 0 1 0 0-6 3 3 0 0 0 0 6Z",
    magic:    "M15 4l5 5M14 5l5 5M4 20 18 6M5 5l1 2 2 1-2 1-1 2-1-2-2-1 2-1 1-2Z",
    check:    "M20 6 9 17l-5-5",
    clock:    "M12 7v5l3 2M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z",
    alert:    "M12 9v4m0 4h.01M10.3 3.9 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0Z",
    grid:     "M4 4h7v7H4zM13 4h7v7h-7zM4 13h7v7H4zM13 13h7v7h-7z",
    more:     "M5 12h.01M12 12h.01M19 12h.01",
  };

  function _iconSvg(name, sizeClass) {
    const d = ICON_PATHS[name] || ICON_PATHS.plus;
    const cls = sizeClass ? `dash-icon ${sizeClass}` : "dash-icon";
    return `<svg class="${cls}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="${d}"/></svg>`;
  }

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

  // i18n helper — falls back to the literal string if i18n hasn't loaded yet.
  function t(key, fallback) {
    if (window.i18n && typeof window.i18n.t === "function") {
      return window.i18n.t(key, fallback);
    }
    return fallback != null ? fallback : key;
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
      statReview: $("stat-review"),
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
    return SUBJECT_LABELS[subjectId] || subjectId || "—";
  }

  function getSubjectIcon(subjectId) {
    return SUBJECT_ICONS[subjectId] || "N";
  }

  function getFamilyColor(family) {
    return state.families[family] || DEFAULT_FAMILY_COLORS[family] || DEFAULT_FAMILY_COLORS["aniq-fanlar"];
  }

  // _subjectFamily — derive family slug from a subject_id. If the API surfaced
  // an explicit family on the subject record, prefer that; otherwise fall back
  // to the static SUBJECT_FAMILY_MAP. Defaults to "aniq-fanlar".
  function _subjectFamily(subjectId) {
    const subject = getSubject(subjectId);
    if (subject && subject.family) return subject.family;
    return SUBJECT_FAMILY_MAP[subjectId] || "aniq-fanlar";
  }

  // _subjectIconChar — single glyph that gets rendered inside the gradient
  // header symbol-tile. Mirrors JSX iconography (Σ, △, ⚛, Aa, ⚗, T, …).
  function _subjectIconChar(subjectId) {
    return SUBJECT_ICONS[subjectId] || "N";
  }

  // _subjectGradient — vanilla CSS gradient string per family. Kept here so
  // the renderer can drive inline styles when a per-card override is needed,
  // but the primary rule is data-family attribute → CSS variable in dashboard.css.
  function _subjectGradient(family) {
    switch (family) {
      case "tabiy-fanlar":    return "linear-gradient(135deg, #10b981 0%, #5eead4 100%)";
      case "til-fanlar":      return "linear-gradient(135deg, #d946ef 0%, #a78bfa 100%)";
      case "ijtimoiy-fanlar": return "linear-gradient(135deg, #f59e0b 0%, #fdba74 100%)";
      case "aniq-fanlar":
      default:                return "linear-gradient(135deg, #3b82f6 0%, #22d3ee 100%)";
    }
  }

  // _relativeTime — Intl.RelativeTimeFormat-driven phrase using the live i18n lang.
  // Returns "2 min ago" / "1 hour ago" / "Yesterday" etc. Falls back to formatRelative.
  function _relativeTime(iso) {
    if (!iso) return "—";
    const date = new Date(iso);
    if (Number.isNaN(date.getTime())) return "—";

    const lang = (window.i18n && typeof window.i18n.getLang === "function" && window.i18n.getLang())
      || document.documentElement.lang
      || "en";
    const localeMap = { uz: "uz", ru: "ru", en: "en" };
    const locale = localeMap[lang] || "en";

    let rtf;
    try {
      rtf = new Intl.RelativeTimeFormat(locale, { numeric: "auto" });
    } catch (_e) {
      return formatRelative(iso);
    }

    const diffSec = Math.round((date.getTime() - Date.now()) / 1000);
    const abs = Math.abs(diffSec);
    if (abs < 60)        return rtf.format(Math.round(diffSec), "second");
    if (abs < 3600)      return rtf.format(Math.round(diffSec / 60), "minute");
    if (abs < 86400)     return rtf.format(Math.round(diffSec / 3600), "hour");
    if (abs < 86400 * 7) return rtf.format(Math.round(diffSec / 86400), "day");
    if (abs < 86400 * 30)return rtf.format(Math.round(diffSec / (86400 * 7)), "week");
    if (abs < 86400 * 365)return rtf.format(Math.round(diffSec / (86400 * 30)), "month");
    return rtf.format(Math.round(diffSec / (86400 * 365)), "year");
  }

  // _progressFromStatus — derive 0..100 progress for the card progress-bar.
  function _progressFromStatus(item) {
    if (!item) return 0;
    if (item.status === "ready") return 100;
    if (typeof item.progress === "number" && item.progress >= 0 && item.progress <= 100) {
      return Math.round(item.progress);
    }
    switch (item.status) {
      case "generating": return 50;
      case "draft":      return 35;
      case "error":      return 20;
      default:           return 0;
    }
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
    const ready = state.homeworks.filter((item) => item.status === "ready").length;
    const drafts = state.homeworks.filter((item) => item.status === "draft").length;
    const review = state.homeworks.filter(
      (item) => item.status === "error" || item.status === "generating"
    ).length;

    els.statTotal.textContent = state.view === "library" ? state.total : state.homeworks.length;
    els.statReady.textContent = ready;
    els.statDraft.textContent = drafts;
    if (els.statReview) els.statReview.textContent = review;

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
      <button class="btn btn-ghost js-page-prev" type="button" ${hasPrev ? "" : "disabled"}>← ${escapeHtml(t("common.previous"))}</button>
      <span class="pagination-label">${start}–${end} / ${total}</span>
      <button class="btn btn-ghost js-page-next" type="button" ${hasNext ? "" : "disabled"}>${escapeHtml(t("common.next"))} →</button>
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

    els.subjectFilter.innerHTML = `<option value="all">${escapeHtml(t("dashboard.all_subjects"))}</option>`;
    els.subjectSelect.innerHTML = `<option value="" disabled selected>${escapeHtml(t("dashboard.select_subject"))}</option>`;

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
    els.gradeSelect.innerHTML = `<option value="" disabled selected>${escapeHtml(t("dashboard.select_grade"))}</option>`;
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
      els.modeNote.textContent = t("dashboard.mode_note_default");
      return;
    }

    if (subject.always_hard) {
      els.modeSelect.value = "hard";
      els.modeSelect.disabled = true;
      els.modeNote.textContent = `${getSubjectLabel(subject.id)} → ${t("common.hard")}`;
      return;
    }

    els.modeSelect.disabled = false;
    els.modeNote.textContent = `${getSubjectLabel(subject.id)}: ${t("common.easy")} / ${t("common.hard")}`;
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
    const subjectIconChar = _subjectIconChar(homework.subject);
    const family = _subjectFamily(homework.subject);
    const status = homework.status || "draft";
    const mode = homework.mode || "easy";
    const isTrash = state.view === "trash";
    const shareUrl = `/h/${encodeURIComponent(homework.id)}`;
    const updatedAbs = formatAbsolute(homework.updated_at || homework.created_at);
    const updatedLabel = _relativeTime(homework.updated_at || homework.created_at);
    const deletedLabel = homework.deleted_at ? _relativeTime(homework.deleted_at) : "";
    const menuOpen = state.openMenuId === homework.id ? "is-open" : "";
    const progress = _progressFromStatus(homework);
    const modeLabel = mode === "hard" ? t("common.hard") : t("common.easy");
    const previewLabel = t("dashboard.card_preview", "Preview");
    const openLabel = t("dashboard.card_open");
    const moreActionsLabel = t("dashboard.card_more_actions");

    // Trash mode: keep restore/hard-delete affordances, but render them as
    // the same hw-action pair so the card silhouette stays consistent.
    const trashActions = `
      <div class="hw-actions">
        <button class="hw-action js-restore" type="button" title="${escapeHtml(t("dashboard.card_restore"))}" aria-label="${escapeHtml(t("dashboard.card_restore"))}">${_iconSvg("refresh", "dash-icon--md")}</button>
        <button class="hw-action hw-action--primary js-hard-delete" type="button" title="${escapeHtml(t("dashboard.card_delete_forever"))}" aria-label="${escapeHtml(t("dashboard.card_delete_forever"))}">${_iconSvg("trash", "dash-icon--md")}</button>
      </div>
    `;

    const liveActions = `
      <div class="hw-actions">
        <a class="hw-action" href="${escapeHtml(shareUrl)}" target="_blank" rel="noreferrer" title="${escapeHtml(previewLabel)}" aria-label="${escapeHtml(previewLabel)}">${_iconSvg("eye", "dash-icon--md")}</a>
        <button class="hw-action hw-action--primary js-open" type="button" title="${escapeHtml(openLabel)}" aria-label="${escapeHtml(openLabel)}">${_iconSvg("arrow", "dash-icon--md")}</button>
        <div class="hw-card-menu card-menu ${menuOpen}">
          <button class="hw-action js-menu-toggle" type="button" title="${escapeHtml(moreActionsLabel)}" aria-label="${escapeHtml(moreActionsLabel)}" aria-expanded="${menuOpen ? "true" : "false"}">${_iconSvg("more", "dash-icon--md")}</button>
          <div class="menu-dropdown" role="menu">
            <a class="menu-item" href="${escapeHtml(shareUrl)}" target="_blank" rel="noreferrer" role="menuitem">${escapeHtml(t("dashboard.menu_open_preview"))}</a>
            <button class="menu-item js-duplicate" type="button" role="menuitem">${escapeHtml(t("dashboard.menu_duplicate"))}</button>
            <button class="menu-item js-versions" type="button" role="menuitem">${escapeHtml(t("dashboard.menu_versions"))}</button>
            <button class="menu-item danger js-delete" type="button" role="menuitem">${escapeHtml(t("dashboard.menu_move_to_trash"))}</button>
          </div>
        </div>
      </div>
    `;

    const updatedDisplay = isTrash
      ? `<span class="hw-updated">${escapeHtml(deletedLabel)}</span>`
      : `<span class="hw-updated" title="${escapeHtml(updatedAbs)}">${escapeHtml(t("dashboard.card_updated", "Updated"))} ${escapeHtml(updatedLabel)}</span>`;

    return `
      <article class="hw-card homework-card glass-card"
               style="--family-color: ${escapeHtml(familyColor)}"
               data-id="${escapeHtml(homework.id)}"
               data-family="${escapeHtml(family)}"
               data-subject="${escapeHtml(homework.subject || "")}">
        <div class="hw-card-header" aria-hidden="false">
          <div class="hw-card-header-top">
            <div class="hw-symbol" aria-hidden="true">${escapeHtml(subjectIconChar)}</div>
            <span class="hw-grade-badge">${escapeHtml(String(homework.grade))}-sinf</span>
          </div>
          <div class="hw-card-header-titleblock">
            <p class="hw-card-subject">${escapeHtml(subjectLabel)}</p>
            <h3 class="hw-card-title">${escapeHtml(homework.title || t("dashboard.untitled"))}</h3>
          </div>
        </div>

        <div class="hw-card-body">
          <div class="hw-pill-row">
            <span class="hw-status status-pill" data-status="${escapeHtml(status)}">${escapeHtml(titleCase(status))}</span>
            <span class="hw-mode" data-mode="${escapeHtml(mode)}">${escapeHtml(modeLabel)}</span>
          </div>

          <div class="hw-progress" aria-hidden="true">
            <div class="hw-progress-head">
              <span>${escapeHtml(t("dashboard.card_progress", "Progress"))}</span>
              <span>${progress}%</span>
            </div>
            <div class="hw-progress-track">
              <div class="hw-progress-fill" style="width: ${progress}%"></div>
            </div>
          </div>

          <div class="hw-foot">
            ${updatedDisplay}
            ${isTrash ? trashActions : liveActions}
          </div>
        </div>
      </article>
    `;
  }

  // Lazy-init IntersectionObserver that reveals .hw-card / .dash-stat-card with
  // an Apple-spring opacity+translate stagger. Cards begin opacity:0 in CSS so
  // the observer's `is-visible` flip is the trigger.
  let _cardObserver = null;
  function _ensureCardObserver() {
    if (_cardObserver || typeof IntersectionObserver === "undefined") return _cardObserver;
    _cardObserver = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting) {
            entry.target.classList.add("is-visible");
            _cardObserver.unobserve(entry.target);
          }
        }
      },
      { threshold: 0.1, rootMargin: "0px 0px -40px 0px" }
    );
    return _cardObserver;
  }

  function _observeReveals(root) {
    const obs = _ensureCardObserver();
    if (!obs) {
      // Reduced motion / unsupported — flip everything visible immediately.
      (root || document).querySelectorAll(".hw-card, .dash-stat-card").forEach((el) => {
        el.classList.add("is-visible");
      });
      return;
    }
    (root || document).querySelectorAll(".hw-card:not(.is-visible), .dash-stat-card:not(.is-visible)")
      .forEach((el) => obs.observe(el));
  }

  function renderHomeworks() {
    const filtered = getFilteredHomeworks();
    renderStats();

    els.homeworkGrid.innerHTML = filtered.map(renderHomeworkCard).join("");
    _observeReveals(els.homeworkGrid);

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
        emptyHeading.textContent = t("dashboard.empty_trash_h3");
        emptyBody.textContent = t("dashboard.empty_trash_text");
        emptyBtn.hidden = true;
      } else if (!hasFiltered) {
        emptyHeading.textContent = t("dashboard.empty_no_match_trash_h3");
        emptyBody.textContent = t("dashboard.empty_no_match_text");
        emptyBtn.hidden = true;
      }
    } else {
      emptyBtn.hidden = false;
      if (!hasAny && !state.loading) {
        emptyHeading.textContent = t("dashboard.empty_h3");
        emptyBody.textContent = t("dashboard.empty_text");
      } else if (hasAny && !hasFiltered && !state.loading) {
        emptyHeading.textContent = t("dashboard.empty_no_match_h3");
        emptyBody.textContent = t("dashboard.empty_no_match_text");
      }
    }
  }

  function setView(view) {
    const apply = () => {
      state.view = view;
      state.openMenuId = null;

      els.tabLibrary.classList.toggle("is-active", view === "library");
      els.tabTrash.classList.toggle("is-active", view === "trash");
      els.tabLibrary.setAttribute("aria-selected", view === "library" ? "true" : "false");
      els.tabTrash.setAttribute("aria-selected", view === "trash" ? "true" : "false");

      els.libraryTitle.textContent = view === "trash" ? t("dashboard.tab_trash") : t("dashboard.lib_h2");
      renderHomeworks();
    };

    // Smooth tab swap via View Transitions API where supported (Chromium 111+).
    if (typeof document.startViewTransition === "function") {
      document.startViewTransition(apply);
    } else {
      apply();
    }
  }

  async function loadHealth() {
    try {
      const [health, aiStatus] = await Promise.all([
        API.getHealth(),
        API.getAiStatus(),
      ]);

      const PROVIDER_LABEL = {
        kimi: 'Kimi',
        vertex: 'Vertex',
        gemini_api: 'Gemini',
      };

      const provider = aiStatus?.active_provider || 'none';
      const label = PROVIDER_LABEL[provider] || 'AI';
      const aiReady = aiStatus?.ai_ready !== false && provider !== 'none';
      const statusText = aiReady ? `API ok · ${label} ready` : t("dashboard.health_api_down");
      setHealth(aiReady ? 'ok' : 'error', statusText);
    } catch (error) {
      setHealth("error", t("dashboard.health_offline"));
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
      showToast(t("dashboard.toast_could_not_load"), state.lastError, "error");
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
    els.gradeSelect.innerHTML = `<option value="" disabled selected>${escapeHtml(t("dashboard.select_grade"))}</option>`;
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
      showToast(t("dashboard.toast_missing_fields"), t("dashboard.toast_missing_fields_msg"), "warning");
      return;
    }

    els.submitCreate.disabled = true;
    els.submitCreate.textContent = t("dashboard.creating");

    try {
      const homework = await API.createHomework({ title, subject, grade, mode });
      showToast(t("dashboard.toast_homework_created"), t("dashboard.toast_opening_builder"), "success");
      closeCreateModal();
      openBuilder(homework.id);
    } catch (error) {
      showToast(t("dashboard.toast_could_not_create"), error.message, "error");
    } finally {
      els.submitCreate.disabled = false;
      els.submitCreate.textContent = t("dashboard.create_and_open");
    }
  }

  async function handleDelete(homeworkId) {
    const homework = state.homeworks.find((item) => item.id === homeworkId);
    const title = homework?.title || homeworkId;

    const confirmed = window.confirm(`"${title}" — ${t("dashboard.confirm_trash")}`);
    if (!confirmed) return;

    try {
      await API.deleteHomework(homeworkId);
      state.homeworks = state.homeworks.filter((item) => item.id !== homeworkId);
      if (homework) {
        state.trash = [{ ...homework, deleted_at: new Date().toISOString() }, ...state.trash];
      }
      renderHomeworks();
      showToast(t("dashboard.toast_moved_to_trash"), `"${title}" → ${t("dashboard.tab_trash")}`, "success");
    } catch (error) {
      showToast(t("dashboard.toast_could_not_delete"), error.message, "error");
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
      showToast(t("dashboard.toast_restored"), `"${title}" → ${t("common.library")}`, "success");
    } catch (error) {
      showToast(t("dashboard.toast_could_not_restore"), error.message, "error");
    }
  }

  async function handleHardDelete(homeworkId) {
    const homework = state.trash.find((item) => item.id === homeworkId);
    const title = homework?.title || homeworkId;
    const confirmed = window.confirm(`"${title}" — ${t("dashboard.confirm_hard_delete")}`);
    if (!confirmed) return;

    try {
      await API.hardDeleteHomework(homeworkId);
      state.trash = state.trash.filter((item) => item.id !== homeworkId);
      renderHomeworks();
      showToast(t("dashboard.toast_deleted_forever"), `"${title}"`, "success");
    } catch (error) {
      showToast(t("dashboard.toast_could_not_delete_forever"), error.message, "error");
    }
  }

  async function handleDuplicate(homeworkId) {
    const homework = state.homeworks.find((item) => item.id === homeworkId);
    const title = homework?.title || homeworkId;
    try {
      const copy = await API.duplicateHomework(homeworkId);
      state.homeworks = [copy, ...state.homeworks];
      renderHomeworks();
      showToast(t("dashboard.toast_duplicated"), `"${title}" → ${t("common.draft")}`, "success");
    } catch (error) {
      showToast(t("dashboard.toast_could_not_duplicate"), error.message, "error");
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
    els.versionsSubtitle.textContent = t("dashboard.versions_loading");
    openVersionsModal();

    try {
      const payload = await API.listVersions(homeworkId);
      const versions = Array.isArray(payload.versions) ? payload.versions : [];
      if (!versions.length) {
        els.versionsSubtitle.textContent = t("dashboard.no_snapshots");
        els.versionsList.innerHTML = "";
        return;
      }
      els.versionsSubtitle.textContent = `${versions.length} · ${homeworkId}`;
      els.versionsList.innerHTML = versions
        .map((v) => `
          <div class="version-row" data-version-id="${escapeHtml(String(v.id))}" data-homework-id="${escapeHtml(homeworkId)}">
            <div class="version-meta">
              <strong>${escapeHtml(v.title || t("dashboard.untitled"))}</strong>
              <span class="muted-text" title="${escapeHtml(formatAbsolute(v.saved_at))}">
                ${escapeHtml(formatRelative(v.saved_at))} · ${escapeHtml(String(v.size_bytes || 0))} B
              </span>
            </div>
            <button class="btn btn-ghost js-version-restore" type="button">${escapeHtml(t("dashboard.version_restore_btn"))}</button>
          </div>
        `)
        .join("");
    } catch (error) {
      els.versionsSubtitle.textContent = `${t("dashboard.toast_could_not_restore_version")}: ${error.message}`;
      els.versionsList.innerHTML = "";
    }
  }

  async function handleVersionRestore(homeworkId, versionId) {
    const confirmed = window.confirm(t("dashboard.confirm_version_restore"));
    if (!confirmed) return;
    try {
      await API.restoreVersion(homeworkId, versionId);
      showToast(t("dashboard.toast_version_restored"), t("dashboard.toast_version_restored_msg"), "success");
      closeVersionsModal();
      await loadHomeworks();
    } catch (error) {
      showToast(t("dashboard.toast_could_not_restore_version"), error.message, "error");
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

    // Hero card "Create homework" CTA — opens the same modal as the topbar btn.
    document.querySelectorAll('[data-action="new-homework"]').forEach((btn) => {
      btn.addEventListener("click", openCreateModal);
    });
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

    // Reveal the four stat-cards via the IntersectionObserver pipeline so they
    // share the Apple-spring stagger with the homework grid.
    _observeReveals(document);

    // Re-render dynamic content when the user switches language. The static
    // [data-i18n] attrs are handled by i18n.js automatically, but rebuilt
    // <option> lists, card markup and dynamic empty-state text need a re-paint.
    if (window.i18n && typeof window.i18n.onChange === "function") {
      window.i18n.onChange(() => {
        renderSubjectOptions();
        renderHomeworks();
        renderPaginationBar();
        if (els.libraryTitle) {
          els.libraryTitle.textContent =
            state.view === "trash" ? t("dashboard.tab_trash") : t("dashboard.lib_h2");
        }
      });
    }

    await Promise.allSettled([loadHealth(), loadSubjects()]);
    await loadHomeworks();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
