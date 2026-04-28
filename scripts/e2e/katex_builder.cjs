// Verify KaTeX behavior on builder.html:
//  (1) Display areas (non-editable) render $...$ as math.
//  (2) contenteditable=true fields KEEP raw $...$ (so authors can edit).
const puppeteer = require('puppeteer');
const URL = 'http://127.0.0.1:8000/builder.html?id=HW-20260427-008';

(async () => {
  const browser = await puppeteer.launch({
    headless: 'new',
    args: ['--no-sandbox', '--disable-setuid-sandbox'],
  });
  const page = await browser.newPage();
  page.setDefaultTimeout(20000);

  console.log('Load', URL);
  await page.goto(URL, { waitUntil: 'networkidle0' });
  await new Promise(r => setTimeout(r, 800));

  const result = await page.evaluate(async () => {
    const ready = typeof window.renderMathInElement === 'function';
    if (!ready) return { ready: false };

    // === A) Display node — should render ===
    const display = document.createElement('div');
    display.id = '__probe_display__';
    display.style.cssText = 'position:fixed;left:-9999px;';
    display.innerHTML = "Test display: $P$ and $\\angle ABC = 90^\\circ$";
    document.body.appendChild(display);

    // === B) Editable node — should NOT render ===
    const edit = document.createElement('div');
    edit.id = '__probe_edit__';
    edit.style.cssText = 'position:fixed;left:-9999px;';
    edit.setAttribute('contenteditable', 'true');
    edit.innerHTML = "Editable: $P$ and $\\angle ABC$";
    document.body.appendChild(edit);

    // === C) Editable node with display child — display child should not render
    //         either, because parent is contenteditable ===
    const editParent = document.createElement('div');
    editParent.setAttribute('contenteditable', 'true');
    editParent.style.cssText = 'position:fixed;left:-9999px;';
    const inner = document.createElement('span');
    inner.textContent = "Inside CE: $X$";
    editParent.appendChild(inner);
    document.body.appendChild(editParent);

    // Allow MutationObserver + rAF + auto-render
    await new Promise(r => setTimeout(r, 700));

    // If display didn't render via the observer, try one direct call to confirm KaTeX itself works.
    const directWorks = (() => {
      const t = document.createElement('div');
      t.innerHTML = "$P$";
      try { window.renderMathInElement(t, { delimiters: [{left:'$',right:'$',display:false}], throwOnError: false }); }
      catch (e) { return { ok: false, err: String(e) }; }
      return { ok: t.querySelectorAll('.katex').length > 0 };
    })();

    return {
      ready: true,
      directWorks,
      display: {
        katex: display.querySelectorAll('.katex').length,
        rawDollars: (display.innerText.match(/\$[^$]{1,30}\$/g) || []),
      },
      edit: {
        katex: edit.querySelectorAll('.katex').length,
        rawDollars: (edit.innerText.match(/\$[^$]{1,30}\$/g) || []),
        text: edit.innerText.slice(0, 80),
      },
      editParent: {
        katex: editParent.querySelectorAll('.katex').length,
        rawDollars: (editParent.innerText.match(/\$[^$]{1,30}\$/g) || []),
      },
    };
  });

  console.log(JSON.stringify(result, null, 2));

  const pass =
    result.ready &&
    result.display.katex >= 2 && result.display.rawDollars.length === 0 &&
    result.edit.katex === 0 && result.edit.rawDollars.length >= 2 &&
    result.editParent.katex === 0 && result.editParent.rawDollars.length >= 1;

  console.log('\n=== VERDICT: builder math behavior ' + (pass ? 'CORRECT ✓' : 'WRONG ✗') + ' ===');
  console.log('  display renders math :', result.display && result.display.katex >= 2);
  console.log('  editor keeps raw $$  :', result.edit && result.edit.rawDollars.length >= 2);
  console.log('  CE-parent stays raw  :', result.editParent && result.editParent.rawDollars.length >= 1);

  await browser.close();
  process.exit(pass ? 0 : 1);
})().catch(e => { console.error('Test crashed:', e); process.exit(2); });
