"""Baixa somente as fontes públicas IBGE necessárias para reproduzir a revisão."""
from pathlib import Path
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
BASE = 'https://geoftp.ibge.gov.br/organizacao_do_territorio/tipologias_do_territorio/areas_urbanizadas_do_brasil/2019/Shapefile/AreasUrbanizadas2019_Brasil/'
OUT = ROOT / 'dados/entrada/ibge_areas_urbanizadas_2019'
OUT.mkdir(parents=True, exist_ok=True)
for ext in ['shp', 'shx', 'dbf', 'prj', 'cpg']:
    name = 'AU_2022_AreasUrbanizadas2019_Brasil.' + ext
    if not (OUT / name).exists():
        with urlopen(BASE + name, timeout=90) as response:
            (OUT / name).write_bytes(response.read())
        print('Baixado:', name)
population = ROOT / 'fontes/populacao-censo2022-sidra.json'
if not population.exists():
    with urlopen('https://apisidra.ibge.gov.br/values/t/4714/n6/in%20n3%2035/v/93/p/2022', timeout=60) as response:
        population.write_bytes(response.read())
print('Fontes disponíveis. O ZIP rodoviário deve ser o insumo fornecido no repositório.')
