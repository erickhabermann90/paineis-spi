"""Gera o link de teste no modelo BI 2027 (várias páginas) para o RC de tools/teste.json.
Uso: python3 tools/bi2027/gerar_teste.py <pasta_extrato>   (chamado pelo build.py quando teste.json tem "modelo": "bi2027")
Lê o painel oficial já gerado (site/<slug oficial>/index.html), o extrato do dia e os arquivos de tools/.
Páginas: index (início), mes, performance, campanhas, prime, clientes (busca + ficha). Roteiro fora do menu (25/11).
"""
import json, os, re, sys, math, datetime, collections

B = os.path.dirname(os.path.abspath(__file__)); T = os.path.dirname(B); SITE = os.path.join(os.path.dirname(T), 'site')
ext = sys.argv[1]
TE = json.load(open(os.path.join(T, 'teste.json'))); COD = str(TE['cod'])
RCS = json.load(open(os.path.join(T, 'rcs.json'))); OFF = RCS[COD]['slug']
d = json.loads(re.search(r'window.__DATA = (.*?);</script>', open(os.path.join(SITE, OFF, 'index.html')).read()).group(1))
one = lambda k: (d.get(k) or [None])[0]
P = one('plano'); data = P['atualizado_em']; dt = datetime.date.fromisoformat(data); mm = data[5:7]
ano1 = dt.year; ano0 = ano1 - 1
data_txt = data[8:10] + '/' + data[5:7]
nome = RCS[COD]['nome'].split()[0].title()
mes_nome = P['mes'].split()[0]
CL = d['clientes']; IT = one('itens') or {}
OUT = json.load(open(os.path.join(ext, 'out.json')))
CLIENTS = json.load(open(os.path.join(ext, 'clients.json')))
INAT = set(json.load(open(os.path.join(T, 'inativos.json')))['clientes'])
ITJ = json.load(open(os.path.join(T, 'itens.json'))); IP = ITJ['produtos']
KPI = json.load(open(os.path.join(T, 'kpi_regional.json'))) if os.path.exists(os.path.join(T, 'kpi_regional.json')) else None
LOGO = {k: 'data:image/webp;base64,' + open(os.path.join(B, 'logos', f + '.b64')).read().strip() for k, f in (('fn', 'fn'), ('or', 'origens'))}

def page(tpl, data, nome_arq, extra=None):
    s = open(os.path.join(B, 'teste', tpl) if os.path.exists(os.path.join(B, 'teste', tpl)) else os.path.join(B, 'fontes', tpl)).read()
    s = s.replace('/*DATA*/', json.dumps(data, ensure_ascii=False, separators=(',', ':')))
    for a, b in (extra or {}).items(): s = s.replace(a, b)
    nav = '''<script>(()=>{const M={'Mês atual':'mes.html','Performance':'performance.html','Campanhas':'campanhas.html','Prime':'prime.html','Clientes':'clientes.html'};
const st=document.createElement('style');st.textContent='.nav button.mid span{width:48px;height:40px;font-size:21px;background:#ffc000!important;box-shadow:0 6px 14px -6px rgba(201,138,0,.8);margin-top:-12px}.nav button.mid{color:#16181d;font-weight:800}.nav button.mid.on span{background:#16181d!important}';document.head.appendChild(st);
document.querySelectorAll('.nav button').forEach(b=>{const k=[...b.childNodes].pop().textContent.trim(); if(M[k]){b.onclick=()=>location.href=M[k]; if(location.pathname.endsWith('/'+M[k])) b.classList.add('on');}});
document.querySelectorAll('.bk > span:first-child, .bk > button:first-child').forEach(e=>{if(!e.onclick){e.style.cursor='pointer'; e.onclick=()=>location.href='index.html';}});})();</script>'''
    s = s.replace('/*NAV*/', nav) if '/*NAV*/' in s else s.replace('</body>', nav + '\n</body>')
    s = re.sub(r'<div class="nav"([^>]*)>(?:<button[^>]*>.*?</button>)+</div>', lambda m: '<div class="nav"' + m.group(1) + '>' + NAVB + '</div>', s, flags=re.S)
    s = s.replace('<head>', '<head><meta name="robots" content="noindex, nofollow">', 1)
    open(os.path.join(OUTD, nome_arq), 'w').write(s)

NAVB = ''.join(f'<button{" class=\"mid\"" if t == "Clientes" else ""}><span>{i}</span>{t}</button>' for i, t in (('🛒', 'Mês atual'), ('📈', 'Performance'), ('🔎', 'Clientes'), ('🎯', 'Campanhas'), ('⭐', 'Prime')))
OUTD = os.path.join(SITE, TE['slug']); os.makedirs(OUTD, exist_ok=True)

# ---------- dias úteis restantes ----------
fim = (dt.replace(day=28) + datetime.timedelta(days=4)); fim = fim - datetime.timedelta(days=fim.day)
du = sum(1 for i in range(1, (fim - dt).days + 1) if (dt + datetime.timedelta(days=i)).weekday() < 5)
du_txt = 'último dia útil' if du == 0 else ('falta 1 dia útil' if du == 1 else f'faltam {du} dias úteis')

# ---------- itens 12 meses (regional) ----------
ativos_reg = {str(x[1]) for x in CLIENTS if str(x[1]) not in INAT}
m12 = collections.defaultdict(dict)
for c, pi, kg in ITJ['linhas']:
    if kg > 0: m12[str(c)][IP[pi]] = m12[str(c)].get(IP[pi], 0) + kg
rank = collections.Counter(p for c in ativos_reg for p in m12.get(c, {}))
mix_reg = round(sum(len(m12[c]) for c in ativos_reg if c in m12) / max(sum(1 for c in ativos_reg if c in m12), 1), 1)
ids = [str(c['cod']) for c in CL]
mix_rc = round(sum(len(m12[c]) for c in ids if c in m12) / max(sum(1 for c in ids if c in m12), 1), 1)

# ---------- Linhas do RC: objetivo = rateio do KPI da Regional pelo plano do RC × 1,05; realizado do mês (kpi_rc.json) + carteira ----------
kpis = {}
krc = os.path.join(ext, 'kpi_rc.json')
if KPI and mm in KPI['meses'] and os.path.exists(krc):
    K = json.load(open(krc)).get(COD, {})
    M = KPI['meses'][mm]; share = P['objetivo'] / M['vol'][0] * 1.05
    cart = collections.Counter()
    for x in OUT['fam']:
        if str(x[0]) == COD and len(x) >= 7: cart[x[5]] += x[6]
    tot_cart = KPI['carteira'].get('vol') or 1
    for k, fam in (('fn', 'FÓRMULA NATURAL'), ('orig', 'ORIGENS'), ('pet', 'PET CARE')):
        kpis[k] = [round(M[k][0] * share), round(K.get('fat', {}).get(fam, 0)), round(cart.get(fam, 0))]
    kpis['rs'] = [round(M['rs'][0] * share), round(K.get('rs', 0)), round(KPI['carteira'].get('rs', 0) * (P['carteira'] / tot_cart))]
M4 = one('meta4t'); FAMS = d.get('familias') or []
pouso = None
if M4:
    real4 = M4['out'] + M4['nov'] + M4['dez']; k26t = sum(f['kg_2026'] for f in FAMS); k25t = sum(f['kg_2025'] for f in FAMS)
    pouso = {'obj': M4['objetivo'], 'real': real4, 'proj': (k26t - real4 + max(M4['objetivo'], real4)) / k25t - 1 if k25t else 0}
pos_fat = sum(1 for c in CL if c['kg_mes'] > 0); pos_cart = sum(1 for c in CL if c['kg_mes'] <= 0 and c['kg_carteira'] > 0)
nota = 'Painel de acompanhamento. A apuração oficial segue o regulamento do Plano Performance.'
page('inicio.tpl.html', {'nome': nome, 'mes': mes_nome, 'data': data_txt, 'dias_uteis': du_txt, 'plano': P, 'kpis': kpis, 'kpis_est': False, 'pouso': pouso,
     'base': {'n': len(CL), 'fat': pos_fat, 'cart': pos_cart, 'obj': .7, 'mix': mix_rc, 'mix_reg': mix_reg, 'mix_txt': '12 meses'}, 'nota': nota},
     'index.html', {'@@FN@@': LOGO['fn'], '@@OR@@': LOGO['or']})

PRIME = {str(r['cod']): {'obj': round(r['objetivo'] * 1.05), 'real': round(r['realizado'])} for r in (d.get('rebate') or []) if r['grupo'] == 'Total'}
# ---------- Mês atual: objetivo por cliente = plano + 10%, curva 5% (maior) a 40% (menor), novo = 150 kg ----------
alvo = P['objetivo'] * 1.10; base = [c for c in CL if c['med_kg_26'] > 0]; novos = [c for c in CL if c['med_kg_26'] <= 0]
rows = []
if base:
    lo = math.log(min(c['med_kg_26'] for c in base)); hi = math.log(max(c['med_kg_26'] for c in base))
    raw = {c['cod']: c['med_kg_26'] * (1 + .40 - .35 * ((math.log(c['med_kg_26']) - lo) / ((hi - lo) or 1))) for c in base}
    k = (alvo - 150 * len(novos)) / sum(raw.values())
for c in CL:
    o = round(raw[c['cod']] * k) if c['cod'] in (raw if base else {}) else 150
    pr = PRIME.get(str(c['cod']))
    rows.append({'cod': c['cod'], 'nome': c['razao_social'], 'fat': round(c['kg_mes']), 'cart': round(c['kg_carteira']), 'dias': c['dias_ult_compra'], 'freq': c['freq_media_dias'], 'base': round(c['med_kg_26']), 'prime': pr})
page('mes_atual.tpl.html', {'plano': P['objetivo'], 'alvo': round(alvo), 'rows': rows}, 'mes.html',
     {'Novembro · clientes ativos · dados de 19/11': f'{mes_nome} · clientes ativos · dados de {data_txt}'})

# ---------- Performance ----------
H = json.load(open(os.path.join(T, 'campanha_base.json')))['hist']; HP = H['produtos']
DESC = set(json.load(open(os.path.join(B, 'dados', 'descontinuados.json')))['itens'])
vendidos = {p for c in m12 for p in m12[c]}
fora = DESC | {p for p in HP if p not in vendidos}
def base_nome(p):
    p = re.sub(r'\b\d+X\s*\(?\d+X\d+G\)?|\b\d+X\(\d+X\d+G\)|\b\d+X\d+G\b|\b\d+(,\d+)?\s*KG\b|\b2X\b', '', p)
    return re.sub(r'\s+', ' ', p).strip()
pc, abr = [], collections.Counter()
nreg = collections.Counter(p for c in m12 for p in m12[c])  # clientes da Regional que compram o item (12 meses)
for c in CL:
    cod = str(c['cod']); hist = {HP[i] for i in H['cli'].get(cod, [])}; atuais = set(m12.get(cod, {}))
    atb = {base_nome(p) for p in atuais}
    ab = sorted(p for p in hist - atuais if p not in fora and base_nome(p) not in atb)
    abr.update(ab)
    pc.append({'cod': cod, 'nome': c['razao_social'], 'm25': c['med_kg_25'], 'm26': c['med_kg_26'], 'mes': c['kg_mes'], 'cart': c['kg_carteira'], 'dias': c['dias_ult_compra'], 'freq': c['freq_media_dias'], 'mix': len(atuais), 'ab': len(ab), 'abl': [[p, nreg[p]] for p in sorted(ab, key=lambda p: (-nreg[p], p))]})
perf = {'fam': d['familias'], 'tot': one('perf_total'), 'plano': P, 'cl': pc, 'ab_top': abr.most_common(8), 'mix_reg': mix_reg, 'n': len(CL)}
page('performance.tpl.html', perf, 'performance.html',
     {'Gabriel · ${A0} × ${A1} · dados de 19/11': nome + ' · ${A0} × ${A1} · dados de ' + data_txt, "A0='2025', A1='2026'": f"A0='{ano0}', A1='{ano1}'",
      'Novembro × novembro': mes_nome + ' × ' + mes_nome.lower(), 'nov/${A0.slice(2)} a incluir': mes_nome[:3].lower() + '/${A0.slice(2)} a incluir'})

# ---------- Campanhas ----------
C = json.load(open(os.path.join(T, 'campanhas', 'campanhas.json')))
need = {'camp_bike_px.webp', 'camp_baldes_px.webp'}
for c in C: need.update(c['packshots']); need.update([c['arte']] if isinstance(c['arte'], str) else c['arte'])
img = {n: '../assets/campanhas/' + n for n in need}
camp = one('campanha') or {}; nm = {str(c['cod']): c['razao_social'] for c in CL}
bb = {'R': one('campanha_regras') or {}, 'cl': [{'cod': k, 'nome': nm.get(k, k), 'real': x['real_vol'], 'obj': x['obj_vol'], 'novos': len(x['novos']), 'ob': x['obj_balde'],
      'bm': max([m[1] for m in x['balde_mes']] or [0])} for k, x in camp.items()]}
page('campanhas.tpl.html', {}, 'campanhas.html', {'/*CAMP*/': json.dumps(C, ensure_ascii=False), '/*IMG*/': json.dumps(img), '/*BB*/': json.dumps(bb, ensure_ascii=False),
     '/*HOJE*/': data, '/*DATA_TXT*/': data_txt, '· Gabriel ·': '· ' + nome + ' ·', 'garantido em novembro': 'garantido em ' + mes_nome.lower()})

# ---------- Prime (rebate negociado com o cliente; objetivo do BI + 5%) — substitui o Roteiro no menu ----------
_reb = collections.OrderedDict()
for r in (d.get('rebate') or []):
    x = _reb.setdefault(str(r['cod']), {'cod': str(r['cod']), 'rede': r['rede'], 'obj': 0, 'real': 0, 'g': []})
    if r['grupo'] == 'Total': x['obj'] = round(r['objetivo'] * 1.05); x['real'] = round(r['realizado'])
    else: x['g'].append({'k': r['grupo'], 'obj': round(r['objetivo'] * 1.05), 'real': round(r['realizado'])})
page('prime.tpl.html', {'data': data_txt, 'redes': [x for x in _reb.values() if x['obj']]}, 'prime.html')
_rot = os.path.join(OUTD, 'roteiro.html')
if os.path.exists(_rot): os.remove(_rot)

# ---------- Clientes (busca + ficha) ----------
reb = collections.defaultdict(list)
for r in d.get('rebate', []): reb[str(r['cod'])].append(r)
prods = sorted({p for c in ids for p in m12.get(c, {})} | {p for p, _ in rank.most_common(400)}); pix = {p: i for i, p in enumerate(prods)}
topreg = [p for p, _ in rank.most_common(400)]
fc = []
for c in CL:
    cod = str(c['cod']); mine = m12.get(cod, {})
    fc.append({'cod': cod, 'nome': c['razao_social'], 'rede': c.get('rede'), 'med26': c['med_kg_26'], 'med27': None, 'mes': c['kg_mes'], 'cart': c['kg_carteira'],
               'dias': c['dias_ult_compra'], 'freq': c['freq_media_dias'], 'reb': reb.get(cod, []),
               'itens': sorted([[pix[p], round(k / 12)] for p, k in mine.items()], key=lambda t: -t[1]),
               'posit': [pix[p] for p in topreg if p not in mine][:30]})
page('clientes.tpl.html', {'produtos': prods, 'rank': [rank.get(p, 0) for p in prods], 'clientes': fc, 'data': data_txt, 'ano0': ano1, 'ano1': ano1 + 1,
     'itens_txt': 'média/mês · últimos 12 meses', 'posit_txt': 'sem compra em 12 meses'}, 'clientes.html')
print('teste BI 2027:', '/' + TE['slug'] + '/', '| páginas:', sorted(os.listdir(OUTD)), '| KPIs por linha:', 'sim' if kpis else 'aguardando kpi_rc.json')
