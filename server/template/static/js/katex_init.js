      (function () {
        const KATEX_OPTS = {
          delimiters: [
            { left: '$$', right: '$$', display: true },
            { left: '$',  right: '$',  display: false },
            { left: '\\(', right: '\\)', display: false },
            { left: '\\[', right: '\\]', display: true }
          ],
          throwOnError: false,
          ignoredTags: ['script','noscript','style','textarea','pre','code','option'],
          ignoredClasses: ['katex','katex-display']
        };

        let isRendering = false;
        function renderNow(node) {
          if (isRendering || !window.renderMathInElement) return;
          isRendering = true;
          try { window.renderMathInElement(node || document.body, KATEX_OPTS); } catch (e) {}
          setTimeout(() => { isRendering = false; }, 50);
        }

        let scheduled = false;
        function scheduleRender() {
          if (scheduled) return;
          scheduled = true;
          requestAnimationFrame(() => {
            scheduled = false;
            renderNow(document.body);
          });
        }
        window.__renderMath = scheduleRender;

        function start() {
          renderNow(document.body);
          new MutationObserver(scheduleRender).observe(document.body, {
            childList: true, subtree: true, characterData: true
          });
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
