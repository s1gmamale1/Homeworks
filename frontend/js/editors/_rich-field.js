// frontend/js/editors/_rich-field.js
// Reusable compact rich-text field — contenteditable + mini toolbar (B, I, Image, SVG).
// Used by memory-sprint, flashcards (def), boss (q), real-life (story + q prompts),
// reading (passage + checkpoints), adaptive-quiz (q), sentence-fill (q).
//
// Exposes:
//   window.RichField.create({value, onChange, placeholder, compact}) => HTMLElement
//
// Distinct class name `.js-rich-mini` (vs `.js-rich-editor` used by Preview) so
// the Preview-specific drag-to-reorder handler doesn't fire here.

(function () {
  "use strict";

  window.RichField = window.RichField || {};

  // ---------- helpers ----------

  function stripScripts(html) {
    return String(html || "")
      .replace(/<script\b[^>]*>[\s\S]*?<\/script>/gi, "")
      .replace(/\son[a-z]+\s*=\s*"[^"]*"/gi, "")
      .replace(/\son[a-z]+\s*=\s*'[^']*'/gi, "")
      .replace(/\son[a-z]+\s*=\s*[^\s>]+/gi, "");
  }

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
    return String(text || "")
      .split(/\n\s*\n/)
      .map((chunk) =>
        chunk
          .trim()
          .split("\n")
          .map((line) =>
            line.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;"),
          )
          .join("<br>"),
      )
      .filter(Boolean)
      .map((p) => `<p>${p}</p>`)
      .join("");
  }

  // Sanitize any HTML (initial value OR pasted) to an allowlisted subset.
  function cleanNode(root) {
    const commentWalker = document.createTreeWalker(root, NodeFilter.SHOW_COMMENT);
    const comments = [];
    while (commentWalker.nextNode()) comments.push(commentWalker.currentNode);
    for (const c of comments) { if (c.parentNode) c.parentNode.removeChild(c); }

    const all = Array.from(root.querySelectorAll("*"));
    const DANGEROUS = [
      "script", "style", "link", "meta", "iframe", "object", "embed",
      "form", "input", "button", "select", "textarea", "noscript", "base",
    ];
    const ALLOWED = [
      "p", "ul", "ol", "li",
      "b", "i", "u", "code", "br", "img", "div",
    ];

    for (const el of all) {
      if (!el.isConnected && !root.contains(el)) continue;
      const tag = (el.tagName || "").toLowerCase();
      if (!tag) continue;

      if (DANGEROUS.includes(tag)) { el.remove(); continue; }

      if (tag.includes(":") || tag.startsWith("o-") || tag.startsWith("w-") || tag.startsWith("v-")) {
        unwrap(el);
        continue;
      }

      const isImageWrap = tag === "div" && el.classList && el.classList.contains("image-wrap");
      const isSvgWrap = tag === "div" && el.classList && el.classList.contains("svg-wrap");

      const attrs = Array.from(el.attributes).map((a) => a.name);
      for (const name of attrs) {
        const keep =
          (tag === "img" && (name === "src" || name === "alt")) ||
          (isImageWrap && (name === "class" || name === "contenteditable" || name === "draggable" || name === "style")) ||
          (isSvgWrap && (name === "class" || name === "contenteditable" || name === "draggable"));
        if (keep) {
          if (name === "src" || name === "href") {
            const val = String(el.getAttribute(name) || "").trim().toLowerCase();
            if (val.startsWith("javascript:")) { el.remove(); break; }
          }
          // For image-wrap style, only keep width.
          if (isImageWrap && name === "style") {
            const styleVal = String(el.getAttribute("style") || "");
            const widthMatch = styleVal.match(/width\s*:\s*[^;]+/i);
            if (widthMatch) {
              el.setAttribute("style", widthMatch[0]);
            } else {
              el.removeAttribute("style");
            }
          }
          continue;
        }
        el.removeAttribute(name);
      }
      if (!el.isConnected && !root.contains(el)) continue;

      // Normalize headings down to <b> since compact field isn't for big headings.
      if (tag === "h1" || tag === "h2" || tag === "h3" || tag === "h4" || tag === "h5" || tag === "h6") {
        renameTag(el, "p");
        continue;
      }
      if (tag === "strong") { renameTag(el, "b"); continue; }
      if (tag === "em") { renameTag(el, "i"); continue; }
      if (tag === "font") { unwrap(el); continue; }
      if (tag === "span") {
        const onlyBr = el.children.length === 1 && el.children[0].tagName.toLowerCase() === "br" && !el.textContent.trim();
        if (!onlyBr) unwrap(el);
        continue;
      }
      if (tag === "a") { unwrap(el); continue; }
      if (tag === "blockquote" || tag === "pre") { renameTag(el, "p"); continue; }
      if (tag === "section" || tag === "article" || tag === "header" || tag === "footer" || tag === "main" || tag === "nav" || tag === "aside" || tag === "figure" || tag === "figcaption") {
        unwrap(el);
        continue;
      }
      if (tag === "div") {
        if (isImageWrap || isSvgWrap) continue;
        if (el.querySelector && el.querySelector(":scope > ul, :scope > ol")) {
          unwrap(el);
          continue;
        }
        renameTag(el, "p");
        continue;
      }

      if (tag === "img") {
        const src = String(el.getAttribute("src") || "").trim();
        const lower = src.toLowerCase();
        const ok =
          lower.startsWith("data:image/") ||
          lower.startsWith("http://") ||
          lower.startsWith("https://") ||
          lower.startsWith("/generated/");
        if (!ok) { el.remove(); continue; }
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

      if (!ALLOWED.includes(tag)) {
        unwrap(el);
      }
    }

    // Drop empty paragraphs.
    const emptyPs = Array.from(root.querySelectorAll("p"));
    for (const p of emptyPs) {
      const text = String(p.textContent || "")
        .replace(/ /g, " ")
        .replace(/[​﻿]/g, "")
        .trim();
      const hasMedia = p.querySelector && p.querySelector("img, svg, br");
      if (!text && !hasMedia) p.remove();
    }

    const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
    const textNodes = [];
    while (walker.nextNode()) textNodes.push(walker.currentNode);
    for (const t of textNodes) {
      t.nodeValue = String(t.nodeValue || "")
        .replace(/[​﻿]/g, "")
        .replace(/ /g, " ")
        .replace(/[ \t]+/g, " ");
    }
  }

  function sanitizeHtml(rawHtml) {
    const prePass = String(rawHtml || "")
      .replace(/<!--\[if[\s\S]*?endif\]-->/gi, "")
      .replace(/<\?xml[\s\S]*?\?>/gi, "");
    const template = document.createElement("template");
    template.innerHTML = prePass;
    cleanNode(template.content);
    return template.innerHTML;
  }

  // Decide whether the initial value is plain text or HTML.
  // If it contains no `<` or `&lt;`, treat as plain text.
  function prepareInitialValue(value) {
    const s = String(value || "");
    if (!s) return "";
    // Heuristic: if it looks like HTML (has a tag), sanitize; else wrap as <p>.
    if (/<[a-z][\s\S]*?>/i.test(s)) {
      return sanitizeHtml(s);
    }
    // Plain text: preserve as-is in a single <p> with line breaks as <br>.
    return plainTextToHtml(s);
  }

  function mediaActionsHtml(kind) {
    return (
      '<div class="media-wrap-actions" contenteditable="false" draggable="false">' +
        '<button type="button" class="media-wrap-btn js-media-replace" data-media-kind="' + kind + '">' +
          (kind === "svg" ? "Edit SVG" : "Replace") +
        '</button>' +
        '<button type="button" class="media-wrap-btn danger js-media-remove">Remove</button>' +
      '</div>'
    );
  }

  function decorateMediaBlocks(root) {
    if (!root || !root.querySelectorAll) return;
    root.querySelectorAll(".image-wrap, .svg-wrap").forEach((wrap) => {
      if (wrap.querySelector(":scope > .media-wrap-actions")) return;
      wrap.insertAdjacentHTML(
        "afterbegin",
        mediaActionsHtml(wrap.classList.contains("svg-wrap") ? "svg" : "image"),
      );
    });
  }

  function serializeEditorHtml(editor) {
    const clone = editor.cloneNode(true);
    clone.querySelectorAll(".media-wrap-actions").forEach((node) => node.remove());
    return clone.innerHTML;
  }

  // ---------- selection helpers ----------

  function saveSelection(editor) {
    const sel = window.getSelection();
    if (!sel || sel.rangeCount === 0) return null;
    const range = sel.getRangeAt(0);
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

    const temp = document.createElement("div");
    temp.innerHTML = htmlString;
    const frag = document.createDocumentFragment();
    let lastNode = null;
    while (temp.firstChild) {
      lastNode = frag.appendChild(temp.firstChild);
    }

    let container = range.startContainer;
    let blockAncestor = container.nodeType === 1 ? container : container.parentNode;
    while (blockAncestor && blockAncestor.parentNode !== editor) {
      blockAncestor = blockAncestor.parentNode;
    }

    if (blockAncestor && blockAncestor.parentNode === editor) {
      if (blockAncestor.nextSibling) {
        editor.insertBefore(frag, blockAncestor.nextSibling);
      } else {
        editor.appendChild(frag);
      }
    } else {
      range.insertNode(frag);
    }

    if (lastNode) {
      const newRange = document.createRange();
      newRange.setStartAfter(lastNode);
      newRange.collapse(true);
      sel.removeAllRanges();
      sel.addRange(newRange);
    }
  }

  // ---------- Image modal ----------

  function openImageModal(onInsert) {
    const backdrop = document.createElement("div");
    backdrop.className = "svg-insert-modal";
    backdrop.innerHTML =
      '<div class="svg-insert-modal-card" role="dialog" aria-modal="true">' +
        '<h3 style="margin:0 0 8px 0;">Insert Image</h3>' +
        '<p class="muted-text" style="margin:0 0 16px 0;">Upload a file or paste an image URL.</p>' +
        '<div class="image-upload-dropzone js-image-drop">' +
          '<input type="file" class="js-image-file" accept="image/*" hidden />' +
          '<div class="image-upload-cta">' +
            '<div style="font-size:28px;line-height:1;">🖼</div>' +
            '<div style="margin-top:8px;font-weight:600;">Click to choose or drop an image</div>' +
            '<div class="muted-text" style="margin-top:4px;font-size:12px;">PNG, JPG, GIF, WEBP, SVG — stored as data URI</div>' +
          '</div>' +
          '<img class="js-image-preview" alt="" hidden />' +
        '</div>' +
        '<div style="display:flex;align-items:center;gap:10px;margin:14px 0;">' +
          '<div style="flex:1;height:1px;background:var(--border);"></div>' +
          '<div class="muted-text" style="font-size:11px;letter-spacing:.08em;">OR</div>' +
          '<div style="flex:1;height:1px;background:var(--border);"></div>' +
        '</div>' +
        '<label class="field" style="margin-bottom:10px;">' +
          '<span>Image URL</span>' +
          '<input type="text" class="js-image-url form-input" placeholder="https://…" />' +
        '</label>' +
        '<label class="field">' +
          '<span>Alt text (optional)</span>' +
          '<input type="text" class="js-image-alt form-input" placeholder="Describe the image" />' +
        '</label>' +
        '<div style="display:flex;justify-content:flex-end;gap:8px;margin-top:18px;">' +
          '<button type="button" class="btn btn-ghost js-image-cancel">Cancel</button>' +
          '<button type="button" class="btn btn-primary js-image-insert">Insert</button>' +
        '</div>' +
      '</div>';
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
    backdrop.innerHTML =
      '<div class="svg-insert-modal-card" role="dialog" aria-modal="true">' +
        '<h3 style="margin:0 0 12px 0;">Insert SVG</h3>' +
        '<p class="muted-text" style="margin:0 0 12px 0;">Paste raw SVG code. &lt;script&gt; tags will be stripped.</p>' +
        '<textarea placeholder="&lt;svg xmlns=&quot;http://www.w3.org/2000/svg&quot; ...&gt;...&lt;/svg&gt;"></textarea>' +
        '<div style="display:flex;justify-content:flex-end;gap:8px;margin-top:16px;">' +
          '<button type="button" class="btn btn-ghost js-svg-cancel">Cancel</button>' +
          '<button type="button" class="btn btn-primary js-svg-insert">Insert</button>' +
        '</div>' +
      '</div>';
    document.body.appendChild(backdrop);
    const textarea = backdrop.querySelector("textarea");
    textarea.focus();
    function close() { backdrop.remove(); }
    backdrop.addEventListener("click", (e) => { if (e.target === backdrop) close(); });
    backdrop.querySelector(".js-svg-cancel").addEventListener("click", close);
    backdrop.querySelector(".js-svg-insert").addEventListener("click", () => {
      const raw = textarea.value.trim();
      if (!raw) return close();
      onInsert(stripScripts(raw));
      close();
    });
  }

  // ---------- main factory ----------

  /**
   * Create a reusable rich-text mini editor.
   * @param {Object} opts
   * @param {string}   opts.value        Initial HTML (or plain text). Sanitized on set.
   * @param {Function} opts.onChange     Called with new HTML string, debounced.
   * @param {string}   [opts.placeholder]
   * @param {boolean}  [opts.compact]    Smaller toolbar/padding.
   * @returns {HTMLElement} root element to append into your host container
   */
  function create(opts) {
    const options = opts || {};
    const initialValue = options.value || "";
    const onChange = typeof options.onChange === "function" ? options.onChange : function () {};
    const placeholder = options.placeholder || "";
    const compact = !!options.compact;

    const root = document.createElement("div");
    root.className = "rich-field" + (compact ? " compact" : "");

    const toolbar = document.createElement("div");
    toolbar.className = "rich-toolbar";
    toolbar.setAttribute("role", "toolbar");
    toolbar.innerHTML =
      '<button type="button" class="js-rich-btn" data-cmd="bold" title="Bold (Ctrl+B)"><b>B</b></button>' +
      '<button type="button" class="js-rich-btn" data-cmd="italic" title="Italic (Ctrl+I)"><i>I</i></button>' +
      '<span class="rich-sep"></span>' +
      '<button type="button" class="js-rich-btn rich-btn-wide" data-cmd="image" title="Insert image">🖼 Image</button>' +
      '<button type="button" class="js-rich-btn rich-btn-wide" data-cmd="svg" title="Insert SVG">◆ SVG</button>';
    root.appendChild(toolbar);

    const editor = document.createElement("div");
    editor.className = "js-rich-mini";
    editor.setAttribute("contenteditable", "true");
    editor.setAttribute("spellcheck", "true");
    if (placeholder) editor.setAttribute("data-placeholder", placeholder);
    editor.innerHTML = prepareInitialValue(initialValue);
    decorateMediaBlocks(editor);
    root.appendChild(editor);

    // ----- change emission (debounced ~300ms) -----

    let debounceId = null;
    function emit() {
      onChange(serializeEditorHtml(editor));
    }
    function scheduleEmit() {
      if (debounceId) clearTimeout(debounceId);
      debounceId = setTimeout(() => { debounceId = null; emit(); }, 300);
    }
    function flushEmit() {
      if (debounceId) { clearTimeout(debounceId); debounceId = null; }
      emit();
    }

    editor.addEventListener("input", scheduleEmit);
    editor.addEventListener("blur", flushEmit);

    // ----- toolbar commands -----

    function runCommand(cmd) {
      editor.focus();
      if (cmd === "bold" || cmd === "italic") {
        document.execCommand(cmd);
        scheduleEmit();
        return;
      }
      if (cmd === "image") {
        const savedRange = saveSelection(editor);
        openImageModal((src, alt) => {
          restoreSelection(editor, savedRange);
          const safeSrc = String(src).replace(/"/g, "&quot;");
          const safeAlt = String(alt || "").replace(/"/g, "&quot;");
          insertBlockAtCaret(
            editor,
            '<div class="image-wrap" contenteditable="false" draggable="true">' + mediaActionsHtml("image") + '<img src="' + safeSrc + '" alt="' + safeAlt + '"></div><p><br></p>',
          );
          flushEmit();
        });
        return;
      }
      if (cmd === "svg") {
        const savedRange = saveSelection(editor);
        openSvgModal((svgCode) => {
          restoreSelection(editor, savedRange);
          insertBlockAtCaret(
            editor,
            '<div class="svg-wrap" contenteditable="false" draggable="true">' + mediaActionsHtml("svg") + svgCode + '</div><p><br></p>',
          );
          flushEmit();
        });
        return;
      }
    }

    // Use `mousedown` (not `click`) for two reasons:
    //   1. Many editors wrap `.js-rich-host` inside a <label>. Clicking the
    //      contenteditable inside that label causes the browser to synthesize
    //      a `click` on the first labelable descendant — which is the Bold
    //      button — toggling bold on every caret placement. Synthetic label
    //      clicks are dispatched as `click` events only; `mousedown` is not
    //      forwarded, so listening on mousedown sidesteps the forwarding bug.
    //   2. `mousedown` fires BEFORE the contenteditable loses focus, so
    //      preventDefault() preserves the current selection and the command
    //      applies to the text the user actually highlighted.
    toolbar.addEventListener("mousedown", (event) => {
      const btn = event.target.closest(".js-rich-btn");
      if (!btn || !toolbar.contains(btn)) return;
      event.preventDefault();
      event.stopPropagation();
      runCommand(btn.dataset.cmd);
    });
    // Swallow the subsequent `click` (including any label-synthesized click
    // that still targets the button) so nothing else can react to it.
    toolbar.addEventListener("click", (event) => {
      const btn = event.target.closest(".js-rich-btn");
      if (!btn || !toolbar.contains(btn)) return;
      event.preventDefault();
      event.stopPropagation();
    });

    function ensureEditableParagraph() {
      const hasEditable = Array.from(editor.childNodes).some((node) => {
        if (node.nodeType === 3) return String(node.textContent || "").trim();
        if (node.nodeType !== 1) return false;
        return !(node.classList && (node.classList.contains("image-wrap") || node.classList.contains("svg-wrap")));
      });
      if (!hasEditable) editor.insertAdjacentHTML("beforeend", "<p><br></p>");
    }

    editor.addEventListener("mousedown", (event) => {
      if (event.target.closest && event.target.closest(".media-wrap-actions")) {
        event.preventDefault();
        event.stopPropagation();
      }
    });

    editor.addEventListener("click", (event) => {
      const action = event.target.closest && event.target.closest(".js-media-remove, .js-media-replace");
      if (!action || !editor.contains(action)) return;
      const wrap = action.closest(".image-wrap, .svg-wrap");
      if (!wrap) return;
      event.preventDefault();
      event.stopPropagation();
      if (action.classList.contains("js-media-remove")) {
        wrap.remove();
        ensureEditableParagraph();
        flushEmit();
        return;
      }
      if (wrap.classList.contains("image-wrap")) {
        openImageModal((src, alt) => {
          const img = wrap.querySelector("img");
          if (!img) return;
          img.setAttribute("src", String(src || ""));
          img.setAttribute("alt", String(alt || ""));
          flushEmit();
        });
        return;
      }
      openSvgModal((svgCode) => {
        const actions = wrap.querySelector(".media-wrap-actions");
        wrap.innerHTML = "";
        if (actions) wrap.appendChild(actions);
        wrap.insertAdjacentHTML("beforeend", svgCode);
        flushEmit();
      });
    });

    // ----- paste sanitizer -----

    editor.addEventListener("paste", (event) => {
      event.preventDefault();
      const cd = event.clipboardData || window.clipboardData;
      if (!cd) return;

      let html = "";
      try { html = cd.getData("text/html") || ""; } catch (e) { html = ""; }

      let cleaned = "";
      if (html) {
        cleaned = sanitizeHtml(html);
      } else {
        let plain = "";
        try { plain = cd.getData("text/plain") || ""; } catch (e) { plain = ""; }
        cleaned = plainTextToHtml(plain);
      }
      if (!cleaned) return;

      try {
        document.execCommand("insertHTML", false, cleaned);
      } catch (e) {
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
      decorateMediaBlocks(editor);
      flushEmit();
    });

    // ----- image-wrap resize capture (native CSS resize) -----

    const resizeTracker = new WeakMap();
    editor.addEventListener("mousedown", (event) => {
      const wrap = event.target.closest && event.target.closest(".image-wrap");
      if (!wrap || !editor.contains(wrap)) return;
      resizeTracker.set(wrap, { w: wrap.offsetWidth, h: wrap.offsetHeight });
    });
    editor.addEventListener("mouseup", (event) => {
      const wrap = event.target.closest && event.target.closest(".image-wrap");
      if (!wrap || !editor.contains(wrap)) return;
      const prev = resizeTracker.get(wrap);
      if (!prev) return;
      resizeTracker.delete(wrap);
      if (wrap.offsetWidth !== prev.w || wrap.offsetHeight !== prev.h) {
        wrap.style.width = wrap.offsetWidth + "px";
        flushEmit();
      }
    });

    return root;
  }

  window.RichField.create = create;
  window.RichField.sanitizeHtml = sanitizeHtml;
  window.RichField.openImageModal = openImageModal;
  window.RichField.openSvgModal = openSvgModal;
  window.RichField.stripScripts = stripScripts;
})();
