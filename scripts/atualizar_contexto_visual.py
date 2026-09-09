"""Alinha a introdução e o glossário; remove pictogramas Unicode do site."""
from pathlib import Path
import re
import json
from bs4 import BeautifulSoup
import geopandas as gpd

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / 'relatorio'
EMOJI = re.compile('[\U0001F000-\U0001FAFF\u2600-\u27BF\uFE0F\u200D\u20E3\u2B05-\u2B07\u2B1B-\u2B1C\u2B50\u2B55]')
for p in list(SITE.glob('*.html')) + list((SITE/'assets/js').glob('*.js')):
    s = p.read_text(encoding='utf-8')
    p.write_text(EMOJI.sub('', s), encoding='utf-8')
p = SITE/'assets/js/cabecalho-componente.js'
s = p.read_text(encoding='utf-8').replace('Revis?o:', 'Revisão:').replace('Malha vi?ria', 'Malha viária')
s = s.replace('Escala municipal · SP', 'São Paulo').replace('Mapa original do estudo: extensão total de rodovias por município, com escala de cores e valores.', 'Rede do cadastro DER/SP: SP, SPA, SPI e BR; linhas coloridas por tipo de rodovia.')
p.write_text(s, encoding='utf-8')
p = SITE/'index.html'
doc = BeautifulSoup(p.read_text(encoding='utf-8'), 'html.parser')
doc.select_one('.hero .badge').string = 'Análise geoespacial · revisão 2026'
for e,v in zip(doc.select('.stat-label'), ['km cadastrais (inclui PLAN)', 'Municípios analisados', 'Registros de subtrecho', 'Habitantes · Censo 2022']):
    e.string = v
for para in doc.find_all('p'):
    text = para.get_text(' ', strip=True)
    if text.startswith('O Estado de São Paulo possui'):
        para.string = 'O estudo descreve a distribuição da malha constante no cadastro DER/SP e sua relação com a área e a população dos territórios. Esses indicadores ajudam a investigar diferenças espaciais; não medem, sozinhos, eficiência, capacidade ou qualidade do acesso.'
    elif text.startswith('Este estudo analisa a rede rodoviária'):
        para.string = 'Este estudo analisa os registros do Sistema Rodoviário Estadual presentes no arquivo fornecido, incluindo:'
    elif 'Este estudo não considera rodovias municipais' in text:
        para.string = 'Universo cadastral: inclui administrações Concessionária, DER, DNIT e Prefeitura e registros PLAN (planejados). A extensão não representa malha física única nem somente vias em operação. Consulte os filtros e a metodologia.'
    elif text.startswith('A análise contempla diferentes recortes'):
        para.string = 'A análise contempla municípios, Regiões Geográficas Imediatas e Intermediárias, Regiões Administrativas e grupos ZEE. Todos os recortes usam a mesma base cadastral e denominadores populacionais oficiais.'
    elif text.startswith('Comparar extens?o'):
        para.string = 'Comparar extensão por população, reconhecendo que acessibilidade exige também informações de tempo de viagem e conectividade.'
    elif 'Identificar áreas com baixa densidade de malha para priorização' in text:
        para.string = 'Identificar diferenças territoriais para investigação, sem transformar densidade isolada em prioridade automática de obras.'
p.write_text(str(doc), encoding='utf-8')
p.write_text(p.read_text(encoding='utf-8').replace('Trechos de rodovias federais delegados ao estado (BR)', 'Registros com código BR, conforme a jurisdição e administração cadastrais').replace('Números da malha rodoviária estadual', 'Números dos registros do cadastro rodoviário'), encoding='utf-8')
p = SITE/'objetivos.html'
s = p.read_text(encoding='utf-8').replace('não concessionadas (administradas diretamente pelo DER/SP)', 'demais administrações (DER, DNIT e Prefeitura)').replace('metodologia baseada em boas práticas do IBGE', 'limiares analíticos do estudo, explicitados na metodologia').replace('exporta??o', 'exportação')
p.write_text(s, encoding='utf-8')
p = SITE/'glossario.html'
s = p.read_text(encoding='utf-8').replace('O recorte apresentado não inclui as rodovias municipais.', 'O universo é o cadastro DER/SP fornecido, incluindo diferentes jurisdições, administrações e registros planejados.').replace('Neste estudo, a unidade ? km/km?.', 'Neste estudo, a unidade é km/km².').replace('com o fator de escala indicado no estudo.', 'multiplicada por 10.000; unidade km/10.000 habitantes.').replace('Distinção espacial empregada para analisar a distribuição dos trechos em contextos urbanos e rurais.', 'Classe analítica segundo a proporção geométrica dentro das áreas urbanizadas IBGE 2019: Urbano >50%, Misto 10–50%, Rural <10%. Não equivale ao campo PerimetroU do DER.')
p.write_text(s, encoding='utf-8')
# Prévia geográfica verdadeira para a home, sem valores do relatório anterior.
geo = gpd.read_file(SITE/'assets/data/municipios.geojson').to_crs(5880)
roads = gpd.read_file(SITE/'assets/data/malha.geojson').to_crs(5880)
data = json.loads((SITE/'assets/data/indicadores.json').read_text(encoding='utf-8'))
types = {r['id']: r['tipo'] for r in data['trechos']}
colors = {'SP':'#ba483c','SPA':'#bd731e','SPI':'#6d5ca0','BR':'#236ba0','Outros':'#56666a'}
left,bottom,right,top=geo.total_bounds
scale = min(750/(right-left),450/(top-bottom))
def coords(points):
    return ' '.join(f'{(x-left)*scale+25:.1f},{(top-y)*scale+25:.1f}' for x,y,*_ in points)
parts=['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 560"><title>Malha cadastral DER/SP por tipo de rodovia</title><rect width="800" height="560" fill="#fff"/>']
for geometry in geo.geometry:
    for poly in (geometry.geoms if geometry.geom_type=='MultiPolygon' else [geometry]):
        parts.append(f'<polygon points="{coords(poly.exterior.coords)}" fill="#edf2eb" stroke="#cad9cb" stroke-width=".3"/>')
for _,row in roads.iterrows():
    for line in (row.geometry.geoms if row.geometry.geom_type=='MultiLineString' else [row.geometry]):
        parts.append(f'<polyline points="{coords(line.coords)}" fill="none" stroke="{colors[types[row.id]]}" stroke-width=".7"/>')
parts.append('<text x="25" y="508" font-family="sans-serif" font-size="14" fill="#304f42">Linhas: tipo de rodovia (categoria, sem unidade)</text>')
for i,(name,color) in enumerate(colors.items()):
    x=25+i*140
    parts.append(f'<path d="M{x},533 h25" stroke="{color}" stroke-width="3"/><text x="{x+32}" y="538" font-family="sans-serif" font-size="13" fill="#304f42">{name}</text>')
parts.append('</svg>')
(SITE/'assets/images').mkdir(exist_ok=True)
(SITE/'assets/images/malha-sp.svg').write_text(''.join(parts), encoding='utf-8')
print('Contexto, emojis e mapa da home atualizados.')
