"""Gera os painéis dos RCs a partir de um extrato do Power BI.

Uso: python3 tools/build.py <extrato_dir> <AAAA-MM-DD atualização> "<Mês AAAA>"
O extrato_dir precisa ter clients.json e out.json (formato do extrator).
Os endereços (slugs) de cada RC ficam fixos em tools/rcs.json.
"""
import json, os, secrets, sys, re
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
T = os.path.join(ROOT, 'tools')
SITE = os.path.join(ROOT, 'site')
ext, atualizado, mes = sys.argv[1], sys.argv[2], sys.argv[3]
clients = json.load(open(os.path.join(ext, 'clients.json')))
out = json.load(open(os.path.join(ext, 'out.json')))
rcs = json.load(open(os.path.join(T, 'rcs.json')))

# Meta 4º tri (reunião): metas fixas por RC/cliente + histórico mensal out/nov/dez gravado a cada rodada
import datetime
metas4t = json.load(open(os.path.join(T, 'metas4t.json')))
hist_path = os.path.join(T, 'q4_mensal.json')
q4hist = json.load(open(hist_path)) if os.path.exists(hist_path) else {}
MESES = {'outubro': 'out', 'novembro': 'nov', 'dezembro': 'dez'}
mes_key = MESES.get(mes.split()[0].lower())
# fechamento do mês anterior (opcional): extrato_dir/mes_anterior.json = {"out"|"nov": [[cod_rc, cod_cliente, kg], ...]}
ant = os.path.join(ext, 'mes_anterior.json')
if os.path.exists(ant):
    for k, linhas in json.load(open(ant)).items():
        q4hist[k] = {}
        for rc_, cli_, kg_ in linhas:
            q4hist[k].setdefault(rc_, {})[cli_] = kg_
if mes_key:
    q4hist[mes_key] = {}
    for x in clients:
        q4hist[mes_key].setdefault(x[0], {})[x[1]] = x[6]
    json.dump(q4hist, open(hist_path, 'w'), ensure_ascii=False)
hoje = datetime.date.fromisoformat(atualizado)
meses_rest = max(12 - hoje.month + 1, 0) if hoje.month >= 10 else 3
# meses do ano já fechados (o mês do painel conta como fechado só se não for o mês corrente)
mes_painel = ['janeiro','fevereiro','março','abril','maio','junho','julho','agosto','setembro','outubro','novembro','dezembro'].index(mes.split()[0].lower()) + 1
meses_fechados = mes_painel if mes_painel < hoje.month else mes_painel - 1

# código do RC -> nome, a partir das linhas de rebate e do histórico
nomes = {}
for r in out['reb']:
    c, n = r[0].split(' - ', 1); nomes[c] = n
plano = {p[0]: p for p in out['plano']}
flash = {f[0]: f for f in out['flash']}
cod_por_nome = {}
for c, n in nomes.items(): cod_por_nome[n] = c
for c in {x[0] for x in clients}:
    pass

def slugify(n):
    return re.sub(r'[^a-z]', '', n.split()[0].lower())

# todos os RCs do Plano Performance
alvo = []
for nome in plano:
    cod = next((c for c, v in rcs.items() if v['nome'] == nome), None) or cod_por_nome.get(nome)
    if cod is None:
        # procura pelo nome no extrato de clientes não é possível; usa mapa fixo
        raise SystemExit(f'Sem código para {nome}: adicione em tools/rcs.json')
    if cod not in rcs:
        rcs[cod] = {'nome': nome, 'slug': f'{slugify(nome)}-{secrets.token_hex(3)}'}
    alvo.append(cod)
json.dump(rcs, open(os.path.join(T, 'rcs.json'), 'w'), ensure_ascii=False, indent=2)

page = open(os.path.join(T, 'template.html')).read().replace('<meta name="dash-one-writer">\n', '')
se = page.index('</style>') + len('</style>')
styles, body = page[:se], page[se:]
si = body.index('<script>'); markup, script = body[:si], body[si:]
SHIM = open(os.path.join(T, 'shim.js')).read()
HEAD = open(os.path.join(T, 'head.html')).read()

# Itens por cliente nos últimos 12 meses (Curva ABC: RC × cliente × família × produto × PESO, filtro MES/ANO = 12 meses)
# extrato_dir/itens.json = [[cod_cliente, produto, kg], ...] (formato antigo: [cod_rc, cod_cliente, produto, familia, kg])
# Itens são extraídos 1x por semana: o extrato novo é guardado compactado em tools/itens.json e reaproveitado nos outros dias
itens_path = os.path.join(ext, 'itens.json')
ITENS_REPO = os.path.join(T, 'itens.json')
if os.path.exists(itens_path):
    _novo = json.load(open(itens_path)); _novo = [[r[1], r[2], r[4]] if len(r) == 5 else r for r in _novo]
    _P = sorted({r[1] for r in _novo}); _ix = {p: i for i, p in enumerate(_P)}
    json.dump({'data': atualizado, 'produtos': _P, 'linhas': [[r[0], _ix[r[1]], r[2]] for r in _novo]}, open(ITENS_REPO, 'w'), ensure_ascii=False, separators=(',', ':'))
    itens_rows = _novo; itens_data = atualizado
elif os.path.exists(ITENS_REPO):
    _r = json.load(open(ITENS_REPO)); itens_rows = [[c, _r['produtos'][i], k] for c, i, k in _r['linhas']]; itens_data = _r['data']
else:
    itens_rows = []; itens_data = None
print('itens 12 meses:', len(itens_rows), 'linhas, extraídos em', itens_data)
itens_rows = [[None, r[0], r[1], '', r[2]] if len(r) == 3 else r for r in itens_rows]
EXCLUI_FAM = {f.strip().upper() for f in json.load(open(os.path.join(T, 'familias_excluidas.json')))} if os.path.exists(os.path.join(T, 'familias_excluidas.json')) else set()
itens_rows = [r for r in itens_rows if r[4] > 0 and str(r[3]).strip().upper() not in EXCLUI_FAM]
# ranking da Regional: nº de clientes distintos que compraram cada item
_cli_por_item = {}
for r in itens_rows: _cli_por_item.setdefault(r[2], set()).add(r[1])
ranking = [{'item': k, 'n': len(v)} for k, v in sorted(_cli_por_item.items(), key=lambda kv: (-len(kv[1]), kv[0]))][:300]

resumo = []
# RCs pausados (ex.: desligados) não são regerados; a página fica com a última versão
alvo = [c for c in alvo if not rcs[c].get('pausado')]
def itens_cli(cod):
    # itens por cliente da carteira ATUAL do RC (Histórico), não pelo RC da venda — clientes transferidos levam o histórico
    carteira = {str(x[1]) for x in clients if x[0] == cod}
    out = {}
    for r in itens_rows:
        if str(r[1]) in carteira:
            out.setdefault(str(r[1]), {}).setdefault(r[2], 0)
            out[str(r[1])][r[2]] += r[4]
    return {c: sorted(([k, v] for k, v in d.items()), key=lambda x: -x[1]) for c, d in out.items()}

for cod in alvo:
    nome = rcs[cod]['nome']; p = plano[nome]; f = flash.get(nome, [nome, 0, 0, 0])
    cl = [{'cod': x[1], 'razao_social': x[2], 'rede': x[3], # médias do próprio BI (MED KG 25/26, mesmo período) quando vierem no extrato
           # 2025 = média do ano inteiro (Histórico MÉD KG 25, jan–dez ÷ 12) quando vier no extrato (x[12])
           'med_kg_25': x[12] if len(x) > 12 else (x[10] if len(x) > 11 else round(x[4] / 12)), 'med_kg_26': x[11] if len(x) > 11 else round((x[5] - (x[6] if mes_painel == hoje.month else 0)) / meses_fechados),
           'kg_mes': x[6], 'kg_carteira': x[7], 'dias_ult_compra': x[8], 'freq_media_dias': x[9]} for x in clients if x[0] == cod]
    reb = []
    for r in out['reb']:
        if r[0].split(' - ')[0] != cod: continue
        rc_cod, rede = r[1].split(' - ', 1)
        for g, vals in zip(['Total', 'G1', 'G2', 'G3'], r[2:6]):
            reb.append({'cod': rc_cod, 'rede': rede, 'grupo': g, 'objetivo': vals[0], 'realizado': vals[1], 'rs_faturado': vals[2], 'rebate': vals[3]})
    # kg 2026 só dos meses fechados: tira a parte do mês vigente na proporção do RC (faturado do mês ÷ kg 2026 do RC)
    _k26 = sum(x[5] for x in clients if x[0] == cod); _mes = sum(x[6] for x in clients if x[0] == cod) if mes_painel == hoje.month else 0
    _fech = (_k26 - _mes) / _k26 if _k26 else 1
    fam = [{'familia': re.sub(r'(\d+)\s*-\s*', r'\1 - ', x[1]), 'kg_2026': x[2], 'kg_2025': x[3], 'positivacao_2026': x[4],
            'kg_2026_fech': round(x[2] * _fech)}
           for x in out['fam'] if x[0] == cod and (x[2] or x[3])]
    m4 = metas4t.get(cod)
    kg_m = {k: q4hist.get(k, {}).get(cod, {}) for k in ('out', 'nov', 'dez')}
    nomes_cli = {x[1]: x[2] for x in clients if x[0] == cod}
    meta4t = [{'objetivo': m4['objetivo'] if m4 else 0, 'meses_rest': meses_rest, 'fechados': sum(1 for k in ('out', 'nov', 'dez') if kg_m[k]),
               **{k: sum(kg_m[k].values()) for k in ('out', 'nov', 'dez')}}]
    # Objetivo 4º tri por cliente: objetivo do RC dividido só entre os clientes ativos (compra em 2026),
    # na proporção da média mensal 2026 de cada um. alvo25 (recuperar 2025) continua vindo da reunião.
    # alvo25 de qualquer RC da reunião (clientes transferidos de RC levam o alvo)
    alvo25 = {c['cod']: c.get('alvo25', 0) for m_ in metas4t.values() for c in m_.get('clientes', [])}
    alvo25.update({c['cod']: c.get('alvo25', 0) for c in (m4['clientes'] if m4 else [])})
    ativos = [c for c in cl if c['med_kg_26'] > 0]
    soma_med = sum(c['med_kg_26'] for c in ativos) or 1
    obj4t = m4['objetivo'] if m4 else 0
    clientes4t = [{'cod': c['cod'], 'razao_social': c['razao_social'], 'meta': round(obj4t * c['med_kg_26'] / soma_med),
                   'alvo25': alvo25.get(c['cod'], 0),
                   'realizado': sum(kg_m[k].get(c['cod'], 0) for k in ('out', 'nov', 'dez'))} for c in ativos]
    d = {'plano': [{'representante': nome, 'regional': 'Regional SPI Campinas', 'mes': mes, 'atualizado_em': atualizado,
                    'objetivo': p[1], 'acelerador': p[2], 'minimo': p[3], 'faturado': f[2], 'carteira': f[3], 'meses_fechados': meses_fechados}],
         'clientes': cl, 'rebate': reb, 'familias': fam, 'meta4t': meta4t, 'clientes4t': clientes4t,
         'itens': [itens_cli(cod)], 'ranking': ranking}
    html = (HEAD % nome.title()) + styles + '\n</head><body>\n<div id="dash-root">' + markup + '</div>\n<script>window.__DATA = ' + json.dumps(d, ensure_ascii=False) + ';</script>\n' + SHIM + script + '\n<script>dash._runAll(); let __t, __w = innerWidth; addEventListener("resize", () => { if (innerWidth === __w) return; __w = innerWidth; clearTimeout(__t); __t = setTimeout(() => dash._runAll(), 200); });</script>\n</body></html>\n'
    os.makedirs(os.path.join(SITE, rcs[cod]['slug']), exist_ok=True)
    open(os.path.join(SITE, rcs[cod]['slug'], 'index.html'), 'w').write(html)
    q = meta4t[0]; rq = q['out'] + q['nov'] + q['dez']
    resumo.append((nome, f[2], p[1], f[2] / p[1], len(cl), sum(c['kg_mes'] for c in cl), q['objetivo'], rq))

open(os.path.join(SITE, 'index.html'), 'w').write('<!doctype html><meta charset="utf-8"><meta name="robots" content="noindex"><title>Acesso restrito</title><body style="background:#050505;color:#999;font-family:system-ui;display:grid;place-items:center;height:100vh;margin:0">Use o link enviado pelo seu gestor.</body>')
open(os.path.join(SITE, 'robots.txt'), 'w').write('User-agent: *\nDisallow: /\n')
open(os.path.join(SITE, '_headers'), 'w').write('/*\n  X-Robots-Tag: noindex, nofollow\n  Cache-Control: no-cache\n')
for r in resumo: print('%-34s fat %7d obj %7d %6.1f%% | 4T meta %7d real %7d %5.1f%%' % (r[0], r[1], r[2], r[3] * 100, r[6], r[7], (r[7] / r[6] * 100) if r[6] else 0))
