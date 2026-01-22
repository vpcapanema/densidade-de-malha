# -*- coding: utf-8 -*-
"""Regenerar apenas mapas Q1 com correções"""
import sys
sys.path.insert(0, r"d:\densidade _de_malha\scripts")
from importlib import reload
import geopandas as gpd
from pathlib import Path

# Carregar dados
gpkg_path = Path(r"d:\densidade _de_malha\dados\saida\densidade_malha.gpkg")
municipios = gpd.read_file(gpkg_path, layer='municipios').to_crs('EPSG:4326')

# Carregar malha
malha_gpkg = Path(r"d:\densidade _de_malha\dados\saida\malha_der_classificada.gpkg")
malha = gpd.read_file(malha_gpkg, layer='malha_der_classificada').to_crs('EPSG:4326')

# Importar funções
import importlib.util
spec = importlib.util.spec_from_file_location("mapas", r"d:\densidade _de_malha\scripts\07_mapas_completos.py")
mapas = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mapas)

# Gerar apenas Q1 COM malha viária
print("\n🗺️ Regenerando mapas Q1...")
mapas.criar_mapa_coropletico(
    municipios, 'Ext_Total', 'NM_MUN',
    'Extensão Total de Rodovias', 'Quilômetros de malha viária por município',
    'mapa_q1_extensao_mun',
    malha=malha,  # Incluir malha viária
    colormap_cores=['#f5f3ff', '#c4b5fd', '#7c3aed', '#3b0764'],
    caption='Extensão (km)'
)

mapas.criar_mapa_coropletico(
    municipios, 'Dens_Area_Total', 'NM_MUN',
    'Densidade por Área', 'km de rodovia / 10.000 km² de território',
    'mapa_q1_densidade_area_mun',
    malha=malha,  # Incluir malha viária
    colormap_cores=['#f7fbff', '#6baed6', '#2171b5', '#08306b'],
    caption='Densidade (km/10000km²)'
)
print("\n✅ Mapas Q1 regenerados!")
