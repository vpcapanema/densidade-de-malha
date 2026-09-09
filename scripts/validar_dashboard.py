"""Testes de integridade independentes do código do navegador."""
from pathlib import Path
import json
import math
import re
from collections import Counter

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / 'relatorio'
data = json.loads((SITE / 'assets/data/indicadores.json').read_text(encoding='utf-8'))
roads = data['trechos']
assert len(roads) == len({r['id'] for r in roads})
assert all(math.isfinite(r['extensao']) and r['extensao'] > 0 for r in roads)
total = sum(r['extensao'] for r in roads)
assert math.isclose(total, 21682.703, abs_tol=1e-6)
assert math.isclose(sum(u['populacao'] for u in data['recortes']['municipios']), 44411238)
assert Counter(r['localizacao'] for r in roads).keys() == {'Urbano', 'Misto', 'Rural'}
assert all(0 <= r['proporcao_urbanizada'] <= 1 for r in roads)
assert all(math.isclose(r['urbano_estimado_km'], r['extensao'] * r['proporcao_urbanizada']) for r in roads)
for r in roads:
    expected = 'Urbano' if r['proporcao_urbanizada'] > .5 else ('Misto' if r['proporcao_urbanizada'] >= .1 else 'Rural')
    assert r['localizacao'] == expected
for level, count in [('municipios',645),('imediatas',53),('intermediarias',11),('administrativas',16),('zee',9)]:
    units = data['recortes'][level]
    ids = {u['id'] for u in units}
    assert len(units) == len(ids) == count
    assert sum(u['populacao'] for u in units) == 44411238
    assert math.isclose(sum(u['area'] for u in units),248219.48,abs_tol=1e-6)
    assert all(r[level] in ids for r in roads)
    # A conciliação deve persistir também dentro dos filtros, não só no total.
    for field in ['administracao','tipo','pista','localizacao']:
        for value in {r[field] for r in roads}:
            subset = [r for r in roads if r[field] == value]
            territorial = sum(sum(r['extensao'] for r in subset if r[level] == code) for code in ids)
            assert math.isclose(territorial,sum(r['extensao'] for r in subset),abs_tol=1e-6)
    geo = json.loads((SITE / f'assets/data/{level}.geojson').read_text(encoding='utf-8'))
    assert {f['properties']['id'] for f in geo['features']} == ids
georoads = json.loads((SITE / 'assets/data/malha.geojson').read_text(encoding='utf-8'))
assert {f['properties']['id'] for f in georoads['features']} == {r['id'] for r in roads}
emoji = re.compile('[\U0001F000-\U0001FAFF\u2600-\u27BF\uFE0F\u20E3]')
for p in list(SITE.rglob('*.html'))+list((SITE/'assets/js').glob('*.js')):
    assert not emoji.search(p.read_text(encoding='utf-8')), f'Emoji em {p}'
print('PASS: fontes, 5 recortes, filtros, urbanização, geometrias de exibição e ausência de emojis.')
