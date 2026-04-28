/* frontend/js/editors/grading.js
 *
 * Grading-system picker. Persists into content_json.grading.
 *
 * Schema written to content_json.grading:
 *   {
 *     system: "amr" | "default" | "off",
 *     provider: "kimi" | "anthropic" | "auto" | "mock",
 *     confidence_threshold: 50..100,        // %
 *     boss_hp_override: number | null,       // overrides per-grade default
 *     mastery_window: integer (default 3),
 *     mastery_threshold_proficient: 50..95,  // %
 *     mastery_threshold_mastered: 70..100,   // %
 *     deploy_port: integer (default 5060)
 *   }
 *
 * The deploy CLI (scripts/deploy_homework.py) reads this and configures the
 * playable HTML server accordingly.
 */
(function () {
  "use strict";

  const DEFAULTS = {
    system: "amr",
    provider: "auto",
    confidence_threshold: 80,
    boss_hp_override: null,
    mastery_window: 3,
    mastery_threshold_proficient: 70,
    mastery_threshold_mastered: 85,
    deploy_port: 5060,
  };

  function escapeHtml(value) {
    return String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;");
  }

  function withDefaults(data) {
    const d = data && typeof data === "object" ? data : {};
    return { ...DEFAULTS, ...d };
  }

  function render(root, data, onChange) {
    const cfg = withDefaults(data);
    root.innerHTML = `
      <div class="editor-card">
        <div class="editor-header">
          <div>
            <p class="eyebrow">Grading System (AMR)</p>
            <h3>Baholash tizimini tanlash</h3>
          </div>
        </div>

        <p class="muted-text">
          Bu sozlamalar homework deploy qilinganda playable HTML serveriga uzatiladi.
          O'qituvchi bu yerda grading rejimini, AI provayderini va threshold'larni belgilaydi.
        </p>

        <div class="form-grid" id="grading-form">
          <label class="field full-span">
            <span>Grading system</span>
            <select id="g-system">
              <option value="amr" ${cfg.system === "amr" ? "selected" : ""}>AMR — 2-axis rubric (concept + process), 3-pass median</option>
              <option value="default" ${cfg.system === "default" ? "selected" : ""}>Builder default — answer_spec deterministic + AI fallback</option>
              <option value="off" ${cfg.system === "off" ? "selected" : ""}>Off — closed-only, no AI grading</option>
            </select>
          </label>

          <label class="field">
            <span>AI provider</span>
            <select id="g-provider">
              <option value="builder" ${cfg.provider === "builder" ? "selected" : ""}>NETS Builder API (recommended)</option>
              <option value="auto" ${cfg.provider === "auto" ? "selected" : ""}>Auto (Builder → Kimi → Anthropic fallback)</option>
              <option value="kimi" ${cfg.provider === "kimi" ? "selected" : ""}>Kimi / Moonshot AI (direct)</option>
              <option value="anthropic" ${cfg.provider === "anthropic" ? "selected" : ""}>Anthropic / Claude (direct)</option>
              <option value="mock" ${cfg.provider === "mock" ? "selected" : ""}>Mock (heuristic, no API)</option>
            </select>
          </label>

          <label class="field full-span" id="g-builder-url-row" style="${cfg.provider === 'builder' ? '' : 'display:none'}">
            <span>Builder URL (when provider = NETS Builder)</span>
            <input type="text" id="g-builder-url" placeholder="http://192.168.1.26:8000" value="${escapeHtml(cfg.builder_url || '')}" />
          </label>

          <label class="field">
            <span>Confidence threshold (%)</span>
            <input type="number" id="g-threshold" min="50" max="100" step="5" value="${escapeHtml(cfg.confidence_threshold)}" />
          </label>

          <label class="field">
            <span>Boss HP override</span>
            <input type="number" id="g-boss-hp" min="20" max="500" placeholder="auto by grade" value="${cfg.boss_hp_override ?? ""}" />
          </label>

          <label class="field">
            <span>Deploy port</span>
            <input type="number" id="g-port" min="1024" max="65535" value="${escapeHtml(cfg.deploy_port)}" />
          </label>

          <label class="field">
            <span>Mastery window (sessions)</span>
            <input type="number" id="g-window" min="1" max="10" value="${escapeHtml(cfg.mastery_window)}" />
          </label>

          <label class="field">
            <span>Threshold → Proficient (%)</span>
            <input type="number" id="g-prof" min="50" max="95" step="5" value="${escapeHtml(cfg.mastery_threshold_proficient)}" />
          </label>

          <label class="field">
            <span>Threshold → Mastered (%)</span>
            <input type="number" id="g-mast" min="70" max="100" step="5" value="${escapeHtml(cfg.mastery_threshold_mastered)}" />
          </label>
        </div>

        <div class="editor-card" style="margin-top: 16px; background: var(--accent-light, rgba(0,122,255,0.08));">
          <h4 style="margin-top: 0;">One-click deploy</h4>
          <p class="muted-text" style="margin-bottom: 10px;">
            Bu homework'ni playable HTML directory'ga deploy qiling. Yuqoridagi grading sozlamalar serverga o'tkaziladi.
          </p>
          <div style="display: flex; gap: 8px; flex-wrap: wrap;">
            <button class="btn btn-primary" id="deploy-btn" type="button">Deploy this homework</button>
            <button class="btn btn-ghost" id="copy-cli-btn" type="button">Copy CLI command</button>
          </div>
          <pre id="deploy-output" style="margin-top: 12px; padding: 10px; background: rgba(0,0,0,0.04); border-radius: 8px; font-size: 12px; max-height: 200px; overflow: auto; display: none;"></pre>
        </div>

        <p class="muted-text" style="margin-top: 12px; font-size: 12px;">
          Spec: <code>D:/Class A Education/standards/framework/AMR-GRADING-SYSTEM.md</code>
        </p>
      </div>
    `;

    function read() {
      const next = {
        system: root.querySelector("#g-system").value,
        provider: root.querySelector("#g-provider").value,
        builder_url: (root.querySelector("#g-builder-url")?.value || "").trim(),
        confidence_threshold: clampInt(root.querySelector("#g-threshold").value, 50, 100, 80),
        boss_hp_override: parseHpOverride(root.querySelector("#g-boss-hp").value),
        mastery_window: clampInt(root.querySelector("#g-window").value, 1, 10, 3),
        mastery_threshold_proficient: clampInt(root.querySelector("#g-prof").value, 50, 95, 70),
        mastery_threshold_mastered: clampInt(root.querySelector("#g-mast").value, 70, 100, 85),
        deploy_port: clampInt(root.querySelector("#g-port").value, 1024, 65535, 5060),
      };
      return next;
    }

    function emit() {
      onChange(read());
      const isBuilder = root.querySelector("#g-provider").value === "builder";
      const row = root.querySelector("#g-builder-url-row");
      if (row) row.style.display = isBuilder ? "" : "none";
    }

    root.querySelector("#grading-form").addEventListener("change", emit);
    root.querySelector("#grading-form").addEventListener("input", emit);

    root.querySelector("#deploy-btn").addEventListener("click", () => deploy(root, read));
    root.querySelector("#copy-cli-btn").addEventListener("click", () => copyCli(root, read));
  }

  function clampInt(v, min, max, fallback) {
    const n = parseInt(v, 10);
    if (Number.isNaN(n)) return fallback;
    return Math.min(Math.max(n, min), max);
  }

  function parseHpOverride(v) {
    if (v === "" || v == null) return null;
    const n = parseInt(v, 10);
    return Number.isNaN(n) ? null : Math.min(Math.max(n, 20), 500);
  }

  async function deploy(root, readCfg) {
    const out = root.querySelector("#deploy-output");
    out.style.display = "block";
    out.textContent = "Deploying…";

    const homework = window.BUILDER_STATE?.homework;
    if (!homework?.id) {
      out.textContent = "ERROR: no homework loaded.";
      return;
    }

    const cfg = readCfg();

    try {
      const res = await fetch("/api/deploy/" + encodeURIComponent(homework.id), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ grading: cfg }),
      });
      const json = await res.json();
      if (json.ok) {
        out.textContent =
          "[OK] Deployed to: " + json.path + "\n\n" +
          "Run:\n" +
          "  cd \"" + json.path + "\"\n" +
          "  python server.py\n\n" +
          "Open: " + json.url;
      } else {
        out.textContent = "ERROR: " + (json.error || "deploy failed") + "\n\nDetails:\n" + (json.details || "");
      }
    } catch (e) {
      out.textContent =
        "Deploy endpoint not available yet (server side not implemented).\n\n" +
        "Run from terminal:\n" +
        "  python scripts/deploy_homework.py --db " + homework.id + " --provider " + cfg.provider + " --port " + cfg.deploy_port;
    }
  }

  function copyCli(root, readCfg) {
    const out = root.querySelector("#deploy-output");
    out.style.display = "block";
    const homework = window.BUILDER_STATE?.homework;
    if (!homework?.id) {
      out.textContent = "ERROR: no homework loaded.";
      return;
    }
    const cfg = readCfg();
    const cmd =
      "python scripts/deploy_homework.py --db " + homework.id +
      " --provider " + cfg.provider +
      " --port " + cfg.deploy_port +
      (cfg.boss_hp_override ? " --boss-hp " + cfg.boss_hp_override : "") +
      " --boot";
    out.textContent = cmd;
    if (navigator.clipboard) navigator.clipboard.writeText(cmd).catch(() => {});
  }

  window.Editors = window.Editors || {};
  window.Editors.grading = { render };
})();
