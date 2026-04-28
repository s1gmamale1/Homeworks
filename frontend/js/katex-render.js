// Shared KaTeX auto-render bootstrap.
// Renders $...$ / $$...$$ math in any display area of the page, but SKIPS
// contenteditable="true" subtrees so the rich-text editors keep raw LaTeX
// while authors are typing. Loaded via <script> on builder.html/index.html/
// library.html. Pulls KaTeX from the jsDelivr CDN (matches the runtime page
// in perfect_homework.html). Re-renders on DOM mutations so swapped panels
// (preview iframes, modal content, dynamic editor previews) stay rendered.

(function () {
  // Idempotency guard — safe to load this script twice (e.g. via cache-bust).
  if (window.__nets_katex_loaded) return;
  window.__nets_katex_loaded = true;

  function injectAsset(tag, attrs) {
    const el = document.createElement(tag);
    Object.assign(el, attrs);
    document.head.appendChild(el);
    return el;
  }

  injectAsset('link', {
    rel: 'stylesheet',
    href: 'https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/katex.min.css',
  });
  // Load katex.min.js first; only inject auto-render after it's loaded so that
  // window.katex (which auto-render references) is guaranteed to exist.
  // (Dynamically-injected <script defer> ignores defer order — must chain via onload.)
  const katexScript = injectAsset('script', {
    src: 'https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/katex.min.js',
  });
  katexScript.addEventListener('load', () => {
    injectAsset('script', {
      src: 'https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/contrib/auto-render.min.js',
    });
  });

  const KATEX_OPTS = {
    delimiters: [
      { left: '$$', right: '$$', display: true },
      { left: '$',  right: '$',  display: false },
      { left: '\\(', right: '\\)', display: false },
      { left: '\\[', right: '\\]', display: true },
    ],
    throwOnError: false,
    ignoredTags: ['script','noscript','style','textarea','pre','code','option','input'],
    ignoredClasses: ['katex','katex-display','no-math','rich-field','mono-input'],
  };

  function isInsideEditable(el) {
    while (el && el !== document.body) {
      if (el.nodeType === 1 && el.getAttribute && el.getAttribute('contenteditable') === 'true') return true;
      el = el.parentNode;
    }
    return false;
  }

  function renderInChildren(root) {
    if (!window.renderMathInElement) return;
    // Walk top-level children, skipping any subtree rooted in a contenteditable=true.
    for (const child of Array.from(root.children || [])) {
      if (child.nodeType !== 1) continue;
      if (child.matches && child.matches('[contenteditable="true"]')) continue;
      if (isInsideEditable(child)) continue;
      try { window.renderMathInElement(child, KATEX_OPTS); } catch (_) {}
    }
  }

  let isRendering = false;
  function renderNow() {
    if (isRendering || !window.renderMathInElement) return;
    isRendering = true;
    try { renderInChildren(document.body); } catch (_) {}
    setTimeout(() => { isRendering = false; }, 50);
  }

  let scheduled = false;
  function schedule() {
    if (scheduled) return;
    scheduled = true;
    requestAnimationFrame(() => { scheduled = false; renderNow(); });
  }
  window.__renderMath = schedule;

  function start() {
    renderNow();
    new MutationObserver((mutations) => {
      // Ignore mutations that happened entirely inside a contenteditable subtree —
      // those are the author typing, not new content needing render.
      for (const m of mutations) {
        if (!isInsideEditable(m.target)) { schedule(); return; }
      }
    }).observe(document.body, { childList: true, subtree: true, characterData: true });
  }

  document.addEventListener('DOMContentLoaded', () => {
    if (window.renderMathInElement) start();
    else {
      const iv = setInterval(() => {
        if (window.renderMathInElement) { clearInterval(iv); start(); }
      }, 50);
    }
  });
})();
