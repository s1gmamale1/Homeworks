// Direct KaTeX render test — inject a known LaTeX string into the page,
// wait for the auto-render MutationObserver to fire, then check that the
// node has been replaced by KaTeX-rendered HTML (.katex span).
const puppeteer = require('puppeteer');
const { launchOptions } = require('./puppeteer_launcher.cjs');
const URL = 'http://127.0.0.1:8000/h/HW-20260427-008';

(async () => {
  const browser = await puppeteer.launch(launchOptions({
    headless: 'new',
    args: ['--no-sandbox', '--disable-setuid-sandbox'],
  }));
  const page = await browser.newPage();
  page.setDefaultTimeout(20000);

  console.log('Load', URL);
  await page.goto(URL, { waitUntil: 'networkidle0' });

  // Wait a frame for KaTeX to attach
  await new Promise(r => setTimeout(r, 500));

  const result = await page.evaluate(async () => {
    const ready = typeof window.renderMathInElement === 'function';
    if (!ready) return { ready: false };

    // Inject a probe div with the exact failing prompt
    const probe = document.createElement('div');
    probe.id = '__katex_probe__';
    probe.style.cssText = 'position:fixed;left:-9999px;top:-9999px;';
    probe.innerHTML = "Aylanadan tashqaridagi $P$ nuqtadan ikkita kesuvchi o'tkazilgan. Ular aylanadan $100^\\circ$ va $40^\\circ$ yoylarni ajratib turadi. $\\angle P$ ning qiymatini toping.";
    document.body.appendChild(probe);

    // Give MutationObserver + rAF time to render (3 frames + 200ms slack)
    await new Promise(r => setTimeout(r, 600));

    const text = probe.innerText;
    const html = probe.innerHTML;
    const katexCount = probe.querySelectorAll('.katex').length;
    const dollarLeft = (text.match(/\$[^$\n]{1,40}\$/g) || []);
    return {
      ready: true,
      katexCount,
      dollarLeft,
      htmlSample: html.slice(0, 600),
      text: text.slice(0, 220),
    };
  });

  console.log(JSON.stringify(result, null, 2));

  const fixed = result.ready && result.katexCount >= 3 && result.dollarLeft.length === 0;
  console.log('\n=== VERDICT: KaTeX rendering ' + (fixed ? 'WORKS ✓' : 'NOT WORKING ✗') + ' ===');

  await browser.close();
  process.exit(fixed ? 0 : 1);
})().catch(e => { console.error('Test crashed:', e); process.exit(2); });
