"""Gera prototipos/campanhas.html a partir de tools/campanhas (dados + imagens) e do progresso Bike·Balde."""
import json, base64, os, sys
R = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # tools/
B = os.path.join(R, 'bi2027')
C = json.load(open(os.path.join(R, 'campanhas', 'campanhas.json')))
need = {'camp_bike_px.webp', 'camp_baldes_px.webp'}
for c in C:
    need.update(c['packshots']); need.update([c['arte']] if isinstance(c['arte'], str) else c['arte'])
img = {n: 'data:image/webp;base64,' + base64.b64encode(open(os.path.join(R, 'campanhas', 'img', n), 'rb').read()).decode() for n in need}
bb = json.load(open(os.path.join(B, 'dados', 'bike_balde_gabriel.json')))
hoje = sys.argv[1] if len(sys.argv) > 1 else '2026-11-19'
t = open(os.path.join(B, 'fontes', 'campanhas.tpl.html')).read()
t = t.replace('/*CAMP*/', json.dumps(C, ensure_ascii=False)).replace('/*IMG*/', json.dumps(img)).replace('/*BB*/', json.dumps(bb, ensure_ascii=False))
t = t.replace('/*HOJE*/', hoje).replace('/*DATA_TXT*/', '/'.join(hoje.split('-')[::-1][:2]))
open(os.path.join(B, 'prototipos', 'campanhas.html'), 'w').write(t)
print('ok', len(t) // 1024, 'KB')
