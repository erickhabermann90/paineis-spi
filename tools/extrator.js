// Extrator do Power BI "Dashboard - Comercial" para os painéis dos RCs.
// Rodar no console da aba do relatório (javascript_tool). Limite ~45s por chamada:
// etapas longas rodam em segundo plano (__bg*) e são acompanhadas com chamadas de espera.
window.__dump=()=>[...document.querySelectorAll('visual-container')].map((v,i)=>({i,role:v.querySelector('[aria-roledescription]')?.getAttribute('aria-roledescription'),text:v.innerText.replace(/\s+/g,' ').trim().slice(0,200)}));
window.__rows=(i)=>{const v=[...document.querySelectorAll('visual-container')][i];return [...v.querySelectorAll('[role="row"]')].map(r=>[...r.querySelectorAll('[role="columnheader"],[role="gridcell"],[role="rowheader"]')].map(c=>c.innerText.replace(/\s+/g,' ').trim()))};
window.__go=async(p)=>{[...document.querySelectorAll('[role="tab"],[role="listitem"],.itemName')].find(e=>e.innerText.trim()===p)?.click();await new Promise(r=>setTimeout(r,8000));return __dump()};
window.__num=x=>Number(String(x||'').replace(/R\$\s*/,'').replace(/\./g,'').replace(',','.'))||0;
// Redefinir para o padrão (limpa filtros que ficam salvos entre sessões — já apareceram REDE e RAZÃO SOCIAL filtrados)
window.__reset=async()=>{[...document.querySelectorAll('button')].find(b=>/Redefinir para o padrão|Redefinir para padrão/i.test(b.getAttribute('aria-label')||b.innerText))?.click(); await new Promise(r=>setTimeout(r,2500)); const c=[...document.querySelectorAll('button')].find(b=>/^Redefinir$/i.test((b.innerText||'').trim())); c?.click(); await new Promise(r=>setTimeout(r,9000)); return !!c;};
// Segmentador de mês em lista suspensa (vi = índice do visual)
window.__mes=async(vi,m)=>{const v=[...document.querySelectorAll('visual-container')]; if(new RegExp(m,'i').test(v[vi].innerText)) return 'ja'; v[vi].querySelector('.slicer-dropdown-menu')?.click(); await new Promise(r=>setTimeout(r,2000)); const pop=document.querySelector('.slicer-dropdown-popup'); const n=pop&&[...pop.querySelectorAll('.slicerItemContainer')].find(e=>e.innerText.trim()===m); n?.click(); await new Promise(r=>setTimeout(r,5000)); document.body.click(); await new Promise(r=>setTimeout(r,800)); return !!n;};
// Rola uma tabela virtualizada coletando linhas (passo 200px, seguro). Chamar até done:true.
window.__scrape=async(vi,keyCols,store,ms=34000)=>{const v=[...document.querySelectorAll('visual-container')][vi]; const s=v.querySelector('.mid-viewport');
const grab=()=>{for(const r of __rows(vi)){ if(r[0]==='Selecionar Linha') store[keyCols.map(k=>r[k]).join('|')]=r; else if(r[1]==='Total') store.__tot=r;}};
grab(); const t0=Date.now();
while(Date.now()-t0<ms){ if(s.scrollTop+s.clientHeight>=s.scrollHeight-2){await new Promise(r=>setTimeout(r,1200)); grab(); if(s.scrollTop+s.clientHeight>=s.scrollHeight-2) return {done:true,n:Object.keys(store).length};} s.scrollTop+=200; s.dispatchEvent(new Event('scroll')); await new Promise(r=>setTimeout(r,550)); grab(); }
return {done:false,n:Object.keys(store).length};};
// Versão rápida (passo = 80% da altura). OK no Histórico e nas famílias; na lista de clientes da Curva ABC pulou linhas.
// Sempre conferir a soma com a linha Total; se faltar, voltar ao topo e completar com __scrape.
window.__scrapeF=async(vi,keyCols,store,ms=34000)=>{const v=[...document.querySelectorAll('visual-container')][vi]; const s=v.querySelector('.mid-viewport'); const step=Math.floor(s.clientHeight*0.8);
const grab=()=>{for(const r of __rows(vi)){ if(r[0]==='Selecionar Linha') store[keyCols.map(k=>r[k]).join('|')]=r; else if(r[1]==='Total') store.__tot=r;}};
grab(); const t0=Date.now();
while(Date.now()-t0<ms){ if(s.scrollTop+s.clientHeight>=s.scrollHeight-2){await new Promise(r=>setTimeout(r,1500)); grab(); if(s.scrollTop+s.clientHeight>=s.scrollHeight-2) return {done:true,n:Object.keys(store).length};} s.scrollTop+=step; s.dispatchEvent(new Event('scroll')); await new Promise(r=>setTimeout(r,500)); grab(); }
return {done:false,n:Object.keys(store).length};};
// Curva ABC: deixa marcados exatamente os itens `targets` no parâmetro de campo vi (1 = dimensões, 2 = medidas).
// Leva ~20–40s: rodar em segundo plano e esperar (ver SKILL).
window.__setSel=async(vi,targets)=>{const v=[...document.querySelectorAll('visual-container')][vi]; const sc=[...v.querySelectorAll('*')].find(e=>e.scrollHeight>e.clientHeight+5 && getComputedStyle(e).overflowY!='visible'); const log=[];
for(let pass=0;pass<2;pass++){ sc.scrollTop=0; sc.dispatchEvent(new Event('scroll')); await new Promise(r=>setTimeout(r,500)); const seen=new Set();
 for(let k=0;k<60;k++){ for(const e of [...v.querySelectorAll('.slicerItemContainer')]){ const t=e.title||e.innerText.trim(); if(seen.has(t)) continue; seen.add(t); const want=targets.includes(t), on=e.getAttribute('aria-checked')==='true'; if(want!==on){ e.dispatchEvent(new MouseEvent('click',{bubbles:true,ctrlKey:true})); log.push((want?'+':'-')+t); await new Promise(r=>setTimeout(r,2500)); } }
  if(sc.scrollTop+sc.clientHeight>=sc.scrollHeight-2) break; sc.scrollTop+=120; sc.dispatchEvent(new Event('scroll')); await new Promise(r=>setTimeout(r,300)); } }
return log;};
// Filtro MES/ANO da Curva ABC (painel Filtros): marca os meses pela caixa de pesquisa do cartão. meses = ['12/2025','01/2026',...]
window.__filtroMeses=async(meses)=>{
 if(![...document.querySelectorAll('button')].some(b=>b.getAttribute('aria-label')==='MES/ANO Expandir ou recolher o cartão de filtro')) [...document.querySelectorAll('button')].find(b=>b.getAttribute('aria-label')==='Mostrar/ocultar painel de filtros')?.click();
 await new Promise(r=>setTimeout(r,2500)); const b=[...document.querySelectorAll('button')].find(b=>b.getAttribute('aria-label')==='MES/ANO Expandir ou recolher o cartão de filtro'); if(b&&b.getAttribute('aria-expanded')!=='true'){ b.click(); await new Promise(r=>setTimeout(r,2500)); }
 const set=Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value').set; const inp=[...document.querySelectorAll('input')].find(i=>i.offsetParent && (i.getAttribute('aria-label')||i.placeholder)==='Pesquisar'); const ok=[];
 for(const m of meses){ inp.focus(); set.call(inp,m); inp.dispatchEvent(new Event('input',{bubbles:true})); inp.dispatchEvent(new KeyboardEvent('keyup',{bubbles:true,key:'0'})); await new Promise(r=>setTimeout(r,1500));
  const e=[...document.querySelectorAll('.slicerItemContainer')].find(e=>e.innerText.trim().startsWith(m)); if(e){ if(e.getAttribute('aria-checked')!=='true'){ e.click(); await new Promise(r=>setTimeout(r,1500)); } ok.push(m);} }
 return {ok:ok.length, resumo:[...document.querySelectorAll('*')].filter(x=>x.children.length===0 && /^é .*\/20/.test((x.innerText||'').trim())).map(x=>x.innerText.trim())[0]};};
// Itens 12 meses (Curva ABC: CÓD CLIENTE × PRODUTO × PESO, ordenado por PESO): roda em segundo plano até o PESO chegar a 0.
window.__itensBg=()=>{window.__st={}; window.__bg={done:false,n:0}; (async()=>{ const v=[...document.querySelectorAll('visual-container')][0]; const s=v.querySelector('.mid-viewport'); s.scrollTop=0; s.dispatchEvent(new Event('scroll')); await new Promise(r=>setTimeout(r,1500));
 const step=Math.floor(s.clientHeight*0.85); let zero=0;
 while(true){ let last=null; for(const r of __rows(0)){ if(r[0]==='Selecionar Linha'){ __st[r[1]+'|'+r[2]]=[r[1],r[2],r[3]]; last=r;} else if(r[1]==='Total') __st.__tot=r; }
  __bg.n=Object.keys(__st).length; if(last && last[3]==='0'){ if(++zero>=3) break; }
  if(s.scrollTop+s.clientHeight>=s.scrollHeight-2){ await new Promise(r=>setTimeout(r,2000)); if(s.scrollTop+s.clientHeight>=s.scrollHeight-2) break; }
  s.scrollTop+=step; s.dispatchEvent(new Event('scroll')); await new Promise(r=>setTimeout(r,500)); }
 __bg.done=true; })(); return 'iniciado';};
// REBATE: tabela larga; as colunas G3/STATUS só aparecem depois de clicar no botão oculto .scrollRight.
window.__rebate=async()=>{const v=[...document.querySelectorAll('visual-container')].find(x=>x.querySelector('[aria-colindex]')); const s=v.querySelector('.mid-viewport'); const rb={}, rh={};
 const grab=()=>{ v.querySelectorAll('[role="columnheader"][aria-colindex]').forEach(c=>rh[c.getAttribute('aria-colindex')]=c.innerText.replace(/\s+/g,' ').trim());
  v.querySelectorAll('[role="row"][aria-rowindex]').forEach(r=>{const ri=r.getAttribute('aria-rowindex'); r.querySelectorAll('[aria-colindex]').forEach(c=>{ if(c.getAttribute('role')==='columnheader') return; (rb[ri]=rb[ri]||{})[c.getAttribute('aria-colindex')]=c.innerText.replace(/\s+/g,' ').trim(); }); }); };
 for(const pass of [0,1]){ if(pass){ for(let k=0;k<10;k++){ v.querySelector('.scrollRight')?.click(); await new Promise(r=>setTimeout(r,400)); } await new Promise(r=>setTimeout(r,1000)); }
  s.scrollTop=0; s.dispatchEvent(new Event('scroll')); await new Promise(r=>setTimeout(r,1200)); grab();
  for(let k=0;k<6;k++){ s.scrollTop+=250; s.dispatchEvent(new Event('scroll')); await new Promise(r=>setTimeout(r,700)); grab(); } }
 const g=(o,a)=>a.map(i=>__num(o[i]));
 window.__reb=Object.values(rb).filter(o=>o['4']&&/ - /.test(o['4'])&&o['5']).map(o=>[o['4'].replace(/^\*/,''),o['5'],g(o,[6,7,9,10]),g(o,[11,12,14,15]),g(o,[16,17,19,20]),g(o,[21,22,24,25]),o['27']]);
 return {cols:Object.keys(rh).length, completo:Object.values(rb).every(o=>Object.keys(o).length>=27), n:__reb.length};};
