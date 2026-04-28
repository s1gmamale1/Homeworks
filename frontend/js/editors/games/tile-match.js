// frontend/js/editors/games/tile-match.js
// Tile Match editor — pairs support rich content (images, SVG, formatting).
// Contract storage: content_json.gb_memory_match: [[left, right], ...]

(function () {
  "use strict";

  window.GameBreakEditors = window.GameBreakEditors || {};

  function escapeHtml(value) {
    return String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#039;");
  }

  function stripHtml(value) {
    return String(value ?? "").replace(/<[^>]+>/g, " ").replace(/\s+/g, " ").trim();
  }

  function clone(value) {
    return JSON.parse(JSON.stringify(value ?? []));
  }

  function normalize(items) {
    return Array.isArray(items)
      ? items.map((pair) => [
          Array.isArray(pair) ? pair[0] || "" : "",
          Array.isArray(pair) ? pair[1] || "" : "",
        ])
      : [];
  }

  function makePair() {
    return ["", ""];
  }

  function emit(state, onChange) {
    onChange(clone(state));
  }

  function summary(value) {
    const stripped = stripHtml(value);
    return stripped || "—";
  }

  function render(container, data, onChange) {
    const state = normalize(data);

    function repaint() {
      container.innerHTML = `
        <div class="editor-list">
          <section class="editor-card">
            <div class="editor-header compact-header">
              <div>
                <p class="eyebrow">Tile Match</p>
                <h3>${state.length} pair${state.length === 1 ? "" : "s"}</h3>
              </div>
              <button class="btn btn-primary js-add-pair" type="button">Add pair</button>
            </div>
            <p class="muted-text">
              Concept-definition matching. Each tile supports images, SVG, and basic formatting — great for matching a formula to its diagram, or a term to a visual.
            </p>
          </section>

          ${
            state.length
              ? state
                  .map(
                    (pair, index) => `
                      <section class="editor-card nested-card" data-index="${index}">
                        <div class="editor-header compact-header">
                          <div>
                            <p class="eyebrow">Pair ${index + 1}</p>
                            <h3>${escapeHtml(summary(pair[0]))} ↔ ${escapeHtml(summary(pair[1]))}</h3>
                          </div>
                          <button class="btn btn-danger js-remove-pair" type="button">Remove</button>
                        </div>

                        <div class="editor-grid">
                          <div class="field">
                            <span>Left tile</span>
                            <div class="js-rich-host" data-slot="0" data-index="${index}"></div>
                          </div>

                          <div class="field">
                            <span>Right tile</span>
                            <div class="js-rich-host" data-slot="1" data-index="${index}"></div>
                          </div>
                        </div>
                      </section>
                    `,
                  )
                  .join("")
              : `<div class="empty-state glass-card inline-empty">
                  <div class="empty-orb" aria-hidden="true">🧠</div>
                  <h3>No tile pairs</h3>
                  <p>Add matching pairs for the memory match board.</p>
                  <button class="btn btn-primary js-add-pair" type="button">Add first pair</button>
                </div>`
          }
        </div>
      `;

      // Mount RichField into each slot
      if (window.RichField && window.RichField.create) {
        container.querySelectorAll(".js-rich-host").forEach((host) => {
          const index = Number(host.dataset.index);
          const slot = Number(host.dataset.slot);
          if (!Number.isFinite(index) || !Number.isFinite(slot)) return;
          const initial = state[index]?.[slot] || "";
          const editor = window.RichField.create({
            value: initial,
            placeholder: slot === 0 ? "Left tile content…" : "Right tile content…",
            compact: true,
            onChange: (html) => {
              state[index][slot] = html;
              emit(state, onChange);
            },
          });
          host.appendChild(editor);
        });
      }
    }

    container.onclick = (event) => {
      if (event.target.closest(".js-add-pair")) {
        state.push(makePair());
        emit(state, onChange);
        repaint();
        return;
      }

      if (event.target.closest(".js-remove-pair")) {
        const index = Number(event.target.closest("[data-index]")?.dataset.index);
        if (!Number.isFinite(index)) return;
        state.splice(index, 1);
        emit(state, onChange);
        repaint();
      }
    };

    repaint();
    if (window.EditorUtils) {
      window.EditorUtils.bindPasteNormalizer(container);
    }
  }

  window.GameBreakEditors.tileMatch = { render };
})();
