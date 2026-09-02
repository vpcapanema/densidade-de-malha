# -*- coding: utf-8 -*-
"""
Script para gerar mapas interativos das camadas do ZEE
Gera mapas de densidade de malha rodoviária para:
1. Regiões Administrativas (16 unidades)
2. Unidades de Análise Integrada (9 grupos)
"""

import geopandas as gpd
import folium
from basemap_openfreemap import OpenFreeMapLayer
from branca.colormap import LinearColormap
import warnings
warnings.filterwarnings('ignore')

print("="*60)
print("GERAÇÃO DE MAPAS DO ZEE")
print("="*60)

# 1. Carregar os dados processados
print("\n1. Carregando dados...")
ra = gpd.read_file('dados/saida/densidade_malha.gpkg', layer='regioes_administrativas')
zee = gpd.read_file('dados/saida/densidade_malha.gpkg', layer='grupos_zee')

print(f"   Regiões Administrativas: {len(ra)}")
print(f"   Grupos ZEE: {len(zee)}")

# Centro de São Paulo
centro_sp = [-22.5, -49.5]

# 2. Função para criar mapa
def criar_mapa(gdf, col_valor, col_nome, titulo, arquivo, colormap_name='YlOrRd'):
    """Cria um mapa Folium interativo"""
    
    # Criar mapa base
    m = folium.Map(location=centro_sp, zoom_start=7, tiles=None)
    OpenFreeMapLayer('positron', name='Claro').add_to(m)
    
    # Calcular min/max para colormap
    vmin = gdf[col_valor].min()
    vmax = gdf[col_valor].max()
    
    # Colormap
    colormap = LinearColormap(
        colors=['#ffffb2', '#fecc5c', '#fd8d3c', '#f03b20', '#bd0026'],
        vmin=vmin,
        vmax=vmax,
        caption=f'{col_valor} ({titulo})'
    )
    
    # Estilo para as features
    def style_function(feature):
        valor = feature['properties'][col_valor]
        return {
            'fillColor': colormap(valor) if valor else '#cccccc',
            'color': '#333333',
            'weight': 1.5,
            'fillOpacity': 0.7,
        }
    
    # Adicionar camada GeoJSON
    gdf_json = gdf.copy()
    
    folium.GeoJson(
        gdf_json,
        style_function=style_function,
        tooltip=folium.GeoJsonTooltip(
            fields=[col_nome, 'Ext_Total', 'Area_km2', 'Pop_2022', col_valor],
            aliases=['Nome:', 'Extensão (km):', 'Área (km²):', 'População:', f'{col_valor}:'],
            localize=True,
            sticky=False,
            labels=True,
            style="""
                background-color: white !important;
                color: #333333 !important;
                font-family: Arial, sans-serif;
                font-size: 12px;
                padding: 10px;
                border: 1px solid #ccc;
                border-radius: 4px;
                box-shadow: 2px 2px 4px rgba(0,0,0,0.2);
            """,
        )
    ).add_to(m)
    
    # Adicionar colormap ao mapa
    colormap.add_to(m)
    
    # Adicionar título
    titulo_html = f'''
        <div style="position: fixed; 
                    top: 10px; left: 50%; transform: translateX(-50%);
                    background-color: white !important; 
                    color: #333333 !important;
                    padding: 10px 20px; 
                    border: 2px solid #666;
                    border-radius: 5px;
                    z-index: 9999;
                    font-size: 16px;
                    font-weight: bold;
                    font-family: Arial, sans-serif;
                    box-shadow: 2px 2px 6px rgba(0,0,0,0.3);">
            {titulo}
        </div>
    '''
    m.get_root().html.add_child(folium.Element(titulo_html))
    
    # Salvar mapa
    m.save(arquivo)
    print(f"   Mapa salvo: {arquivo}")
    
    return m

# 3. Gerar mapas das Regiões Administrativas
print("\n2. Gerando mapas das Regiões Administrativas...")

criar_mapa(
    ra, 'Dens_Area_Total', 'Nome',
    'Densidade de Malha por Área (km/km²) - Regiões Administrativas',
    'relatorio/mapas/mapa_ra_dens_area.html'
)

criar_mapa(
    ra, 'Ext_Total', 'Nome',
    'Extensão Total de Rodovias (km) - Regiões Administrativas',
    'relatorio/mapas/mapa_ra_extensao.html'
)

# 4. Gerar mapas dos Grupos ZEE
print("\n3. Gerando mapas dos Grupos ZEE...")

criar_mapa(
    zee, 'Dens_Area_Total', 'Nome',
    'Densidade de Malha por Área (km/km²) - Grupos ZEE',
    'relatorio/mapas/mapa_zee_dens_area.html'
)

criar_mapa(
    zee, 'Ext_Total', 'Nome',
    'Extensão Total de Rodovias (km) - Grupos ZEE',
    'relatorio/mapas/mapa_zee_extensao.html'
)

# 5. Gerar mapa combinado com ambas as camadas
print("\n4. Gerando mapa combinado...")

m_combo = folium.Map(location=centro_sp, zoom_start=7, tiles=None)
OpenFreeMapLayer('positron', name='Claro').add_to(m_combo)

# Colormap para RA
vmin_ra = ra['Dens_Area_Total'].min()
vmax_ra = ra['Dens_Area_Total'].max()
colormap_ra = LinearColormap(
    colors=['#ffffb2', '#fecc5c', '#fd8d3c', '#f03b20', '#bd0026'],
    vmin=vmin_ra, vmax=vmax_ra
)

# Colormap para ZEE
vmin_zee = zee['Dens_Area_Total'].min()
vmax_zee = zee['Dens_Area_Total'].max()
colormap_zee = LinearColormap(
    colors=['#c7e9c0', '#74c476', '#31a354', '#006d2c'],
    vmin=vmin_zee, vmax=vmax_zee
)

# Feature groups
fg_ra = folium.FeatureGroup(name='Regiões Administrativas', show=True)
fg_zee = folium.FeatureGroup(name='Grupos ZEE', show=False)

# Adicionar RAs
def style_ra(feature):
    valor = feature['properties']['Dens_Area_Total']
    return {
        'fillColor': colormap_ra(valor) if valor else '#cccccc',
        'color': '#333333',
        'weight': 1.5,
        'fillOpacity': 0.7,
    }

folium.GeoJson(
    ra,
    style_function=style_ra,
    tooltip=folium.GeoJsonTooltip(
        fields=['Nome', 'Ext_Total', 'Dens_Area_Total'],
        aliases=['Região:', 'Extensão (km):', 'Densidade:'],
        localize=True,
        style="""
            background-color: white !important;
            color: #333333 !important;
            padding: 8px;
            border-radius: 4px;
        """,
    )
).add_to(fg_ra)

# Adicionar ZEE
def style_zee(feature):
    valor = feature['properties']['Dens_Area_Total']
    return {
        'fillColor': colormap_zee(valor) if valor else '#cccccc',
        'color': '#006d2c',
        'weight': 2,
        'fillOpacity': 0.7,
    }

folium.GeoJson(
    zee,
    style_function=style_zee,
    tooltip=folium.GeoJsonTooltip(
        fields=['Nome', 'Ext_Total', 'Dens_Area_Total'],
        aliases=['Grupo ZEE:', 'Extensão (km):', 'Densidade:'],
        localize=True,
        style="""
            background-color: white !important;
            color: #333333 !important;
            padding: 8px;
            border-radius: 4px;
        """,
    )
).add_to(fg_zee)

fg_ra.add_to(m_combo)
fg_zee.add_to(m_combo)

# Controle de camadas
folium.LayerControl().add_to(m_combo)

# Título
titulo_html = '''
    <div style="position: fixed; 
                top: 10px; left: 50%; transform: translateX(-50%);
                background-color: white !important; 
                color: #333333 !important;
                padding: 10px 20px; 
                border: 2px solid #666;
                border-radius: 5px;
                z-index: 9999;
                font-size: 16px;
                font-weight: bold;
                font-family: Arial, sans-serif;
                box-shadow: 2px 2px 6px rgba(0,0,0,0.3);">
        ZEE - Densidade de Malha Rodoviária (SP)
    </div>
'''
m_combo.get_root().html.add_child(folium.Element(titulo_html))

m_combo.save('relatorio/mapas/mapa_zee_combinado.html')
print("   Mapa combinado salvo: relatorio/mapas/mapa_zee_combinado.html")

print("\n" + "="*60)
print("MAPAS GERADOS COM SUCESSO!")
print("="*60)
print("\nMapas gerados:")
print("  - mapa_ra_dens_area.html")
print("  - mapa_ra_extensao.html")
print("  - mapa_zee_dens_area.html")
print("  - mapa_zee_extensao.html")
print("  - mapa_zee_combinado.html")
