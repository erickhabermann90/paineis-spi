#!/usr/bin/env python3
"""Junta as partes base64 da exportação (__parte) e grava o extrato.
Uso: python3 tools/importar.py <pasta_extrato> <arquivo_tool_result_1> [<arquivo_2> ...]
Grava clients.json, out.json, kpi_mes.json e, se vierem, campanha.json / itens.json / inativos (tools/inativos.json)."""
import json, base64, sys, os
T = os.path.dirname(os.path.abspath(__file__)); D = sys.argv[1]; os.makedirs(D, exist_ok=True)
txt = ''
for f in sys.argv[2:]:
    raw = open(f).read()
    try: raw = json.load(open(f))[0]['text']
    except Exception: pass
    s, _ = json.JSONDecoder().raw_decode(raw.strip()) if raw.strip().startswith('"') else (raw.strip(), 0)
    txt += base64.b64decode(s).decode('utf-8')
d = json.loads(txt)
# TRAVA DO DIVISOR — o Histórico só traz médias: KG 26 = MÉD KG 26 × N (N = meses que o BI usa, mês aberto incluído) e
# KG 25 = MÉD KG 25 × 12. Confere as somas com a tabela de famílias (KG 26 / KG 25 direto do BI). Se não bater (ex.: virada
# do mês, BI dividindo por N−1 ou N+1), testa os divisores vizinhos, usa o que bater e avisa; se nenhum bater, para aqui.
TOL = 0.001
N = int(d.get('mes_num') or d['kpi_mes']['mes'])
cl = d['clients']; fam26 = sum(x[2] for x in d['out']['fam']); fam25 = sum(x[3] for x in d['out']['fam'])
s25 = sum(x[4] for x in cl)
if fam25 and abs(s25 - fam25) / fam25 > TOL:
    sys.exit(f'PARADO: KG 25 do Histórico ({s25:,}) não bate com a tabela de famílias ({fam25:,}). Conferir colunas do Histórico.')
s26 = sum(x[5] for x in cl); div = None
for n in (N, N - 1, N + 1):
    if n >= 1 and fam26 and abs(s26 * n / N - fam26) / fam26 <= TOL: div = n; break
if div is None:
    sys.exit(f'PARADO: KG 26 do Histórico ({s26:,}) não bate com a tabela de famílias ({fam26:,}) com divisor {N-1}, {N} ou {N+1}. Nada foi gravado.')
if div != N:
    print(f'AVISO: o BI está dividindo a média de 2026 por {div} (esperado {N}). Totais recalculados com {div}.')
    for x in cl:
        x[5] = round(x[5] * div / N)
for x in cl:  # média 2026 só com meses fechados do calendário: (total − mês aberto) ÷ (mês vigente − 1), seja qual for o divisor do BI
    x[11] = round((x[5] - x[6]) / (N - 1)) if N > 1 else 0
print(f'trava do divisor: ok (divisor {div}; KG 26 {s26 * div / N:,.0f} × famílias {fam26:,} · KG 25 {s25:,} × {fam25:,})')
# PLANO PERFORMANCE só é extraído no 1º dia útil do mês; nos outros dias reaproveita tools/plano_mes.json (do mesmo mês).
PM = os.path.join(T, 'plano_mes.json'); mes = d['kpi_mes']['mes']
if d['out'].get('plano'):
    json.dump({'mes': mes, 'plano': d['out']['plano']}, open(PM, 'w'), ensure_ascii=False)
else:
    pm = json.load(open(PM)) if os.path.exists(PM) else {}
    if pm.get('mes') != mes:
        sys.exit(f'PARADO: sem Plano Performance do mês {mes} — extrair a página Representantes - Pl. Performance hoje.')
    d['out']['plano'] = pm['plano']; print('plano performance: reaproveitado do início do mês')
json.dump(cl, open(os.path.join(D, 'clients.json'), 'w'), ensure_ascii=False)
json.dump(d['out'], open(os.path.join(D, 'out.json'), 'w'), ensure_ascii=False)
json.dump(d['kpi_mes'], open(os.path.join(D, 'kpi_mes.json'), 'w'), ensure_ascii=False)
P = d.get('P')
dec = lambda s: [[c, P[int(p)], int(float(k))] for c, p, k in (x.split(',') for x in s.split(';'))] if s else []
if 'q4' in d:
    camp = {'q4': d['q4'], 'q4_itens': dec(d.get('I', '')) if d.get('I') else json.load(open(os.path.join(T, 'campanha_ult.json')))['q4_itens']}
    fo_out = json.load(open(os.path.join(T, 'campanha_fo_mes.json'))).get('10', {})
    camp['fo_mes_atual'] = [[str(r[0]), r[2] + r[3] - fo_out.get(str(r[0]), 0)] for r in d['q4'] if r[2] + r[3] - fo_out.get(str(r[0]), 0) > 0]
    json.dump(camp, open(os.path.join(D, 'campanha.json'), 'w'), ensure_ascii=False)
if d.get('I12'):
    json.dump(dec(d['I12']), open(os.path.join(D, 'itens.json'), 'w'), ensure_ascii=False)
if d.get('kpi_rc'):  # KPIs do mês por RC e família geral (link de teste BI 2027)
    json.dump(d['kpi_rc'], open(os.path.join(D, 'kpi_rc.json'), 'w'), ensure_ascii=False)
if d.get('INAT'):
    json.dump({'extraido_em': 'semanal', 'fonte': 'Power BI · SITUAÇÃO CLIENTE = INATIVO', 'clientes': sorted(set(map(str, d['INAT'])), key=int)}, open(os.path.join(T, 'inativos.json'), 'w'), ensure_ascii=False)
k = d['kpi_mes']['vals']
print('clientes', len(d['clients']), '| faltando', d['miss'][:5], '| fat mês', sum(x[6] for x in d['clients']), '| KPI vol', k['vol'],
      '| campanha', 'sim' if 'q4' in d else 'não', '| itens 12m', 'sim' if d.get('I12') else 'não', '| inativos', len(d.get('INAT') or []) or 'não')
