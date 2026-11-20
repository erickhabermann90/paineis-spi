"""Roteiro sugerido de 4 semanas por RC.
Entradas: rot_cli.json (cód -> rc, nome, med, mix, dias, freq), geo.json (cód -> [rc, cód, lat, lon, nível, bairro, cidade, endereço]).
Regras:
- Curva de volume (média 2026): A = clientes que somam 80% do volume do RC; B = próximos 15%; C = últimos 5%.
- Mix (famílias compradas em 12 meses): terços dentro do RC (alto / médio / baixo).
- Frequência: A semanal (4 visitas no ciclo), B quinzenal (2), C mensal (1). Mix baixo = flag "foco em mix".
- Tempo de visita: 15–20 min (menor) até 180 min (maior), pela combinação volume (75%) + mix (25%).
- Cada cliente tem um dia fixo da semana (zona geográfica). RCs com sexta de pequenos: sexta só com curva C.
- Cidade primeiro: cada dia (de cada semana) atende uma única cidade; dentro da cidade, zonas por proximidade.
  Sobra de dia vira dia alternado (semanas 1/3 de uma cidade, 2/4 de outra). Cidades em WHATS ficam fora (atendimento por WhatsApp).
- Máximo 8 visitas e 6 h por dia (visita + deslocamento); se passar, os menores perdem frequência.
- Deslocamento estimado a 30 km/h com fator de rua 1,3.
"""
import json, math, sys, random, collections

S = sys.argv[1]
CLI = json.load(open(S + '/rot_cli.json')); GEO = json.load(open(S + '/geo.json'))
SEXTA_PEQ = {'166091', '130253', '172437', '168005'}  # Lucas + (Maria, Yuri, Thiago) — conferido no rcs.json abaixo
DIAS = ['Seg', 'Ter', 'Qua', 'Qui', 'Sex']
WHATS = {'166091': {'Americana'}}  # cidades atendidas por WhatsApp (fora do roteiro presencial)

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
    cl = []; wpp = []
    for cod, c in CLI.items():
        if c['rc'] != rc: continue
        g = GEO.get(cod)
        if not g or g[2] is None: continue
        if g[6].title() in WHATS.get(rc, ()): wpp.append({'cod': cod, 'nome': c['nome'], 'cidade': g[6].title(), 'med': c['med']}); continue
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
            if horas() <= 6 * ndias: break
            c['curva'] = para; c['ajust'] = de; ajust += 1
    for c in cl:
        c['vis'] = fr[c['curva']]; c['carga'] = c['min'] + c['rap'] * (c['vis'] - 1)
    dias = DIAS[:4] if sexta_peq else DIAS
    MAXV = 8; MAXH = 6; FR = {'A': 4, 'B': 2, 'C': 1}; DOWN = {'A': 'B', 'B': 'C'}
    # ---- 1) CIDADE PRIMEIRO: cada célula (dia × semana) pertence a uma única cidade ----
    def cells_plan(grp, days):
        V = collections.Counter(); NA = collections.Counter()
        for c in grp: V[c['cidade']] += FR[c['curva']]; NA[c['cidade']] += c['curva'] == 'A'
        tot = sum(V.values()) or 1; N = 4 * len(days)
        q = {k: v / tot * N for k, v in V.items()}; sl = {k: max(1, int(q[k])) for k in V}
        while sum(sl.values()) < N: k = max(V, key=lambda k: q[k] - sl[k]); sl[k] += 1
        while sum(sl.values()) > N: k = max((k for k in V if sl[k] > 1), key=lambda k: sl[k] - q[k]); sl[k] -= 1
        # dias inteiros (semanais) por cidade; sobra vira dia compartilhado (semanas alternadas)
        own = {d: [None] * 4 for d in days}; free = list(days)
        for k in sorted(V, key=lambda k: -sl[k]):
            for _ in range(sl[k] // 4):
                if free: d = free.pop(0); own[d] = [k] * 4; sl[k] -= 4
        rest = sorted([k for k in V if sl[k] > 0], key=lambda k: -sl[k])
        for d in free:
            for w in (0, 2, 1, 3):
                if not rest: break
                k = rest[0]; own[d][w] = k; sl[k] -= 1
                if sl[k] <= 0: rest.pop(0)
            for w in range(4):
                if own[d][w] is None: own[d][w] = max(V, key=lambda k: q[k])
        return own
    def city_assign(grp, days):
        own = cells_plan(grp, days); log = []
        for cid in sorted({c['cidade'] for c in grp}):
            z = [c for c in grp if c['cidade'] == cid]
            full = [d for d in days if own[d] == [cid] * 4]
            part = [(d, [w for w in range(4) if own[d][w] == cid]) for d in days if cid in own[d] and own[d] != [cid] * 4]
            if not full:   # cidade sem dia inteiro: clientes A viram quinzenais/mensais conforme as semanas que a cidade tem
                for c in z:
                    ws = part[0][1] if part else []
                    while (c['curva'] == 'A') or (c['curva'] == 'B' and not ({0, 2} <= set(ws) or {1, 3} <= set(ws))):
                        c.setdefault('ajust', c['curva']); c['curva'] = DOWN[c['curva']]; log.append(('sem dia inteiro', cid, c['nome']))
            # proximidade dentro da cidade: zonas = dias inteiros; parte compartilhada recebe os B/C mais afastados do centro das zonas
            if full:
                zones = balance(kmeans(z, len(full)), 'carga', len(full))
                for d, zz in zip(full, zones):
                    for c in zz: c['dia'] = d; c['wmask'] = [0, 1, 2, 3]
            for d, ws in part:
                cap = 8 * len(ws)
                cand = sorted([c for c in z if c['curva'] != 'A' and (not full or True)], key=lambda c: c['med'])
                if not full:
                    for c in z: c['dia'] = d; c['wmask'] = ws
                    continue
                # puxa para o dia compartilhado os menores B/C do dia inteiro mais carregado até preencher
                used = 0
                for c in cand:
                    need = FR[c['curva']]
                    if c['curva'] == 'B' and not ({0, 2} <= set(ws) or {1, 3} <= set(ws)): continue
                    if used + need > cap: continue
                    c['dia'] = d; c['wmask'] = ws; used += need
        return own, log
    def assign(d):
        z = [c for c in cl if c.get('dia') == d]; load = [0] * 4; cnt = [0] * 4
        for c in z: c.pop('sem', None)
        for c in sorted([c for c in z if c['curva'] == 'A'], key=lambda c: -c['min']):
            c['sem'] = [0, 1, 2, 3]; full = min(range(4), key=lambda i: load[i]); c['full'] = full
            for w in c['sem']: load[w] += c['min'] if w == full else c['rap']; cnt[w] += 1
        for c in sorted([c for c in z if c['curva'] == 'B'], key=lambda c: -c['min']):
            ops = [p for p in (0, 1) if p in c['wmask'] and p + 2 in c['wmask']] or [0]
            par = min(ops, key=lambda p: (cnt[p] + cnt[p + 2], load[p] + load[p + 2]))
            c['sem'] = [par, par + 2]; c['full'] = par if load[par] <= load[par + 2] else par + 2
            for w in c['sem']: load[w] += c['min'] if w == c['full'] else c['rap']; cnt[w] += 1
        for c in sorted([c for c in z if c['curva'] == 'C'], key=lambda c: -c['min']):
            w = min(c['wmask'], key=lambda i: (cnt[i], load[i])) if len(c['wmask']) > 1 or True else c['wmask'][0]; c['sem'] = [w]; c['full'] = w; load[w] += c['min']; cnt[w] += 1
        return max(cnt) if z else 0
    mid = [c for c in cl if not c['sexta']]
    OWN, LOG = city_assign(mid, dias)
    if sexta_peq:
        sx = [c for c in cl if c['sexta']]; o2, l2 = city_assign(sx, ['Sex']); OWN.update(o2); LOG += l2
    # limite por dia: 8 visitas e MAXH horas (visita + deslocamento). Passou → o menor cliente com mais de 1 visita
    # naquela célula perde frequência; se só houver mensais, o menor muda para a semana da mesma cidade/dia com mais folga.
    def cell(d, w):
        st = order([c for c in cl if c.get('dia') == d and w in c.get('sem', [])])
        t = sum((c['min'] if c['curva'] == 'C' or c.get('full') == w else c['rap']) for c in st)
        t += sum(int(round((km((a['lat'], a['lon']), (b['lat'], b['lon'])) / 30 * 60 + 10) / 5) * 5) for a, b in zip(st, st[1:]))
        return st, t / 60
    for d in DIAS:
        for _ in range(400):
            assign(d)
            cells = [cell(d, w) for w in range(4)]
            bad = [w for w in range(4) if len(cells[w][0]) > MAXV or cells[w][1] > MAXH]
            if not bad: break
            w = max(bad, key=lambda w: cells[w][1]); st = cells[w][0]
            red = sorted([c for c in st if FR[c['curva']] > 1], key=lambda c: c['med'])
            if red:
                c = red[0]; c.setdefault('ajust', c['curva']); c['curva'] = DOWN[c['curva']]; ajust += 1; continue
            c = min(st, key=lambda c: c['med'])
            alvo = [x for x in c['wmask'] if x != w and cells[x][1] + c['min'] / 60 + .25 <= MAXH and len(cells[x][0]) < MAXV]
            if not alvo: c['excede'] = True; break
            c['wmask'] = [min(alvo, key=lambda x: cells[x][1])]
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
              'mix_cortes': [t1, t2], 'ajust': sum(1 for c in cl if c.get('ajust')), 'whatsapp': wpp, 'max_horas': MAXH,
              'excede': [c['nome'] for c in cl if c.get('excede')]}
    return {'resumo': resumo, 'semanas': weeks}

if __name__ == '__main__':
    out = {}
    for rc, nome, sp in [('133242', 'Gabriel', False), ('166091', 'Lucas', True)]:
        out[rc] = dict(plan(rc, sp), nome=nome)
        r = out[rc]['resumo']; print(nome, r)
        for w, wk in enumerate(out[rc]['semanas']):
            print('  S%d ' % (w + 1) + ' | '.join('%s %d %.1fh %dkm' % (d['dia'], len(d['stops']), d['horas'], d['km']) for d in wk))
    json.dump(out, open(S + '/roteiro.json', 'w'), ensure_ascii=False)
