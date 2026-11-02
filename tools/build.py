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

resumo = []
for cod in alvo:
    nome = rcs[cod]['nome']; p = plano[nome]; f = flash.get(nome, [nome, 0, 0, 0])
    cl = [{'cod': x[1], 'razao_social': x[2], 'rede': x[3], 'med_kg_25': round(x[4] / 12), 'med_kg_26': round(x[5] / 10),
           'kg_mes': x[6], 'kg_carteira': x[7], 'dias_ult_compra': x[8], 'freq_media_dias': x[9]} for x in clients if x[0] == cod]
    reb = []
    for r in out['reb']:
        if r[0].split(' - ')[0] != cod: continue
        rc_cod, rede = r[1].split(' - ', 1)
        for g, vals in zip(['Total', 'G1', 'G2', 'G3'], r[2:6]):
            reb.append({'cod': rc_cod, 'rede': rede, 'grupo': g, 'objetivo': vals[0], 'realizado': vals[1], 'rs_faturado': vals[2], 'rebate': vals[3]})
    fam = [{'familia': re.sub(r'(\d+)\s*-\s*', r'\1 - ', x[1]), 'kg_2026': x[2], 'kg_2025': x[3], 'positivacao_2026': x[4]}
           for x in out['fam'] if x[0] == cod and (x[2] or x[3])]
    d = {'plano': [{'representante': nome, 'regional': 'Regional SPI Campinas', 'mes': mes, 'atualizado_em': atualizado,
                    'objetivo': p[1], 'acelerador': p[2], 'minimo': p[3], 'faturado': f[2], 'carteira': f[3]}],
         'clientes': cl, 'rebate': reb, 'familias': fam}
    html = (HEAD % nome.title()) + styles + '\n</head><body>\n<div id="dash-root">' + markup + '</div>\n<script>window.__DATA = ' + json.dumps(d, ensure_ascii=False) + ';</script>\n' + SHIM + script + '\n<script>dash._runAll(); let __t; addEventListener("resize", () => { clearTimeout(__t); __t = setTimeout(() => dash._runAll(), 200); });</script>\n</body></html>\n'
    os.makedirs(os.path.join(SITE, rcs[cod]['slug']), exist_ok=True)
    open(os.path.join(SITE, rcs[cod]['slug'], 'index.html'), 'w').write(html)
    resumo.append((nome, f[2], p[1], f[2] / p[1], len(cl), sum(c['kg_mes'] for c in cl)))

open(os.path.join(SITE, 'index.html'), 'w').write('<!doctype html><meta charset="utf-8"><meta name="robots" content="noindex"><title>Acesso restrito</title><body style="background:#050505;color:#999;font-family:system-ui;display:grid;place-items:center;height:100vh;margin:0">Use o link enviado pelo seu gestor.</body>')
open(os.path.join(SITE, 'robots.txt'), 'w').write('User-agent: *\nDisallow: /\n')
open(os.path.join(SITE, '_headers'), 'w').write('/*\n  X-Robots-Tag: noindex, nofollow\n  Cache-Control: no-cache\n')
for r in resumo: print('%-36s fat %7d obj %7d %6.1f%%  clientes %4d  soma_out %7d' % (r[0], r[1], r[2], r[3] * 100, r[4], r[5]))
