const { chromium } = require('playwright');
(async () => { const b = await chromium.launch(); const out = {};
  const rcs = require('fs').readdirSync(require('path').resolve(__dirname, '..', 'site')).filter(d => /-/.test(d));
  // node tools/auditoria.js --rapido → só 390px (dia a dia); sem argumento → todas as larguras (quando o layout mudar)
  const LARG = process.argv.includes('--rapido') ? [390] : [360, 390, 430, 768, 1280];
  for (const W of LARG) for (const rc of rcs) {
    const p = await b.newPage({ viewport: { width: W, height: 800 } });
    await p.route('**/fonts.g*/**', r => r.abort());
    await p.goto('file://' + require('path').resolve(__dirname, '..', 'site') + '/' + rc + '/index.html'); await p.waitForTimeout(900);
    for (const g of ['home','mes','prime','ano','q4','pos','prop']) {
      if (g !== 'home') { await p.evaluate((g) => document.querySelector('.px-card[data-go="' + g + '"]')?.click(), g); await p.waitForTimeout(250); }
      if (g === 'pos' || g === 'prop') { await p.evaluate(() => { if (!window.pxCli) return; const pr = pxOne('proposta') || {}; const c = Object.keys(pr).sort((a, b) => pr[b].itens.length - pr[a].itens.length)[0]; pxCli.cod = c || null; pxRedrawCli(); }); await p.waitForTimeout(200); }
      const r = await p.evaluate(() => {
        const bad = []; const sec = document.querySelector('section:not([hidden])');
        const boxes = sec.querySelectorAll('.px-card, .px-mini, .px-panel, .px-hero, .px-g, .px-rank-row, .px-kpi, .px-rec, .px-rede-status, .px-tw');
        boxes.forEach(bx => { const br = bx.getBoundingClientRect();
          bx.querySelectorAll('*').forEach(e => { if (bx.className !== 'px-tw' && e.closest('.px-tw')) return; const er = e.getBoundingClientRect(); if (!er.width || !er.height) return;
            if (er.right > br.right + 1 || er.left < br.left - 1 || er.bottom > br.bottom + 1) bad.push('fora: ' + (bx.className.split(' ')[0]) + ' > "' + (e.textContent || e.className).trim().slice(0, 30) + '"'); }); });
        // textos sobrepostos
        const leaves = [...sec.querySelectorAll('*')].filter(e => e.childElementCount === 0 && (e.textContent || '').trim() && e.getBoundingClientRect().width);
        const rects = leaves.map(e => [e, e.getBoundingClientRect()]);
        for (let i = 0; i < rects.length; i++) for (let j = i + 1; j < rects.length; j++) { const [a, ra] = rects[i], [c, rc] = rects[j];
          if (a.contains(c) || c.contains(a)) continue;
          const ox = Math.min(ra.right, rc.right) - Math.max(ra.left, rc.left), oy = Math.min(ra.bottom, rc.bottom) - Math.max(ra.top, rc.top);
          if (ox > 2 && oy > 3) bad.push('sobrepõe: "' + a.textContent.trim().slice(0, 20) + '" x "' + c.textContent.trim().slice(0, 20) + '"'); }
        // texto cortado
        sec.querySelectorAll('*').forEach(e => { const cs = getComputedStyle(e); if ((cs.overflow === 'hidden' || cs.textOverflow === 'ellipsis') && e.scrollWidth > e.clientWidth + 1 && e.childElementCount === 0) bad.push('cortado: "' + e.textContent.trim().slice(0, 30) + '"'); });
        sec.querySelectorAll('.px-tw').forEach(t => { if (t.scrollWidth > t.clientWidth + 1) bad.push('tabela rola ' + (t.scrollWidth - t.clientWidth) + 'px'); });
        if (document.documentElement.scrollWidth > innerWidth) bad.push('página rola na horizontal');
        return [...new Set(bad)].slice(0, 8); });
      if (r.length) out[`${W} ${rc.split('-')[0]} ${g}`] = r;
      if (g !== 'home') { await p.evaluate(() => document.querySelector('section:not([hidden]) .px-back')?.click()); await p.waitForTimeout(150); }
    } await p.close(); }
  console.log(JSON.stringify(out, null, 1)); await b.close(); })();
