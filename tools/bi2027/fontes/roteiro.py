"""Roteiro sugerido de 4 semanas por RC.
Entradas: rot_cli.json (cód -> rc, nome, med, mix, dias, freq), geo.json (cód -> [rc, cód, lat, lon, nível, bairro, cidade, endereço]).
Regras:
- Curva de volume (média 2026): A = clientes que somam 80% do volume do RC; B = próximos 15%; C = últimos 5%.
- Mix (famílias compradas em 12 meses): terços dentro do RC (alto / médio / baixo).
- Frequência: A semanal (4 visitas no ciclo), B quinzenal (2), C mensal (1). Mix baixo = flag "foco em mix".
- Tempo de visita: 15–20 min (menor) até 180 min (maior), pela combinação volume (75%) + mix (25%).
- Cada cliente tem um dia fixo da semana (zona geográfica). RCs com sexta de pequenos: sexta só com curva C.
- Ideal ~8 visitas/dia; deslocamento estimado a 30 km/h com fator de rua 1,3.
"""
import json, math, sys, random

S = sys.argv[1]
CLI = json.load(open(S + '/rot_cli.json')); GEO = json.load(open(S + '/geo.json'))
SEXTA_PEQ = {'166091', '130253', '172437', '168005'}  # Lucas + (Maria, Yuri, Thiago) — conferido no rcs.json abaixo
DIAS = ['Seg', 'Ter', 'Qua', 'Qui', 'Sex']

def km(a, b):
    R = 6371; la1, lo1, la2, lo2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    h = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return 2 * R * math.asin(math.sqrt(h)) * 1.3

def kmeans(pts, k, it=60):
    random.seed(7)
    if len(pts) <= k: return [[p] for p in pts]
    pts_s = sorted(pts, key=lambda p: (p['lon'], p['lat']))
    cen = [(pts_s[int((i + .5) * len(pts_s) / k)]['lat'], pts_s[int((i + .5) * len(pts_s) / k)]['lon']) for i in range(k)]
    for _ in range(it):
        gr = [[] for _ in range(k)]
        for p in pts: gr[min(range(k), key=lambda i: km((p['lat'], p['lon']), cen[i]))].append(p)
        cen = [(sum(p['lat'] for p in g) / len(g), sum(p['lon'] for p in g) / len(g)) if g else cen[i] for i, g in enumerate(gr)]
    return gr

def balance(groups, cap_key, k):
    """move pontos da zona mais carregada para a vizinha mais próxima até equilibrar a carga semanal"""
    for _ in range(400):
        load = [sum(p[cap_key] for p in g) for g in groups]
        hi = max(range(k), key=lambda i: load[i]); lo = min(range(k), key=lambda i: load[i])
        if load[hi] - load[lo] < 0.10 * (sum(load) / k): break
        cl = (sum(p['lat'] for p in groups[lo]) / max(len(groups[lo]), 1), sum(p['lon'] for p in groups[lo]) / max(len(groups[lo]), 1)) if groups[lo] else (groups[hi][0]['lat'], groups[hi][0]['lon'])
        cand = min(groups[hi], key=lambda p: km((p['lat'], p['lon']), cl))
        groups[hi].remove(cand); groups[lo].append(cand)
    return groups

def order(stops):
    if len(stops) < 3: return stops
    start = min(stops, key=lambda p: p['lon']); rest = [p for p in stops if p is not start]; route = [start]
    while rest:
        nx = min(rest, key=lambda p: km((route[-1]['lat'], route[-1]['lon']), (p['lat'], p['lon']))); route.append(nx); rest.remove(nx)
    return route

def plan(rc, sexta_peq):
    cl = []
    for cod, c in CLI.items():
        if c['rc'] != rc: continue
        g = GEO.get(cod)
        if not g or g[2] is None: continue
        cl.append(dict(c, cod=cod, lat=g[2], lon=g[3], geo=g[4], bairro=g[5].title(), cidade=g[6].title(), end=g[7]))
    tot = sum(c['med'] for c in cl) or 1; acc = 0
    for c in sorted(cl, key=lambda c: -c['med']):
        acc += c['med']; c['curva'] = 'A' if acc - c['med'] < .8 * tot else ('B' if acc - c['med'] < .95 * tot else 'C')
    mixs = sorted(c['mix'] for c in cl); t1, t2 = mixs[len(mixs) // 3], mixs[2 * len(mixs) // 3]
    lv = [math.log(c['med'] + 1) for c in cl]; lmin, lmax = min(lv), max(lv); mmax = max(mixs) or 1
    for c in cl:
        c['mixn'] = 'alto' if c['mix'] > t2 else ('médio' if c['mix'] > t1 else 'baixo')
        vmax = max(x['med'] for x in cl) or 1
        s = (c['med'] / vmax) ** .6 * (.85 + .3 * c['mix'] / mmax)
        c['min'] = max(15, min(180, int(round(180 * s / 5) * 5)))
        c['rap'] = max(15, int(round(c['min'] * .4 / 5) * 5))   # visita de rotina (pedido) nas outras semanas
        c['vis'] = {'A': 4, 'B': 2, 'C': 1}[c['curva']]
        c['carga'] = c['min'] + c['rap'] * (c['vis'] - 1)
    # sexta dos pequenos: todos os C + os menores B até ~7 visitas por sexta
    fr = {'A': 4, 'B': 2, 'C': 1}
    for c in cl: c['sexta'] = sexta_peq and c['curva'] == 'C'
    if sexta_peq:
        for c in sorted([c for c in cl if c['curva'] == 'B'], key=lambda c: c['med']):
            if sum(fr[x['curva']] for x in cl if x['sexta']) >= 28: break
            c['sexta'] = True
    # capacidade em horas: ~8h/dia com visitas + 15 min de deslocamento/estacionamento por visita.
    # Se não couber, os menores A viram quinzenais (rotina) e, se preciso, os menores B viram mensais.
    ndias = 4 * (4 if sexta_peq else 5); ajust = 0
    def horas():
        t = 0
        for c in cl:
            if c['sexta']: continue
            v = fr[c['curva']]; t += c['min'] + c['rap'] * (v - 1) + 15 * v
        return t / 60
    for de, para in (('A', 'B'), ('B', 'C')):
        for c in sorted([c for c in cl if c['curva'] == de and not c['sexta']], key=lambda c: c['med']):
            if horas() <= 8 * ndias: break
            c['curva'] = para; c['ajust'] = de; ajust += 1
    for c in cl:
        c['vis'] = fr[c['curva']]; c['carga'] = c['min'] + c['rap'] * (c['vis'] - 1)
    dias = DIAS[:4] if sexta_peq else DIAS
    mid = [c for c in cl if not c['sexta']]
    zones = balance(kmeans(mid, len(dias)), 'carga', len(dias))
    for d, z in zip(dias, zones):
        for c in z: c['dia'] = d
    for c in cl:
        if c['sexta']: c['dia'] = 'Sex'
    # semanas: A todas; B alterna (1/3 ou 2/4); C na semana com menos visitas. Máximo de 8 visitas por dia:
    # se passar, o menor cliente do dia com mais de 1 visita perde frequência (semanal → quinzenal → mensal);
    # se o dia só tiver mensais e ainda passar, o menor mensal muda para o dia com mais folga.
    MAXV = 8; FR = {'A': 4, 'B': 2, 'C': 1}; DOWN = {'A': 'B', 'B': 'C'}
    def assign(d):
        z = [c for c in cl if c.get('dia') == d]; load = [0] * 4; cnt = [0] * 4
        for c in z: c.pop('sem', None)
        for c in sorted([c for c in z if c['curva'] == 'A'], key=lambda c: -c['min']):
            c['sem'] = [0, 1, 2, 3]; full = min(range(4), key=lambda i: load[i]); c['full'] = full
            for w in c['sem']: load[w] += c['min'] if w == full else c['rap']; cnt[w] += 1
        for c in sorted([c for c in z if c['curva'] == 'B'], key=lambda c: -c['min']):
            par = 0 if (cnt[0] + cnt[2], load[0] + load[2]) <= (cnt[1] + cnt[3], load[1] + load[3]) else 1
            c['sem'] = [par, par + 2]; c['full'] = par if load[par] <= load[par + 2] else par + 2
            for w in c['sem']: load[w] += c['min'] if w == c['full'] else c['rap']; cnt[w] += 1
        for c in sorted([c for c in z if c['curva'] == 'C'], key=lambda c: -c['min']):
            w = min(range(4), key=lambda i: (cnt[i], load[i])); c['sem'] = [w]; c['full'] = w; load[w] += c['min']; cnt[w] += 1
        return max(cnt) if z else 0
    for d in DIAS:
        for _ in range(200):
            if assign(d) <= MAXV: break
            z = [c for c in cl if c.get('dia') == d]
            red = sorted([c for c in z if FR[c['curva']] > 1], key=lambda c: c['med'])
            if red:
                c = red[0]; c.setdefault('ajust', c['curva']); c['curva'] = DOWN[c['curva']]; ajust += 1
            else:
                livres = [x for x in DIAS if x != d and (x != 'Sex' or not sexta_peq)]
                alvo = min(livres, key=lambda x: sum(FR[c['curva']] for c in cl if c.get('dia') == x))
                c = min(z, key=lambda c: c['med']); c['dia'] = alvo; assign(alvo)
    for c in cl: c['vis'] = FR[c['curva']]
    weeks = []
    for w in range(4):
        wk = []
        for d in DIAS:
            st = order([c for c in cl if c.get('dia') == d and w in c['sem']])
            for c in st: c['min_w'] = c['min'] if c['curva'] == 'C' or c.get('full') == w else c['rap']; c['tipo'] = 'completa' if c['min_w'] == c['min'] else 'rotina'
            # deslocamento: distância em linha reta × 1,3 a 30 km/h + 10 min de estacionamento/acesso por trecho
            for i, c in enumerate(st): c['desl_min'] = 0 if i == 0 else int(round((km((st[i-1]['lat'], st[i-1]['lon']), (c['lat'], c['lon'])) / 30 * 60 + 10) / 5) * 5)
            desl = sum(km((a['lat'], a['lon']), (b['lat'], b['lon'])) for a, b in zip(st, st[1:]))
            vis = sum(c['min_w'] for c in st); dmin = sum(c['desl_min'] for c in st); tmin = vis + dmin
            cid = sorted({c['cidade'] for c in st}, key=lambda x: -sum(1 for c in st if c['cidade'] == x))
            wk.append({'dia': d, 'zona': ' · '.join(cid[:2]), 'km': round(desl), 'horas': round(tmin / 60, 1), 'vis_min': vis, 'desl_min': dmin,
                       'stops': [{k: c.get(k) for k in ('cod', 'nome', 'curva', 'mixn', 'ajust', 'mix', 'min_w', 'tipo', 'desl_min', 'med', 'bairro', 'cidade', 'end', 'lat', 'lon', 'geo', 'dias', 'freq')} for c in st]})
        weeks.append(wk)
    resumo = {'clientes': len(cl), 'visitas': sum(c['vis'] for c in cl), 'A': sum(c['curva'] == 'A' for c in cl), 'B': sum(c['curva'] == 'B' for c in cl), 'C': sum(c['curva'] == 'C' for c in cl),
              'sem_geo': sum(1 for cod, c in CLI.items() if c['rc'] == rc and not (GEO.get(cod) and GEO[cod][2] is not None)), 'sexta_peq': sexta_peq,
              'mix_cortes': [t1, t2], 'ajust': sum(1 for c in cl if c.get('ajust'))}
    return {'resumo': resumo, 'semanas': weeks}

if __name__ == '__main__':
    out = {}
    for rc, nome, sp in [('133242', 'Gabriel', False), ('166091', 'Lucas', True)]:
        out[rc] = dict(plan(rc, sp), nome=nome)
        r = out[rc]['resumo']; print(nome, r)
        for w, wk in enumerate(out[rc]['semanas']):
            print('  S%d ' % (w + 1) + ' | '.join('%s %d %.1fh %dkm' % (d['dia'], len(d['stops']), d['horas'], d['km']) for d in wk))
    json.dump(out, open(S + '/roteiro.json', 'w'), ensure_ascii=False)
