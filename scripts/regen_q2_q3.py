#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Regenerar mapas Q2 e Q3 com malha viária funcional"""

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

# Gerar mapas Q2 e Q3
print("\n🗺️ Regenerando Q2 e Q3...")
mapas.gerar_mapas_concessao(municipios, malha)
mapas.gerar_mapas_urbano_rural(municipios, malha)

print("\n✅ Mapas Q2 e Q3 regenerados com sucesso!")
