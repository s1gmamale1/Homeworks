// frontend/js/editors/preview.js
// Preview editor: WYSIWYG Word-style rich text per page.
// Edits content_json.meta, content_json.panels, and content_json.gate_quote.
// Data shape out: panels[].pages[].blocks[] with types p|h2|quote|ol|ul|code|image|svg.
//
// Gate quote schema: { mode: "auto" | "pinned" | "custom", pinned_id?: number,
// pinned_preview?: {text, author, origin, type}, custom?: {text, author} }.
// Legacy `content_json.quotes` (array of strings or {t,a}) is migrated on read.

(function () {
  "use strict";

  window.Editors = window.Editors || {};

  // ---------- helpers ----------

  function escapeHtml(value) {
    return String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#039;");
  }

  function escapeAttr(value) {
    return escapeHtml(value);
  }

  function clone(value) {
    return JSON.parse(JSON.stringify(value ?? null));
  }

  function asArray(value) {
    return Array.isArray(value) ? value : [];
  }

  function innerTextOf(node) {
    // jsdom sometimes returns undefined for innerText; fall back to textContent.
    if (!node) return "";
    return String(node.innerText ?? node.textContent ?? "");
  }

  function stripScripts(html) {
    // Remove <script>...</script> and on* event attributes from a fragment of HTML.
    return String(html || "")
      .replace(/<script\b[^>]*>[\s\S]*?<\/script>/gi, "")
      .replace(/\son[a-z]+\s*=\s*"[^"]*"/gi, "")
      .replace(/\son[a-z]+\s*=\s*'[^']*'/gi, "")
      .replace(/\son[a-z]+\s*=\s*[^\s>]+/gi, "");
  }

  // ---------- paste sanitization ----------

  function unwrap(el) {
    const parent = el.parentNode;
    if (!parent) return;
    while (el.firstChild) parent.insertBefore(el.firstChild, el);
    parent.removeChild(el);
  }

  function renameTag(el, newTagName) {
    const next = document.createElement(newTagName);
    while (el.firstChild) next.appendChild(el.firstChild);
    el.replaceWith(next);
    return next;
  }

  function plainTextToHtml(text) {
    // Split paragraphs on blank lines, preserve single newlines as <br>.
    return String(text || "")
      .split(/\n\s*\n/)
      .map((chunk) =>
        chunk
          .trim()
          .split("\n")
          .map((line) =>
            line
              .replace(/&/g, "&amp;")
              .replace(/</g, "&lt;")
              .replace(/>/g, "&gt;"),
          )
          .join("<br>"),
      )
      .filter(Boolean)
      .map((p) => `<p>${p}</p>`)
      .join("");
  }

  function cleanNode(root) {
    // Remove Office conditional comments (<!--[if ...]>...<![endif]-->).
    const commentWalker = document.createTreeWalker(root, NodeFilter.SHOW_COMMENT);
    const comments = [];
    while (commentWalker.nextNode()) comments.push(commentWalker.currentNode);
    for (const c of comments) {
      if (c.parentNode) c.parentNode.removeChild(c);
    }

    // Walk all descendants. Use a static snapshot because we'll mutate.
    const all = Array.from(root.querySelectorAll("*"));
    const DANGEROUS = [
      "script", "style", "link", "meta", "iframe", "object", "embed",
      "form", "input", "button", "select", "textarea", "noscript", "base",
    ];
    const ALLOWED = [
      "p", "h2", "ul", "ol", "li", "blockquote", "pre",
      "b", "i", "u", "code", "br", "img", "div",
    ];

    for (const el of all) {
      // Element may have been removed by a prior iteration.
      if (!el.isConnected && !root.contains(el)) continue;

      const tag = (el.tagName || "").toLowerCase();
      if (!tag) continue;

      // Drop dangerous/noise tags entirely.
      if (DANGEROUS.includes(tag)) {
        el.remove();
        continue;
      }

      // Word/XML namespaced tags: <o:p>, <w:sdt>, <v:shape>, xml: etc.
      if (tag.includes(":") || tag.startsWith("o-") || tag.startsWith("w-") || tag.startsWith("v-")) {
        unwrap(el);
        continue;
      }

      // Preserve our own wrappers as-is.
      const isImageWrap = tag === "div" && el.classList && el.classList.contains("image-wrap");
      const isSvgWrap = tag === "div" && el.classList && el.classList.contains("svg-wrap");

      // Strip attributes. Keep only a tiny allowlist per-tag.
      const attrs = Array.from(el.attributes).map((a) => a.name);
      for (const name of attrs) {
        const keep =
          (tag === "img" && (name === "src" || name === "alt")) ||
          (isImageWrap && (name === "class" || name === "contenteditable" || name === "draggable")) ||
          (isSvgWrap && (name === "class" || name === "contenteditable" || name === "draggable"));
        if (keep) {
          // Guard against javascript: URLs on src/href even when kept.
          if (name === "src" || name === "href") {
            const val = String(el.getAttribute(name) || "").trim().toLowerCase();
            if (val.startsWith("javascript:")) {
              el.remove();
              break;
            }
          }
          continue;
        }
        el.removeAttribute(name);
      }
      if (!el.isConnected && !root.contains(el)) continue;

      // Normalize tags.
      if (tag === "h1" || tag === "h3" || tag === "h4" || tag === "h5" || tag === "h6") {
        renameTag(el, "h2");
        continue;
      }
      if (tag === "strong") { renameTag(el, "b"); continue; }
      if (tag === "em") { renameTag(el, "i"); continue; }

      // Unwrap presentational / wrapper tags.
      if (tag === "font") { unwrap(el); continue; }
      if (tag === "span") {
        // Keep a span only if its sole contribution is wrapping a <br>.
        const onlyBr = el.children.length === 1 && el.children[0].tagName.toLowerCase() === "br" && !el.textContent.trim();
        if (!onlyBr) unwrap(el);
        continue;
      }
      if (tag === "a") { unwrap(el); continue; }
      if (tag === "section" || tag === "article" || tag === "header" || tag === "footer" || tag === "main" || tag === "nav" || tag === "aside" || tag === "figure" || tag === "figcaption") {
        unwrap(el);
        continue;
      }
      if (tag === "div") {
        if (isImageWrap || isSvgWrap) continue; // our wrappers, keep.
        // If div contains a list, unwrap (let the list stand on its own).
        if (el.querySelector && el.querySelector(":scope > ul, :scope > ol")) {
          unwrap(el);
          continue;
        }
        // Otherwise convert div -> p (block-level-ish).
        renameTag(el, "p");
        continue;
      }

      // Handle images: keep data URIs and http(s). Drop others.
      if (tag === "img") {
        const src = String(el.getAttribute("src") || "").trim();
        const lower = src.toLowerCase();
        const ok =
          lower.startsWith("data:image/") ||
          lower.startsWith("http://") ||
          lower.startsWith("https://") ||
          lower.startsWith("/generated/");
        if (!ok) {
          el.remove();
          continue;
        }
        // Wrap bare <img> in image-wrap so it participates in our drag/resize logic.
        const alreadyWrapped = el.parentNode && el.parentNode.classList && el.parentNode.classList.contains("image-wrap");
        if (!alreadyWrapped) {
          const wrap = document.createElement("div");
          wrap.className = "image-wrap";
          wrap.setAttribute("contenteditable", "false");
          wrap.setAttribute("draggable", "true");
          el.replaceWith(wrap);
          wrap.appendChild(el);
        }
        continue;
      }

      // Unwrap anything not in the allowlist.
      if (!ALLOWED.includes(tag)) {
        unwrap(el);
      }
    }

    // Remove empty paragraphs left behind by Word/Docs.
    const emptyPs = Array.from(root.querySelectorAll("p"));
    for (const p of emptyPs) {
      const text = String(p.textContent || "")
        .replace(/ /g, " ")
        .replace(/[​﻿]/g, "")
        .trim();
      const hasMedia = p.querySelector && p.querySelector("img, svg, br");
      if (!text && !hasMedia) p.remove();
    }

    // Normalize text nodes: strip zero-width, collapse nbsp + whitespace.
    const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
    const textNodes = [];
    while (walker.nextNode()) textNodes.push(walker.currentNode);
    for (const t of textNodes) {
      t.nodeValue = String(t.nodeValue || "")
        .replace(/[​﻿]/g, "")  // zero-width space / BOM
        .replace(/ /g, " ")           // nbsp -> regular space
        .replace(/[ \t]+/g, " ");          // collapse runs of spaces/tabs (not newlines)
    }
  }

  function sanitizePastedHtml(rawHtml) {
    // Remove Office conditional comments before they ever hit the parser quirks.
    const prePass = String(rawHtml || "")
      .replace(/<!--\[if[\s\S]*?endif\]-->/gi, "")
      .replace(/<\?xml[\s\S]*?\?>/gi, "");
    const template = document.createElement("template");
    template.innerHTML = prePass;
    cleanNode(template.content);
    return template.innerHTML;
  }

  function makeEmptyPage() {
    return { blocks: [{ type: "p", text: "" }] };
  }

  function makeEmptyPanel(nextId) {
    return {
      id: nextId,
      title: `PANEL ${nextId} — NEW SECTION`,
      pages: [makeEmptyPage()],
    };
  }

  function normalizeBlock(block) {
    const type = block?.type || "p";
    if (type === "ol" || type === "ul") {
      const items = asArray(block.items);
      return { type, items: items.length ? items.map((i) => String(i ?? "")) : [""] };
    }
    if (type === "image") {
      return { type: "image", src: String(block.src || ""), alt: String(block.alt || "") };
    }
    if (type === "svg") {
      return { type: "svg", html: String(block.html || "") };
    }
    return { type, text: String(block.text ?? "") };
  }

  function normalizeGateQuote(value, legacyQuotes) {
    // New shape passthrough.
    if (value && typeof value === "object" && !Array.isArray(value)) {
      const mode = value.mode === "pinned" || value.mode === "custom" ? value.mode : "auto";
      const out = { mode };
      if (mode === "pinned") {
        out.pinned_id = value.pinned_id != null ? Number(value.pinned_id) : null;
        if (value.pinned_preview && typeof value.pinned_preview === "object") {
          out.pinned_preview = {
            text: String(value.pinned_preview.text || ""),
            author: String(value.pinned_preview.author || ""),
            origin: String(value.pinned_preview.origin || "National"),
            type: String(value.pinned_preview.type || "fact"),
          };
        }
      }
      if (mode === "custom") {
        const c = value.custom || {};
        out.custom = {
          text: String(c.text || ""),
          author: String(c.author || ""),
        };
      }
      return out;
    }
    // Legacy: content_json.quotes was an array of strings or {t,a}.
    const arr = asArray(legacyQuotes);
    for (const entry of arr) {
      if (typeof entry === "string" && entry.trim()) {
        return { mode: "custom", custom: { text: entry.trim(), author: "" } };
      }
      if (entry && typeof entry === "object") {
        const text = String(entry.t || entry.text || "").trim();
        const author = String(entry.a || entry.author || "").trim();
        if (text) return { mode: "custom", custom: { text, author } };
      }
    }
    return { mode: "auto" };
  }

  function normalizeData(data) {
    const safe = data && typeof data === "object" ? clone(data) : {};
    safe.meta = {
      title: safe.meta?.title || "",
      subject_display: safe.meta?.subject_display || "",
      section: safe.meta?.section || "",
      cefr_level: safe.meta?.cefr_level || "",
    };
    safe.gate_quote = normalizeGateQuote(safe.gate_quote, safe.quotes);
    // Drop the legacy key from the editor's working state — saves go through
    // gate_quote going forward. The injector falls back to `quotes` for any
    // already-saved homework that hasn't been edited yet.
    delete safe.quotes;
    safe.panels = asArray(safe.panels).map((panel, index) => ({
      id: Number(panel?.id || index + 1),
      title: panel?.title || `PANEL ${index + 1}`,
      pages: asArray(panel?.pages).length
        ? asArray(panel.pages).map((page) => ({
            blocks: asArray(page?.blocks).length
              ? asArray(page.blocks).map(normalizeBlock)
              : [{ type: "p", text: "" }],
          }))
        : [makeEmptyPage()],
    }));
    return safe;
  }

  function getNextPanelId(panels) {
    const ids = panels.map((p) => Number(p.id || 0));
    return ids.length ? Math.max(...ids) + 1 : 1;
  }

  // ---------- blocks <-> HTML ----------

  function mediaActionsHtml(kind) {
    return `
      <div class="media-wrap-actions" contenteditable="false" draggable="false">
        <button type="button" class="media-wrap-btn js-media-replace" data-media-kind="${kind}">
          ${kind === "svg" ? "Edit SVG" : "Replace"}
        </button>
        <button type="button" class="media-wrap-btn danger js-media-remove">Remove</button>
      </div>
    `;
  }

  function blocksToHtml(blocks) {
    return asArray(blocks)
      .map((b) => {
        if (!b || !b.type) return "";
        if (b.type === "h2") return `<h2>${b.text || ""}</h2>`;
        if (b.type === "quote") return `<blockquote>${escapeHtml(b.text || "")}</blockquote>`;
        if (b.type === "ul") {
          const items = asArray(b.items).map((i) => `<li>${i || ""}</li>`).join("");
          return `<ul>${items || "<li></li>"}</ul>`;
        }
        if (b.type === "ol") {
          const items = asArray(b.items).map((i) => `<li>${i || ""}</li>`).join("");
          return `<ol>${items || "<li></li>"}</ol>`;
        }
        if (b.type === "code") return `<pre><code>${escapeHtml(b.text || "")}</code></pre>`;
        if (b.type === "image") {
          const src = escapeAttr(b.src || "");
          const alt = escapeAttr(b.alt || "");
          const widthStyle = b.width ? `style="width:${escapeAttr(String(b.width))}"` : "";
          return `<div class="image-wrap" contenteditable="false" draggable="true" ${widthStyle}>${mediaActionsHtml("image")}<img src="${src}" alt="${alt}"></div>`;
        }
        if (b.type === "svg") {
          return `<div class="svg-wrap" contenteditable="false" draggable="true">${mediaActionsHtml("svg")}${stripScripts(b.html || "")}</div>`;
        }
        return `<p>${b.text || ""}</p>`;
      })
      .join("");
  }

  // ── Math hydration: $LaTeX$ text → <math-field> WYSIWYG widgets ──
  //
  // Storage stays as plain $LaTeX$ / $$LaTeX$$ text (the runtime renders
  // these via the existing KaTeX bootstrap). Inside the builder editor we
  // upgrade them to MathLive <math-field> widgets so authors edit a real
  // fraction with placeholder boxes instead of typing \frac{a}{b}.
  //
  // Regex: matches $...$ and $$...$$, ignoring escaped \$. Greedy on display
  // ($$..$$), non-greedy on inline ($..$). Empty bodies are skipped — they
  // would only confuse MathLive.
  const _MATH_DELIM_RE = /\$\$([^$]+)\$\$|(?<!\\)\$([^$]+?)(?<!\\)\$/g;

  function hydrateMathInElement(host) {
    if (!host) return;
    if (typeof window.netsMathLive === "undefined") return;
    // Walk text nodes only — never re-process inside an existing math-field
    // (already a widget) or inside a contenteditable=false block (image-wrap,
    // svg-wrap, math-block — those carry their own contract).
    const SKIP = new Set(["MATH-FIELD", "SCRIPT", "STYLE", "TEXTAREA", "PRE", "CODE"]);
    const walker = document.createTreeWalker(host, NodeFilter.SHOW_TEXT, {
      acceptNode(node) {
        let cur = node.parentNode;
        while (cur && cur !== host) {
          if (cur.nodeType === 1) {
            if (SKIP.has(cur.tagName)) return NodeFilter.FILTER_REJECT;
            if (cur.classList && cur.classList.contains("math-block")) return NodeFilter.FILTER_REJECT;
            if (cur.getAttribute && cur.getAttribute("contenteditable") === "false") return NodeFilter.FILTER_REJECT;
          }
          cur = cur.parentNode;
        }
        return /\$\$?[^$]+\$\$?/.test(node.nodeValue || "") ? NodeFilter.FILTER_ACCEPT : NodeFilter.FILTER_REJECT;
      },
    });
    const targets = [];
    let n;
    while ((n = walker.nextNode())) targets.push(n);
    if (!targets.length) return;
    // Lazy-load MathLive once we know we have something to hydrate.
    window.netsMathLive.ensureLoaded().catch(() => {/* graceful fallback */});

    for (const textNode of targets) {
      const text = textNode.nodeValue;
      const frag = document.createDocumentFragment();
      let lastIdx = 0;
      _MATH_DELIM_RE.lastIndex = 0;
      let m;
      while ((m = _MATH_DELIM_RE.exec(text)) !== null) {
        const [match, dispBody, inlineBody] = m;
        const body = (dispBody || inlineBody || "").trim();
        if (!body) continue;
        const isDisplay = !!dispBody;
        if (m.index > lastIdx) {
          frag.appendChild(document.createTextNode(text.slice(lastIdx, m.index)));
        }
        const wrap = document.createElement("span");
        wrap.className = "math-block";
        wrap.setAttribute("contenteditable", "false");
        const field = window.netsMathLive.makeField({ value: body });
        if (isDisplay) field.dataset.displayMode = "true";
        wrap.appendChild(field);
        frag.appendChild(wrap);
        // Bind events so edits to the field bubble as `input` to the host editor.
        if (window.EquationPicker && typeof window.EquationPicker.bindFieldEvents === "function") {
          // host editor is the closest ancestor with class js-rich-editor.
          const ed = wrap.closest && wrap.closest(".js-rich-editor");
          if (ed) window.EquationPicker.bindFieldEvents(field, ed);
        }
        lastIdx = m.index + match.length;
      }
      if (lastIdx === 0) continue; // no replacements
      if (lastIdx < text.length) {
        frag.appendChild(document.createTextNode(text.slice(lastIdx)));
      }
      textNode.parentNode.replaceChild(frag, textNode);
    }
  }

  // ── Math serialization: <math-field> → $LaTeX$ text on save ─────
  //
  // Build a DOM snapshot of the editor where every <span.math-block> has
  // been replaced with a plain text node carrying $LaTeX$ ($$..$$ for
  // display mode). The snapshot is a fresh <div> we can hand to
  // htmlToBlocks; the live editor is left untouched.
  //
  // We can't simply cloneNode() the editor because the cloned <math-field>
  // loses its custom-element state — `clone.value` is undefined. Instead
  // we walk the live editor's childNodes, copy each one shallowly, and
  // splice math-block contents inline as we go.
  function snapshotForSerialize(editor) {
    if (!editor) return editor;
    const out = document.createElement("div");
    function walk(srcParent, dstParent) {
      for (const child of Array.from(srcParent.childNodes)) {
        if (child.nodeType === 1
            && child.classList
            && child.classList.contains("media-wrap-actions")) {
          continue;
        }
        if (child.nodeType === 1
            && child.classList
            && child.classList.contains("math-block")) {
          const field = child.querySelector("math-field");
          let latex = "";
          if (field) {
            // Live custom element — read .value (MathLive's getter).
            try { latex = String(field.value || ""); } catch (_) { latex = ""; }
            if (!latex) latex = field.getAttribute("value") || "";
          }
          latex = latex.trim();
          if (!latex) continue;
          const isDisplay = (field && field.dataset && field.dataset.displayMode === "true")
            || /^\\begin\{(pmatrix|bmatrix|vmatrix|cases|aligned|gather)\}/.test(latex);
          dstParent.appendChild(
            document.createTextNode(isDisplay ? "$$" + latex + "$$" : "$" + latex + "$"),
          );
          continue;
        }
        if (child.nodeType === 3) {
          dstParent.appendChild(document.createTextNode(child.nodeValue || ""));
          continue;
        }
        if (child.nodeType !== 1) continue;
        // Element: clone the wrapper shallowly, recurse into its children.
        const wrap = child.cloneNode(false);
        // Strip the zero-width spacer text we use as a caret-target after
        // a math-block insert so it doesn't pollute saved text.
        if (wrap.tagName === "MATH-FIELD") {
          // Stray field outside a wrap — should never happen, but recover.
          let v = "";
          try { v = String(child.value || ""); } catch (_) {}
          if (v.trim()) {
            dstParent.appendChild(document.createTextNode("$" + v.trim() + "$"));
          }
          continue;
        }
        dstParent.appendChild(wrap);
        walk(child, wrap);
      }
    }
    walk(editor, out);
    // Strip zero-width spacers used during insertion.
    out.innerHTML = (out.innerHTML || "").replace(/​/g, "");
    return out;
  }

  function isBlank(node) {
    if (!node) return true;
    if (node.nodeType === 3) return !String(node.textContent || "").trim();
    if (node.nodeType === 1) {
      const el = node;
      if (el.querySelector && (el.querySelector("img, svg, br, input, video, audio, canvas"))) return false;
      return !String(el.textContent || "").trim() && !(el.innerHTML || "").match(/<br\s*\/?>/i);
    }
    return true;
  }

  function htmlToBlocks(root) {
    const out = [];
    if (!root) return out;
    Array.from(root.childNodes).forEach((node) => {
      // Skip pure whitespace text nodes.
      if (node.nodeType === 3) {
        const txt = String(node.textContent || "").trim();
        if (!txt) return;
        out.push({ type: "p", text: escapeHtml(txt) });
        return;
      }
      if (node.nodeType !== 1) return;
      const tag = node.tagName.toLowerCase();

      if (tag === "h2") {
        if (isBlank(node)) return;
        out.push({ type: "h2", text: node.innerHTML.trim() });
        return;
      }
      if (tag === "h3") {
        // Template doesn't yet support h3 — downgrade to h2.
        if (isBlank(node)) return;
        out.push({ type: "h2", text: node.innerHTML.trim() });
        return;
      }
      if (tag === "blockquote") {
        if (isBlank(node)) return;
        out.push({ type: "quote", text: innerTextOf(node).trim() });
        return;
      }
      if (tag === "ul" || tag === "ol") {
        const items = Array.from(node.querySelectorAll(":scope > li"))
          .map((li) => li.innerHTML.trim())
          .filter((s) => s.length > 0);
        if (!items.length) return;
        out.push({ type: tag, items });
        return;
      }
      if (tag === "pre") {
        const codeEl = node.querySelector("code");
        const text = innerTextOf(codeEl || node).trim();
        if (!text) return;
        out.push({ type: "code", text });
        return;
      }
      if (tag === "img") {
        out.push({ type: "image", src: node.getAttribute("src") || "", alt: node.getAttribute("alt") || "" });
        return;
      }
      if (tag === "svg") {
        out.push({ type: "svg", html: stripScripts(node.outerHTML) });
        return;
      }
      if (tag === "div" && node.classList.contains("svg-wrap")) {
        const svg = node.querySelector("svg");
        if (svg) out.push({ type: "svg", html: stripScripts(svg.outerHTML) });
        return;
      }
      if (tag === "div" && node.classList.contains("image-wrap")) {
        const img = node.querySelector("img");
        if (img) {
          const block = {
            type: "image",
            src: img.getAttribute("src") || "",
            alt: img.getAttribute("alt") || "",
          };
          // Preserve the user-resized width on the wrapper (if any).
          const w = node.style.width;
          if (w) block.width = w;
          out.push(block);
        }
        return;
      }
      if (tag === "p") {
        // A <p> that only wraps an <img> or <svg> gets lifted into its own block.
        const children = Array.from(node.children);
        const onlyImg = children.length === 1 && children[0].tagName.toLowerCase() === "img" && !innerTextOf(node).trim();
        const onlySvg = children.length === 1 && children[0].tagName.toLowerCase() === "svg";
        if (onlyImg) {
          const img = children[0];
          out.push({ type: "image", src: img.getAttribute("src") || "", alt: img.getAttribute("alt") || "" });
          return;
        }
        if (onlySvg) {
          out.push({ type: "svg", html: stripScripts(children[0].outerHTML) });
          return;
        }
        if (isBlank(node)) return;
        out.push({ type: "p", text: node.innerHTML.trim() });
        return;
      }
      // Fallback for div/span/etc: treat as paragraph if it has content.
      if (!isBlank(node)) {
        out.push({ type: "p", text: node.innerHTML.trim() });
      }
    });
    // Ensure at least one block so data shape stays stable.
    if (!out.length) out.push({ type: "p", text: "" });
    return out;
  }

  // ---------- rendering ----------

  function originLabelUz(origin) {
    return origin === "Global" ? "Global" : "Milliy";
  }

  function renderGateQuoteSlot(gq) {
    const mode = gq.mode || "auto";
    const tab = (id, label) => `
      <button class="gate-quote-mode-btn js-gq-mode${mode === id ? " is-active" : ""}" type="button" data-gq-mode="${id}">
        ${label}
      </button>
    `;

    let body = "";
    if (mode === "auto") {
      body = `
        <div class="gate-quote-body gate-quote-body--auto">
          <p class="muted-text">
            Har safar talaba homeworkni ochganda kutubxonadan bitta iqtibos avtomatik tanlanadi.
            Tarqatish: <b>55%</b> Milliy / <b>45%</b> Global · <b>70%</b> Bilarmidingiz fakti / <b>30%</b> hikmat iqtibosi.
          </p>
          <p class="muted-text" style="margin-top:8px;">600-iqtibosli kutubxona — Mirziyoyev, Karimov, Amir Temur, Ibn Sino, al-Khwarizmi, Ulug'bek, Bobur, Tony Buzan va boshqalar.</p>
        </div>
      `;
    } else if (mode === "pinned") {
      const pid = gq.pinned_id;
      const preview = gq.pinned_preview || null;
      if (preview && preview.text) {
        const originClass =
          preview.origin === "Global" ? "quote-chip-origin-global" : "quote-chip-origin-national";
        body = `
          <div class="gate-quote-body gate-quote-body--pinned">
            <div class="quote-card-preview">
              <div class="quote-card-preview-text">${escapeHtml(preview.text)}</div>
              <div class="quote-card-preview-meta">
                <span class="quote-card-preview-author">— ${escapeHtml(preview.author || "")}</span>
                <span class="quote-picker-chip ${originClass}">${escapeHtml(originLabelUz(preview.origin))}</span>
                ${pid != null ? `<span class="quote-picker-chip">#${escapeHtml(pid)}</span>` : ""}
              </div>
            </div>
            <div class="inline-actions">
              <button class="btn btn-ghost js-gq-pick" type="button">Boshqasini tanlash…</button>
              <button class="btn btn-ghost js-gq-clear" type="button">Avtomatga qaytish</button>
            </div>
          </div>
        `;
      } else {
        body = `
          <div class="gate-quote-body gate-quote-body--pinned-empty">
            <p class="muted-text">Hech narsa biriktirilmagan. Kutubxonadan iqtibos tanlang.</p>
            <button class="btn btn-primary js-gq-pick" type="button">Kutubxonani ochish</button>
          </div>
        `;
      }
    } else {
      // custom
      const c = gq.custom || { text: "", author: "" };
      body = `
        <div class="gate-quote-body gate-quote-body--custom">
          <label class="field">
            <span>Iqtibos matni</span>
            <textarea class="js-gq-custom-text form-input" rows="3" placeholder="Iqtibos matnini yozing">${escapeHtml(c.text)}</textarea>
          </label>
          <label class="field">
            <span>Muallif (ixtiyoriy)</span>
            <input class="js-gq-custom-author form-input" type="text" value="${escapeHtml(c.author)}" placeholder="Muallif ismi" />
          </label>
        </div>
      `;
    }

    return `
      <div class="gate-quote-modes" role="tablist">
        ${tab("auto", "Avtomatik")}
        ${tab("pinned", "Kutubxonadan")}
        ${tab("custom", "Maxsus")}
      </div>
      ${body}
    `;
  }

  function renderToolbar() {
    return `
      <div class="rich-toolbar" role="toolbar" aria-label="Formatting toolbar">
        <button type="button" class="js-rich-btn" data-cmd="h2" title="Heading 2">H2</button>
        <button type="button" class="js-rich-btn" data-cmd="h3" title="Heading 3">H3</button>
        <span class="rich-sep"></span>
        <button type="button" class="js-rich-btn" data-cmd="bold" title="Bold (Ctrl+B)"><b>B</b></button>
        <button type="button" class="js-rich-btn" data-cmd="italic" title="Italic (Ctrl+I)"><i>I</i></button>
        <button type="button" class="js-rich-btn" data-cmd="code" title="Inline code">&lt;/&gt;</button>
        <span class="rich-sep"></span>
        <button type="button" class="js-rich-btn" data-cmd="quote" title="Blockquote">&ldquo;</button>
        <button type="button" class="js-rich-btn" data-cmd="ul" title="Bullet list">• List</button>
        <button type="button" class="js-rich-btn" data-cmd="ol" title="Numbered list">1. List</button>
        <span class="rich-sep"></span>
        <button type="button" class="js-rich-btn rich-btn-wide" data-cmd="equation" title="Insert equation (Σ)" aria-haspopup="dialog">Σ Math</button>
        <button type="button" class="js-rich-btn rich-btn-wide" data-cmd="image" title="Insert image">🖼 Image</button>
        <button type="button" class="js-rich-btn rich-btn-wide" data-cmd="svg" title="Insert SVG">◆ SVG</button>
      </div>
    `;
  }

  function renderPage(page, panelIndex, pageIndex) {
    const html = blocksToHtml(asArray(page.blocks));
    return `
      <div class="editor-card page-card" data-panel-index="${panelIndex}" data-page-index="${pageIndex}">
        <div class="editor-header compact-header">
          <div>
            <p class="eyebrow">Page ${pageIndex + 1}</p>
            <h3>Rich content</h3>
          </div>
          <div class="inline-actions">
            <button class="btn btn-danger js-remove-page" type="button">Remove page</button>
          </div>
        </div>
        ${renderToolbar()}
        <div
          class="rich-editor js-rich-editor"
          contenteditable="true"
          spellcheck="true"
          data-placeholder="Bosqich matnini yozing..."
          data-panel-index="${panelIndex}"
          data-page-index="${pageIndex}"
        >${html}</div>
      </div>
    `;
  }

  function renderPanel(panel, panelIndex) {
    const pages = asArray(panel.pages);
    return `
      <section class="editor-card panel-editor-card" data-panel-index="${panelIndex}">
        <div class="editor-header">
          <div>
            <p class="eyebrow">Panel ${panelIndex + 1}</p>
            <h3>${escapeHtml(panel.title || "Untitled panel")}</h3>
          </div>
          <div class="inline-actions">
            <button class="btn btn-ghost js-add-page" type="button">Add page</button>
            <button class="btn btn-danger js-remove-panel" type="button">Remove panel</button>
          </div>
        </div>
        <div class="editor-grid">
          <label class="field">
            <span>Panel ID</span>
            <input class="js-panel-id" type="number" min="1" value="${escapeHtml(panel.id)}" />
          </label>
          <label class="field">
            <span>Panel title</span>
            <input class="js-panel-title" type="text" value="${escapeHtml(panel.title)}" />
          </label>
        </div>
        <div class="editor-list page-list">
          ${pages.map((page, pageIndex) => renderPage(page, panelIndex, pageIndex)).join("")}
        </div>
      </section>
    `;
  }

  // ---------- Image modal ----------

  function openImageModal(onInsert) {
    const backdrop = document.createElement("div");
    backdrop.className = "svg-insert-modal";
    backdrop.innerHTML = `
      <div class="svg-insert-modal-card" role="dialog" aria-modal="true">
        <h3 style="margin:0 0 8px 0;">Insert Image</h3>
        <p class="muted-text" style="margin:0 0 16px 0;">Upload a file or paste an image URL.</p>

        <div class="image-upload-dropzone js-image-drop">
          <input type="file" class="js-image-file" accept="image/*" hidden />
          <div class="image-upload-cta">
            <div style="font-size:28px;line-height:1;">🖼</div>
            <div style="margin-top:8px;font-weight:600;">Click to choose or drop an image</div>
            <div class="muted-text" style="margin-top:4px;font-size:12px;">PNG, JPG, GIF, WEBP, SVG — stored as data URI</div>
          </div>
          <img class="js-image-preview" alt="" hidden />
        </div>

        <div style="display:flex;align-items:center;gap:10px;margin:14px 0;">
          <div style="flex:1;height:1px;background:var(--border);"></div>
          <div class="muted-text" style="font-size:11px;letter-spacing:.08em;">OR</div>
          <div style="flex:1;height:1px;background:var(--border);"></div>
        </div>

        <label class="field" style="margin-bottom:10px;">
          <span>Image URL</span>
          <input type="text" class="js-image-url form-input" placeholder="https://…" />
        </label>
        <label class="field">
          <span>Alt text (optional)</span>
          <input type="text" class="js-image-alt form-input" placeholder="Describe the image" />
        </label>

        <div style="display:flex;justify-content:flex-end;gap:8px;margin-top:18px;">
          <button type="button" class="btn btn-ghost js-image-cancel">Cancel</button>
          <button type="button" class="btn btn-primary js-image-insert">Insert</button>
        </div>
      </div>`;
    document.body.appendChild(backdrop);

    const dropzone = backdrop.querySelector(".js-image-drop");
    const fileInput = backdrop.querySelector(".js-image-file");
    const previewImg = backdrop.querySelector(".js-image-preview");
    const urlInput = backdrop.querySelector(".js-image-url");
    const altInput = backdrop.querySelector(".js-image-alt");
    const ctaBlock = backdrop.querySelector(".image-upload-cta");

    let dataUri = null;
    function showPreview(src) {
      previewImg.src = src;
      previewImg.hidden = false;
      ctaBlock.style.display = "none";
    }
    function handleFile(file) {
      if (!file || !file.type.startsWith("image/")) return;
      const reader = new FileReader();
      reader.onload = () => {
        dataUri = reader.result;
        urlInput.value = "";
        showPreview(dataUri);
      };
      reader.readAsDataURL(file);
    }

    dropzone.addEventListener("click", (e) => {
      if (e.target.tagName.toLowerCase() === "img") return;
      fileInput.click();
    });
    fileInput.addEventListener("change", () => handleFile(fileInput.files && fileInput.files[0]));
    dropzone.addEventListener("dragover", (e) => {
      e.preventDefault();
      dropzone.classList.add("dragover");
    });
    dropzone.addEventListener("dragleave", () => dropzone.classList.remove("dragover"));
    dropzone.addEventListener("drop", (e) => {
      e.preventDefault();
      dropzone.classList.remove("dragover");
      const f = e.dataTransfer.files && e.dataTransfer.files[0];
      handleFile(f);
    });
    urlInput.addEventListener("input", () => {
      if (urlInput.value.trim()) {
        dataUri = null;
        showPreview(urlInput.value.trim());
      }
    });

    function close() { backdrop.remove(); }
    backdrop.addEventListener("click", (e) => { if (e.target === backdrop) close(); });
    backdrop.querySelector(".js-image-cancel").addEventListener("click", close);
    backdrop.querySelector(".js-image-insert").addEventListener("click", () => {
      const src = dataUri || urlInput.value.trim();
      if (!src) return close();
      onInsert(src, altInput.value.trim());
      close();
    });
  }

  // ---------- SVG modal ----------

  function openSvgModal(onInsert) {
    const backdrop = document.createElement("div");
    backdrop.className = "svg-insert-modal";
    backdrop.innerHTML = `
      <div class="svg-insert-modal-card" role="dialog" aria-modal="true">
        <h3 style="margin:0 0 12px 0;">Insert SVG</h3>
        <p class="muted-text" style="margin:0 0 12px 0;">Paste raw SVG code. &lt;script&gt; tags will be stripped.</p>
        <textarea placeholder='<svg xmlns="http://www.w3.org/2000/svg" ...>...</svg>'></textarea>
        <div style="display:flex;justify-content:flex-end;gap:8px;margin-top:16px;">
          <button type="button" class="btn btn-ghost js-svg-cancel">Cancel</button>
          <button type="button" class="btn btn-primary js-svg-insert">Insert</button>
        </div>
      </div>`;
    document.body.appendChild(backdrop);
    const textarea = backdrop.querySelector("textarea");
    textarea.focus();
    function close() {
      backdrop.remove();
    }
    backdrop.addEventListener("click", (e) => {
      if (e.target === backdrop) close();
    });
    backdrop.querySelector(".js-svg-cancel").addEventListener("click", close);
    backdrop.querySelector(".js-svg-insert").addEventListener("click", () => {
      const raw = textarea.value.trim();
      if (!raw) return close();
      onInsert(stripScripts(raw));
      close();
    });
  }

  // ---------- selection helpers ----------

  function saveSelection(editor) {
    const sel = window.getSelection();
    if (!sel || sel.rangeCount === 0) return null;
    const range = sel.getRangeAt(0);
    // Only save if the range is inside our editor
    if (!editor.contains(range.commonAncestorContainer)) return null;
    return range.cloneRange();
  }

  function restoreSelection(editor, savedRange) {
    editor.focus();
    const sel = window.getSelection();
    sel.removeAllRanges();
    if (savedRange) {
      sel.addRange(savedRange);
    } else {
      // Fallback: place caret at end of editor
      const range = document.createRange();
      range.selectNodeContents(editor);
      range.collapse(false);
      sel.addRange(range);
    }
  }

  function insertBlockAtCaret(editor, htmlString) {
    const sel = window.getSelection();
    if (!sel || sel.rangeCount === 0) {
      editor.insertAdjacentHTML("beforeend", htmlString);
      return;
    }
    const range = sel.getRangeAt(0);
    range.deleteContents();

    // Parse the HTML fragment
    const temp = document.createElement("div");
    temp.innerHTML = htmlString;
    const frag = document.createDocumentFragment();
    let lastNode = null;
    while (temp.firstChild) {
      lastNode = frag.appendChild(temp.firstChild);
    }

    // If the caret sits inside an inline element (like <p> or <span>), we need to
    // insert AFTER the containing block so the new block doesn't end up nested inside it.
    let container = range.startContainer;
    // Climb up to the editor's direct child (block level)
    let blockAncestor = container.nodeType === 1 ? container : container.parentNode;
    while (blockAncestor && blockAncestor.parentNode !== editor) {
      blockAncestor = blockAncestor.parentNode;
    }

    if (blockAncestor && blockAncestor.parentNode === editor) {
      // Insert our block AFTER the current block-level ancestor
      if (blockAncestor.nextSibling) {
        editor.insertBefore(frag, blockAncestor.nextSibling);
      } else {
        editor.appendChild(frag);
      }
    } else {
      // Fallback: insert at range
      range.insertNode(frag);
    }

    // Place caret after the inserted content
    if (lastNode) {
      const newRange = document.createRange();
      newRange.setStartAfter(lastNode);
      newRange.collapse(true);
      sel.removeAllRanges();
      sel.addRange(newRange);
    }
  }

  // ---------- main render ----------

  function render(container, data, onChange) {
    const state = normalizeData(data);

    function emit() {
      onChange(clone(state));
    }

    function repaint() {
      container.innerHTML = `
        <div class="editor-list">
          <section class="editor-card">
            <div class="editor-header">
              <div>
                <p class="eyebrow">Preview metadata</p>
                <h3>Title and caption</h3>
              </div>
            </div>
            <div class="editor-grid">
              <label class="field">
                <span>Title</span>
                <input class="js-meta" data-meta-key="title" type="text" value="${escapeHtml(state.meta.title)}" placeholder="Kvadrat tenglama" />
              </label>
              <label class="field">
                <span>Subject display</span>
                <input class="js-meta" data-meta-key="subject_display" type="text" value="${escapeHtml(state.meta.subject_display)}" placeholder="Algebra" />
              </label>
              <label class="field">
                <span>Section</span>
                <input class="js-meta" data-meta-key="section" type="text" value="${escapeHtml(state.meta.section)}" placeholder="22-§" />
              </label>
              <label class="field">
                <span>CEFR level</span>
                <input class="js-meta" data-meta-key="cefr_level" type="text" value="${escapeHtml(state.meta.cefr_level)}" placeholder="B1" />
              </label>
            </div>
          </section>

          <section class="editor-card gate-quote-slot">
            <div class="editor-header">
              <div>
                <p class="eyebrow">Phase 0-A · Gate Quote</p>
                <h3>Ochilish iqtibosi</h3>
              </div>
            </div>
            ${renderGateQuoteSlot(state.gate_quote)}
          </section>

          <section class="editor-card">
            <div class="editor-header">
              <div>
                <p class="eyebrow">Panels</p>
                <h3>${state.panels.length} panel${state.panels.length === 1 ? "" : "s"}</h3>
              </div>
              <button class="btn btn-primary js-add-panel" type="button">Add panel</button>
            </div>
          </section>

          ${
            state.panels.length
              ? state.panels.map((panel, i) => renderPanel(panel, i)).join("")
              : `<div class="empty-state glass-card inline-empty">
                  <div class="empty-orb" aria-hidden="true">📋</div>
                  <h3>No panels yet</h3>
                  <p>Add a panel to start building the preview section.</p>
                  <button class="btn btn-primary js-add-panel" type="button">Add first panel</button>
                </div>`
          }
        </div>`;
      // After every paint, hydrate $LaTeX$ text inside the rich editors
      // into <math-field> WYSIWYG widgets. Idempotent — already-hydrated
      // text stays inside math-block wrappers which the walker skips.
      const editors = container.querySelectorAll(".js-rich-editor");
      editors.forEach((ed) => {
        try { hydrateMathInElement(ed); } catch (_) {}
      });
    }

    function panelIndexOf(el) {
      return Number(el.closest("[data-panel-index]")?.dataset.panelIndex);
    }
    function pageIndexOf(el) {
      return Number(el.closest("[data-page-index]")?.dataset.pageIndex);
    }

    function syncEditor(editor) {
      const pi = Number(editor.dataset.panelIndex);
      const gi = Number(editor.dataset.pageIndex);
      if (Number.isNaN(pi) || Number.isNaN(gi)) return;
      // Take a snapshot where math-blocks have been collapsed into $LaTeX$
      // text BEFORE running htmlToBlocks. This keeps storage compatible
      // with the existing runtime KaTeX render path — no schema change.
      const snap = (typeof snapshotForSerialize === "function")
        ? snapshotForSerialize(editor)
        : editor;
      const blocks = htmlToBlocks(snap);
      state.panels[pi].pages[gi].blocks = blocks;
      emit();
    }

    function runCommand(editor, cmd) {
      editor.focus();
      if (cmd === "bold" || cmd === "italic") {
        document.execCommand(cmd);
      } else if (cmd === "ul") {
        document.execCommand("insertUnorderedList");
      } else if (cmd === "ol") {
        document.execCommand("insertOrderedList");
      } else if (cmd === "h2" || cmd === "h3") {
        // Toggle: if already in the heading, switch back to P.
        const sel = window.getSelection();
        if (sel && sel.anchorNode) {
          let node = sel.anchorNode.nodeType === 1 ? sel.anchorNode : sel.anchorNode.parentNode;
          while (node && node !== editor && node.tagName) {
            if (node.tagName.toLowerCase() === cmd) {
              document.execCommand("formatBlock", false, "P");
              return;
            }
            node = node.parentNode;
          }
        }
        document.execCommand("formatBlock", false, cmd.toUpperCase());
      } else if (cmd === "quote") {
        // Toggle: if caret is inside a <blockquote>, switch back to P.
        const sel = window.getSelection();
        if (sel && sel.anchorNode) {
          let node = sel.anchorNode.nodeType === 1 ? sel.anchorNode : sel.anchorNode.parentNode;
          while (node && node !== editor && node.tagName) {
            if (node.tagName.toLowerCase() === "blockquote") {
              document.execCommand("formatBlock", false, "P");
              return;
            }
            node = node.parentNode;
          }
        }
        document.execCommand("formatBlock", false, "BLOCKQUOTE");
      } else if (cmd === "code") {
        const sel = window.getSelection();
        if (!sel || !sel.rangeCount) return;
        const range = sel.getRangeAt(0);

        // Find if selection anchor is inside a <code> ancestor (up to editor root).
        function findCodeAncestor(node) {
          while (node && node !== editor) {
            if (node.nodeType === 1 && node.tagName && node.tagName.toLowerCase() === "code") {
              return node;
            }
            node = node.parentNode;
          }
          return null;
        }

        const anchorEl = sel.anchorNode && sel.anchorNode.nodeType === 1
          ? sel.anchorNode
          : (sel.anchorNode && sel.anchorNode.parentNode);
        const existingCode = findCodeAncestor(anchorEl);

        if (existingCode) {
          // UNWRAP: replace <code>text</code> with plain text node, place caret after it.
          const parent = existingCode.parentNode;
          const textNode = document.createTextNode(existingCode.textContent.replace(/​/g, ""));
          parent.insertBefore(textNode, existingCode);
          parent.removeChild(existingCode);
          sel.removeAllRanges();
          const r2 = document.createRange();
          r2.setStartAfter(textNode);
          r2.collapse(true);
          sel.addRange(r2);
        } else if (range.collapsed) {
          // No selection and not inside code: insert empty <code> with caret inside.
          const code = document.createElement("code");
          code.appendChild(document.createTextNode("​"));
          range.insertNode(code);
          const r2 = document.createRange();
          r2.setStart(code.firstChild, 1);
          r2.collapse(true);
          sel.removeAllRanges();
          sel.addRange(r2);
        } else {
          // Wrap the selected text in <code>.
          const text = range.toString();
          const code = document.createElement("code");
          code.textContent = text;
          range.deleteContents();
          range.insertNode(code);
          sel.removeAllRanges();
          const r2 = document.createRange();
          r2.setStartAfter(code);
          r2.collapse(true);
          sel.addRange(r2);
        }
      } else if (cmd === "equation") {
        // Open the MathLive picker. If the caret is inside an existing
        // math-field, the picker targets it (insert symbol into existing
        // equation). Otherwise the picker mounts a fresh math-field at
        // the caret on the first tile click.
        if (!window.EquationPicker || !window.EquationSymbols || !window.netsMathLive) {
          // Fail-soft: dependent module missing — do nothing rather than
          // alert. Static cache-bust tests verify these are loaded.
          return;
        }
        const card = editor.closest(".page-card");
        const trigger = card && card.querySelector('.js-rich-btn[data-cmd="equation"]');
        // Pre-check: if the caret currently sits inside a math-field, hand
        // that field to the picker so tile clicks insert into it instead
        // of mounting a new equation.
        let activeMathField = null;
        if (document.activeElement && document.activeElement.tagName === "MATH-FIELD"
            && editor.contains(document.activeElement)) {
          activeMathField = document.activeElement;
        }
        window.EquationPicker.open({
          anchor: trigger || editor,
          editor,
          activeMathField,
          onInsert: () => syncEditor(editor),
        });
        return;
      } else if (cmd === "image") {
        // Save selection BEFORE the modal opens.
        const savedRange = saveSelection(editor);
        openImageModal((src, alt) => {
          restoreSelection(editor, savedRange);
          const safeSrc = String(src).replace(/"/g, "&quot;");
          const safeAlt = String(alt || "").replace(/"/g, "&quot;");
          insertBlockAtCaret(
            editor,
            `<div class="image-wrap" contenteditable="false" draggable="true">${mediaActionsHtml("image")}<img src="${safeSrc}" alt="${safeAlt}"></div><p><br></p>`,
          );
          syncEditor(editor);
        });
        return; // async, sync happens in callback
      } else if (cmd === "svg") {
        // Save selection BEFORE the modal opens (modal steals focus).
        const savedRange = saveSelection(editor);
        openSvgModal((svgCode) => {
          restoreSelection(editor, savedRange);
          // Wrap SVG in a block-level container so it lands on its own line and is movable.
          insertBlockAtCaret(editor, `<div class="svg-wrap" contenteditable="false" draggable="true">${mediaActionsHtml("svg")}${svgCode}</div><p><br></p>`);
          syncEditor(editor);
        });
        return; // async, sync happens in callback
      }
      syncEditor(editor);
    }

    // ---- drag-to-reorder for .svg-wrap and .image-wrap inside rich editors ----

    let draggedSvgWrap = null;

    function ensureEditableParagraph(editor) {
      if (!editor) return;
      const hasEditable = Array.from(editor.childNodes).some((node) => {
        if (node.nodeType === 3) return String(node.textContent || "").trim();
        if (node.nodeType !== 1) return false;
        return !(node.classList && (node.classList.contains("image-wrap") || node.classList.contains("svg-wrap")));
      });
      if (!hasEditable) editor.insertAdjacentHTML("beforeend", "<p><br></p>");
    }

    function replaceMediaWrap(wrap, editor) {
      if (!wrap || !editor) return;
      if (wrap.classList.contains("image-wrap")) {
        openImageModal((src, alt) => {
          const img = wrap.querySelector("img");
          if (!img) return;
          img.setAttribute("src", String(src || ""));
          img.setAttribute("alt", String(alt || ""));
          syncEditor(editor);
        });
        return;
      }
      if (wrap.classList.contains("svg-wrap")) {
        openSvgModal((svgCode) => {
          const actions = wrap.querySelector(".media-wrap-actions");
          wrap.innerHTML = "";
          if (actions) wrap.appendChild(actions);
          wrap.insertAdjacentHTML("beforeend", svgCode);
          syncEditor(editor);
        });
      }
    }

    function removeMediaWrap(wrap, editor) {
      if (!wrap || !editor) return;
      wrap.remove();
      ensureEditableParagraph(editor);
      syncEditor(editor);
    }

    container.addEventListener("mousedown", (event) => {
      if (event.target.closest && event.target.closest(".media-wrap-actions")) {
        event.preventDefault();
        event.stopPropagation();
      }
    });

    container.addEventListener("click", (event) => {
      const action = event.target.closest && event.target.closest(".js-media-remove, .js-media-replace");
      if (!action) return;
      const wrap = action.closest(".svg-wrap, .image-wrap");
      const editor = action.closest(".js-rich-editor");
      if (!wrap || !editor) return;
      event.preventDefault();
      event.stopPropagation();
      if (action.classList.contains("js-media-remove")) removeMediaWrap(wrap, editor);
      else replaceMediaWrap(wrap, editor);
    });

    container.addEventListener("dragstart", (event) => {
      if (event.target.closest && event.target.closest(".media-wrap-actions")) return;
      const wrap = event.target.closest && event.target.closest(".svg-wrap, .image-wrap");
      if (!wrap) return;
      draggedSvgWrap = wrap;
      event.dataTransfer.effectAllowed = "move";
      // Firefox requires setData to start a drag
      try { event.dataTransfer.setData("text/plain", "svg-block"); } catch (e) {}
      wrap.style.opacity = "0.4";
    });

    container.addEventListener("dragend", (event) => {
      if (draggedSvgWrap) {
        draggedSvgWrap.style.opacity = "";
        draggedSvgWrap = null;
      }
      // Clean up drag-over markers
      container.querySelectorAll(".drag-over-top, .drag-over-bottom").forEach((el) => {
        el.classList.remove("drag-over-top", "drag-over-bottom");
      });
    });

    container.addEventListener("dragover", (event) => {
      if (!draggedSvgWrap) return;
      const editor = event.target.closest && event.target.closest(".js-rich-editor");
      if (!editor || !editor.contains(draggedSvgWrap)) return;
      event.preventDefault();
      event.dataTransfer.dropEffect = "move";

      // Find nearest direct child of editor under the pointer
      const y = event.clientY;
      let target = null;
      for (const child of editor.children) {
        if (child === draggedSvgWrap) continue;
        const rect = child.getBoundingClientRect();
        if (y >= rect.top && y <= rect.bottom) { target = child; break; }
      }
      // Clear previous markers
      editor.querySelectorAll(".drag-over-top, .drag-over-bottom").forEach((el) => {
        el.classList.remove("drag-over-top", "drag-over-bottom");
      });
      if (target) {
        const rect = target.getBoundingClientRect();
        const midY = rect.top + rect.height / 2;
        target.classList.add(y < midY ? "drag-over-top" : "drag-over-bottom");
      }
    });

    container.addEventListener("drop", (event) => {
      if (!draggedSvgWrap) return;
      const editor = event.target.closest && event.target.closest(".js-rich-editor");
      if (!editor || !editor.contains(draggedSvgWrap)) return;
      event.preventDefault();

      const y = event.clientY;
      let target = null;
      for (const child of editor.children) {
        if (child === draggedSvgWrap) continue;
        const rect = child.getBoundingClientRect();
        if (y >= rect.top && y <= rect.bottom) { target = child; break; }
      }
      if (target) {
        const rect = target.getBoundingClientRect();
        const midY = rect.top + rect.height / 2;
        if (y < midY) {
          editor.insertBefore(draggedSvgWrap, target);
        } else {
          editor.insertBefore(draggedSvgWrap, target.nextSibling);
        }
      } else {
        // Dropped past the last child: append
        editor.appendChild(draggedSvgWrap);
      }
      // Sync and clean up
      editor.querySelectorAll(".drag-over-top, .drag-over-bottom").forEach((el) => {
        el.classList.remove("drag-over-top", "drag-over-bottom");
      });
      syncEditor(editor);
    });

    // ---- resize capture for image-wrap (native CSS resize handle) ----

    const resizeTracker = new WeakMap(); // wrap element -> {w, h}

    container.addEventListener("mousedown", (event) => {
      const wrap = event.target.closest && event.target.closest(".image-wrap");
      if (!wrap) return;
      resizeTracker.set(wrap, {
        w: wrap.offsetWidth,
        h: wrap.offsetHeight,
        editor: event.target.closest(".js-rich-editor"),
      });
    });

    container.addEventListener("mouseup", (event) => {
      const wrap = event.target.closest && event.target.closest(".image-wrap");
      if (!wrap) return;
      const prev = resizeTracker.get(wrap);
      if (!prev) return;
      resizeTracker.delete(wrap);
      const curW = wrap.offsetWidth;
      const curH = wrap.offsetHeight;
      // Only save if dimensions actually changed (i.e., user resized, not just clicked)
      if (curW !== prev.w || curH !== prev.h) {
        // Persist inline width so the value survives round-trips.
        wrap.style.width = curW + "px";
        if (prev.editor) syncEditor(prev.editor);
      }
    });

    // ---- event wiring ----

    container.addEventListener("input", (event) => {
      const target = event.target;

      if (target.matches(".js-meta")) {
        state.meta[target.dataset.metaKey] = target.value;
        emit();
        return;
      }
      if (target.matches(".js-gq-custom-text")) {
        if (!state.gate_quote.custom) state.gate_quote.custom = { text: "", author: "" };
        state.gate_quote.custom.text = target.value;
        emit();
        return;
      }
      if (target.matches(".js-gq-custom-author")) {
        if (!state.gate_quote.custom) state.gate_quote.custom = { text: "", author: "" };
        state.gate_quote.custom.author = target.value;
        emit();
        return;
      }
      if (target.matches(".js-panel-id")) {
        state.panels[panelIndexOf(target)].id = Number(target.value || 0);
        emit();
        return;
      }
      if (target.matches(".js-panel-title")) {
        state.panels[panelIndexOf(target)].title = target.value;
        emit();
        return;
      }
      if (target.matches(".js-rich-editor")) {
        // Debounce per editor via requestAnimationFrame to avoid thrashing.
        if (target._rafId) cancelAnimationFrame(target._rafId);
        target._rafId = requestAnimationFrame(() => syncEditor(target));
      }
    });

    container.addEventListener("blur", (event) => {
      const target = event.target;
      if (target && target.matches && target.matches(".js-rich-editor")) {
        syncEditor(target);
      }
    }, true);

    // Paste auto-correction: intercept paste inside rich editors, sanitize HTML
    // (strip Word/Docs styles, normalize headings, unwrap spans/fonts, etc.),
    // then insert the cleaned fragment at the caret. Non-rich fields paste normally.
    container.addEventListener("paste", (event) => {
      const editor = event.target.closest && event.target.closest(".js-rich-editor");
      if (!editor) return;
      event.preventDefault();
      const cd = event.clipboardData || window.clipboardData;
      if (!cd) return;

      let html = "";
      try { html = cd.getData("text/html") || ""; } catch (e) { html = ""; }

      let cleaned = "";
      if (html) {
        cleaned = sanitizePastedHtml(html);
      } else {
        let plain = "";
        try { plain = cd.getData("text/plain") || ""; } catch (e) { plain = ""; }
        cleaned = plainTextToHtml(plain);
      }
      if (!cleaned) return;

      try {
        document.execCommand("insertHTML", false, cleaned);
      } catch (e) {
        // Fallback: append at caret via manual insertion.
        const sel = window.getSelection();
        if (sel && sel.rangeCount) {
          const range = sel.getRangeAt(0);
          range.deleteContents();
          const tmp = document.createElement("div");
          tmp.innerHTML = cleaned;
          const frag = document.createDocumentFragment();
          while (tmp.firstChild) frag.appendChild(tmp.firstChild);
          range.insertNode(frag);
          range.collapse(false);
        } else {
          editor.insertAdjacentHTML("beforeend", cleaned);
        }
      }
      syncEditor(editor);
    });

    container.addEventListener("click", (event) => {
      const target = event.target;

      const richBtn = target.closest(".js-rich-btn");
      if (richBtn) {
        const editor = richBtn.closest(".page-card").querySelector(".js-rich-editor");
        if (editor) runCommand(editor, richBtn.dataset.cmd);
        return;
      }

      const modeBtn = target.closest(".js-gq-mode");
      if (modeBtn) {
        const next = modeBtn.dataset.gqMode || "auto";
        if (state.gate_quote.mode !== next) {
          state.gate_quote.mode = next;
          if (next === "custom" && !state.gate_quote.custom) {
            state.gate_quote.custom = { text: "", author: "" };
          }
          emit();
          repaint();
        }
        return;
      }
      if (target.closest(".js-gq-pick")) {
        if (!window.QuotePicker) return;
        const currentPin = state.gate_quote.mode === "pinned" ? state.gate_quote.pinned_id : null;
        window.QuotePicker.open({
          pinnedId: currentPin,
          onPick: (entry) => {
            state.gate_quote = {
              mode: "pinned",
              pinned_id: Number(entry.id),
              pinned_preview: {
                text: String(entry.text || ""),
                author: String(entry.author || ""),
                origin: String(entry.origin || "National"),
                type: String(entry.type || "fact"),
              },
            };
            emit();
            repaint();
          },
        });
        return;
      }
      if (target.closest(".js-gq-clear")) {
        state.gate_quote = { mode: "auto" };
        emit();
        repaint();
        return;
      }
      if (target.closest(".js-add-panel")) {
        state.panels.push(makeEmptyPanel(getNextPanelId(state.panels)));
        emit();
        repaint();
        return;
      }
      if (target.closest(".js-remove-panel")) {
        state.panels.splice(panelIndexOf(target), 1);
        emit();
        repaint();
        return;
      }
      if (target.closest(".js-add-page")) {
        state.panels[panelIndexOf(target)].pages.push(makeEmptyPage());
        emit();
        repaint();
        return;
      }
      if (target.closest(".js-remove-page")) {
        const pi = panelIndexOf(target);
        const gi = pageIndexOf(target);
        state.panels[pi].pages.splice(gi, 1);
        if (!state.panels[pi].pages.length) state.panels[pi].pages.push(makeEmptyPage());
        emit();
        repaint();
      }
    });

    // Ctrl/Cmd+B and Ctrl/Cmd+I work natively on contenteditable, but we resync on keyup.
    container.addEventListener("keyup", (event) => {
      const target = event.target;
      if (target && target.matches && target.matches(".js-rich-editor")) {
        if (target._rafId) cancelAnimationFrame(target._rafId);
        target._rafId = requestAnimationFrame(() => syncEditor(target));
      }
    });

    repaint();
  }

  window.Editors.preview = { render };
})();
