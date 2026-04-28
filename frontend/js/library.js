// frontend/js/library.js
// Library page — browse homeworks by subject × grade.
// Depends on api.js (window.API).

(function () {
  "use strict";

  // ── DOM refs ────────────────────────────────────────────────────────────────
  const searchInput  = document.getElementById("lib-search");
  const subjectSel   = document.getElementById("lib-subject");
  const gradeSel     = document.getElementById("lib-grade");
  const modeSel      = document.getElementById("lib-mode");
  const clearBtn     = document.getElementById("lib-clear-btn");
  const grid         = document.getElementById("lib-grid");
  const loadingEl    = document.getElementById("lib-loading");
  const errorEl      = document.getElementById("lib-error");
  const errorMsgEl   = document.getElementById("lib-error-msg");
  const emptyEl      = document.getElementById("lib-empty");
  const retryBtn     = document.getElementById("lib-retry-btn");
  const countEl      = document.getElementById("lib-count");
  const paginationEl = document.getElementById("lib-pagination");
  const prevBtn      = document.getElementById("lib-prev-btn");
  const nextBtn      = document.getElementById("lib-next-btn");
  const pageLabelEl  = document.getElementById("lib-page-label");

  // ── State ───────────────────────────────────────────────────────────────────
  const PAGE_SIZE = 24;
  let currentOffset = 0;
  let totalItems    = 0;
  let debounceTimer = null;

  // ── Helpers ─────────────────────────────────────────────────────────────────
  function show(el)  { el.classList.remove("hidden"); }
  function hide(el)  { el.classList.add("hidden"); }

  // i18n helper — falls back to the literal string if i18n hasn't loaded yet.
  function t(key, fallback) {
    if (window.i18n && typeof window.i18n.t === "function") {
      return window.i18n.t(key, fallback);
    }
    return fallback != null ? fallback : key;
  }

  function buildApiUrl(offset) {
    const params = new URLSearchParams();
    const subject = subjectSel.value;
    const grade   = gradeSel.value;
    const mode    = modeSel.value;
    const q       = searchInput.value.trim();

    if (subject) params.set("subject", subject);
    if (grade)   params.set("grade",   grade);
    if (mode)    params.set("mode",    mode);
    if (q)       params.set("q",       q);
    params.set("limit",  String(PAGE_SIZE));
    params.set("offset", String(offset));

    return `/api/library?${params.toString()}`;
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

  function renderCard(hw) {
    const card = document.createElement("a");
    card.className   = "lib-card";
    card.href        = `/h/${encodeURIComponent(hw.id)}`;
    card.target      = "_blank";
    card.rel         = "noreferrer";
    card.setAttribute("aria-label", hw.title || hw.id);

    const mode = (hw.mode || "").toLowerCase();
    const chapter = hw.chapter || "";

    card.innerHTML = `
      <div class="lib-card-header">
        <h3 class="lib-card-title">${escHtml(hw.title || hw.id)}</h3>
        <span class="lib-mode-badge" data-mode="${escAttr(mode)}">${escHtml(hw.mode || "")}</span>
      </div>
      <div class="lib-card-meta">
        ${hw.subject ? `<span class="lib-card-pill">${escHtml(hw.subject)}</span>` : ""}
        ${hw.grade   ? `<span class="lib-card-pill grade">${escHtml(t("common.grade"))} ${escHtml(String(hw.grade))}</span>` : ""}
      </div>
      ${chapter ? `<p class="lib-card-chapter">${escHtml(chapter)}</p>` : ""}
      <time class="lib-card-time" datetime="${escAttr(hw.updated_at || "")}">${formatDate(hw.updated_at)}</time>
    `;

    return card;
  }

  function escHtml(str) {
    return String(str)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function escAttr(str) { return escHtml(str); }

  // ── Fetch & render ──────────────────────────────────────────────────────────
  async function loadPage(offset) {
    currentOffset = offset;
    hide(errorEl);
    hide(emptyEl);
    hide(paginationEl);
    show(loadingEl);
    grid.innerHTML = "";

    try {
      const url  = buildApiUrl(offset);
      const data = await API.request(url);
      totalItems = data.total || 0;

      hide(loadingEl);

      countEl.textContent = totalItems > 0 ? `(${totalItems})` : "";

      if (!data.items || data.items.length === 0) {
        show(emptyEl);
        return;
      }

      const fragment = document.createDocumentFragment();
      data.items.forEach(hw => fragment.appendChild(renderCard(hw)));
      grid.appendChild(fragment);

      // Pagination
      const totalPages  = Math.ceil(totalItems / PAGE_SIZE);
      const currentPage = Math.floor(offset / PAGE_SIZE) + 1;

      if (totalPages > 1) {
        show(paginationEl);
        pageLabelEl.textContent = `${currentPage} / ${totalPages}`;
        prevBtn.disabled = currentPage <= 1;
        nextBtn.disabled = currentPage >= totalPages;
      }
    } catch (err) {
      hide(loadingEl);
      errorMsgEl.textContent = err.message || t("common.check_connection");
      show(errorEl);
    }
  }

  // ── Facets (populate dropdowns) ─────────────────────────────────────────────
  async function loadFacets() {
    try {
      const facets = await API.request("/api/library/facets");

      (facets.subjects || []).forEach(s => {
        const opt = document.createElement("option");
        opt.value       = s;
        opt.textContent = s;
        subjectSel.appendChild(opt);
      });

      (facets.grades || []).forEach(g => {
        const opt = document.createElement("option");
        opt.value       = g;
        opt.textContent = `${t("common.grade")} ${g}`;
        gradeSel.appendChild(opt);
      });

      (facets.modes || []).forEach(m => {
        const opt = document.createElement("option");
        opt.value       = m;
        opt.textContent = m.charAt(0).toUpperCase() + m.slice(1);
        modeSel.appendChild(opt);
      });
    } catch (err) {
      console.warn("loadFacets failed:", err);
    }
  }

  // ── Event wiring ────────────────────────────────────────────────────────────
  function onFilterChange() {
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(() => loadPage(0), 300);
  }

  searchInput.addEventListener("input",  onFilterChange);
  subjectSel.addEventListener("change",  onFilterChange);
  gradeSel.addEventListener("change",    onFilterChange);
  modeSel.addEventListener("change",     onFilterChange);

  clearBtn.addEventListener("click", () => {
    searchInput.value = "";
    subjectSel.value  = "";
    gradeSel.value    = "";
    modeSel.value     = "";
    loadPage(0);
  });

  retryBtn.addEventListener("click", () => loadPage(currentOffset));

  prevBtn.addEventListener("click", () => {
    if (currentOffset >= PAGE_SIZE) {
      loadPage(currentOffset - PAGE_SIZE);
    }
  });

  nextBtn.addEventListener("click", () => {
    if (currentOffset + PAGE_SIZE < totalItems) {
      loadPage(currentOffset + PAGE_SIZE);
    }
  });

  // ── Boot ────────────────────────────────────────────────────────────────────
  // Re-render dynamic cards/pagination on language switch — static [data-i18n]
  // attrs are auto-applied by i18n.js, but the card body and pagination labels
  // are built in JS and need a manual repaint.
  if (window.i18n && typeof window.i18n.onChange === "function") {
    window.i18n.onChange(() => loadPage(currentOffset));
  }

  loadFacets().then(() => loadPage(0));
})();
