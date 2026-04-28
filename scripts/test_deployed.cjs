/**
 * Generic smoke test for any deployed homework.
 * Usage: SERVER=http://127.0.0.1:5061 node scripts/test_deployed.cjs
 */
const { JSDOM, ResourceLoader, VirtualConsole } = require('jsdom');
const SERVER = process.env.SERVER || 'http://127.0.0.1:5061';
const vc = new VirtualConsole();
const errors = [];
vc.on('jsdomError', e => errors.push(['jsdomError', e.message]));
vc.forwardTo(console, { omitJSDOMErrors: false });

(async () => {
  console.log('Probing', SERVER);
  const dom = await JSDOM.fromURL(SERVER + '/', {
    runScripts: 'dangerously',
    resources: new ResourceLoader(),
    pretendToBeVisual: true,
    virtualConsole: vc
  });
  const { window } = dom;
  const realFetch = fetch;
  window.fetch = (url, opts) => {
    if (typeof url === 'string' && url.startsWith('/')) url = SERVER + url;
    return realFetch(url, opts);
  };
  await new Promise(res => {
    if (window.document.readyState === 'complete') return res();
    window.addEventListener('load', () => res(), { once: true });
  });
  await new Promise(r => setTimeout(r, 1000));

  const $ = sel => window.document.querySelector(sel);
  const $$ = sel => Array.from(window.document.querySelectorAll(sel));
  let pass = 0, fail = 0;
  function assert(cond, msg) {
    if (!cond) { console.error('  [FAIL]', msg); fail++; }
    else { console.log('  [PASS]', msg); pass++; }
  }
  async function next() { $('#next-phase-btn').click(); await new Promise(r => setTimeout(r, 250)); }

  console.log('[1] Topbar');
  console.log('    Title:', $('#hw-title')?.textContent);
  assert($('#hw-title')?.textContent?.length > 1, 'title rendered');
  assert($$('#phase-list li').length === 9, '9 phase chips');

  console.log('[2] Walking through every phase without runtime errors');
  for (let i = 0; i < 8; i++) {
    await next();
    const realErrs = errors.filter(e => !e[1].includes('scrollTo'));
    if (realErrs.length) {
      console.error('  [FAIL] runtime error after phase ' + (i+2), realErrs[realErrs.length-1]);
      fail++;
      break;
    }
  }
  if (fail === 0) console.log('  [PASS] all 9 phases render without runtime error');

  console.log('[3] Final report renders');
  assert($('.report-card'), 'report card present');

  console.log('\n=========================================');
  console.log(`PASS ${pass}  FAIL ${fail}`);
  console.log('=========================================');
  process.exit(fail > 0 ? 1 : 0);
})().catch(e => { console.error('crash:', e.stack || e); process.exit(2); });
