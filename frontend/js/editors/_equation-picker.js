// frontend/js/editors/_equation-picker.js
// MathLive-aware Equation Picker — opens from any toolbar button. Two modes:
//
//   1. The user clicks the toolbar Σ button with the caret in plain text:
//      → mount a new <math-field> at the caret (wrapped in
//        <span class="math-block" contenteditable="false">), focus it, and
//        keep the picker open so they can pick a template/symbol.
//
//   2. The user has the caret inside an existing <math-field> and opens the
//      picker:
//      → tile clicks call mathField.executeCommand(["insert", latex,
//        { selectionMode: "placeholder", insertionMode: "replaceSelection" }])
//        — MathLive then lands the cursor inside the first {} placeholder.
//
// Storage: math-fields serialize back to $LaTeX$ text via netsMathLive
// .fieldToTextNode() at save time (preview.js htmlToBlocks). On load,
// $LaTeX$ text is hydrated back into <math-field> elements (preview.js
// hydrateMathInEditor).
//
// Public API:
//   window.EquationPicker.open({ anchor, editor, onInsert })
//   window.EquationPicker.close()
//
// Responsive surfaces (same logic as before):
//   <480px : bottom sheet     480-720 : centered      ≥720 : popover
//
// Dependencies: window.EquationSymbols, window.netsMathLive.
(function () {
  "use strict";

  const RECENT_KEY = "nets.equationPicker.recent";
  const RECENT_CAP = 16;

  const STATE = {
    root: null,
    panel: null,
    backdrop: null,
    grid: null,
    searchInput: null,
    tabsRoot: null,
    activeCategoryId: null,
    currentEntries: [],
    anchor: null,
    editor: null,
    activeMathField: null,
    onInsert: null,
    isOpen: false,
    keydownListener: null,
    outsideClickListener: null,
    resizeListener: null,
    surface: "popover",
  };

  // ── Helpers ─────────────────────────────────────────────────────

  function escHtml(s) {
    return String(s == null ? "" : s)
      .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;").replace(/'/g, "&#39;");
  }

  function loadRecent() {
    try {
      const raw = localStorage.getItem(RECENT_KEY);
      if (!raw) return [];
      const parsed = JSON.parse(raw);
      if (!Array.isArray(parsed)) return [];
      return parsed.filter((s) => typeof s === "string").slice(0, RECENT_CAP);
    } catch (e) { return []; }
  }
  function saveRecent(latex) {
    try {
      const cur = loadRecent().filter((s) => s !== latex);
      cur.unshift(latex);
      const trimmed = cur.slice(0, RECENT_CAP);
      localStorage.setItem(RECENT_KEY, JSON.stringify(trimmed));
      return trimmed;
    } catch (e) { return loadRecent(); }
  }

  function pickSurface() {
    const w = window.innerWidth || 1200;
    if (w < 480) return "sheet";
    if (w < 720) return "centered";
    return "popover";
  }

  // ── Math-field mount + insertion ───────────────────────────────

  // Insert a fresh math-field at the editor's current caret. Wraps in
  // <span class="math-block" contenteditable="false"> so the browser
  // treats the equation as a single atomic unit (delete-as-one,
  // selectable-as-one). Returns the math-field element.
  function insertNewFieldAtCaret(editor) {
    if (!editor) return null;
    const wrap = document.createElement("span");
    wrap.className = "math-block";
    wrap.setAttribute("contenteditable", "false");

    const field = window.netsMathLive.makeField({});
    wrap.appendChild(field);

    const sel = window.getSelection();
    if (sel && sel.rangeCount && editor.contains(sel.anchorNode)) {
      const r = sel.getRangeAt(0);
      r.deleteContents();
      r.insertNode(wrap);
      // Trailing zero-width text node so the caret can land after the field.
      const trailing = document.createTextNode("​");
      wrap.parentNode.insertBefore(trailing, wrap.nextSibling);
      const after = document.createRange();
      after.setStartAfter(trailing);
      after.collapse(true);
      sel.removeAllRanges();
      sel.addRange(after);
    } else {
      editor.appendChild(wrap);
    }

    // Wire MathLive lifecycle so the surrounding editor's autosave fires
    // when the equation changes, and the picker tracks which field is
    // currently focused.
    bindFieldEvents(field, editor);

    // Focus into the new field so the next picker click goes into IT.
    setTimeout(() => {
      try { field.focus(); } catch (_) {}
      STATE.activeMathField = field;
    }, 0);

    // Notify the host editor that content changed (autosave path).
    editor.dispatchEvent(new InputEvent("input", { bubbles: true }));
    return field;
  }

  // Insert a symbol or template into the active math-field. If no field
  // is active (e.g. picker opened on plain text and user clicked a tile
  // before placing caret in any equation), mount a new field first then
  // insert the symbol into it.
  function insertSymbol(entry, useUnicode) {
    if (!STATE.editor) return;
    let field = STATE.activeMathField;
    if (!field || !field.isConnected) {
      field = insertNewFieldAtCaret(STATE.editor);
      if (!field) return;
    }
    // Display-mode templates: flip the field to displaystyle.
    if (entry.displayMode) {
      field.dataset.displayMode = "true";
      field.setAttribute("default-mode", "math");
    }
    try {
      if (useUnicode && entry.unicode) {
        // Insert the literal Unicode glyph as text inside the math expression.
        field.executeCommand(["insert", entry.unicode]);
      } else {
        field.executeCommand([
          "insert",
          entry.latex,
          { selectionMode: "placeholder", insertionMode: "replaceSelection" },
        ]);
      }
    } catch (e) {
      // Fallback: just append the LaTeX to the field's value.
      field.value = (field.value || "") + entry.latex;
    }
    saveRecent(entry.latex);
    if (typeof STATE.onInsert === "function") {
      try { STATE.onInsert(entry.latex, useUnicode ? "unicode" : "latex"); } catch (_) {}
    }
    // Re-focus the field so the next typing keystroke lands in it.
    try { field.focus(); } catch (_) {}
  }

  // ── Math-field <-> editor lifecycle wiring ──────────────────────

  function bindFieldEvents(field, hostEditor) {
    if (field.dataset.netsBound === "1") return;
    field.dataset.netsBound = "1";

    // MathLive's `input` event fires on every keystroke + every
    // executeCommand. Bubbling lets the host editor's autosave see it.
    field.addEventListener("input", () => {
      hostEditor.dispatchEvent(new InputEvent("input", { bubbles: true }));
    });

    // Track which field has the cursor — picker tile clicks target it.
    field.addEventListener("focus", () => {
      STATE.activeMathField = field;
    });
    field.addEventListener("blur", () => {
      // Don't immediately drop — picker tiles temporarily steal focus
      // when clicked. Reassert on next interaction.
      setTimeout(() => {
        if (document.activeElement !== field
            && (!STATE.panel || !STATE.panel.contains(document.activeElement))) {
          if (STATE.activeMathField === field) STATE.activeMathField = null;
          // Auto-remove the math-block if the user blurred without filling
          // anything in. Without this, an accidental tile-click leaves an
          // empty placeholder widget the user can't easily delete (Backspace
          // inside an empty placeholder is a no-op in MathLive — they have
          // to click adjacent first). Empty here means: value is "" OR is
          // exclusively structural placeholders / template scaffolding with
          // no actual user-typed content.
          if (isStructurallyEmpty(field)) {
            const wrap = field.closest(".math-block");
            if (wrap && wrap.parentNode) {
              wrap.parentNode.removeChild(wrap);
              if (hostEditor) {
                hostEditor.dispatchEvent(new InputEvent("input", { bubbles: true }));
              }
            }
          }
        }
      }, 50);
    });

    // ESC inside the field exits to the surrounding editor (move caret to
    // right after the math-block wrapper). Pressing ESC twice in quick
    // succession from an empty field removes the field entirely — gives
    // keyboard users a way to abort a wrong template choice.
    field.addEventListener("keydown", (event) => {
      if (event.key === "Escape") {
        event.preventDefault();
        const wrap = field.closest(".math-block");
        if (!wrap) return;
        // Esc-Esc on empty field = abort and remove.
        if (isStructurallyEmpty(field)) {
          if (wrap.parentNode) {
            wrap.parentNode.removeChild(wrap);
            if (hostEditor) {
              hostEditor.dispatchEvent(new InputEvent("input", { bubbles: true }));
              hostEditor.focus();
            }
          }
          return;
        }
        const sel = window.getSelection();
        const r = document.createRange();
        r.setStartAfter(wrap);
        r.collapse(true);
        sel.removeAllRanges();
        sel.addRange(r);
        if (hostEditor) hostEditor.focus();
      }
    });
  }

  // A math-field is "structurally empty" when its value is either the
  // empty string OR contains only `\placeholder{}` markers and template
  // scaffolding (\frac, \sqrt, \int, \begin{}/\end{}, & for matrix
  // separators, \\ for matrix row breaks, _, ^, \to). The heuristic strips
  // every known scaffolding token and checks if anything substantive is
  // left. Anything substantive = the user typed actual math content.
  function isStructurallyEmpty(field) {
    if (!field) return true;
    let v = "";
    try { v = String(field.value || ""); } catch (_) { v = ""; }
    if (!v.trim()) return true;
    // Strip placeholder markers.
    let cleaned = v.replace(/\\placeholder\{\}/g, "");
    // Strip common scaffolding macros (no arguments — we already stripped
    // braces below).
    cleaned = cleaned.replace(
      /\\(?:frac|dfrac|tfrac|sqrt|int|iint|iiint|oint|sum|prod|lim|hat|vec|dot|ddot|bar|overline|underline|to|infty|partial|nabla|begin|end|left|right|cdot|times|div|pm|mp)\b/g,
      "",
    );
    // Strip braces, brackets, and operator chars used for structure.
    cleaned = cleaned.replace(/[{}\[\]_^&\\\s,]/g, "");
    // Strip env names like "pmatrix" "cases" "aligned".
    cleaned = cleaned.replace(/\b(?:pmatrix|bmatrix|vmatrix|cases|aligned|gather|matrix|array)\b/g, "");
    return cleaned.length === 0;
  }

  // Public hook: walk an editor and bind events on every math-field that's
  // already there (used after hydration on initial render).
  function bindAllFields(editor) {
    if (!editor) return;
    const fields = Array.from(editor.querySelectorAll("math-field"));
    for (const f of fields) bindFieldEvents(f, editor);
  }

  // ── Picker DOM ──────────────────────────────────────────────────

  function renderRoot() {
    const root = document.createElement("div");
    root.className = "equation-picker-root";
    root.setAttribute("role", "dialog");
    root.setAttribute("aria-modal", "true");
    root.setAttribute("aria-label", "Insert equation");
    root.hidden = true;

    const backdrop = document.createElement("div");
    backdrop.className = "equation-picker-backdrop";

    const panel = document.createElement("div");
    panel.className = "equation-picker-panel";

    const header = document.createElement("div");
    header.className = "equation-picker-header";
    header.innerHTML =
      '<div class="equation-picker-title">Insert equation</div>' +
      '<div class="equation-picker-header-actions">' +
        '<button type="button" class="equation-picker-codeview" title="Toggle Code View (LaTeX)" aria-pressed="false">&lt;/&gt; LaTeX</button>' +
        '<button type="button" class="equation-picker-close" aria-label="Close equation picker">×</button>' +
      '</div>';

    const search = document.createElement("div");
    search.className = "equation-picker-search";
    search.innerHTML =
      '<input type="search" class="equation-picker-search-input" ' +
      'placeholder="Search symbols (e.g. integral, alpha, leq)" ' +
      'aria-label="Search symbols" autocomplete="off" />';

    const tabs = document.createElement("div");
    tabs.className = "equation-picker-tabs";
    tabs.setAttribute("role", "tablist");

    const grid = document.createElement("div");
    grid.className = "equation-picker-grid";
    grid.setAttribute("role", "grid");

    const hint = document.createElement("div");
    hint.className = "equation-picker-hint";
    hint.innerHTML =
      '<span>Click to insert · <kbd>Shift</kbd>+click for Unicode glyph · ' +
      '<kbd>Esc</kbd> exits the equation · <kbd>Tab</kbd> jumps to next placeholder</span>';

    panel.appendChild(header);
    panel.appendChild(search);
    panel.appendChild(tabs);
    panel.appendChild(grid);
    panel.appendChild(hint);

    root.appendChild(backdrop);
    root.appendChild(panel);

    document.body.appendChild(root);

    STATE.root = root;
    STATE.backdrop = backdrop;
    STATE.panel = panel;
    STATE.tabsRoot = tabs;
    STATE.grid = grid;
    STATE.searchInput = search.querySelector(".equation-picker-search-input");

    header.querySelector(".equation-picker-close").addEventListener("click", () => closePicker());
    backdrop.addEventListener("click", () => closePicker());
    header.querySelector(".equation-picker-codeview").addEventListener("click", toggleCodeView);

    STATE.searchInput.addEventListener("input", () => {
      onSearchChange(STATE.searchInput.value);
    });

    tabs.addEventListener("click", (event) => {
      const btn = event.target.closest(".equation-picker-tab");
      if (!btn || !tabs.contains(btn)) return;
      activateCategory(btn.dataset.categoryId);
    });

    // Tile click handlers — mousedown.preventDefault keeps the math-field's
    // selection alive through the click round-trip. Click then dispatches
    // the symbol insertion.
    grid.addEventListener("mousedown", (event) => {
      const tile = event.target.closest(".equation-picker-tile");
      if (!tile) return;
      event.preventDefault();
    });
    grid.addEventListener("click", (event) => {
      const tile = event.target.closest(".equation-picker-tile");
      if (!tile) return;
      const idx = Number(tile.dataset.idx);
      const entry = STATE.currentEntries[idx];
      if (!entry) return;
      insertSymbol(entry, !!event.shiftKey);
    });

    grid.addEventListener("keydown", onGridKeydown);
    STATE.searchInput.addEventListener("keydown", (event) => {
      if (event.key === "ArrowDown") {
        event.preventDefault();
        focusTile(0);
      } else if (event.key === "Enter") {
        event.preventDefault();
        const entry = STATE.currentEntries[0];
        if (entry) insertSymbol(entry, !!event.shiftKey);
      } else if (event.key === "Escape") {
        event.preventDefault();
        closePicker();
      }
    });

    return root;
  }

  function buildTabs() {
    const recent = loadRecent();
    const items = [];
    if (recent.length) items.push({ id: "recent", label: "Recent" });
    for (const cat of window.EquationSymbols.CATEGORIES) items.push({ id: cat.id, label: cat.label });
    STATE.tabsRoot.innerHTML = items
      .map((it, i) =>
        '<button type="button" class="equation-picker-tab" role="tab" ' +
          'data-category-id="' + escHtml(it.id) + '" tabindex="' + (i === 0 ? "0" : "-1") + '">' +
          escHtml(it.label) +
        '</button>',
      )
      .join("");
    STATE.tabsRoot.onkeydown = (event) => {
      if (!["ArrowLeft", "ArrowRight", "Home", "End"].includes(event.key)) return;
      event.preventDefault();
      const arr = Array.from(STATE.tabsRoot.querySelectorAll(".equation-picker-tab"));
      if (!arr.length) return;
      const cur = arr.findIndex((t) => t === document.activeElement);
      let next = cur;
      if (event.key === "ArrowLeft") next = (cur <= 0 ? arr.length - 1 : cur - 1);
      if (event.key === "ArrowRight") next = (cur >= arr.length - 1 ? 0 : cur + 1);
      if (event.key === "Home") next = 0;
      if (event.key === "End") next = arr.length - 1;
      arr[next].focus();
      activateCategory(arr[next].dataset.categoryId);
    };
  }

  function entriesForCategory(catId) {
    if (catId === "recent") {
      const recent = loadRecent();
      const out = [];
      for (const latex of recent) {
        const e = window.EquationSymbols.lookup(latex);
        if (e) out.push(e);
      }
      return out;
    }
    const cat = window.EquationSymbols.CATEGORIES.find((c) => c.id === catId);
    return cat ? cat.entries.map((e) => ({ ...e, _categoryId: cat.id })) : [];
  }

  function activateCategory(catId) {
    STATE.activeCategoryId = catId;
    Array.from(STATE.tabsRoot.querySelectorAll(".equation-picker-tab")).forEach((btn) => {
      const active = btn.dataset.categoryId === catId;
      btn.classList.toggle("is-active", active);
      btn.setAttribute("aria-selected", active ? "true" : "false");
      btn.tabIndex = active ? 0 : -1;
    });
    STATE.searchInput.value = "";
    renderEntries(entriesForCategory(catId));
  }

  function onSearchChange(query) {
    if (!query || !query.trim()) {
      renderEntries(entriesForCategory(STATE.activeCategoryId));
      return;
    }
    renderEntries(window.EquationSymbols.search(query));
  }

  function renderEntries(entries) {
    STATE.currentEntries = entries.slice();
    if (!entries.length) {
      STATE.grid.innerHTML =
        '<div class="equation-picker-empty">No symbols match. Try a different search term.</div>';
      return;
    }
    const html = entries
      .map(
        (entry, idx) =>
          '<button type="button" class="equation-picker-tile" role="gridcell" ' +
            'data-idx="' + idx + '" tabindex="' + (idx === 0 ? "0" : "-1") + '" ' +
            'aria-label="' + escHtml(entry.name || entry.latex) + '" ' +
            'title="' + escHtml((entry.name ? entry.name + " · " : "") + entry.latex) + '">' +
            '<span class="equation-picker-tile-glyph" data-tex="' + escHtml(entry.display || entry.latex) + '">' +
              escHtml(entry.unicode || entry.display || entry.latex) +
            '</span>' +
            '<span class="equation-picker-tile-label">' + escHtml(entry.name || "") + '</span>' +
          '</button>',
      )
      .join("");
    STATE.grid.innerHTML = html;
    if (window.katex && typeof window.katex.render === "function") {
      const glyphs = STATE.grid.querySelectorAll(".equation-picker-tile-glyph");
      glyphs.forEach((g) => {
        const tex = g.dataset.tex || "";
        if (tex.indexOf("\\") === -1 && tex.indexOf("{") === -1) return;
        try {
          window.katex.render(tex, g, { throwOnError: false, displayMode: false });
        } catch (_) {}
      });
    }
  }

  function tilesArray() {
    return Array.from(STATE.grid.querySelectorAll(".equation-picker-tile"));
  }
  function focusTile(idx) {
    const tiles = tilesArray();
    if (!tiles.length) return;
    const c = Math.max(0, Math.min(idx, tiles.length - 1));
    tiles.forEach((t, i) => { t.tabIndex = i === c ? 0 : -1; });
    tiles[c].focus();
  }
  function gridColumnCount() {
    const tiles = tilesArray();
    if (!tiles.length) return 1;
    const top0 = tiles[0].offsetTop;
    let n = 0;
    for (const t of tiles) {
      if (t.offsetTop !== top0) break;
      n++;
    }
    return Math.max(1, n);
  }
  function onGridKeydown(event) {
    const tiles = tilesArray();
    if (!tiles.length) return;
    const cur = tiles.findIndex((t) => t === document.activeElement);
    let next = cur;
    if (event.key === "ArrowRight") next = Math.min(cur + 1, tiles.length - 1);
    else if (event.key === "ArrowLeft") next = Math.max(cur - 1, 0);
    else if (event.key === "ArrowDown") next = Math.min(cur + gridColumnCount(), tiles.length - 1);
    else if (event.key === "ArrowUp") {
      const back = cur - gridColumnCount();
      if (back < 0) { event.preventDefault(); STATE.searchInput.focus(); return; }
      next = back;
    } else if (event.key === "Home") next = 0;
    else if (event.key === "End") next = tiles.length - 1;
    else if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      const idx = Number(tiles[cur] && tiles[cur].dataset.idx);
      const entry = STATE.currentEntries[idx];
      if (entry) insertSymbol(entry, !!event.shiftKey);
      return;
    } else if (event.key === "Escape") {
      event.preventDefault();
      closePicker();
      return;
    } else { return; }
    if (next !== cur) { event.preventDefault(); focusTile(next); }
  }

  // ── Code View toggle ────────────────────────────────────────────

  function toggleCodeView() {
    if (!STATE.activeMathField) return;
    const f = STATE.activeMathField;
    const cur = f.getAttribute("default-mode") || "math";
    const btn = STATE.panel.querySelector(".equation-picker-codeview");
    if (cur === "math") {
      // Switch the field into LaTeX-source view.
      try { f.executeCommand("toggleMathLatexView"); } catch (_) {}
      f.setAttribute("default-mode", "latex");
      if (btn) btn.setAttribute("aria-pressed", "true");
    } else {
      try { f.executeCommand("toggleMathLatexView"); } catch (_) {}
      f.setAttribute("default-mode", "math");
      if (btn) btn.setAttribute("aria-pressed", "false");
    }
  }

  // ── Position / open / close ─────────────────────────────────────

  function positionPanel() {
    STATE.surface = pickSurface();
    STATE.panel.classList.remove("is-popover", "is-centered", "is-sheet");
    STATE.panel.classList.add("is-" + STATE.surface);
    STATE.root.classList.remove("is-popover", "is-centered", "is-sheet");
    STATE.root.classList.add("is-" + STATE.surface);
    if (STATE.surface !== "popover") {
      STATE.panel.style.left = ""; STATE.panel.style.top = "";
      return;
    }
    const anchor = STATE.anchor;
    if (!anchor || !anchor.getBoundingClientRect) return;
    const rect = anchor.getBoundingClientRect();
    const panelRect = STATE.panel.getBoundingClientRect();
    const VW = window.innerWidth, VH = window.innerHeight, margin = 12;
    let top = rect.bottom + 8;
    let left = rect.left;
    if (left + panelRect.width > VW - margin) left = Math.max(margin, VW - panelRect.width - margin);
    if (left < margin) left = margin;
    if (top + panelRect.height > VH - margin) {
      const flipped = rect.top - panelRect.height - 8;
      top = flipped >= margin ? flipped : Math.max(margin, VH - panelRect.height - margin);
    }
    STATE.panel.style.left = Math.round(left) + "px";
    STATE.panel.style.top = Math.round(top) + "px";
  }

  function open(opts) {
    const o = opts || {};
    if (!STATE.root) renderRoot();

    STATE.anchor = o.anchor || null;
    STATE.editor = o.editor || null;
    STATE.onInsert = typeof o.onInsert === "function" ? o.onInsert : null;

    // If the caller passed an existing math-field as activeMathField, use it;
    // otherwise see whether the current document.activeElement is one.
    if (o.activeMathField) {
      STATE.activeMathField = o.activeMathField;
    } else if (document.activeElement
        && document.activeElement.tagName === "MATH-FIELD"
        && o.editor && o.editor.contains(document.activeElement)) {
      STATE.activeMathField = document.activeElement;
    }

    // Lazy-load MathLive on first open; the picker UI is usable while the
    // module finishes downloading because it doesn't need MathLive to render
    // its own KaTeX tile previews.
    if (window.netsMathLive && typeof window.netsMathLive.ensureLoaded === "function") {
      window.netsMathLive.ensureLoaded().catch(() => {/* ignored — picker still opens */});
    }

    buildTabs();
    const recent = loadRecent();
    activateCategory(recent.length ? "recent" : "common");

    STATE.root.hidden = false;
    STATE.isOpen = true;
    requestAnimationFrame(() => {
      positionPanel();
      STATE.searchInput.focus();
      STATE.searchInput.select();
    });

    STATE.keydownListener = (event) => {
      if (event.key === "Escape" && STATE.isOpen) {
        // Don't swallow ESC inside the math-field — let it exit to the
        // surrounding editor first, then close the picker on the next ESC.
        if (event.target && event.target.tagName === "MATH-FIELD") return;
        event.preventDefault();
        closePicker();
        return;
      }
      if (event.key === "Tab" && STATE.isOpen) {
        const focusables = STATE.panel.querySelectorAll(
          'button, input, [tabindex]:not([tabindex="-1"])',
        );
        if (!focusables.length) return;
        const list = Array.from(focusables);
        const first = list[0], last = list[list.length - 1];
        if (event.shiftKey && document.activeElement === first) {
          event.preventDefault(); last.focus();
        } else if (!event.shiftKey && document.activeElement === last) {
          event.preventDefault(); first.focus();
        }
      }
    };
    document.addEventListener("keydown", STATE.keydownListener);

    STATE.outsideClickListener = (event) => {
      if (!STATE.isOpen) return;
      if (STATE.backdrop.contains(event.target)) return;
      if (STATE.panel.contains(event.target)) return;
      if (STATE.anchor && STATE.anchor.contains(event.target)) return;
      // Clicks INSIDE a math-field (the active equation we're editing) must
      // not close the picker — the user is just navigating placeholders.
      if (event.target && event.target.closest("math-field")) return;
      closePicker();
    };
    setTimeout(() => {
      document.addEventListener("mousedown", STATE.outsideClickListener);
    }, 0);

    STATE.resizeListener = () => positionPanel();
    window.addEventListener("resize", STATE.resizeListener);
    window.addEventListener("scroll", STATE.resizeListener, true);
  }

  function closePicker() {
    if (!STATE.isOpen) return;
    STATE.isOpen = false;
    if (STATE.root) STATE.root.hidden = true;
    if (STATE.keydownListener) {
      document.removeEventListener("keydown", STATE.keydownListener);
      STATE.keydownListener = null;
    }
    if (STATE.outsideClickListener) {
      document.removeEventListener("mousedown", STATE.outsideClickListener);
      STATE.outsideClickListener = null;
    }
    if (STATE.resizeListener) {
      window.removeEventListener("resize", STATE.resizeListener);
      window.removeEventListener("scroll", STATE.resizeListener, true);
      STATE.resizeListener = null;
    }
    const anchor = STATE.anchor;
    STATE.anchor = null; STATE.editor = null; STATE.onInsert = null;
    // Don't clear activeMathField — keep editing context after picker closes.
    if (anchor && typeof anchor.focus === "function") {
      try { anchor.focus({ preventScroll: true }); } catch (_) {
        try { anchor.focus(); } catch (__) {}
      }
    }
  }

  // ── Public API ──────────────────────────────────────────────────

  window.EquationPicker = {
    open,
    close: closePicker,
    insertNewFieldAtCaret,
    bindFieldEvents,
    bindAllFields,
    _state: STATE,
    _loadRecent: loadRecent,
    _saveRecent: saveRecent,
    _pickSurface: pickSurface,
  };
})();
