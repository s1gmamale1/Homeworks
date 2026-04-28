/* NETS i18n — vanilla IIFE, no dependencies.
   Requires window.STRINGS (from i18n/strings.js) to be loaded first. */
(function () {
  'use strict';

  var LANGS = ['uz', 'ru', 'en'];
  var _lang = 'en';
  var _callbacks = [];

  function getLang() {
    var stored = (typeof localStorage !== 'undefined') && localStorage.getItem('nets_lang');
    if (stored && LANGS.indexOf(stored) !== -1) return stored;
    var attr = document.documentElement.getAttribute('lang');
    if (attr && LANGS.indexOf(attr) !== -1) return attr;
    return 'en';
  }

  function t(key, fallback) {
    var S = window.STRINGS || { uz: {}, ru: {}, en: {} };
    var langObj = S[_lang] || {};
    if (key in langObj) return langObj[key];
    if (S.en && key in S.en) return S.en[key];
    if (S.uz && key in S.uz) return S.uz[key];
    if (typeof fallback !== 'undefined') return fallback;
    return key;
  }

  function applyAll() {
    document.querySelectorAll('[data-i18n]').forEach(function (el) {
      el.textContent = t(el.dataset.i18n);
    });
    document.querySelectorAll('[data-i18n-placeholder]').forEach(function (el) {
      el.setAttribute('placeholder', t(el.dataset.i18nPlaceholder));
    });
    document.querySelectorAll('[data-i18n-aria-label]').forEach(function (el) {
      el.setAttribute('aria-label', t(el.dataset.i18nAriaLabel));
    });
    document.querySelectorAll('[data-i18n-title]').forEach(function (el) {
      el.setAttribute('title', t(el.dataset.i18nTitle));
    });
  }

  function _syncPills(lang) {
    document.querySelectorAll('.lang-pill').forEach(function (btn) {
      var active = btn.dataset.lang === lang;
      btn.setAttribute('aria-pressed', String(active));
      if (active) btn.classList.add('is-active');
      else btn.classList.remove('is-active');
    });
  }

  function setLang(lang) {
    if (LANGS.indexOf(lang) === -1) return;
    _lang = lang;
    localStorage.setItem('nets_lang', lang);
    document.documentElement.setAttribute('lang', lang);
    applyAll();
    _syncPills(lang);
    _callbacks.forEach(function (cb) { try { cb(lang); } catch (e) {} });
  }

  function onChange(cb) {
    _callbacks.push(cb);
  }

  // Delegated click handler for lang-pill buttons
  document.addEventListener('click', function (e) {
    var btn = e.target.closest('.lang-pill');
    if (!btn) return;
    setLang(btn.dataset.lang);
  });

  // Init
  _lang = getLang();
  document.documentElement.setAttribute('lang', _lang);
  if (typeof localStorage !== 'undefined') localStorage.setItem('nets_lang', _lang);
  applyAll();
  _syncPills(_lang);

  window.i18n = { t: t, setLang: setLang, getLang: getLang, onChange: onChange };
})();
