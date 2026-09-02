"""
Script para Geração de Mapas Interativos
=========================================

Gera mapas temáticos interativos usando Folium a partir dos shapefiles
processados, para inclusão no relatório HTML.

Autor: [Seu Nome]
Data: Dezembro/2025
"""

import os
import sys
from pathlib import Path

import folium
from basemap_openfreemap import OpenFreeMapLayer
from folium import plugins
import geopandas as gpd
import pandas as pd
import numpy as np
import branca.colormap as cm

# Configurações
BASE_DIR = Path(r"d:\densidade _de_malha")
DADOS_SAIDA = BASE_DIR / "dados" / "saida"
RELATORIO_DIR = BASE_DIR / "relatorio" / "mapas"
RELATORIO_DIR.mkdir(parents=True, exist_ok=True)

# Centro de SP
SP_CENTER = [-22.5, -48.5]
SP_ZOOM = 7

def carregar_dados():
    """Carrega os dados processados."""
    print("📂 Carregando dados...")
    
    gpkg_path = DADOS_SAIDA / "densidade_malha.gpkg"
    
    municipios = gpd.read_file(gpkg_path, layer='municipios')
    rg_imediatas = gpd.read_file(gpkg_path, layer='rg_imediatas')
    rg_intermediarias = gpd.read_file(gpkg_path, layer='rg_intermediarias')
    
    # Converter para WGS84 (necessário para Folium)
    municipios = municipios.to_crs('EPSG:4326')
    rg_imediatas = rg_imediatas.to_crs('EPSG:4326')
    rg_intermediarias = rg_intermediarias.to_crs('EPSG:4326')
    
    print(f"   Municípios: {len(municipios)}")
    print(f"   RG Imediatas: {len(rg_imediatas)}")
    print(f"   RG Intermediárias: {len(rg_intermediarias)}")
    
    return municipios, rg_imediatas, rg_intermediarias

def criar_mapa_densidade_area(gdf: gpd.GeoDataFrame, col_nome: str, titulo: str, output_name: str):
    """Cria mapa coroplético de densidade por área."""
    print(f"   Gerando mapa: {titulo}...")
    
    # Preparar dados
    gdf = gdf.copy()
    col_dens = 'Dens_Area_Total'
    
    if col_dens not in gdf.columns:
        print(f"      ⚠️ Coluna {col_dens} não encontrada!")
        return
    
    # Substituir NaN e Inf por 0
    gdf[col_dens] = gdf[col_dens].replace([np.inf, -np.inf], np.nan).fillna(0)
    
    # Criar mapa base
    m = folium.Map(
        location=SP_CENTER,
        zoom_start=SP_ZOOM,
        tiles=None
    )
    
    # Adicionar camadas base
    OpenFreeMapLayer('positron', name='Claro').add_to(m)
    OpenFreeMapLayer('dark', name='Escuro', show=False).add_to(m)
    
    # Colormap
    vmin = gdf[col_dens].quantile(0.05)
    vmax = gdf[col_dens].quantile(0.95)
    
    colormap = cm.LinearColormap(
        colors=['#f7fbff', '#6baed6', '#2171b5', '#08306b'],
        vmin=vmin,
        vmax=vmax,
        caption='Densidade (km/km²)'
    )
    
    # Estilo
    def style_function(feature):
        valor = feature['properties'].get(col_dens, 0)
        if valor is None or pd.isna(valor):
            valor = 0
        return {
            'fillColor': colormap(valor) if valor > 0 else '#ffffff',
            'color': '#333333',
            'weight': 0.5,
            'fillOpacity': 0.7
        }
    
    # Highlight
    def highlight_function(feature):
        return {
            'weight': 2,
            'color': '#ff6b6b',
            'fillOpacity': 0.9
        }
    
    # Tooltip
    tooltip = folium.GeoJsonTooltip(
        fields=[col_nome, col_dens, 'Ext_Total'],
        aliases=['Nome:', 'Densidade (km/km²):', 'Extensão Total (km):'],
        localize=True,
        sticky=True
    )
    
    # Adicionar camada
    folium.GeoJson(
        gdf,
        name=titulo,
        style_function=style_function,
        highlight_function=highlight_function,
        tooltip=tooltip
    ).add_to(m)
    
    # Adicionar colormap
    colormap.add_to(m)
    
    # Controle de camadas
    folium.LayerControl().add_to(m)
    
    # Título
    title_html = f'''
        <style>
            .map-title-box {{
                position: fixed; top: 80px; left: 50px; z-index: 1000;
                background: white; padding: 10px 20px; border-radius: 8px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.2); font-family: Arial;
                transition: all 0.3s ease;
            }}
            .map-title-box h4 {{ margin: 0; color: #1a5276; }}
            .map-title-box p {{ margin: 5px 0 0; font-size: 12px; color: #666; }}
            .leaflet-control-layers {{ background: white !important; }}
            .leaflet-bar a {{ color: #333 !important; }}
            /* Estilo para tooltips */
            .leaflet-tooltip {{ 
                background: white !important; 
                color: #333 !important;
                border: 1px solid #ccc !important;
            }}
            .leaflet-tooltip-left:before {{ border-left-color: white !important; }}
            .leaflet-tooltip-right:before {{ border-right-color: white !important; }}
            /* Legend colormap */
            .legend {{ background: white !important; padding: 10px !important; border-radius: 8px !important; }}
        </style>
        <div class="map-title-box">
            <h4>{titulo}</h4>
            <p>Densidade por Área (km de rodovia / km²)</p>
        </div>
    '''
    m.get_root().html.add_child(folium.Element(title_html))
    
    # Salvar
    output_path = RELATORIO_DIR / f"{output_name}.html"
    m.save(str(output_path))
    print(f"      ✓ Salvo: {output_path}")

def criar_mapa_extensao(gdf: gpd.GeoDataFrame, col_nome: str, titulo: str, output_name: str):
    """Cria mapa coroplético de extensão total."""
    print(f"   Gerando mapa: {titulo}...")
    
    gdf = gdf.copy()
    col_ext = 'Ext_Total'
    
    if col_ext not in gdf.columns:
        print(f"      ⚠️ Coluna {col_ext} não encontrada!")
        return
    
    gdf[col_ext] = gdf[col_ext].fillna(0)
    
    # Criar mapa
    m = folium.Map(location=SP_CENTER, zoom_start=SP_ZOOM, tiles=None)
    OpenFreeMapLayer('positron', name='Claro').add_to(m)
    OpenFreeMapLayer('dark', name='Escuro', show=False).add_to(m)
    
    # Colormap
    vmax = gdf[col_ext].quantile(0.95)
    colormap = cm.LinearColormap(
        colors=['#fff5f0', '#fb6a4a', '#cb181d', '#67000d'],
        vmin=0,
        vmax=vmax,
        caption='Extensão (km)'
    )
    
    def style_function(feature):
        valor = feature['properties'].get(col_ext, 0) or 0
        return {
            'fillColor': colormap(valor) if valor > 0 else '#ffffff',
            'color': '#333333',
            'weight': 0.5,
            'fillOpacity': 0.7
        }
    
    tooltip = folium.GeoJsonTooltip(
        fields=[col_nome, col_ext],
        aliases=['Nome:', 'Extensão (km):'],
        localize=True
    )
    
    folium.GeoJson(
        gdf,
        name=titulo,
        style_function=style_function,
        highlight_function=lambda x: {'weight': 2, 'color': '#ff6b6b'},
        tooltip=tooltip
    ).add_to(m)
    
    colormap.add_to(m)
    folium.LayerControl().add_to(m)
    
    # Título
    title_html = f'''
        <style>
            .map-title-box {{
                position: fixed; top: 80px; left: 50px; z-index: 1000;
                background: white; padding: 10px 20px; border-radius: 8px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.2); font-family: Arial;
            }}
            .map-title-box h4 {{ margin: 0; color: #c0392b; }}
            .map-title-box p {{ margin: 5px 0 0; font-size: 12px; color: #666; }}
            .leaflet-tooltip {{ background: white !important; color: #333 !important; border: 1px solid #ccc !important; }}
        </style>
        <div class="map-title-box">
            <h4>{titulo}</h4>
            <p>Extensão Total de Rodovias (km)</p>
        </div>
    '''
    m.get_root().html.add_child(folium.Element(title_html))
    
    output_path = RELATORIO_DIR / f"{output_name}.html"
    m.save(str(output_path))
    print(f"      ✓ Salvo: {output_path}")

def criar_mapa_concessao(gdf: gpd.GeoDataFrame, col_nome: str, titulo: str, output_name: str):
    """Cria mapa de proporção de rodovias concessionadas."""
    print(f"   Gerando mapa: {titulo}...")
    
    gdf = gdf.copy()
    
    # Calcular proporção de concessionadas
    if 'Ext_Concessionada' in gdf.columns and 'Ext_Total' in gdf.columns:
        gdf['Prop_Concessao'] = (gdf['Ext_Concessionada'] / gdf['Ext_Total'] * 100).fillna(0)
    else:
        print("      ⚠️ Colunas necessárias não encontradas!")
        return
    
    m = folium.Map(location=SP_CENTER, zoom_start=SP_ZOOM, tiles=None)
    OpenFreeMapLayer('positron', name='Claro').add_to(m)
    
    colormap = cm.LinearColormap(
        colors=['#27ae60', '#f1c40f', '#e74c3c'],
        vmin=0,
        vmax=100,
        caption='% Concessionada'
    )
    
    def style_function(feature):
        valor = feature['properties'].get('Prop_Concessao', 0) or 0
        return {
            'fillColor': colormap(valor),
            'color': '#333333',
            'weight': 0.5,
            'fillOpacity': 0.7
        }
    
    tooltip = folium.GeoJsonTooltip(
        fields=[col_nome, 'Prop_Concessao', 'Ext_Concessionada', 'Ext_Não_Concessionada'],
        aliases=['Nome:', '% Concessionada:', 'Ext. Concess. (km):', 'Ext. DER (km):'],
        localize=True
    )
    
    folium.GeoJson(
        gdf,
        name=titulo,
        style_function=style_function,
        highlight_function=lambda x: {'weight': 2, 'color': '#3498db'},
        tooltip=tooltip
    ).add_to(m)
    
    colormap.add_to(m)
    folium.LayerControl().add_to(m)
    
    title_html = f'''
        <style>
            .map-title-box {{
                position: fixed; top: 80px; left: 50px; z-index: 1000;
                background: white; padding: 10px 20px; border-radius: 8px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.2); font-family: Arial;
            }}
            .map-title-box h4 {{ margin: 0; color: #8e44ad; }}
            .map-title-box p {{ margin: 5px 0 0; font-size: 12px; color: #666; }}
            .leaflet-tooltip {{ background: white !important; color: #333 !important; border: 1px solid #ccc !important; }}
        </style>
        <div class="map-title-box">
            <h4>{titulo}</h4>
            <p>Percentual de Rodovias sob Concessão</p>
        </div>
    '''
    m.get_root().html.add_child(folium.Element(title_html))
    
    output_path = RELATORIO_DIR / f"{output_name}.html"
    m.save(str(output_path))
    print(f"      ✓ Salvo: {output_path}")

def criar_mapa_urbano_rural(gdf: gpd.GeoDataFrame, col_nome: str, titulo: str, output_name: str):
    """Cria mapa de proporção urbana."""
    print(f"   Gerando mapa: {titulo}...")
    
    gdf = gdf.copy()
    
    # Calcular proporção urbana
    if 'Ext_Urbano' in gdf.columns and 'Ext_Total' in gdf.columns:
        gdf['Prop_Urbano'] = (gdf['Ext_Urbano'] / gdf['Ext_Total'] * 100).fillna(0)
    else:
        print("      ⚠️ Colunas necessárias não encontradas!")
        return
    
    m = folium.Map(location=SP_CENTER, zoom_start=SP_ZOOM, tiles=None)
    OpenFreeMapLayer('positron', name='Claro').add_to(m)
    
    colormap = cm.LinearColormap(
        colors=['#27ae60', '#f1c40f', '#e74c3c', '#8e44ad'],
        vmin=0,
        vmax=50,
        caption='% em Área Urbana'
    )
    
    def style_function(feature):
        valor = feature['properties'].get('Prop_Urbano', 0) or 0
        return {
            'fillColor': colormap(min(valor, 50)),
            'color': '#333333',
            'weight': 0.5,
            'fillOpacity': 0.7
        }
    
    tooltip = folium.GeoJsonTooltip(
        fields=[col_nome, 'Prop_Urbano', 'Ext_Urbano', 'Ext_Misto', 'Ext_Rural'],
        aliases=['Nome:', '% Urbano:', 'Ext. Urbano (km):', 'Ext. Misto (km):', 'Ext. Rural (km):'],
        localize=True
    )
    
    folium.GeoJson(
        gdf,
        name=titulo,
        style_function=style_function,
        highlight_function=lambda x: {'weight': 2, 'color': '#3498db'},
        tooltip=tooltip
    ).add_to(m)
    
    colormap.add_to(m)
    folium.LayerControl().add_to(m)
    
    title_html = f'''
        <style>
            .map-title-box {{
                position: fixed; top: 80px; left: 50px; z-index: 1000;
                background: white; padding: 10px 20px; border-radius: 8px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.2); font-family: Arial;
            }}
            .map-title-box h4 {{ margin: 0; color: #e74c3c; }}
            .map-title-box p {{ margin: 5px 0 0; font-size: 12px; color: #666; }}
            .leaflet-tooltip {{ background: white !important; color: #333 !important; border: 1px solid #ccc !important; }}
        </style>
        <div class="map-title-box">
            <h4>{titulo}</h4>
            <p>Percentual em Área Urbana</p>
        </div>
    '''
    m.get_root().html.add_child(folium.Element(title_html))
    
    output_path = RELATORIO_DIR / f"{output_name}.html"
    m.save(str(output_path))
    print(f"      ✓ Salvo: {output_path}")

def main():
    print("="*60)
    print("GERAÇÃO DE MAPAS INTERATIVOS")
    print("="*60)
    
    # Carregar dados
    municipios, rg_imediatas, rg_intermediarias = carregar_dados()
    
    # Identificar colunas de nome
    col_mun = 'NM_MUN'
    col_rgi = [c for c in rg_imediatas.columns if 'NM_' in c][0] if any('NM_' in c for c in rg_imediatas.columns) else 'NM_RGI'
    col_rgint = [c for c in rg_intermediarias.columns if 'NM_' in c][0] if any('NM_' in c for c in rg_intermediarias.columns) else 'NM_RGINT'
    
    print(f"\n📍 Colunas de nome: Mun={col_mun}, RGI={col_rgi}, RGInt={col_rgint}")
    
    # Gerar mapas municipais
    print("\n🗺️ Mapas Municipais:")
    criar_mapa_densidade_area(municipios, col_mun, "Densidade por Área - Municípios", "mapa_densidade_municipios")
    criar_mapa_extensao(municipios, col_mun, "Extensão Total - Municípios", "mapa_extensao_municipios")
    criar_mapa_concessao(municipios, col_mun, "Rodovias Concessionadas - Municípios", "mapa_concessao_municipios")
    criar_mapa_urbano_rural(municipios, col_mun, "Proporção Urbana - Municípios", "mapa_urbano_municipios")
    
    # Gerar mapas regionais
    print("\n🗺️ Mapas Regionais (RG Imediatas):")
    criar_mapa_densidade_area(rg_imediatas, col_rgi, "Densidade por Área - RG Imediatas", "mapa_densidade_rgi")
    criar_mapa_extensao(rg_imediatas, col_rgi, "Extensão Total - RG Imediatas", "mapa_extensao_rgi")
    
    print("\n🗺️ Mapas Regionais (RG Intermediárias):")
    criar_mapa_densidade_area(rg_intermediarias, col_rgint, "Densidade por Área - RG Intermediárias", "mapa_densidade_rgint")
    criar_mapa_extensao(rg_intermediarias, col_rgint, "Extensão Total - RG Intermediárias", "mapa_extensao_rgint")
    
    print("\n" + "="*60)
    print("✅ MAPAS GERADOS COM SUCESSO!")
    print(f"📂 Local: {RELATORIO_DIR}")
    print("="*60)

if __name__ == "__main__":
    main()
