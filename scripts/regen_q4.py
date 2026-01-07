#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Regenerar apenas o mapa da Q4 (Acessibilidade).

Uso:
  .venv\\Scripts\\python.exe scripts\\regen_q4.py

Gera/atualiza:
  relatorio/mapas/mapa_q4_acessibilidade_mun.html
  relatorio/mapas/mapa_q4_pop_por_km_mun.html
"""

import importlib.util
from pathlib import Path

import geopandas as gpd

BASE_DIR = Path(r"d:\densidade _de_malha")

# Importar módulo 07_mapas_completos.py dinamicamente
spec = importlib.util.spec_from_file_location(
    "mapas",
    str(BASE_DIR / "scripts" / "07_mapas_completos.py"),
)
mapas = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(mapas)


def main() -> None:
    gpkg_path = BASE_DIR / "dados" / "saida" / "densidade_malha.gpkg"
    municipios = gpd.read_file(gpkg_path, layer="municipios").to_crs("EPSG:4326")

    malha = mapas.carregar_malha_viaria()

    print("\n🗺️ Regenerando mapa Q4 (Acessibilidade)...")
    mapas.gerar_mapas_acessibilidade(municipios, malha)
    print("\n✅ Mapa Q4 regenerado!")


if __name__ == "__main__":
    main()
