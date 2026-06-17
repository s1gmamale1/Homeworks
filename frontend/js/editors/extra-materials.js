// frontend/js/editors/extra-materials.js
// Extra Materials editor (UNGRADED): a list of supplementary links/videos.
// Each item is a labelled URL with an optional kind hint (video/article/file).
// URL-only — nothing is uploaded or graded. The runtime shows these near the
// end of the flow and the student can always continue past them.

(function () {
  "use strict";

  window.Editors = window.Editors || {};

  function escapeHtml(value) {
    return String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#039;");
  }

  function clone(value) {
    return JSON.parse(JSON.stringify(value ?? null));
  }

  const KINDS = ["link", "video", "article", "file"];

  function normalizeItem(item) {
    const kind = String(item?.kind || "link").toLowerCase();
    return {
      label: item?.label || "",
      url: item?.url || "",
      kind: KINDS.includes(kind) ? kind : "link",
    };
  }

  function normalize(data) {
    const safe = data && typeof data === "object" ? data : {};
    return {
      title: safe.title || "",
      intro: safe.intro || "",
      items: Array.isArray(safe.items) ? safe.items.map(normalizeItem) : [],
    };
  }

  function makeItem() {
    return { label: "", url: "", kind: "link" };
  }

  function emit(state, onChange) {
    onChange(clone(state));
  }

  function renderItems(state) {
    if (!state.items.length) {
      return `
        <div class="empty-state glass-card inline-empty">
          <div class="empty-orb" aria-hidden="true">📺</div>
          <h3>No extra materials yet</h3>
          <p>Add supplementary links — videos, articles or files.</p>
          <button class="btn btn-primary js-add-item" type="button">Add first link</button>
        </div>
      `;
    }

    return state.items
      .map(
        (item, index) => `
          <section class="editor-card" data-index="${index}">
            <div class="editor-header">
              <div>
                <p class="eyebrow">Item ${index + 1}</p>
                <h3>${escapeHtml(item.label || item.url || "Untitled link")}</h3>
              </div>
              <button class="btn btn-danger js-remove-item" type="button">Remove</button>
            </div>

            <div class="editor-grid">
              <label class="field full-span">
                <span>Label</span>
                <input class="js-item-field" data-key="label" type="text" value="${escapeHtml(item.label)}" placeholder="What the student will see" />
              </label>

              <label class="field full-span">
                <span>URL</span>
                <input class="js-item-field" data-key="url" type="url" value="${escapeHtml(item.url)}" placeholder="https://…" />
              </label>

              <label class="field full-span">
                <span>Kind</span>
                <select class="js-item-field" data-key="kind">
                  ${KINDS.map((k) => `<option value="${k}"${k === item.kind ? " selected" : ""}>${k}</option>`).join("")}
                </select>
              </label>
            </div>
          </section>
        `
      )
      .join("");
  }

  function repaint(container, state) {
    container.innerHTML = `
      <div class="editor-list">
        <section class="editor-card">
          <div class="editor-header">
            <div>
              <p class="eyebrow">Extra Materials</p>
              <h3>Supplementary links (ungraded)</h3>
            </div>
            <button class="btn btn-primary js-add-item" type="button">Add link</button>
          </div>

          <p class="muted-text">
            Ungraded. Shown near the end of the homework. Links open in a new tab —
            only http(s) and mailto links are allowed; paste a URL (no upload).
          </p>

          <div class="editor-grid">
            <label class="field full-span">
              <span>Section title</span>
              <input class="js-root-field" data-key="title" type="text" value="${escapeHtml(state.title)}" placeholder="e.g. Go further" />
            </label>

            <label class="field full-span">
              <span>Intro (optional)</span>
              <input class="js-root-field" data-key="intro" type="text" value="${escapeHtml(state.intro)}" placeholder="One line of context" />
            </label>
          </div>
        </section>

        ${renderItems(state)}
      </div>
    `;
  }

  function render(container, data, onChange) {
    const state = normalize(data);

    function sync() {
      emit(state, onChange);
    }

    function refresh() {
      repaint(container, state);
    }

    container.oninput = (event) => {
      const rootField = event.target.closest(".js-root-field");
      const itemField = event.target.closest(".js-item-field");

      if (rootField) {
        state[rootField.dataset.key] = rootField.value;
        sync();
        return;
      }

      if (itemField) {
        const index = Number(itemField.closest("[data-index]")?.dataset.index);
        if (Number.isInteger(index)) {
          state.items[index][itemField.dataset.key] = itemField.value;
          sync();
        }
      }
    };

    // <select> changes fire "change", not "input".
    container.onchange = (event) => {
      const itemField = event.target.closest(".js-item-field[data-key='kind']");
      if (itemField) {
        const index = Number(itemField.closest("[data-index]")?.dataset.index);
        if (Number.isInteger(index)) {
          state.items[index].kind = itemField.value;
          sync();
        }
      }
    };

    container.onclick = (event) => {
      if (event.target.closest(".js-add-item")) {
        state.items.push(makeItem());
        sync();
        refresh();
        return;
      }

      if (event.target.closest(".js-remove-item")) {
        const index = Number(event.target.closest("[data-index]")?.dataset.index);
        state.items.splice(index, 1);
        sync();
        refresh();
      }
    };

    refresh();
    if (window.EditorUtils) {
      window.EditorUtils.bindPasteNormalizer(container);
    }
  }

  window.Editors.extraMaterials = { render };
})();
