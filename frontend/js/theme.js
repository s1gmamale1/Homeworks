/* NETS theme manager — global dark/light toggle.
 * Same storage key (`nets_theme`) and same `data-theme` attribute used by the
 * runtime tutor IIFE in server/template/perfect_homework.html, so the two
 * toggles stay in sync via localStorage + the storage event.
 */
(function () {
  var THEME_KEY = 'nets_theme';

  // Phase A — apply theme synchronously before paint to avoid FOUC.
  var saved = null;
  try { saved = localStorage.getItem(THEME_KEY); } catch (e) { /* private mode */ }
  document.documentElement.setAttribute('data-theme', saved === 'dark' ? 'dark' : 'light');

  function currentTheme() {
    return document.documentElement.getAttribute('data-theme') === 'dark' ? 'dark' : 'light';
  }

  function updateButtons(theme) {
    var isDark = theme === 'dark';
    var buttons = document.querySelectorAll('[data-theme-toggle]');
    for (var i = 0; i < buttons.length; i++) {
      var btn = buttons[i];
      btn.textContent = isDark ? '☀️' : '🌙';
      btn.setAttribute('aria-label', isDark ? 'Switch to light mode' : 'Switch to dark mode');
      btn.setAttribute('aria-pressed', isDark ? 'true' : 'false');
    }
  }

  function applyTheme(theme) {
    document.documentElement.setAttribute('data-theme', theme);
    try { localStorage.setItem(THEME_KEY, theme); } catch (e) { /* private mode */ }
    updateButtons(theme);
  }

  function wire() {
    var buttons = document.querySelectorAll('[data-theme-toggle]');
    for (var i = 0; i < buttons.length; i++) {
      buttons[i].addEventListener('click', function () {
        applyTheme(currentTheme() === 'dark' ? 'light' : 'dark');
      });
    }
    updateButtons(currentTheme());
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', wire);
  } else {
    wire();
  }

  // Sync across tabs and across the parent ↔ runtime-iframe boundary.
  window.addEventListener('storage', function (e) {
    if (e.key !== THEME_KEY) return;
    var next = e.newValue === 'dark' ? 'dark' : 'light';
    document.documentElement.setAttribute('data-theme', next);
    updateButtons(next);
  });
})();
