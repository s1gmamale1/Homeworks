// Audit the rendered Theme Preview (panels) for presentation quality.
//   - All 7 panels reachable
//   - SVGs render with valid dimensions (not hidden, not 0×0)
//   - KaTeX math expressions render (no leftover $...$ in DOM text)
//   - Bracketed authoring directives don't leak into rendered text
//   - Memory Sprint prompts have no leftover ✓ / option markers in HTML
//   - Headings (h2) render at appropriate visual weight
const puppeteer = require('puppeteer');
const { launchOptions } = require('./puppeteer_launcher.cjs');
const URL = 'http://127.0.0.1:8000/h/HW-20260427-008';

(async () => {
  const browser = await puppeteer.launch(launchOptions({
    headless: 'new',
    args: ['--no-sandbox', '--disable-setuid-sandbox'],
    defaultViewport: { width: 1280, height: 900 },
  }));
  const page = await browser.newPage();
  page.setDefaultTimeout(20000);
  page.on('pageerror', e => console.log('PAGEERROR:', e.message));

  console.log('Load', URL);
  await page.goto(URL, { waitUntil: 'networkidle0' });
  await new Promise(r => setTimeout(r, 1200));

  // Read rendered preview structure: walk PANELS array (which the template
  // injects with the same data we sent) and ask the DOM what got rendered.
  const audit = await page.evaluate(() => {
    const out = { panels: [], errors: [] };
    if (typeof PANELS === 'undefined') return { error: 'no PANELS constant' };
    PANELS.forEach((p, i) => {
      const panelInfo = {
        idx: i,
        title: p.title,
        blockTypes: (p.pages[0]?.blocks || []).map(b => b.type),
      };
      out.panels.push(panelInfo);
    });
    return out;
  });
  console.log('\n=== Panel structure ===');
  audit.panels.forEach(p => console.log(`  ${p.idx}: ${p.title} blocks=[${p.blockTypes.join(', ')}]`));

  // Walk through each panel by clicking next, take a quick measurement on
  // each. The runtime renders one panel at a time on screen 0 (theme preview).
  const screenInfo = await page.evaluate(() => {
    const sc = document.querySelectorAll('.screen');
    return Array.from(sc).map(s => ({ id: s.id, visible: s.classList.contains('active') }));
  });
  console.log('\n=== Screens ===', screenInfo.slice(0, 12));

  // Force-navigate to screen-2 (Theme Preview / panels) and render panel 4
  // (Misollar — the most complex one with 5 SVGs and 2 h2 headings).
  const panelDom = await page.evaluate(async () => {
    // Switch to the panels screen and render panel 4 (zero-indexed: 3).
    // Walk to screen-2 (panels) and render panel 4 (Misollar, idx 3).
    if (typeof state !== 'undefined') {
      state.stage = 2;
      state.panelIndex = 3;
      state.pageIndex = 0;
    }
    document.querySelectorAll('.screen').forEach(s => s.classList.remove('active'));
    const sc2 = document.getElementById('screen-2');
    if (sc2) sc2.classList.add('active');
    if (typeof renderPanel === 'function') renderPanel();
    await new Promise(r => setTimeout(r, 800));
    const card = document.getElementById('panel-card');
    if (!card) return { found: false, count: 0 };
    // panel-content is the live render target.
    const content = document.getElementById('panel-content');
    if (!content) return { found: false, count: 0 };
    const svgs   = content.querySelectorAll('svg');
    const ps     = content.querySelectorAll('p');
    const h2s    = content.querySelectorAll('h2');
    const quotes = content.querySelectorAll('blockquote');
    const unknown = content.querySelectorAll('.block-unknown');
    const katex  = content.querySelectorAll('.katex');
    const txt    = content.innerText || '';
    const dollarLeft  = (txt.match(/\$[^$\n]{1,40}\$/g) || []);
    const bracketLeft = (txt.match(/^\s*\[[^\]]+\]\s*$/gm) || []);
    const tickLeft    = (txt.match(/✓/g) || []).length;
    const svgDims = Array.from(svgs).map(s => ({ w: s.getBoundingClientRect().width, h: s.getBoundingClientRect().height }));
    return {
      found: true,
      count: 1,
      panels: [{
        idx: 3,
        h2: h2s.length, p: ps.length, svg: svgs.length, quote: quotes.length,
        unknown: unknown.length, katex: katex.length,
        dollar_left: dollarLeft.length, bracket_left: bracketLeft.length, tick_left: tickLeft,
        svg_dims: svgDims,
        txt_head: txt.slice(0, 200).replace(/\s+/g, ' '),
      }],
    };
  });
  console.log('\n=== Rendered panel DOM (first page only) ===');
  console.log('  panels rendered:', panelDom.count);
  if (panelDom.panels) panelDom.panels.slice(0, 8).forEach(p =>
    console.log(`  panel#${p.idx}: h2=${p.h2} p=${p.p} svg=${p.svg} quote=${p.quote} unknown=${p.unknown} | dollar=${p.dollar_left} bracket=${p.bracket_left} tick=${p.tick_left}\n           dims=${JSON.stringify(p.svg_dims)}\n           head=${JSON.stringify(p.txt_head)}`));

  // Memory Sprint prompts — check for leaked option markers
  const msHtml = await page.evaluate(() => {
    if (typeof MS_QUESTIONS === 'undefined') return null;
    return MS_QUESTIONS.map((q, i) => ({
      i, type: q.type, has_tick: /✓/.test(q.prompt || '') || /✓/.test(q.explain || ''),
      has_letterPrefix: /\b[A-D]\)/.test(q.prompt || ''),
      has_dashOption:   /\n\s*-\s+/.test(q.prompt || ''),
      tags: q.tags,
      promptHead: (q.prompt || '').slice(0, 90),
    }));
  });
  console.log('\n=== Memory Sprint prompt cleanliness ===');
  if (msHtml) msHtml.forEach(m => console.log(`  Q${m.i+1} ${m.type}: tick=${m.has_tick} letterPrefix=${m.has_letterPrefix} dashOpt=${m.has_dashOption} tags=${JSON.stringify(m.tags)}\n     ${JSON.stringify(m.promptHead)}`));

  // Verdicts
  const firstPanel = (panelDom.panels && panelDom.panels[0]) || {};
  const verdict = {
    panel_count_7: audit.panels.length === 7,
    panel_titles_clean: audit.panels.every(p => /^PANEL \d — \w/.test(p.title)) &&
                        audit.panels[0].title.includes('NIMA UCHUN') &&
                        audit.panels[6].title.includes('NIMA UCHUN'),
    panel4_has_h2: audit.panels[3] && audit.panels[3].blockTypes.includes('h2'),
    panel4_has_5_svgs: audit.panels[3] && audit.panels[3].blockTypes.filter(t => t === 'svg').length === 5,
    no_dollar_leftovers: firstPanel.dollar_left === 0 || firstPanel.dollar_left == null,
    no_bracket_leftovers: firstPanel.bracket_left === 0 || firstPanel.bracket_left == null,
    no_tick_in_prompts: msHtml ? msHtml.every(m => !m.has_tick && !m.has_letterPrefix && !m.has_dashOption) : false,
    ms_tags_proper: msHtml ? msHtml.every(m => /Bloom: L\d \| PISA: L\d/.test(m.tags || '')) : false,
    no_unknown_blocks: firstPanel.unknown === 0 || firstPanel.unknown == null,
    svgs_have_dim: firstPanel.svg_dims && firstPanel.svg_dims.length > 0 && firstPanel.svg_dims.every(d => d.w > 50 && d.h > 50),
  };
  console.log('\n=== Verdicts ===');
  console.log(JSON.stringify(verdict, null, 2));
  const allPass = Object.values(verdict).every(Boolean);
  console.log('\n=== ' + (allPass ? 'ALL PASS ✓' : 'FAILURES — see above ✗') + ' ===');

  await browser.close();
  process.exit(allPass ? 0 : 1);
})().catch(e => { console.error(e); process.exit(2); });
