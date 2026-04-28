// frontend/js/editors/games/puzzle-lock.js
// Puzzle Lock editor — knowledge-gated sliding-tile puzzle.
// Contract storage: content_json.gb_puzzle_lock: [{ content, q, a }]
//   - content: HTML fragment shown on the puzzle tile
//   - q: question shown when student tries to slide this tile
//   - a: accepted answer (case-insensitive, whitespace-trimmed)
// Runtime grid: 8 tiles → 3×3, 15 tiles → 4×4. Other counts use the
// nearest fitting grid (runtime caps at 15).

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
      ? items.map((tile) => ({
          content: typeof tile?.content === "string" ? tile.content : "",
          q: typeof tile?.q === "string" ? tile.q : "",
          a: typeof tile?.a === "string" ? tile.a : "",
        }))
      : [];
  }

  function makeTile() {
    return { content: "", q: "", a: "" };
  }

  function emit(state, onChange) {
    onChange(clone(state));
  }

  function summary(value) {
    const stripped = stripHtml(value);
    return stripped || "—";
  }

  function gridHint(count) {
    if (count === 0) return "Add 8 tiles for 3×3, or 15 for 4×4";
    if (count === 8) return "✓ 3×3 grid (G1-6)";
    if (count === 15) return "✓ 4×4 grid (G7-11)";
    if (count < 8) return `${count} tiles — need 8 for 3×3 or 15 for 4×4`;
    if (count < 15) return `${count} tiles — runtime will use 3×3 (8 used) or pad`;
    return `${count} tiles — runtime caps at 15 (extras ignored)`;
  }

  function render(container, data, onChange) {
    const state = normalize(data);

    function repaint() {
      container.innerHTML = `
        <div class="editor-list">
          <section class="editor-card">
            <div class="editor-header compact-header">
              <div>
                <p class="eyebrow">Puzzle Lock</p>
                <h3>${gridHint(state.length)}</h3>
              </div>
              <button class="btn btn-primary js-add-tile" type="button">Add tile</button>
            </div>
            <p class="muted-text">
              Sliding-tile puzzle. Each move is gated by a question — correct answer slides the chosen tile, wrong answer slides a random adjacent tile. Author 8 tiles for 3×3 (younger grades) or 15 for 4×4.
            </p>
          </section>

          ${
            state.length
              ? state
                  .map(
                    (tile, index) => `
                      <section class="editor-card nested-card" data-index="${index}">
                        <div class="editor-header compact-header">
                          <div>
                            <p class="eyebrow">Tile ${index + 1}</p>
                            <h3>${escapeHtml(summary(tile.content))}</h3>
                          </div>
                          <button class="btn btn-danger js-remove-tile" type="button">Remove</button>
                        </div>

                        <div class="editor-grid">
                          <div class="field full-span">
                            <span>Tile content (what shows on the puzzle piece)</span>
                            <div class="js-rich-host" data-key="content" data-index="${index}"></div>
                          </div>

                          <div class="field full-span">
                            <span>Question (asked when student tries to slide this tile)</span>
                            <input class="js-field" data-key="q" type="text" value="${escapeHtml(tile.q)}" placeholder="Why does this come after the previous tile?" />
                          </div>

                          <div class="field full-span">
                            <span>Accepted answer</span>
                            <input class="js-field" data-key="a" type="text" value="${escapeHtml(tile.a)}" placeholder="Logical / chronological / causal connection" />
                          </div>
                        </div>
                      </section>
                    `,
                  )
                  .join("")
              : `<div class="empty-state glass-card inline-empty">
                  <div class="empty-orb" aria-hidden="true">🧩</div>
                  <h3>No puzzle tiles</h3>
                  <p>Add 8 tiles for a 3×3 puzzle, or 15 for 4×4. Each tile carries a content fragment and a question that gates its movement.</p>
                  <button class="btn btn-primary js-add-tile" type="button">Add first tile</button>
                </div>`
          }
        </div>
      `;

      if (window.RichField && window.RichField.create) {
        container.querySelectorAll(".js-rich-host").forEach((host) => {
          const index = Number(host.dataset.index);
          const key = host.dataset.key;
          if (!Number.isFinite(index) || !key) return;
          const initial = state[index]?.[key] || "";
          const editor = window.RichField.create({
            value: initial,
            placeholder: "Tile fragment (text, formula, image)…",
            compact: true,
            onChange: (html) => {
              if (!state[index]) return;
              state[index][key] = html;
              emit(state, onChange);
            },
          });
          host.appendChild(editor);
        });
      }
    }

    container.oninput = (event) => {
      const field = event.target.closest(".js-field");
      if (!field) return;
      const wrap = field.closest("[data-index]");
      if (!wrap) return;
      const index = Number(wrap.dataset.index);
      const key = field.dataset.key;
      if (!Number.isFinite(index) || !key) return;
      state[index][key] = field.value;
      emit(state, onChange);
    };

    container.onclick = (event) => {
      if (event.target.closest(".js-add-tile")) {
        state.push(makeTile());
        emit(state, onChange);
        repaint();
        return;
      }
      if (event.target.closest(".js-remove-tile")) {
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

  window.GameBreakEditors.puzzleLock = { render };
})();
