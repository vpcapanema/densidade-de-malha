"""Auditoria reproduzível e extratos estáticos do cadastro rodoviário.

Executar da raiz: python scripts/auditar_e_construir_dashboard.py
Requer geopandas. Não usa comprimentos de geometrias simplificadas nos indicadores.
"""
from pathlib import Path
import gzip
import hashlib
import json
import re
import unicodedata
from datetime import datetime, timezone
import geopandas as gpd
import pandas as pd
from shapely import make_valid

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'relatorio/assets/data'
OUT.mkdir(parents=True, exist_ok=True)


def norm(value):
    return ''.join(c for c in unicodedata.normalize('NFKD', str(value).upper())
                   if not unicodedata.combining(c) and c.isalnum())


def write(name, data):
    (OUT / name).write_text(json.dumps(data, ensure_ascii=False, separators=(',', ':'),
                                     allow_nan=False), encoding='utf-8')


def build():
    with gzip.open(ROOT / 'fontes/indicadores-legados.json.gz', 'rt', encoding='utf-8') as f:
        old = json.load(f)
    population = json.loads((ROOT / 'fontes/populacao-censo2022-sidra.json').read_bytes())
    pop = {p['D1C']: int(p['V']) for p in population[1:]}
    assert len(pop) == 645 and sum(pop.values()) == 44411238
    boundaries = {k: gpd.GeoDataFrame.from_features(v, crs=4326).to_crs(5880)
                  for k, v in old.items()}
    mun = boundaries['municipios']
    assert len(mun) == 645 and mun.CD_MUN.is_unique
    assert all(code in pop for code in mun.CD_MUN)
    # A associação por nome usa uma única equivalência ortográfica comprovada
    # pelo cadastro DER e pelo nome/código municipal IBGE.
    aliases = {'SAOLUISDOPARAITINGA': 'SAOLUIZDOPARAITINGA'}
    mun_index = {norm(r.NM_MUN): str(r.CD_MUN) for _, r in mun.iterrows()}
    assignments = {}
    overlap_audit = []
    for _, row in mun.iterrows():
        code = str(row.CD_MUN)
        assignments[code] = {'municipios': code, 'imediatas': str(row.CD_RGI),
                             'intermediarias': str(row.CD_RGINT)}
    for level in ['administrativas', 'zee']:
        regions = boundaries[level]
        regions['dashboard_id'] = [f'{level}-{i+1:02}' for i in range(len(regions))]
        for _, row in mun.iterrows():
            polygon = make_valid(row.geometry)
            overlaps = regions.geometry.intersection(polygon).area
            idx = overlaps.idxmax()
            share = float(overlaps.loc[idx] / polygon.area)
            assert share > .5, f'Associação territorial ambígua: {row.NM_MUN}'
            assignments[str(row.CD_MUN)][level] = regions.loc[idx, 'dashboard_id']
            overlap_audit.append({'municipio': row.NM_MUN, 'codigo': str(row.CD_MUN),
                                  'recorte': level, 'proporcao_area': round(share, 6)})
    zip_path = ROOT / 'dados/Sistema Rodoviário Estadual.zip'
    roads = gpd.read_file('zip://' + str(zip_path))
    assert roads.Subtrecho.is_unique and roads.Subtrecho.notna().all()
    assert roads.Extensao.notna().all() and (roads.Extensao >= 0).all()
    assert roads.geometry.notna().all() and (~roads.geometry.is_empty).all()
    assert roads.geometry.is_valid.all()
    urban_file = next((ROOT / 'dados/entrada/ibge_areas_urbanizadas_2019').glob('*.shp'))
    urban = gpd.read_file(urban_file, bbox=(-53.2, -25.4, -44.1, -19.7))
    urban = urban[urban.Tipo == 'Área urbanizada'].to_crs(5880)
    urban.geometry = urban.geometry.make_valid()
    spatial_index = urban.sindex
    road_geometry = roads.to_crs(5880).geometry
    ratios = []
    for geometry in road_geometry:
        candidates = spatial_index.query(geometry, predicate='intersects')
        if len(candidates):
            covered = geometry.intersection(urban.iloc[candidates].geometry.union_all()).length
            ratio = float(covered / geometry.length)
        else:
            ratio = 0.0
        assert -.000001 <= ratio <= 1.000001
        ratios.append(max(0, min(1, ratio)))
    records = []
    for (_, r), ratio in zip(roads.iterrows(), ratios):
        key = aliases.get(norm(r.Municipio), norm(r.Municipio))
        assert key in mun_index, f'Município sem correspondência: {r.Municipio}'
        code = mun_index[key]
        kind = re.match(r'^(SPI|SPA|SP|BR)', str(r.Rodovia).strip())
        records.append({'id': str(r.Subtrecho), 'rodovia': str(r.Rodovia),
                        'municipio': code, 'extensao': float(r.Extensao),
                        'tipo': kind[1] if kind else 'Outros',
                        'administracao': str(r.Administra), 'pista': str(r.TipoPista),
                        'perimetro': 'Sim' if r.PerimetroU == 'Sim' else 'Não',
                        'jurisdicao': str(r.Jurisdicao), 'proporcao_urbanizada': ratio,
                        'urbano_estimado_km': float(r.Extensao) * ratio,
                        'localizacao': 'Urbano' if ratio > .5 else ('Misto' if ratio >= .1 else 'Rural'),
                        **assignments[code]})
    levels = {}
    for level, geo in boundaries.items():
        features = []
        units = []
        for i, r in geo.iterrows():
            if level == 'municipios':
                code, name = str(r.CD_MUN), r.NM_MUN
            elif level == 'imediatas':
                code, name = str(r.CD_RGI), r.NM_RGI
            elif level == 'intermediarias':
                code, name = str(r.CD_RGINT), r.NM_RGINT
            else:
                code, name = r.dashboard_id, r.Nome
            codes = [c for c, a in assignments.items() if a[level] == code]
            assert codes, f'Recorte sem municípios: {code}'
            area = float(mun[mun.CD_MUN.isin(codes)].Area_km2.sum())
            units.append({'id': code, 'nome': name, 'area': area,
                          'populacao': sum(pop[c] for c in codes), 'municipios': len(codes)})
        # Simplificação exclusivamente visual, em metros; preserva topologia de cada polígono.
        visual = geo.copy()
        visual.geometry = visual.geometry.make_valid().simplify(80, preserve_topology=True)
        visual = visual.to_crs(4326)
        for (_, r), u in zip(visual.iterrows(), units):
            features.append({'type': 'Feature', 'properties': {'id': u['id'], 'nome': u['nome']},
                             'geometry': r.geometry.__geo_interface__})
        write(f'{level}.geojson', {'type': 'FeatureCollection', 'features': features})
        levels[level] = units
        assert sum(u['populacao'] for u in units) == sum(pop.values())
        assert abs(sum(u['area'] for u in units) - mun.Area_km2.sum()) < 1e-6
        assert len({u['id'] for u in units}) == len(units)
    road_visual = roads.to_crs(5880).geometry.simplify(12, preserve_topology=True).to_crs(4326)
    write('malha.geojson', {'type': 'FeatureCollection', 'features': [
        {'type': 'Feature', 'properties': {'id': r['id']}, 'geometry': g.__geo_interface__}
        for r, g in zip(records, road_visual)]})
    total = sum(r['extensao'] for r in records)
    for level, units in levels.items():
        ids = {u['id'] for u in units}
        assert all(r[level] in ids for r in records)
        assert abs(sum(sum(r['extensao'] for r in records if r[level] == u['id'])
                       for u in units) - total) < 1e-7
    # Conferência das afirmações antigas contra os próprios valores dos mapas.
    legacy = pd.DataFrame([f['properties'] for f in old['municipios']['features']])
    bins = [0, 20, 40, 60, 80, 100, float('inf')]
    actual_bins = pd.cut(legacy.Ext_Total, bins, right=False).value_counts(sort=False).tolist()
    audit = {'data': datetime.now(timezone.utc).isoformat(),
             'legado': {'extensao_municipal_km': float(legacy.Ext_Total.sum()),
                        'populacao_rotulada_2022': int(legacy.Populacao.sum()),
                        'populacao_censo2022_confirmada': sum(pop.values()),
                        'concessionada_km': float(legacy.Ext_Concessionada.sum()),
                        'grafico_concessao_publicado_km': [6847, 15267],
                        'histograma_publicado': [285, 168, 92, 48, 27, 25],
                        'histograma_recalculado': actual_bins,
                        'densidade_pop_escala_real': 1000, 'densidade_pop_rotulo': 10000,
                        'extensao_ra_geometrica_km': sum(f['properties']['Ext_Total'] for f in old['administrativas']['features'])},
             'cadastro_atual': {'arquivo': str(zip_path.relative_to(ROOT)),
                                'sha256': hashlib.sha256(zip_path.read_bytes()).hexdigest(),
                                'registros': len(records), 'extensao_km': total,
                                'data_maxima_atualizacao_registro': str(roads.DataAtuali.max().date()),
                                'duplicatas_subtrecho': int(roads.Subtrecho.duplicated().sum()),
                                'geometrias_invalidas': int((~roads.geometry.is_valid).sum()),
                                'extensao_zero': int((roads.Extensao == 0).sum()),
                                'soma_comprimento_geometrico_km': float(roads.to_crs(5880).length.sum()/1000),
                                'registros_sobreposicao_declarada': int(roads.Sobreposic.notna().sum())},
             'urbanizacao': {'fonte': 'Áreas Urbanizadas do Brasil 2019, IBGE',
                              'sha256_shp': hashlib.sha256(urban_file.read_bytes()).hexdigest(),
                              'poligonos_bbox_tipo_area_urbanizada': len(urban),
                              'criterio': 'Tipo = Área urbanizada; exclui loteamentos vazios, equipamentos e vazios intraurbanos',
                              'extensao_urbanizada_estimada_km': sum(r['urbano_estimado_km'] for r in records),
                              'extensao_por_classe_km': {c: sum(r['extensao'] for r in records if r['localizacao'] == c)
                                                         for c in ['Urbano', 'Misto', 'Rural']}},
             'associacao_territorial': {'metodo': 'Maior área de interseção municipal com RA/ZEE; RGI/RGINT por código IBGE',
                                       'min_proporcao': min(a['proporcao_area'] for a in overlap_audit),
                                       'abaixo_99_porcento': [a for a in overlap_audit if a['proporcao_area'] < .99]},
             'normalizacao_municipal': {'São Luís do Paraitinga (DER)': 'São Luiz do Paraitinga, 3550001 (IBGE)'},
             'checagens': ['645 códigos populacionais únicos', 'IDs de subtrecho únicos',
                          'Nenhuma extensão ausente ou negativa', 'Geometrias válidas',
                          'Nenhum trecho sem município', 'Mesma extensão nos cinco recortes',
                          'Mesma população e área nos cinco recortes', 'Simplificação não altera métricas']}
    metadata = {'titulo': 'Cadastro rodoviário DER/SP e indicadores territoriais',
                'populacao': {'ano': 2022, 'fonte': 'IBGE/SIDRA, tabela 4714, variável 93',
                             'url': 'https://sidra.ibge.gov.br/tabela/4714'},
                'malha': {'fonte': 'Sistema Rodoviário Estadual.zip fornecido no repositório',
                          'data_maxima_registro': audit['cadastro_atual']['data_maxima_atualizacao_registro']},
                'area': 'Área municipal IBGE 2024 preservada na base original; soma dos municípios em todos os recortes',
                'recortes': 'Limites IBGE e RA/ZEE recuperados dos mapas originais; associação RA/ZEE por maior interseção municipal',
                'universo': 'Registros cadastrais, incluindo PLAN; não equivale a quilômetros de pista em operação nem a comprimento geométrico único',
                'localizacao': 'Proporção geométrica dentro de feições Tipo = Área urbanizada, IBGE 2019. Urbano >50%; Misto 10–50%; Rural <10%. Limiares analíticos deste estudo, não norma IBGE. PerimetroU DER é informação independente.',
                'atualizado': audit['data']}
    write('indicadores.json', {'metadata': metadata, 'recortes': levels, 'trechos': records})
    write('auditoria.json', audit)
    print(json.dumps({'trechos': len(records), 'extensao_km': total, 'populacao': sum(pop.values()),
                      'min_intersecao': audit['associacao_territorial']['min_proporcao'],
                      'histograma_legado': actual_bins}, ensure_ascii=True))


if __name__ == '__main__':
    build()
