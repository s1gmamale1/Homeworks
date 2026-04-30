/* ============================================================
   Homeworks Landing Page — vanilla JS
   - i18n (uz/ru/en) with localStorage persistence
   - View Transitions API panel switching
   - IntersectionObserver scroll reveals
   - rAF-throttled hero parallax
   - Inline SVG icon set (matches the JSX iconPaths map)
   ============================================================ */

(function () {
  "use strict";

  // ── Icon paths (mirrors JSX iconPaths map) ──────────────────────────────
  // Available: arrowRight, book, brain, check, chevronRight, cap, layers,
  //            lock, message, play, sparkles, wand, zap
  const iconPaths = {
    arrowRight: "M5 12h14M13 5l7 7-7 7",
    book: "M4 19.5A2.5 2.5 0 0 1 6.5 17H20M4 4.5A2.5 0 0 1 6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15Z",
    brain: "M9 3a3 3 0 0 0-3 3v1a3 3 0 0 0-2 5.23V14a4 4 0 0 0 4 4h1m6-15a3 3 0 0 1 3 3v1a3 3 0 0 1 2 5.23V14a4 4 0 0 1-4 4h-1M9 3v18m6-18v18M9 9H6m12 0h-3M9 15H6m12 0h-3",
    check: "M20 6 9 17l-5-5",
    chevronRight: "m9 18 6-6-6-6",
    cap: "M3 8l9-5 9 5-9 5Zm5 5v4c2.5 2 5.5 2 8 0v-4M19 10v6",
    layers: "M12 3 3 8l9 5 9-5-9-5Zm-7 9 7 4 7-4M5 16l7 4 7-4",
    lock: "M7 11V8a5 5 0 0 1 10 0v3M6 11h12v10H6V11Zm6 4v3",
    message: "M21 12a8 8 0 0 1-8 8H7l-4 3v-6a8 8 0 1 1 18-5Z",
    play: "M8 5v14l11-7L8 5Z",
    sparkles: "M12 2l1.6 5.2L19 9l-5.4 1.8L12 16l-1.6-5.2L5 9l5.4-1.8L12 2Zm7 12 .8 2.6L22 17l-2.2.4L19 20l-.8-2.6L16 17l2.2-.4L19 14ZM5 13l.8 2.6L8 16l-2.2.4L5 19l-.8-2.6L2 16l2.2-.4L5 13Z",
    wand: "M15 4l5 5M14 5l5 5M4 20 18 6M5 5l1 2 2 1-2 1-1 2-1-2-2-1 2-1 1-2Zm14 9 .7 1.4 1.3.6-1.3.6L19 18l-.7-1.4-1.3-.6 1.3-.6L19 14Z",
    zap: "M13 2 4 14h7l-1 8 10-13h-7l1-7Z",
  };

  // Exposed for tests/debugging; no runtime dependency on this.
  if (typeof window !== "undefined") {
    window.__landingIconPaths = iconPaths;
  }

  /**
   * Render an SVG icon string. Useful if we ever need to inject icons
   * from JS (currently we ship them inline in the HTML for FOUC-free first paint).
   */
  function renderIcon(name, size) {
    size = size || 20;
    const d = iconPaths[name];
    if (!d) return "";
    return (
      '<svg width="' + size + '" height="' + size +
      '" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" ' +
      'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">' +
      '<path d="' + d + '"></path></svg>'
    );
  }

  // ── i18n strings (uz, ru, en) ───────────────────────────────────────────
  const i18n = {
    uz: {
      brand: "Homeworks",
      footerNote: "Beta loyiha — interaktiv darslar uchun.",
      nav: {
        overview: "Umumiy",
        preview: "Ko‘rinish",
        tutor: "Tutor",
        workflow: "Jarayon",
        launch: "Boshlash",
      },
      tryBeta: "Beta sinash",
      heroBadge: "Aqlliroq uy vazifalari uchun beta loyiha",
      heroTitle: "Uy vazifasi endi majburiyatdek tuyilmaydi.",
      heroText:
        "Reading panellar, adaptiv savollar, AI tutor yordami va toza student linklar bilan interaktiv darslar yarating.",
      watchPreview: "Preview ko‘rish",
      seeWorkflow: "Jarayonni ko‘rish",
      stats: [
        ["3", "o‘quv bosqichi"],
        ["AI", "tutor + baholash"],
        ["/h", "ulashiladigan homework linklar"],
      ],
      floating: { panels: "Panellar", tutor: "Tutor", grade: "Baholash" },
      overviewEyebrow: "Umumiy",
      overviewTitle: "To‘liq dars jarayoni bitta chiroyli link ichida.",
      overviewText:
        "Oddiy forma o‘rniga har bir uy vazifasi mini learning experience bo‘ladi: o‘qish, mashq, feedback, reflection va tutor yordami.",
      previewEyebrow: "Ko‘rinish",
      previewTitle: "Avval tushuntiradi. Keyin tekshiradi.",
      previewText:
        "Hozirgi g‘oya kuchli: alohida panellar, swipe sahifalar va oxirgi line-button interaksiyasi. Bu versiya panelni lesson card sifatida aniqroq ko‘rsatadi: progress, checkpoint va CTA tartibli turadi.",
      tutorEyebrow: "Live tutor",
      tutorTitle: "Savolni tartibsiz yozadigan studentlar uchun ham ishlaydi.",
      studentLabel: "Student",
      studentMessage: "aka narx oshsa nima uchun keyin pul kamayib ketadi?",
      tutorLabel: "Tutor",
      tutorMessage:
        "Chunki narx juda baland bo‘lsa, kamroq odam sotib oladi. Daromadga narx ham, xaridor soni ham kerak.",
      usefulTitle: "Kamroq robot. Ko‘proq foyda.",
      usefulText:
        "Tutor casual gaplarni tushunadi, conceptni sodda tushuntiradi va studentni tozaro akademik javobga yo‘naltiradi.",
      workflowEyebrow: "Jarayon",
      workflowTitle: "Teacher g‘oyasidan student linkgacha.",
      quickCardTitle: "Teacher uchun tez.",
      quickCardText:
        "Har safar homeworkni noldan qurish shart emas. Templatedan boshlang, darsni sozlang va publish qiling.",
      safeCardTitle: "Dizayndan xavfsizroq.",
      safeCardText:
        "Keyingi beta wave uchun uzun random homework sluglar, rate limit va privacy-aware student sahifalarini qo‘shing.",
      launchTitle: "Har bir homeworkga ozgina miya bering.",
      launchText:
        "Premium interfeys. Oddiy teacher flow. Student sahifalari esa jazoga o‘xshagan forma emas, guided learning kabi ishlaydi.",
      openBuilder: "Builderni ochish",
      viewApi: "Kutubxonani ko‘rish",
      phone: {
        header: "Homework",
        subject: "Kvadratik daromad",
        checkpoint: "Checkpoint",
        aiReady: "AI tayyor",
        question: "Nega daromad grafigi avval ko‘tarilib, keyin pasayadi?",
        placeholder: "Student javobni shu yerga yozadi...",
        continue: "Darsni davom ettirish",
      },
      lessonPanels: [
        {
          eyebrow: "Reading Panel 01",
          title: "Avval concept.",
          body: "Studentlar javob berishdan oldin toza lesson cardlar orqali swipe qiladi. Ortiqcha shovqin yo‘q.",
          tag: "Swipe learning",
        },
        {
          eyebrow: "Adaptiv Quiz",
          title: "Javob tartibsiz bo‘lsa ham, AI ma’noni tushunadi.",
          body: "Tizim student javobini kerakli javob bilan solishtiradi va mayda wording xatolari uchun darrov jazolamaydi.",
          tag: "Hybrid grading",
        },
        {
          eyebrow: "Live Tutor",
          title: "Har savol yonida tutor bor.",
          body: "Student hint, tushuntirish yoki til bo‘yicha yordam so‘rashi mumkin, lesson flowdan chiqmasdan.",
          tag: "AI yordam",
        },
      ],
      features: [
        {
          icon: "wand",
          title: "Template asosidagi builder",
          body: "Tayyor fixturelarni yuklang, lesson contentni tahrirlang va student linkni qo‘lda hammasini qayta qurmasdan chiqaring.",
        },
        {
          icon: "layers",
          title: "Panel-based darslar",
          body: "Qiyinroq darslar ko‘proq panellarga ajraladi, student esa practice oldidan conceptni bosqichma-bosqich ko‘radi.",
        },
        {
          icon: "brain",
          title: "AI baholash yordami",
          body: "Flexible answer matching ma’noni tekshiradi, feedback beradi va teacherni nazoratda qoldiradi.",
        },
        {
          icon: "message",
          title: "Live tutor mode",
          body: "Student Uzbek, English yoki aralash casual speechda yordam so‘rashi mumkin.",
        },
      ],
      workflow: [
        ["01", "Template yuklash", "Algebra, fizika, biologiya, English, tarix, kimyo yoki geometriya fixturelarini tanlang."],
        ["02", "Panellarni tahrirlash", "Reading cardlar, quiz blocklar, checkpoint promptlar va explanationsni sozlang."],
        ["03", "Link chiqarish", "Student uchun bitta stable homework URL yarating."],
        ["04", "Natijalarni ko‘rish", "AI-assisted checking va feedback orqali student performance’ni tezroq tushuning."],
      ],
    },

    ru: {
      brand: "Homeworks",
      footerNote: "Beta-проект — для интерактивных уроков.",
      nav: {
        overview: "Обзор",
        preview: "Превью",
        tutor: "Тьютор",
        workflow: "Процесс",
        launch: "Запуск",
      },
      tryBeta: "Открыть beta",
      heroBadge: "Beta-проект для умных домашних заданий",
      heroTitle: "Домашка, которая не ощущается как наказание.",
      heroText:
        "Создавайте интерактивные уроки с reading-панелями, адаптивными вопросами, AI-тьютором и чистыми ссылками для учеников.",
      watchPreview: "Смотреть превью",
      seeWorkflow: "Посмотреть процесс",
      stats: [
        ["3", "этапа обучения"],
        ["AI", "тьютор + оценка"],
        ["/h", "ссылки на домашку"],
      ],
      floating: { panels: "Панели", tutor: "Тьютор", grade: "Оценка" },
      overviewEyebrow: "Обзор",
      overviewTitle: "Полный учебный flow внутри одной красивой ссылки.",
      overviewText:
        "Вместо обычной формы каждая домашка превращается в мини-урок: чтение, практика, feedback, reflection и помощь тьютора.",
      previewEyebrow: "Превью",
      previewTitle: "Сначала объясняет. Потом проверяет.",
      previewText:
        "Текущая идея уже сильная: отдельные панели, свайп-страницы и финальная line-to-button интеракция. Эта версия делает механику яснее: lesson card, progress, checkpoint и CTA стоят в правильной иерархии.",
      tutorEyebrow: "Live тьютор",
      tutorTitle: "Работает даже когда ученик пишет вопрос хаотично.",
      studentLabel: "Ученик",
      studentMessage: "бро почему цена растет а деньги потом падают?",
      tutorLabel: "Тьютор",
      tutorMessage:
        "Потому что при слишком высокой цене меньше людей покупают. Для выручки нужны и цена, и количество покупателей.",
      usefulTitle: "Меньше робота. Больше пользы.",
      usefulText:
        "Тьютор понимает casual-речь, объясняет concept простым языком и направляет ученика к более аккуратному академическому ответу.",
      workflowEyebrow: "Процесс",
      workflowTitle: "От идеи учителя до ссылки ученика.",
      quickCardTitle: "Быстро для учителя.",
      quickCardText:
        "Не нужно каждый раз собирать домашку с нуля. Выберите шаблон, настройте урок и опубликуйте.",
      safeCardTitle: "Безопаснее по дизайну.",
      safeCardText:
        "Для следующей beta-волны добавьте длинные случайные homework slug’и, rate limit и privacy-aware страницы учеников.",
      launchTitle: "Дайте каждой домашке немного мозга.",
      launchText:
        "Премиальный интерфейс. Простой teacher flow. Страницы учеников ощущаются как guided learning, а не как скучная форма.",
      openBuilder: "Открыть builder",
      viewApi: "Открыть библиотеку",
      phone: {
        header: "Homework",
        subject: "Квадратичная выручка",
        checkpoint: "Checkpoint",
        aiReady: "AI готов",
        question: "Почему график выручки сначала растет, достигает пика, а потом падает?",
        placeholder: "Ученик пишет ответ здесь...",
        continue: "Продолжить урок",
      },
      lessonPanels: [
        {
          eyebrow: "Reading Panel 01",
          title: "Сначала concept.",
          body: "Перед ответом ученик проходит чистые lesson cards свайпом. Без шума и стены текста.",
          tag: "Swipe learning",
        },
        {
          eyebrow: "Адаптивный Quiz",
          title: "Ответ может быть messy. AI всё равно поймет смысл.",
          body: "Система сравнивает ответ ученика с ожидаемым ответом и не наказывает сразу за мелкие wording-ошибки.",
          tag: "Hybrid grading",
        },
        {
          eyebrow: "Live Tutor",
          title: "Тьютор рядом с каждым вопросом.",
          body: "Ученик может попросить hint, объяснение или языковую помощь, не выходя из lesson flow.",
          tag: "AI помощь",
        },
      ],
      features: [
        {
          icon: "wand",
          title: "Builder на шаблонах",
          body: "Загрузите готовые fixtures, отредактируйте lesson content и опубликуйте ссылку без ручной сборки всего заново.",
        },
        {
          icon: "layers",
          title: "Panel-based уроки",
          body: "Более сложные уроки делятся на больше панелей, чтобы ученик понял concept перед практикой.",
        },
        {
          icon: "brain",
          title: "AI-помощь в оценке",
          body: "Flexible answer matching проверяет смысл, дает feedback и оставляет учителя в контроле.",
        },
        {
          icon: "message",
          title: "Live tutor mode",
          body: "Ученик может спрашивать помощь на узбекском, английском или смешанной casual-речью.",
        },
      ],
      workflow: [
        ["01", "Загрузить шаблон", "Выберите fixture по алгебре, физике, биологии, английскому, истории, химии или геометрии."],
        ["02", "Редактировать панели", "Настройте reading cards, quiz blocks, checkpoint prompts и explanations."],
        ["03", "Опубликовать ссылку", "Создайте стабильный homework URL для ученика."],
        ["04", "Проверить результаты", "AI-assisted checking и feedback помогают быстрее понять performance ученика."],
      ],
    },

    en: {
      brand: "Homeworks",
      footerNote: "A beta project — for interactive lessons.",
      nav: {
        overview: "Overview",
        preview: "Preview",
        tutor: "Tutor",
        workflow: "Flow",
        launch: "Launch",
      },
      tryBeta: "Try the beta",
      heroBadge: "A beta project for smarter homework",
      heroTitle: "Homework that doesn’t feel like a chore.",
      heroText:
        "Build interactive lessons with reading panels, adaptive questions, an AI tutor, and clean student links — all in one place.",
      watchPreview: "Watch the preview",
      seeWorkflow: "See the flow",
      stats: [
        ["3", "learning steps"],
        ["AI", "tutor + grading"],
        ["/h", "shareable homework links"],
      ],
      floating: { panels: "Panels", tutor: "Tutor", grade: "Grading" },
      overviewEyebrow: "Overview",
      overviewTitle: "A full lesson, hiding inside one tidy link.",
      overviewText:
        "Instead of a plain form, every homework becomes a tiny learning experience: read, practice, feedback, reflect — with the tutor close by.",
      previewEyebrow: "Preview",
      previewTitle: "Explain first. Then check.",
      previewText:
        "The core idea is sharp: separate panels, swipeable pages, and that final line-to-button moment. This pass clarifies the lesson card, progress, checkpoint and CTA so the hierarchy reads at a glance.",
      tutorEyebrow: "Live tutor",
      tutorTitle: "Works even when the student types like, well, a student.",
      studentLabel: "Student",
      studentMessage: "yo why does revenue go up first then drop later",
      tutorLabel: "Tutor",
      tutorMessage:
        "Because if the price is too high, fewer people buy. Revenue needs both a workable price and enough buyers.",
      usefulTitle: "Less robot. More signal.",
      usefulText:
        "The tutor reads casual phrasing, explains the concept in plain language, and gently nudges the student toward a tighter academic answer.",
      workflowEyebrow: "Flow",
      workflowTitle: "From a teacher’s idea to a student-ready link.",
      quickCardTitle: "Fast for the teacher.",
      quickCardText:
        "You don’t rebuild homework from scratch every time. Start from a template, tune the lesson, and ship the link.",
      safeCardTitle: "Safer by design.",
      safeCardText:
        "For the next beta wave: long random homework slugs, rate limits, and privacy-aware student pages — locked in by default.",
      launchTitle: "Give every homework a little brain.",
      launchText:
        "A premium interface. A simple teacher flow. Student pages that feel like guided learning — not punishment dressed as a form.",
      openBuilder: "Open the builder",
      viewApi: "Browse the library",
      phone: {
        header: "Homework",
        subject: "Quadratic revenue",
        checkpoint: "Checkpoint",
        aiReady: "AI ready",
        question: "Why does the revenue curve rise to a peak and then fall?",
        placeholder: "Student types their answer here...",
        continue: "Continue the lesson",
      },
      lessonPanels: [
        {
          eyebrow: "Reading Panel 01",
          title: "Concept first.",
          body: "Students swipe through clean lesson cards before they’re asked to answer. No walls of text, no noise.",
          tag: "Swipe learning",
        },
        {
          eyebrow: "Adaptive Quiz",
          title: "The answer can be messy — the AI still gets the meaning.",
          body: "The system compares the student’s answer to the expected one and doesn’t punish them for small wording slips.",
          tag: "Hybrid grading",
        },
        {
          eyebrow: "Live Tutor",
          title: "A tutor sits next to every question.",
          body: "Students can ask for a hint, an explanation, or a quick language nudge — without leaving the lesson flow.",
          tag: "AI help",
        },
      ],
      features: [
        {
          icon: "wand",
          title: "Template-based builder",
          body: "Load a ready fixture, edit the lesson content, and ship a student link without rebuilding everything by hand.",
        },
        {
          icon: "layers",
          title: "Panel-based lessons",
          body: "Tougher lessons split into more panels, so the student sees the concept step by step before practice begins.",
        },
        {
          icon: "brain",
          title: "AI-assisted grading",
          body: "Flexible answer matching checks the meaning, returns feedback, and keeps the teacher firmly in the loop.",
        },
        {
          icon: "message",
          title: "Live tutor mode",
          body: "Students can ask for help in Uzbek, English, or messy mid-sentence code-switching — the tutor handles it.",
        },
      ],
      workflow: [
        ["01", "Load a template", "Pick a fixture across algebra, physics, biology, English, history, chemistry, or geometry."],
        ["02", "Edit the panels", "Tune reading cards, quiz blocks, checkpoint prompts, and explanations until it reads right."],
        ["03", "Ship the link", "Generate one stable homework URL the student can open from anywhere."],
        ["04", "Review results", "AI-assisted checking and feedback help you read student performance faster."],
      ],
    },
  };

  // ── State ───────────────────────────────────────────────────────────────
  const STORAGE_KEY = "nets-landing-lang";
  const SUPPORTED_LANGS = ["uz", "ru", "en"];
  const DEFAULT_LANG = "uz";

  const state = {
    lang: DEFAULT_LANG,
    activePanel: 0,
  };

  function readStoredLang() {
    try {
      const stored = window.localStorage.getItem(STORAGE_KEY);
      if (stored && SUPPORTED_LANGS.indexOf(stored) !== -1) return stored;
    } catch (_e) { /* localStorage may be blocked */ }
    return DEFAULT_LANG;
  }

  function persistLang(lang) {
    try { window.localStorage.setItem(STORAGE_KEY, lang); } catch (_e) {}
  }

  // ── Translation rendering ───────────────────────────────────────────────
  function getDeep(obj, path) {
    const parts = path.split(".");
    let cur = obj;
    for (let i = 0; i < parts.length; i++) {
      if (cur == null) return undefined;
      cur = cur[parts[i]];
    }
    return cur;
  }

  function applyTranslations(lang) {
    const dict = i18n[lang] || i18n[DEFAULT_LANG];
    if (!dict) return;

    // Plain text bindings
    document.querySelectorAll("[data-i18n]").forEach(function (el) {
      const key = el.getAttribute("data-i18n");
      const val = getDeep(dict, key);
      if (typeof val === "string") el.textContent = val;
    });

    document.querySelectorAll("[data-i18n-title]").forEach(function (el) {
      const key = el.getAttribute("data-i18n-title");
      const val = getDeep(dict, key);
      if (typeof val === "string") el.setAttribute("title", val);
    });

    // Stats: data-i18n-stat-value/label="<index>"
    const stats = dict.stats || [];
    document.querySelectorAll("[data-i18n-stat-value]").forEach(function (el) {
      const i = parseInt(el.getAttribute("data-i18n-stat-value"), 10);
      if (stats[i]) el.textContent = stats[i][0];
    });
    document.querySelectorAll("[data-i18n-stat-label]").forEach(function (el) {
      const i = parseInt(el.getAttribute("data-i18n-stat-label"), 10);
      if (stats[i]) el.textContent = stats[i][1];
    });

    // Features
    const features = dict.features || [];
    document.querySelectorAll("[data-i18n-feature-title]").forEach(function (el) {
      const i = parseInt(el.getAttribute("data-i18n-feature-title"), 10);
      if (features[i]) el.textContent = features[i].title;
    });
    document.querySelectorAll("[data-i18n-feature-body]").forEach(function (el) {
      const i = parseInt(el.getAttribute("data-i18n-feature-body"), 10);
      if (features[i]) el.textContent = features[i].body;
    });

    // Lesson panels (left list)
    const panels = dict.lessonPanels || [];
    document.querySelectorAll("[data-i18n-panel-eyebrow]").forEach(function (el) {
      const i = parseInt(el.getAttribute("data-i18n-panel-eyebrow"), 10);
      if (panels[i]) el.textContent = panels[i].eyebrow;
    });
    document.querySelectorAll("[data-i18n-panel-title]").forEach(function (el) {
      const i = parseInt(el.getAttribute("data-i18n-panel-title"), 10);
      if (panels[i]) el.textContent = panels[i].title;
    });

    // Workflow
    const workflow = dict.workflow || [];
    document.querySelectorAll("[data-i18n-workflow-num]").forEach(function (el) {
      const i = parseInt(el.getAttribute("data-i18n-workflow-num"), 10);
      if (workflow[i]) el.textContent = workflow[i][0];
    });
    document.querySelectorAll("[data-i18n-workflow-title]").forEach(function (el) {
      const i = parseInt(el.getAttribute("data-i18n-workflow-title"), 10);
      if (workflow[i]) el.textContent = workflow[i][1];
    });
    document.querySelectorAll("[data-i18n-workflow-body]").forEach(function (el) {
      const i = parseInt(el.getAttribute("data-i18n-workflow-body"), 10);
      if (workflow[i]) el.textContent = workflow[i][2];
    });

    // Phone lesson card (active panel)
    renderPhonePanel(state.activePanel, false);

    // Update <html lang>
    document.documentElement.setAttribute("lang", lang);

    // Update language pills active state
    document.querySelectorAll(".lang-pill").forEach(function (pill) {
      const l = pill.getAttribute("data-lang");
      pill.classList.toggle("is-active", l === lang);
      pill.setAttribute("aria-pressed", l === lang ? "true" : "false");
    });
  }

  // ── Phone lesson-card swap with View Transitions API ────────────────────
  function renderPhonePanel(index, useTransition) {
    const dict = i18n[state.lang] || i18n[DEFAULT_LANG];
    const panels = dict.lessonPanels || [];
    const panel = panels[index];
    if (!panel) return;

    const apply = function () {
      const eyebrowEl = document.getElementById("phone-eyebrow");
      const titleEl = document.getElementById("phone-title");
      const bodyEl = document.getElementById("phone-body");
      const tagEl = document.getElementById("phone-tag");
      if (eyebrowEl) eyebrowEl.textContent = panel.eyebrow;
      if (titleEl) titleEl.textContent = panel.title;
      if (bodyEl) bodyEl.textContent = panel.body;
      if (tagEl) tagEl.textContent = panel.tag;

      // Update dots
      const dots = document.querySelectorAll("#phone-dots .phone-dot");
      dots.forEach(function (dot, i) {
        dot.classList.toggle("is-active", i === index);
      });

      // Update lesson-panel buttons in left list
      const lessonButtons = document.querySelectorAll(".lesson-panel");
      lessonButtons.forEach(function (btn, i) {
        const isActive = i === index;
        btn.classList.toggle("is-active", isActive);
        btn.setAttribute("aria-selected", isActive ? "true" : "false");
      });
    };

    if (
      useTransition &&
      typeof document.startViewTransition === "function" &&
      !window.matchMedia("(prefers-reduced-motion: reduce)").matches
    ) {
      try {
        document.startViewTransition(apply);
      } catch (_e) {
        apply();
      }
    } else {
      apply();
    }
  }

  // ── Language toggle wiring ──────────────────────────────────────────────
  function setLang(lang) {
    if (SUPPORTED_LANGS.indexOf(lang) === -1) lang = DEFAULT_LANG;
    state.lang = lang;
    persistLang(lang);
    applyTranslations(lang);
  }

  function bindLanguageToggle() {
    document.querySelectorAll(".lang-pill").forEach(function (pill) {
      pill.addEventListener("click", function () {
        const lang = pill.getAttribute("data-lang");
        if (lang) setLang(lang);
      });
    });
  }

  // ── Lesson panel selection (left list) ──────────────────────────────────
  function bindLessonPanels() {
    document.querySelectorAll(".lesson-panel").forEach(function (btn) {
      btn.addEventListener("click", function () {
        const idx = parseInt(btn.getAttribute("data-panel-index"), 10);
        if (Number.isNaN(idx)) return;
        if (idx === state.activePanel) return;
        state.activePanel = idx;
        renderPhonePanel(idx, true);
      });
    });
  }

  // ── IntersectionObserver reveals ────────────────────────────────────────
  function bindRevealObserver() {
    if (!("IntersectionObserver" in window)) {
      // Fallback: just show everything.
      document.querySelectorAll("[data-reveal], .stagger-parent").forEach(function (el) {
        el.classList.add("is-visible");
      });
      return;
    }

    const observer = new IntersectionObserver(
      function (entries) {
        entries.forEach(function (entry) {
          if (entry.isIntersecting) {
            entry.target.classList.add("is-visible");
            observer.unobserve(entry.target);
          }
        });
      },
      { threshold: 0.18, rootMargin: "0px 0px -8% 0px" }
    );

    document.querySelectorAll("[data-reveal], .stagger-parent").forEach(function (el) {
      // The hero content is already marked .is-visible in the HTML — skip those.
      if (el.classList.contains("is-visible")) return;
      observer.observe(el);
    });
  }

  // ── Hero scroll parallax (rAF-throttled) ────────────────────────────────
  function bindHeroParallax() {
    const hero = document.querySelector("[data-hero-parallax]");
    if (!hero) return;

    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;

    let ticking = false;
    let lastScrollY = 0;

    function update() {
      ticking = false;
      // 0..1 progress over the first ~22% of the viewport, similar to the JSX useTransform map.
      const docH = document.documentElement.scrollHeight - window.innerHeight;
      const progress = docH > 0 ? Math.min(1, lastScrollY / docH) : 0;
      // Apply only across the early scroll range — past 22% the hero is mostly off-screen.
      const earlyProgress = Math.min(1, progress / 0.22);
      const opaqueProgress = Math.min(1, progress / 0.18);

      const y = -95 * earlyProgress;
      const scale = 1 - 0.08 * earlyProgress;
      const opacity = 1 - 0.65 * opaqueProgress;

      hero.style.transform = "translate3d(0," + y.toFixed(2) + "px, 0) scale(" + scale.toFixed(3) + ")";
      hero.style.opacity = opacity.toFixed(3);
    }

    function onScroll() {
      lastScrollY = window.scrollY || window.pageYOffset || 0;
      if (!ticking) {
        window.requestAnimationFrame(update);
        ticking = true;
      }
    }

    // Run once to set initial state.
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    window.addEventListener("resize", onScroll, { passive: true });
  }

  // ── Smooth scroll for in-page anchors ───────────────────────────────────
  function bindSmoothAnchors() {
    document.querySelectorAll('a[href^="#"]').forEach(function (a) {
      a.addEventListener("click", function (e) {
        const href = a.getAttribute("href");
        if (!href || href === "#" || href.length < 2) return;
        const target = document.querySelector(href);
        if (!target) return;
        e.preventDefault();
        target.scrollIntoView({ behavior: "smooth", block: "start" });
        // Move focus for a11y, but don't yank scroll.
        target.setAttribute("tabindex", "-1");
        target.focus({ preventScroll: true });
      });
    });
  }

  // ── Boot ─────────────────────────────────────────────────────────────────
  function init() {
    state.lang = readStoredLang();
    state.activePanel = 0;

    applyTranslations(state.lang);
    bindLanguageToggle();
    bindLessonPanels();
    bindRevealObserver();
    bindHeroParallax();
    bindSmoothAnchors();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
