// frontend/js/mathlive-bootstrap.js
// Lazy-loaded MathLive bootstrap. Same idiom as katex-render.js, but
// MathLive is large enough (~150 KB gzipped) that we don't pull it on
// every page — only on builder.html, where the equation editor lives.
//
// Provides:
//   window.netsMathLive.ensureLoaded()    -> Promise<void>  resolves when
//     the <math-field> custom element is registered and ready to construct.
//   window.netsMathLive.makeField(opts)   -> HTMLElement     creates a
//     ready-to-use <math-field> with project-defaults (read-only by default
//     until the picker mounts it inline; commit-mode "input" so changes
//     fire input events the editor's autosave already listens for).
//
// Storage contract:
//   The editor stores equations as plain LaTeX wrapped in $...$ delimiters
//   inside the existing block.text fields. The runtime page already
//   auto-renders that LaTeX via KaTeX. MathLive is ONLY used inside the
//   builder's contenteditable so authors edit a real WYSIWYG fraction
//   instead of typing \frac{a}{b}. The serializer in preview.js
//   (htmlToBlocks) extracts each <math-field>'s LaTeX value and writes
//   $LaTeX$ text. The hydrator (blocksToHtml) does the reverse on load.
//
// Why a Web Component:
//   <math-field> is a self-contained custom element. It works inside
//   contenteditable="true" hosts (with the wrapping math-block being
//   contenteditable=false so the browser treats the equation as a single
//   atomic unit). MathLive ships with its own internal renderer + cursor
//   manager + virtual keyboard for mobile — exactly what the project
//   requirements list asked for, without us reinventing it.
(function () {
  "use strict";

  if (window.netsMathLive) return;

  // jsDelivr endpoint pinned to a specific version so a future MathLive
  // release can't change behavior under us. Bump deliberately + verify
  // the editor smoke tests pass.
  const MATHLIVE_VERSION = "0.106.0";
  // MathLive ships mathlive.min.mjs at the package ROOT (no /dist prefix).
  // Bumping the version: verify the URL still 200s — older releases used
  // /dist/, newer ones don't. The .mjs is the ES module entry; the
  // companion .min.js is UMD which doesn't auto-register the custom element.
  const MATHLIVE_URL =
    `https://cdn.jsdelivr.net/npm/mathlive@${MATHLIVE_VERSION}/mathlive.min.mjs`;

  let loadPromise = null;
  let loadFailed = false;

  function ensureLoaded() {
    if (typeof window.MathfieldElement === "function") {
      return Promise.resolve();
    }
    if (loadPromise) return loadPromise;
    loadPromise = new Promise((resolve, reject) => {
      const s = document.createElement("script");
      s.type = "module";
      s.src = MATHLIVE_URL;
      s.crossOrigin = "anonymous";
      s.onload = () => {
        // The module export auto-registers the <math-field> custom element.
        // Give the registration microtask one tick to flush.
        setTimeout(() => resolve(), 0);
      };
      s.onerror = (err) => {
        loadFailed = true;
        reject(err || new Error("MathLive failed to load"));
      };
      document.head.appendChild(s);
    });
    return loadPromise;
  }

  // Defaults applied to every math-field this project mounts. Each option
  // is documented with the why so future tweaks are deliberate.
  function applyDefaults(field) {
    // No virtual keyboard auto-popup on focus — the picker palette + a
    // Tab into the field is enough for desktop, and mobile users get the
    // virtual keyboard via the bottom-sheet picker which already exists.
    field.setAttribute("virtual-keyboard-mode", "manual");
    // Math-mode by default. Code View toggles between math and latex modes
    // via a toolbar button (see _equation-picker.js).
    field.setAttribute("default-mode", "math");
    // Smart-mode interprets typed-out words ("alpha" -> α) which is the
    // exact UX students expect from Word.
    field.setAttribute("smart-mode", "on");
    // Forbid \input (raw HTML/JS injection into MathLive expressions).
    field.setAttribute("smart-superscript", "on");
    field.setAttribute("remove-extraneous-parentheses", "on");
    // Inline display by default — switch to "block" only for templates
    // explicitly marked as display-mode (matrices, cases, aligned).
    field.style.display = "inline-block";
    field.style.minWidth = "32px";
    field.style.verticalAlign = "middle";
  }

  function makeField(opts) {
    const o = opts || {};
    const field = document.createElement("math-field");
    applyDefaults(field);
    if (o.value) field.value = o.value;
    if (o.readOnly) field.setAttribute("read-only", "");
    return field;
  }

  // Walk a contenteditable host and return all math-field descendants in
  // document order. Used by serialization to build the LaTeX-text form.
  function collectFields(host) {
    if (!host) return [];
    return Array.from(host.querySelectorAll("math-field"));
  }

  // Replace one math-field element with a placeholder text node carrying
  // the LaTeX wrapped in $...$ ($$..$$ for display-mode templates). The
  // serializer uses this when computing block.text from the editor DOM.
  function fieldToTextNode(field) {
    const latex = String(field.value || "").trim();
    if (!latex) return document.createTextNode("");
    const isDisplay = field.dataset.displayMode === "true"
      || /^\\begin\{(pmatrix|bmatrix|vmatrix|cases|aligned|gather)\}/.test(latex);
    const wrapped = isDisplay ? "$$" + latex + "$$" : "$" + latex + "$";
    return document.createTextNode(wrapped);
  }

  window.netsMathLive = {
    VERSION: MATHLIVE_VERSION,
    ensureLoaded,
    isLoaded: () => typeof window.MathfieldElement === "function",
    didFail: () => loadFailed,
    makeField,
    applyDefaults,
    collectFields,
    fieldToTextNode,
  };
})();
