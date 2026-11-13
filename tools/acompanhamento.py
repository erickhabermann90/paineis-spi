#!/usr/bin/env python3
"""Print do ACOMPANHAMENTO 4º TRIMESTRE (OUT-NOV-DEZ), no mesmo formato da tabela do Erick.

Uso: python3 tools/acompanhamento.py <pasta do extrato> <AAAA-MM-DD> <saída.png>
- Objetivo 4T: tools/metas4t.json (Wilian já com o do Marcelo) + extras em tools/acomp4t.json (Star Max).
- Faturado de meses fechados: tools/q4_mensal.json (por RC e cliente; Marcelo somado ao Wilian).
- Mês vigente (faturado e carteira): página FLASH do extrato (out.json → flash).
"""
import json, os, sys, datetime

T = os.path.dirname(os.path.abspath(__file__))
ext, data, saida = sys.argv[1], sys.argv[2], sys.argv[3]
hoje = datetime.date.fromisoformat(data)
rcs = json.load(open(os.path.join(T, 'rcs.json')))
metas = json.load(open(os.path.join(T, 'metas4t.json')))
extra = json.load(open(os.path.join(T, 'acomp4t.json')))
q4m = json.load(open(os.path.join(T, 'q4_mensal.json')))
flash = {r[0].strip('*'): r for r in json.load(open(os.path.join(ext, 'out.json')))['flash']}

MESES = {10: ('out', 'FAT OUT'), 11: ('nov', 'FAT NOV'), 12: ('dez', 'FAT DEZ')}
mes_atual = hoje.month if hoje.month in MESES else 12
fechados = [m for m in (10, 11, 12) if m < mes_atual]
somar = extra.get('somar', {})          # cód RC pausado → cód RC que herdou a carteira

linhas = []
alvo = {cod: m['objetivo'] for cod, m in metas.items() if not rcs.get(cod, {}).get('pausado')}
for e in extra['rcs']:
    alvo[e['cod']] = e['objetivo']
for cod, obj in alvo.items():
    nome_bi = rcs[cod]['nome'] if cod in rcs else next(e['nome_bi'] for e in extra['rcs'] if e['cod'] == cod)
    rotulo = next((e['nome'] for e in extra['rcs'] if e['cod'] == cod), nome_bi)
    origem = [cod] + [k for k, v in somar.items() if v == cod]
    fech = [sum(sum(q4m.get(MESES[m][0], {}).get(c, {}).values()) for c in origem) for m in fechados]
    f = flash.get(nome_bi)
    if f is None:
        sys.exit(f'RC sem linha na FLASH: {nome_bi}')
    fat_mes, cart = f[2], f[3]
    for k in origem[1:]:
        fp = flash.get(rcs[k]['nome'])
        if fp: fat_mes += fp[2]; cart += fp[3]
    total = sum(fech) + fat_mes + cart
    linhas.append({'nome': rotulo, 'obj': obj, 'meses': fech + [fat_mes], 'cart': cart, 'total': total,
                   'gap': obj - total, 'vend': total / obj, 'fat': (sum(fech) + fat_mes) / obj})
linhas.sort(key=lambda r: r['nome'])
G = {'obj': sum(r['obj'] for r in linhas), 'meses': [sum(r['meses'][i] for r in linhas) for i in range(len(fechados) + 1)],
     'cart': sum(r['cart'] for r in linhas), 'total': sum(r['total'] for r in linhas)}
G['gap'] = G['obj'] - G['total']; G['vend'] = G['total'] / G['obj']; G['fat'] = sum(G['meses']) / G['obj']

n = lambda v: f'{round(v):,}'.replace(',', '.')
p = lambda v, d=2: f'{v * 100:.{d}f}%'.replace('.', ',')
cols = ['REPRESENTANTE', 'OBJETIVO 4T'] + [MESES[m][1] for m in fechados + [mes_atual]] + ['CARTEIRA', 'TOTAL', 'GAP', '% VENDIDO', '% FATURADO']
th = ''.join(f'<th{" class=l" if i == 0 else ""}>{c}</th>' for i, c in enumerate(cols))
def tr(r, geral=False):
    gap = f'<td class="{"" if geral else ("red" if r["gap"] > 0 else "grn")}">{n(r["gap"])}</td>'
    cel = [f'<td class="l">{"GERAL" if geral else r["nome"]}</td>', f'<td>{n(r["obj"])}</td>'] + [f'<td>{n(v)}</td>' for v in r['meses']] + \
          [f'<td>{n(r["cart"])}</td>', f'<td>{n(r["total"])}</td>', gap,
           f'<td class="b">{p(r["vend"], 0 if geral else 2)}</td>', f'<td class="b">{p(r["fat"], 0 if geral else 2)}</td>']
    return f'<tr{" class=g" if geral else ""}>' + ''.join(cel) + '</tr>'
corpo = ''.join(tr(r) for r in linhas) + tr(G, True)
html = f'''<!doctype html><html><head><meta charset="utf-8"><style>
body {{ margin: 0; background: #fff; font-family: "Liberation Sans", Arial, Helvetica, sans-serif; color: #000; }}
.w {{ display: inline-block; padding: 6px; }}
table {{ border-collapse: collapse; font-size: 15px; }}
td, th {{ border: 1px solid #000; padding: 4px 10px; text-align: right; white-space: nowrap; }}
th {{ background: #ffc000; font-weight: 700; }}
.l {{ text-align: left; }}
.tit th {{ text-align: center; font-size: 16px; }}
.red {{ color: #c00000; }} .grn {{ color: #00703c; }} .b {{ font-weight: 700; }}
tr.g td {{ background: #ffc000; font-weight: 700; }} tr.g td.l {{ text-align: center; }}
table {{ border: 2px solid #000; }}
.rod {{ font-size: 12px; color: #444; margin-top: 4px; }}
</style></head><body><div class="w" id="w"><table>
<tr class="tit"><th colspan="{len(cols)}">ACOMPANHAMENTO 4º TRIMESTRE (OUT-NOV-DEZ)</th></tr><tr>{th}</tr>{corpo}</table>
<div class="rod">Atualizado em {hoje.strftime("%d/%m/%y")} · Fonte: Power BI Dashboard Comercial + objetivo 4º tri da reunião · GAP positivo = falta para o objetivo</div></div></body></html>'''
open(os.path.splitext(saida)[0] + '.html', 'w').write(html)

from playwright.sync_api import sync_playwright
with sync_playwright() as pw:
    b = pw.chromium.launch(); pg = b.new_page(viewport={'width': 1700, 'height': 800}, device_scale_factor=2)
    pg.set_content(html); pg.locator('#w').screenshot(path=saida); b.close()
for r in linhas + [dict(G, nome='GERAL')]:
    print('%-36s obj %9s meses %s cart %7s total %9s gap %9s vend %s fat %s' % (r['nome'], n(r['obj']), [n(v) for v in r['meses']], n(r['cart']), n(r['total']), n(r['gap']), p(r['vend']), p(r['fat'])))
