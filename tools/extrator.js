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
// ATENÇÃO: a ordem das colunas de medida muda entre sessões (em 10/11 veio KG 26 antes de KG 25): ler sempre pelo nome no cabeçalho (__rows(0)[0].indexOf("KG 25")).
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
// Filtro MES/ANO sem usar a caixa de pesquisa (que às vezes não filtra): limpa o cartão e marca os meses rolando a lista.
// Depois de mudar o filtro, a tabela pode mostrar o total antigo até alguma medida mudar: conferir a linha Total.
window.__filtroLista=async(meses)=>{
 const b=[...document.querySelectorAll('button')].find(b=>b.getAttribute('aria-label')==='MES/ANO Expandir ou recolher o cartão de filtro');
 const card=b?.closest('filter-visual-card, [class*="filterCard"], .filter-card')||b?.parentElement?.parentElement; const l=card&&[...card.querySelectorAll('button')].find(x=>/Limpar filtro/i.test(x.getAttribute('aria-label')||x.title||'')); l?.click(); await new Promise(r=>setTimeout(r,3000));
 if(b?.getAttribute('aria-expanded')!=='true'){ b?.click(); await new Promise(r=>setTimeout(r,2500)); }
 const it0=[...document.querySelectorAll('.slicerItemContainer')].find(e=>/^\d\d\/20\d\d/.test(e.innerText.trim())); let sc=it0; while(sc && !(sc.scrollHeight>sc.clientHeight+5)) sc=sc.parentElement;
 const done=new Set(); for(let k=0;k<60 && done.size<meses.length;k++){ for(const e of [...document.querySelectorAll('.slicerItemContainer')]){ const t=e.innerText.trim().split(/\s/)[0]; if(meses.includes(t)&&!done.has(t)){ if(e.getAttribute('aria-checked')!=='true'){ e.click(); await new Promise(r=>setTimeout(r,900)); } done.add(t);} }
  sc.dispatchEvent(new WheelEvent('wheel',{deltaY:120,bubbles:true,cancelable:true})); sc.scrollTop+=60; sc.dispatchEvent(new Event('scroll')); await new Promise(r=>setTimeout(r,500)); }
 return {n:done.size, resumo:[...document.querySelectorAll('*')].filter(x=>x.children.length===0 && /^é .*\/20/.test((x.innerText||'').trim())).map(x=>x.innerText.trim())[0]};};
// Campanha Bike/Dispenser/Baldes (diário): filtro out–dez/2026 (__filtroLista(['10/2026','11/2026','12/2026']))
//  a) dims [CÓD CLIENTE], medidas [KG 26, KG FN 26, KG ORIGENS 26] → q4 = [[cli, kg26, fn, origens]] (ler colunas pelo nome)
//  b) dims [CÓD CLIENTE, PRODUTO], medida [PESO] ordenado desc → __itensBg() → q4_itens = [[cli, produto, kg]]
//  gravar extrato/campanha.json = {q4, q4_itens}. A base fixa (jan–set/2026 e itens jan/2025–set/2026) está em tools/campanha_base.json.
// ===================== ROTINA ENXUTA (desde 17/11) =====================
// Clientes: KG 25 e KG 26 saem do HISTÓRICO (MÉD KG 25 × 12 e MÉD KG 26 × nº do mês; erro ≤ 6 kg) — não precisa mais da extração de clientes na Curva ABC.
// Famílias + carteira por linha numa única tabela: dims [CÓD RC - REPRESENTANTE, FAMÍLIA GERAL, FAMÍLIA SISTEMA],
//   medidas [KG 26, KG 25, POSITIVACAO 26, PESO NÃO FATURADO, R$ NÃO FATURADO] → __famOut (lê colunas pelo nome).
window.__famLe=()=>{const h=__rows(0)[0], ix=(n)=>h.indexOf(n); const rows=Object.entries(__fam).filter(([k])=>k!=='__tot').map(([,v])=>v);
 window.__famOut=rows.map(r=>[r[ix('CÓD RC - REPRESENTANTE')].split(' - ')[0], r[ix('FAMÍLIA SISTEMA')], __num(r[ix('KG 26')]), __num(r[ix('KG 25')]), __num(r[ix('POSITIVACAO 26')]), r[ix('FAMÍLIA GERAL')], __num(r[ix('PESO NÃO FATURADO')])]);
 const t=__fam.__tot||[]; window.__rsCart=__num(t[ix('R$ NÃO FATURADO')]);
 return {n:__famOut.length, kg26:__famOut.reduce((a,x)=>a+x[2],0), cart:__famOut.reduce((a,x)=>a+x[6],0), rsCart:__rsCart, tot:t};};
// KPI da Regional (página KPI): mês no segmentador 0, tabela no visual 1 (17 colunas, revela com .scrollRight).
window.__kpi=async(mesNome)=>{await __mes(0,mesNome); const v=[...document.querySelectorAll('visual-container')][1]; const c={};
 const grab=()=>v.querySelectorAll('[role="row"][aria-rowindex="2"] [aria-colindex]').forEach(e=>c[e.getAttribute('aria-colindex')]=e.innerText.replace(/\s+/g,' ').trim());
 for(let k=0;k<12;k++){ v.querySelector('.scrollLeft')?.click(); await new Promise(r=>setTimeout(r,150)); } grab();
 for(let k=0;k<12;k++){ v.querySelector('.scrollRight')?.click(); await new Promise(r=>setTimeout(r,400)); grab(); }
 const n=(i)=>__num(c[i]); window.__kpiMes={vol:[n(3),n(4)], rs:[n(6),n(7)], fn:[n(9),n(10)], orig:[n(12),n(13)], pet:[n(15),n(16)]}; return {cols:Object.keys(c).length, kpi:__kpiMes};};
// Exportação em partes: __exportar(mesNum, 'MM') e depois __parte(0), __parte(1)… (partes de até 180 mil caracteres, iguais entre si,
// para cada retorno ir para um arquivo tool-results; o arquivo trunca acima de ~260 mil caracteres em base64).
window.__exportar=(mesNum,mesStr,extra={})=>{const miss=[]; const clients=Object.entries(__all).filter(([k])=>k!=='__tot').map(([,r])=>{ const m25=__num(r[5]), m26=__num(r[6]), m=__num(r[7]); const k25=m25*12, k26=m26*mesNum;
  return [r[1].split(' - ')[0], r[3], r[4], r[2], k25, k26, m, __num(r[8]), __num(r[9]), __num(r[10]), m25, Math.round((k26-m)/(mesNum-1)), m25];});
 const flash=__flash.slice(1).filter(r=>r[0]!=='Total').map(r=>[r[0].replace(/^\*/,''),__num(r[1]),__num(r[2]),__num(r[6])]);
 const plano=(window.__plano||[]).slice(1).filter(r=>r[0]==='Selecionar Linha').map(r=>[r[3],__num(r[4]),__num(r[5]),__num(r[6])]);
 window.__EXP=JSON.stringify(Object.assign({mes_num:mesNum, miss, clients, out:{flash,plano,fam:__famOut,reb:__reb}, kpi_mes:{mes:mesStr, vals:__kpiMes, rs_carteira:__rsCart}}, extra));
 return {len:__EXP.length, partes:__np()};};
window.__np=()=>Math.max(1,Math.ceil(__EXP.length/180000));
window.__parte=(i)=>{const n=__np(), sz=Math.ceil(__EXP.length/n); return btoa(unescape(encodeURIComponent(__EXP.slice(i*sz,(i+1)*sz))));};

// ===== KPIs do mês por RC (link de teste BI 2027) =====
// Curva ABC: __filtroLista(['MM/AAAA']) só do mês; dims [CÓD RC - REPRESENTANTE, FAMÍLIA GERAL]; medidas [KG 26, R$ FAT 26];
// __krc={}; __scrapeF(0,[1,2],__krc) até done; __kpiRCLe() → window.__kpiRC = {rc: {fat: {família geral: kg}, rs: R$}}; exportar com {kpi_rc: __kpiRC}
window.__kpiRCLe=()=>{const h=__rows(0)[0], ix=(n)=>h.indexOf(n), o={};
 Object.entries(__krc).filter(([k])=>k!=='__tot').forEach(([,r])=>{const rc=r[ix('CÓD RC - REPRESENTANTE')].split(' - ')[0].replace(/^\*/,''), fam=r[ix('FAMÍLIA GERAL')];
  const x=o[rc]=o[rc]||{fat:{},rs:0}; x.fat[fam]=(x.fat[fam]||0)+__num(r[ix('KG 26')]); x.rs+=__num(r[ix('R$ FAT 26')]);});
 window.__kpiRC=o; const t=__krc.__tot||[]; return {rcs:Object.keys(o).length, kg:Object.values(o).reduce((a,x)=>a+Object.values(x.fat).reduce((b,v)=>b+v,0),0), rs:Object.values(o).reduce((a,x)=>a+x.rs,0), tot_kg:t[ix('KG 26')], tot_rs:t[ix('R$ FAT 26')]};};
