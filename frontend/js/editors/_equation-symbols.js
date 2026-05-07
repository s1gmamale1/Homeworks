// frontend/js/editors/_equation-symbols.js
// Curated math symbol + template catalogue used by the Equation Picker.
//
// Pure data — no DOM, no side effects. Loads onto window.EquationSymbols.
//
// Authoring rules:
//   - latex     : LaTeX inserted into the math-field. The picker passes this
//                 to MathLive's `executeCommand("insert", latex)` which keeps
//                 the cursor inside the first {} placeholder for templates.
//   - unicode   : optional fast-path glyph for Shift-click inserts.
//   - display   : the visible label rendered inside the tile (KaTeX target).
//   - name      : human-readable name used by search.
//   - aliases   : extra search terms (e.g. Uzbek transliteration).
//   - displayMode: true for templates that render in display style (matrices,
//                  cases, aligned). The picker wraps these in $$..$$ on
//                  insert + flips the math-field's display attribute.
(function () {
  "use strict";

  const COMMON = [
    { latex: "\\pm",      unicode: "±",  display: "\\pm",      name: "plus or minus" },
    { latex: "\\mp",      unicode: "∓",  display: "\\mp",      name: "minus or plus" },
    { latex: "\\times",   unicode: "×",  display: "\\times",   name: "times",        aliases: ["multiply", "kopaytirish"] },
    { latex: "\\div",     unicode: "÷",  display: "\\div",     name: "divide",       aliases: ["bolish"] },
    { latex: "\\cdot",    unicode: "⋅",  display: "\\cdot",    name: "dot product" },
    { latex: "\\infty",   unicode: "∞",  display: "\\infty",   name: "infinity",     aliases: ["cheksizlik"] },
    { latex: "\\sqrt{#0}",          display: "\\sqrt{x}",      name: "square root",  aliases: ["root", "ildiz"] },
    { latex: "\\frac{#0}{#1}",      display: "\\frac{a}{b}",   name: "fraction",     aliases: ["kasr"] },
    { latex: "\\sum",     unicode: "∑",  display: "\\sum",     name: "summation",    aliases: ["sigma", "yigindi"] },
    { latex: "\\int",     unicode: "∫",  display: "\\int",     name: "integral" },
    { latex: "\\approx",  unicode: "≈",  display: "\\approx",  name: "approximately",aliases: ["taqriban"] },
    { latex: "\\neq",     unicode: "≠",  display: "\\neq",     name: "not equal",    aliases: ["teng emas"] },
    { latex: "\\leq",     unicode: "≤",  display: "\\leq",     name: "less or equal", aliases: ["kichik teng"] },
    { latex: "\\geq",     unicode: "≥",  display: "\\geq",     name: "greater or equal", aliases: ["katta teng"] },
    { latex: "\\equiv",   unicode: "≡",  display: "\\equiv",   name: "identical" },
    { latex: "#0^{#1}",   display: "x^{n}",      name: "superscript power", aliases: ["power", "daraja"] },
    { latex: "#0_{#1}",   display: "x_{n}",      name: "subscript",         aliases: ["index"] },
  ];

  const GREEK_LOWER = [
    { latex: "\\alpha",   unicode: "α", display: "\\alpha",   name: "alpha",   aliases: ["alfa"] },
    { latex: "\\beta",    unicode: "β", display: "\\beta",    name: "beta" },
    { latex: "\\gamma",   unicode: "γ", display: "\\gamma",   name: "gamma" },
    { latex: "\\delta",   unicode: "δ", display: "\\delta",   name: "delta" },
    { latex: "\\epsilon", unicode: "ε", display: "\\epsilon", name: "epsilon" },
    { latex: "\\zeta",    unicode: "ζ", display: "\\zeta",    name: "zeta" },
    { latex: "\\eta",     unicode: "η", display: "\\eta",     name: "eta" },
    { latex: "\\theta",   unicode: "θ", display: "\\theta",   name: "theta",   aliases: ["teta"] },
    { latex: "\\iota",    unicode: "ι", display: "\\iota",    name: "iota" },
    { latex: "\\kappa",   unicode: "κ", display: "\\kappa",   name: "kappa" },
    { latex: "\\lambda",  unicode: "λ", display: "\\lambda",  name: "lambda" },
    { latex: "\\mu",      unicode: "μ", display: "\\mu",      name: "mu",      aliases: ["myu"] },
    { latex: "\\nu",      unicode: "ν", display: "\\nu",      name: "nu" },
    { latex: "\\xi",      unicode: "ξ", display: "\\xi",      name: "xi",      aliases: ["ksi"] },
    { latex: "\\pi",      unicode: "π", display: "\\pi",      name: "pi" },
    { latex: "\\rho",     unicode: "ρ", display: "\\rho",     name: "rho" },
    { latex: "\\sigma",   unicode: "σ", display: "\\sigma",   name: "sigma" },
    { latex: "\\tau",     unicode: "τ", display: "\\tau",     name: "tau" },
    { latex: "\\phi",     unicode: "φ", display: "\\phi",     name: "phi",     aliases: ["fi"] },
    { latex: "\\chi",     unicode: "χ", display: "\\chi",     name: "chi" },
    { latex: "\\psi",     unicode: "ψ", display: "\\psi",     name: "psi" },
    { latex: "\\omega",   unicode: "ω", display: "\\omega",   name: "omega" },
  ];

  const GREEK_UPPER = [
    { latex: "\\Gamma",   unicode: "Γ", display: "\\Gamma",   name: "Gamma capital" },
    { latex: "\\Delta",   unicode: "Δ", display: "\\Delta",   name: "Delta capital" },
    { latex: "\\Theta",   unicode: "Θ", display: "\\Theta",   name: "Theta capital" },
    { latex: "\\Lambda",  unicode: "Λ", display: "\\Lambda",  name: "Lambda capital" },
    { latex: "\\Xi",      unicode: "Ξ", display: "\\Xi",      name: "Xi capital" },
    { latex: "\\Pi",      unicode: "Π", display: "\\Pi",      name: "Pi capital" },
    { latex: "\\Sigma",   unicode: "Σ", display: "\\Sigma",   name: "Sigma capital" },
    { latex: "\\Phi",     unicode: "Φ", display: "\\Phi",     name: "Phi capital" },
    { latex: "\\Psi",     unicode: "Ψ", display: "\\Psi",     name: "Psi capital" },
    { latex: "\\Omega",   unicode: "Ω", display: "\\Omega",   name: "Omega capital" },
  ];

  const OPERATORS = [
    { latex: "+",          unicode: "+",  display: "+",          name: "plus" },
    { latex: "-",          unicode: "−",  display: "-",          name: "minus" },
    { latex: "\\times",    unicode: "×",  display: "\\times",    name: "times" },
    { latex: "\\div",      unicode: "÷",  display: "\\div",      name: "divide" },
    { latex: "\\cdot",     unicode: "⋅",  display: "\\cdot",     name: "dot" },
    { latex: "\\ast",      unicode: "∗",  display: "\\ast",      name: "asterisk" },
    { latex: "\\circ",     unicode: "∘",  display: "\\circ",     name: "ring" },
    { latex: "\\oplus",    unicode: "⊕",  display: "\\oplus",    name: "circled plus" },
    { latex: "\\otimes",   unicode: "⊗",  display: "\\otimes",   name: "circled times" },
    { latex: "\\nabla",    unicode: "∇",  display: "\\nabla",    name: "nabla del" },
    { latex: "\\partial",  unicode: "∂",  display: "\\partial",  name: "partial" },
    { latex: "\\propto",   unicode: "∝",  display: "\\propto",   name: "proportional" },
  ];

  const RELATIONS = [
    { latex: "=",         unicode: "=",  display: "=",         name: "equal",          aliases: ["teng"] },
    { latex: "\\neq",     unicode: "≠",  display: "\\neq",     name: "not equal" },
    { latex: "<",         unicode: "<",  display: "<",         name: "less than" },
    { latex: ">",         unicode: ">",  display: ">",         name: "greater than" },
    { latex: "\\leq",     unicode: "≤",  display: "\\leq",     name: "less or equal" },
    { latex: "\\geq",     unicode: "≥",  display: "\\geq",     name: "greater or equal" },
    { latex: "\\approx",  unicode: "≈",  display: "\\approx",  name: "approximately" },
    { latex: "\\equiv",   unicode: "≡",  display: "\\equiv",   name: "identical" },
    { latex: "\\sim",     unicode: "∼",  display: "\\sim",     name: "similar" },
    { latex: "\\cong",    unicode: "≅",  display: "\\cong",    name: "congruent" },
    { latex: "\\propto",  unicode: "∝",  display: "\\propto",  name: "proportional" },
    { latex: "\\parallel",unicode: "∥",  display: "\\parallel",name: "parallel" },
    { latex: "\\perp",    unicode: "⊥",  display: "\\perp",    name: "perpendicular",  aliases: ["perpendikulyar"] },
  ];

  const FRACTIONS_ROOTS = [
    { latex: "\\frac{#0}{#1}",      display: "\\frac{a}{b}",      name: "fraction",         aliases: ["kasr"] },
    { latex: "\\dfrac{#0}{#1}",     display: "\\dfrac{a}{b}",     name: "display fraction" },
    { latex: "\\sqrt{#0}",          display: "\\sqrt{x}",         name: "square root",      aliases: ["ildiz"] },
    { latex: "\\sqrt[#0]{#1}",      display: "\\sqrt[n]{x}",      name: "nth root" },
    { latex: "\\sqrt[3]{#0}",       display: "\\sqrt[3]{x}",      name: "cube root",        aliases: ["kub ildiz"] },
  ];

  const SUPER_SUB = [
    { latex: "#0^{#1}",   display: "x^{n}",         name: "superscript",       aliases: ["power", "daraja"] },
    { latex: "#0_{#1}",   display: "x_{n}",         name: "subscript",         aliases: ["index"] },
    { latex: "#0^{2}",    display: "x^{2}",         name: "squared",           aliases: ["kvadrat"] },
    { latex: "#0^{3}",    display: "x^{3}",         name: "cubed",             aliases: ["kub"] },
    { latex: "#0^{-1}",   display: "x^{-1}",        name: "inverse" },
    { latex: "#0_{#1}^{#2}", display: "x_{i}^{n}",  name: "sub and super" },
    { latex: "\\overline{#0}", display: "\\overline{x}", name: "overline bar" },
    { latex: "\\hat{#0}",      display: "\\hat{x}",      name: "hat" },
    { latex: "\\vec{#0}",      display: "\\vec{x}",      name: "vector",        aliases: ["vektor"] },
  ];

  const CALCULUS = [
    { latex: "\\int_{#0}^{#1}",     display: "\\int_{a}^{b}",        name: "integral with limits" },
    { latex: "\\iint",              display: "\\iint",               name: "double integral" },
    { latex: "\\oint",              display: "\\oint",               name: "contour integral" },
    { latex: "\\sum_{#0}^{#1}",     display: "\\sum_{i=1}^{n}",      name: "sum with limits", aliases: ["yigindi"] },
    { latex: "\\prod_{#0}^{#1}",    display: "\\prod_{i=1}^{n}",     name: "product with limits" },
    { latex: "\\lim_{#0\\to#1}",    display: "\\lim_{x \\to 0}",     name: "limit" },
    { latex: "\\frac{d}{d#0}",      display: "\\frac{d}{dx}",        name: "derivative",     aliases: ["hosila"] },
    { latex: "\\frac{\\partial #0}{\\partial #1}", display: "\\frac{\\partial f}{\\partial x}", name: "partial derivative" },
    { latex: "\\nabla",             display: "\\nabla",              name: "nabla" },
  ];

  const BRACKETS = [
    { latex: "(#0)",        display: "(\\,)",          name: "parentheses",     aliases: ["qavs"] },
    { latex: "[#0]",        display: "[\\,]",          name: "square brackets" },
    { latex: "\\{#0\\}",    display: "\\{\\,\\}",      name: "curly braces" },
    { latex: "\\langle #0 \\rangle", display: "\\langle\\,\\rangle", name: "angle brackets" },
    { latex: "\\lfloor #0 \\rfloor", display: "\\lfloor\\,\\rfloor", name: "floor" },
    { latex: "\\lceil #0 \\rceil",   display: "\\lceil\\,\\rceil",   name: "ceiling" },
    { latex: "\\left( #0 \\right)",  display: "\\left(\\,\\right)",  name: "auto-sized parens" },
    { latex: "|#0|",        display: "|x|",            name: "absolute value",  aliases: ["modul"] },
  ];

  const ARROWS = [
    { latex: "\\leftarrow",      unicode: "←", display: "\\leftarrow",      name: "left arrow" },
    { latex: "\\rightarrow",     unicode: "→", display: "\\rightarrow",     name: "right arrow" },
    { latex: "\\leftrightarrow", unicode: "↔", display: "\\leftrightarrow", name: "left-right arrow" },
    { latex: "\\Leftarrow",      unicode: "⇐", display: "\\Leftarrow",      name: "double left" },
    { latex: "\\Rightarrow",     unicode: "⇒", display: "\\Rightarrow",     name: "implies" },
    { latex: "\\Leftrightarrow", unicode: "⇔", display: "\\Leftrightarrow", name: "iff" },
    { latex: "\\mapsto",         unicode: "↦", display: "\\mapsto",         name: "maps to" },
    { latex: "\\to",             unicode: "→", display: "\\to",             name: "to" },
  ];

  const LOGIC_SETS = [
    { latex: "\\forall",   unicode: "∀", display: "\\forall",   name: "for all",          aliases: ["barcha"] },
    { latex: "\\exists",   unicode: "∃", display: "\\exists",   name: "there exists",     aliases: ["mavjud"] },
    { latex: "\\in",       unicode: "∈", display: "\\in",       name: "element of",       aliases: ["tegishli"] },
    { latex: "\\notin",    unicode: "∉", display: "\\notin",    name: "not element of" },
    { latex: "\\subset",   unicode: "⊂", display: "\\subset",   name: "subset" },
    { latex: "\\subseteq", unicode: "⊆", display: "\\subseteq", name: "subset or equal" },
    { latex: "\\cup",      unicode: "∪", display: "\\cup",      name: "union" },
    { latex: "\\cap",      unicode: "∩", display: "\\cap",      name: "intersection" },
    { latex: "\\emptyset", unicode: "∅", display: "\\emptyset", name: "empty set" },
    { latex: "\\land",     unicode: "∧", display: "\\land",     name: "logical and" },
    { latex: "\\lor",      unicode: "∨", display: "\\lor",      name: "logical or" },
    { latex: "\\lnot",     unicode: "¬", display: "\\lnot",     name: "logical not" },
    { latex: "\\therefore",unicode: "∴", display: "\\therefore",name: "therefore" },
  ];

  // Matrix / cases / aligned templates use MathLive's canonical form (no
  // surrounding whitespace inside \begin{} / \end{} pairs — MathLive collapses
  // those at insertion time anyway). One single ASCII space after `\\` is
  // preserved because that DOES survive MathLive's expansion.
  const MATRICES = [
    {
      latex: "\\begin{pmatrix}#0 & #1\\\\ #2 & #3\\end{pmatrix}",
      display: "\\begin{pmatrix} a & b \\\\ c & d \\end{pmatrix}",
      name: "2x2 matrix parens",
      displayMode: true,
    },
    {
      latex: "\\begin{bmatrix}#0 & #1\\\\ #2 & #3\\end{bmatrix}",
      display: "\\begin{bmatrix} a & b \\\\ c & d \\end{bmatrix}",
      name: "2x2 matrix brackets",
      displayMode: true,
    },
    {
      latex: "\\begin{vmatrix}#0 & #1\\\\ #2 & #3\\end{vmatrix}",
      display: "\\begin{vmatrix} a & b \\\\ c & d \\end{vmatrix}",
      name: "2x2 determinant",
      aliases: ["determinant"],
      displayMode: true,
    },
    {
      latex: "\\begin{pmatrix}#0 & #1 & #2\\\\ #3 & #4 & #5\\\\ #6 & #7 & #8\\end{pmatrix}",
      display: "\\begin{pmatrix} a & b & c \\\\ d & e & f \\\\ g & h & i \\end{pmatrix}",
      name: "3x3 matrix parens",
      displayMode: true,
    },
    {
      latex: "\\begin{cases}#0, & #1\\\\ #2, & #3\\end{cases}",
      display: "\\begin{cases} a, & x>0 \\\\ b, & x\\le 0 \\end{cases}",
      name: "piecewise cases",
      displayMode: true,
    },
    {
      latex: "\\begin{aligned}#0 &= #1\\\\ #2 &= #3\\end{aligned}",
      display: "\\begin{aligned} a &= b \\\\ c &= d \\end{aligned}",
      name: "aligned equations",
      displayMode: true,
    },
  ];

  const CATEGORIES = [
    { id: "common",     label: "Common",       entries: COMMON },
    { id: "greek",      label: "Greek",        entries: GREEK_LOWER.concat(GREEK_UPPER) },
    { id: "operators",  label: "Operators",    entries: OPERATORS },
    { id: "relations",  label: "Relations",    entries: RELATIONS },
    { id: "fractions",  label: "Fractions",    entries: FRACTIONS_ROOTS },
    { id: "scripts",    label: "Scripts",      entries: SUPER_SUB },
    { id: "calculus",   label: "Calculus",     entries: CALCULUS },
    { id: "brackets",   label: "Brackets",     entries: BRACKETS },
    { id: "arrows",     label: "Arrows",       entries: ARROWS },
    { id: "logic",      label: "Logic / Sets", entries: LOGIC_SETS },
    { id: "matrices",   label: "Matrices",     entries: MATRICES },
  ];

  const ALL_BY_KEY = (function () {
    const out = Object.create(null);
    for (const cat of CATEGORIES) {
      for (const entry of cat.entries) {
        out[entry.latex] = { ...entry, _categoryId: cat.id };
      }
    }
    return out;
  })();

  function searchableText(entry) {
    return [
      entry.name || "",
      entry.latex || "",
      entry.unicode || "",
      ...(entry.aliases || []),
    ]
      .join(" ")
      .toLowerCase();
  }

  function search(query) {
    const q = String(query || "").trim().toLowerCase();
    if (!q) return [];
    const hits = [];
    for (const cat of CATEGORIES) {
      for (const entry of cat.entries) {
        if (searchableText(entry).indexOf(q) !== -1) {
          hits.push({ ...entry, _categoryId: cat.id });
        }
      }
    }
    return hits;
  }

  function lookup(latex) {
    return ALL_BY_KEY[latex] || null;
  }

  window.EquationSymbols = {
    CATEGORIES,
    search,
    lookup,
    all() {
      const out = [];
      for (const cat of CATEGORIES) {
        for (const e of cat.entries) out.push({ ...e, _categoryId: cat.id });
      }
      return out;
    },
  };
})();
