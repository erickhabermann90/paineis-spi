// Extrator do Power BI "Dashboard - Comercial" para os painéis dos RCs.
// Rodar no console da aba do relatório (javascript_tool), uma etapa por chamada.
// Ver passo a passo no comando /atualizar-paineis.
window.__dump=()=>[...document.querySelectorAll('visual-container')].map((v,i)=>({i,role:v.querySelector('[aria-roledescription]')?.getAttribute('aria-roledescription'),text:v.innerText.replace(/\s+/g,' ').trim().slice(0,200)}));
window.__rows=(i)=>{const v=[...document.querySelectorAll('visual-container')][i];return [...v.querySelectorAll('[role="row"]')].map(r=>[...r.querySelectorAll('[role="columnheader"],[role="gridcell"],[role="rowheader"]')].map(c=>c.innerText.replace(/\s+/g,' ').trim()))};
window.__go=async(p)=>{[...document.querySelectorAll('[role="tab"],[role="listitem"],.itemName')].find(e=>e.innerText.trim()===p)?.click();await new Promise(r=>setTimeout(r,8000));return __dump()};
window.__num=x=>Number(String(x||'').replace(/R\$\s*/,'').replace(/\./g,'').replace(',','.'))||0;
// Rola uma tabela virtualizada coletando linhas. Chamar de novo até done:true (limite ~40s por chamada).
window.__scrape=async(vi,keyCols,store,ms=40000)=>{const v=[...document.querySelectorAll('visual-container')][vi]; const s=v.querySelector('.mid-viewport');
const grab=()=>{for(const r of __rows(vi)){ if(r[0]==='Selecionar Linha') store[keyCols.map(k=>r[k]).join('|')]=r; else if(r[1]==='Total') store.__tot=r;}};
grab(); const t0=Date.now();
while(Date.now()-t0<ms){ if(s.scrollTop+s.clientHeight>=s.scrollHeight-2){await new Promise(r=>setTimeout(r,1200)); grab(); if(s.scrollTop+s.clientHeight>=s.scrollHeight-2) return {done:true,n:Object.keys(store).length};} s.scrollTop+=200; s.dispatchEvent(new Event('scroll')); await new Promise(r=>setTimeout(r,550)); grab(); }
return {done:false,n:Object.keys(store).length};};
// Clica num item de segmentação (dimensão/medida) da Curva ABC. ctrl=true adiciona à seleção.
window.__pick=async(vi,txt,ctrl)=>{const el=[...[...document.querySelectorAll('visual-container')][vi].querySelectorAll('.slicerItemContainer,[role="option"],[role="checkbox"]')].find(e=>(e.getAttribute('aria-label')||e.innerText).trim()===txt); if(!el) return 'nf:'+txt; el.dispatchEvent(new MouseEvent('click',{bubbles:true,ctrlKey:!!ctrl})); await new Promise(r=>setTimeout(r,3500)); return 'ok';};
