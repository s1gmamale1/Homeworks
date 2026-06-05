/* Homeworks — Legal pages (Privacy + Terms) language toggle.
 * Shares the `nets-landing-lang` localStorage key with landing.js so the choice
 * carries across pages. The initial language is set synchronously by a small
 * inline <head> script (see privacy.html / terms.html) to avoid a flash; this
 * file wires the .lang-pill click handlers, keeps the active state in sync, and
 * translates the shared chrome (back-link + footer links) via data-i18n-<lang>.
 * Theme stays owned by theme.js.
 */
(function () {
  var LANG_KEY = 'nets-landing-lang';
  var SUPPORTED = ['uz', 'ru', 'en'];
  var DEFAULT = 'uz';

  function readLang() {
    try {
      var v = localStorage.getItem(LANG_KEY);
      if (v && SUPPORTED.indexOf(v) !== -1) return v;
    } catch (e) { /* private mode */ }
    return DEFAULT;
  }

  function applyLang(lang) {
    if (SUPPORTED.indexOf(lang) === -1) lang = DEFAULT;
    document.documentElement.setAttribute('data-lang', lang);
    document.documentElement.lang = lang;
    try { localStorage.setItem(LANG_KEY, lang); } catch (e) { /* private mode */ }

    var pills = document.querySelectorAll('.lang-pill');
    for (var i = 0; i < pills.length; i++) {
      var on = pills[i].getAttribute('data-lang') === lang;
      pills[i].classList.toggle('is-active', on);
      pills[i].setAttribute('aria-pressed', on ? 'true' : 'false');
    }

    // Translate shared chrome (back-link + footer link).
    var nodes = document.querySelectorAll('[data-i18n-uz]');
    for (var n = 0; n < nodes.length; n++) {
      var t = nodes[n].getAttribute('data-i18n-' + lang);
      if (t !== null) nodes[n].textContent = t;
    }
  }

  function wire() {
    var pills = document.querySelectorAll('.lang-pill');
    for (var i = 0; i < pills.length; i++) {
      pills[i].addEventListener('click', function () {
        var lang = this.getAttribute('data-lang');
        if (lang) applyLang(lang);
      });
    }
    applyLang(readLang());
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', wire);
  } else {
    wire();
  }
})();
