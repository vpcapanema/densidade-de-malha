# -*- coding: utf-8 -*-
"""Exportar camadas para QGIS (Shapefile)

Gera uma pasta com shapefiles e um ZIP com os arquivos necessários para reproduzir
no QGIS os mapas/gráficos do relatório (a partir das camadas já consolidadas).

Camadas exportadas:
- Municípios com indicadores (densidade_malha.gpkg / layer=municipios)
- RG Imediatas (densidade_malha.gpkg / layer=rg_imediatas)
- RG Intermediárias (densidade_malha.gpkg / layer=rg_intermediarias)
- Malha DER classificada (malha_der_classificada.gpkg / layer=malha_der_classificada)

Saída:
- dados/saida/qgis_export_shp/<camada>/*.{shp,shx,dbf,prj,cpg}
- dados/saida/qgis_export_shp.zip

Uso:
  "D:/densidade _de_malha/.venv/Scripts/python.exe" scripts/exportar_shapefiles_qgis.py
"""

from __future__ import annotations

from pathlib import Path
import zipfile

import geopandas as gpd
import pandas as pd


BASE_DIR = Path(__file__).resolve().parents[1]
DADOS_SAIDA = BASE_DIR / "dados" / "saida"

GPKG_DENS = DADOS_SAIDA / "densidade_malha.gpkg"
GPKG_MALHA = DADOS_SAIDA / "malha_der_classificada.gpkg"

OUT_DIR = DADOS_SAIDA / "qgis_export_shp"
OUT_ZIP = DADOS_SAIDA / "qgis_export_shp.zip"


def _read_layer(gpkg: Path, layer: str) -> gpd.GeoDataFrame:
    if not gpkg.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {gpkg}")
    return gpd.read_file(gpkg, layer=layer)


def _ensure_crs(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    # Para QGIS, tanto faz, mas garantir CRS definido ajuda.
    if gdf.crs is None:
        # Não chutar CRS; manter sem alteração.
        return gdf
    return gdf


def _write_shp(gdf: gpd.GeoDataFrame, out_base: Path) -> None:
    out_base.parent.mkdir(parents=True, exist_ok=True)

    # Shapefile limita nomes de campos; manter o que já estiver no GPKG.
    # Garantir tipos básicos para evitar warnings no driver.
    gdf2 = gdf.copy()
    for col in gdf2.columns:
        if col == "geometry":
            continue
        if pd.api.types.is_bool_dtype(gdf2[col]):
            gdf2[col] = gdf2[col].astype(int)

    gdf2 = _ensure_crs(gdf2)

    # Para nomes acentuados em DBF
    gdf2.to_file(out_base.with_suffix(".shp"), driver="ESRI Shapefile", encoding="UTF-8")


def _zip_folder(folder: Path, zip_path: Path) -> None:
    if zip_path.exists():
        zip_path.unlink()

    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in folder.rglob("*"):
            if path.is_file():
                zf.write(path, arcname=path.relative_to(folder))


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    exports = [
        (GPKG_DENS, "municipios", OUT_DIR / "densidade_municipios" / "densidade_municipios"),
        (GPKG_DENS, "rg_imediatas", OUT_DIR / "densidade_rg_imediatas" / "densidade_rg_imediatas"),
        (GPKG_DENS, "rg_intermediarias", OUT_DIR / "densidade_rg_intermediarias" / "densidade_rg_intermediarias"),
        (GPKG_MALHA, "malha_der_classificada", OUT_DIR / "malha_der_classificada" / "malha_der_classificada"),
    ]

    for gpkg, layer, out_base in exports:
        print(f"Exportando {layer} -> {out_base.parent} ...")
        gdf = _read_layer(gpkg, layer)
        _write_shp(gdf, out_base)

    _zip_folder(OUT_DIR, OUT_ZIP)

    print("OK")
    print(f"Pasta: {OUT_DIR}")
    print(f"ZIP:   {OUT_ZIP}")


if __name__ == "__main__":
    main()
