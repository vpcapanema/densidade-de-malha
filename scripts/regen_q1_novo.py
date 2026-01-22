#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Regenerar mapas Q1 com legendas customizadas e malha viária"""

import sys
import importlib.util

# Importar módulo 07_mapas_completos.py dinamicamente
spec = importlib.util.spec_from_file_location(
    "mapas",
    r"d:\densidade _de_malha\scripts\07_mapas_completos.py"
)
mapas = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mapas)

import geopandas as gpd
from pathlib import Path

# Carregar dados
print("📂 Carregando dados...")
gpkg_path = Path(r"d:\densidade _de_malha\dados\saida\densidade_malha.gpkg")
municipios = gpd.read_file(gpkg_path, layer='municipios').to_crs('EPSG:4326')
print(f"   ✓ {len(municipios)} municípios carregados")

# Carregar malha viária
malha = mapas.carregar_malha_viaria()
if malha is not None:
    print(f"   ✓ Malha viária carregada ({len(malha)} segmentos)")
else:
    print("   ⚠️ Malha viária não encontrada")

# Gerar mapas Q1
print("\n🗺️ Gerando mapas Q1...")

# Mapa 1: Extensão
print("   1. Extensão por município...")
mapas.criar_mapa_coropletico(
    gdf=municipios,
    col_valor='Ext_Total',
    col_nome='NM_MUN',
    titulo='Extensão Total de Rodovias',
    subtitulo='Quilômetros de malha viária por município',
    output_name='mapa_q1_extensao_mun',
    malha=malha,
    colormap_cores=['#f5f3ff', '#c4b5fd', '#7c3aed', '#3b0764'],
    caption='Extensão (km)'
)

# Mapa 2: Densidade
print("   2. Densidade por área...")
mapas.criar_mapa_coropletico(
    gdf=municipios,
    col_valor='Dens_Area_Total',
    col_nome='NM_MUN',
    titulo='Densidade por Área',
    subtitulo='km de rodovia / km² de território',
    output_name='mapa_q1_densidade_area_mun',
    malha=malha,
    colormap_cores=['#f7fbff', '#6baed6', '#2171b5', '#08306b'],
    caption='Densidade (km/10000km²)'
)

print("\n✅ Mapas Q1 regenerados com sucesso!")
