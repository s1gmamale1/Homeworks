// frontend/js/editors/_quote-picker.js
// Searchable picker for the gate-quote library.
// Usage:
//   QuotePicker.open({ pinnedId: 42, onPick: (entry) => { ... } })
//
// Mirrors the lightweight in-DOM modal pattern used by the image/SVG insert
// modals in preview.js — appends a backdrop, returns when the user picks or
// cancels, cleans up on close. No HTML wiring required in builder.html.
//
// All interpolations into the modal HTML go through escapeHtml(), the same
// XSS guard used by preview.js elsewhere in this codebase.

(function () {
  "use strict";

  function escapeHtml(value) {
    return String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#039;");
  }

  function originLabel(origin) {
    return origin === "Global" ? "Global" : "Milliy";
  }

  function typeIcon(type) {
    return type === "fact" ? "\u{1F4A1}" : "❝";
  }

  function renderRow(entry, pinnedId) {
    const isPinned = entry.id === pinnedId;
    const originClass =
      entry.origin === "Global"
        ? "quote-chip-origin-global"
        : "quote-chip-origin-national";
    const cat = entry.category
      ? '<span class="quote-picker-chip">' + escapeHtml(entry.category) + "</span>"
      : "";
    return [
      '<button class="quote-picker-row' + (isPinned ? " is-pinned" : "") + '" type="button" data-quote-id="' + escapeHtml(entry.id) + '">',
      '<div class="quote-picker-row-text">',
      '<span class="quote-picker-icon">' + typeIcon(entry.type) + "</span>",
      "<span>" + escapeHtml(entry.text || "") + "</span>",
      "</div>",
      '<div class="quote-picker-row-meta">',
      '<span class="quote-picker-author">' + escapeHtml(entry.author || "") + "</span>",
      '<span class="quote-picker-chip ' + originClass + '">' + escapeHtml(originLabel(entry.origin)) + "</span>",
      cat,
      "</div>",
      "</button>",
    ].join("");
  }

  function buildShell() {
    const html = [
      '<div class="quote-picker-modal" role="dialog" aria-modal="true">',
      '<div class="quote-picker-card">',
      '<div class="quote-picker-header">',
      "<div>",
      '<p class="eyebrow">Phase 0-A</p>',
      "<h3>Gate Quote Library</h3>",
      "</div>",
      '<button class="icon-btn js-quote-picker-close" type="button" title="Close">×</button>',
      "</div>",
      '<div class="quote-picker-filters">',
      '<input class="js-quote-search form-input" type="search" placeholder="Qidirish — matn yoki muallif…" autocomplete="off" />',
      '<select class="js-quote-type form-input"><option value="">Barcha turlar</option></select>',
      '<select class="js-quote-origin form-input"><option value="">Barcha kelib chiqish</option></select>',
      '<select class="js-quote-category form-input"><option value="">Barcha toifalar</option></select>',
      '<select class="js-quote-author form-input"><option value="">Barcha mualliflar</option></select>',
      "</div>",
      '<div class="quote-picker-meta js-quote-meta">Yuklanmoqda…</div>',
      '<div class="quote-picker-list js-quote-list"></div>',
      '<div class="quote-picker-footer">',
      '<button class="btn btn-ghost js-quote-picker-cancel" type="button">Bekor qilish</button>',
      "</div>",
      "</div>",
      "</div>",
    ].join("");
    const wrap = document.createElement("div");
    wrap.innerHTML = html;
    return wrap.firstElementChild;
  }

  async function fetchPage(filters) {
    if (!window.API || typeof window.API.getQuotes !== "function") {
      throw new Error("API.getQuotes is not available");
    }
    return window.API.getQuotes({
      q: filters.q || undefined,
      type: filters.type || undefined,
      origin: filters.origin || undefined,
      category: filters.category || undefined,
      author: filters.author || undefined,
      limit: 100,
      offset: 0,
    });
  }

  function debounce(fn, ms) {
    let id = null;
    return function () {
      const args = arguments;
      if (id) clearTimeout(id);
      id = setTimeout(() => fn.apply(null, args), ms);
    };
  }

  function setOptions(selectEl, values, placeholder) {
    const current = selectEl.value;
    selectEl.innerHTML = "";
    const ph = document.createElement("option");
    ph.value = "";
    ph.textContent = placeholder;
    selectEl.appendChild(ph);
    for (const value of values) {
      const opt = document.createElement("option");
      opt.value = value;
      opt.textContent = value;
      if (value === current) opt.selected = true;
      selectEl.appendChild(opt);
    }
  }

  function open(opts) {
    const pinnedId = (opts && opts.pinnedId) || null;
    const onPick = (opts && opts.onPick) || function () {};

    const root = buildShell();
    document.body.appendChild(root);

    const $list = root.querySelector(".js-quote-list");
    const $meta = root.querySelector(".js-quote-meta");
    const $search = root.querySelector(".js-quote-search");
    const $type = root.querySelector(".js-quote-type");
    const $origin = root.querySelector(".js-quote-origin");
    const $category = root.querySelector(".js-quote-category");
    const $author = root.querySelector(".js-quote-author");

    let cachedFacets = null;
    let lastItems = [];
    const filters = { q: "", type: "", origin: "", category: "", author: "" };

    function close() {
      if (root.parentNode) root.parentNode.removeChild(root);
      document.removeEventListener("keydown", onKey);
    }
    function onKey(event) {
      if (event.key === "Escape") close();
    }
    document.addEventListener("keydown", onKey);

    function applyFacets(newFacets) {
      cachedFacets = newFacets;
      setOptions($type, newFacets.types || [], "Barcha turlar");
      setOptions($origin, newFacets.origins || [], "Barcha kelib chiqish");
      setOptions($category, newFacets.categories || [], "Barcha toifalar");
      setOptions($author, newFacets.authors || [], "Barcha mualliflar");
    }

    async function refresh() {
      $meta.textContent = "Yuklanmoqda…";
      try {
        const result = await fetchPage(filters);
        if (!cachedFacets) applyFacets(result.facets || {});
        const items = result.items || [];
        lastItems = items;
        $meta.textContent = (result.total || 0) + " ta natija";
        if (!items.length) {
          $list.innerHTML = '<div class="empty-mini"><p>Filtrga mos hech narsa topilmadi.</p></div>';
          return;
        }
        $list.innerHTML = items.map((entry) => renderRow(entry, pinnedId)).join("");
      } catch (error) {
        $meta.textContent = "Xatolik: " + error.message;
        $list.innerHTML = "";
      }
    }

    const debouncedRefresh = debounce(refresh, 200);
    $search.addEventListener("input", () => {
      filters.q = $search.value.trim();
      debouncedRefresh();
    });
    [$type, $origin, $category, $author].forEach((sel) => {
      sel.addEventListener("change", () => {
        filters.type = $type.value;
        filters.origin = $origin.value;
        filters.category = $category.value;
        filters.author = $author.value;
        refresh();
      });
    });

    root.addEventListener("click", (event) => {
      if (event.target.closest(".js-quote-picker-close") || event.target.closest(".js-quote-picker-cancel")) {
        close();
        return;
      }
      const row = event.target.closest(".quote-picker-row");
      if (row) {
        const id = Number(row.dataset.quoteId);
        const entry = lastItems.find((e) => Number(e.id) === id);
        if (entry) {
          onPick(entry);
          close();
        }
        return;
      }
      // Backdrop click (target is the modal backdrop itself).
      if (event.target === root) close();
    });

    refresh();
  }

  window.QuotePicker = { open };
})();
