"""
Script para extrair estatísticas de indicadores de densidade
"""

import geopandas as gpd
import numpy as np

mun = gpd.read_file('dados/saida/densidade_malha.gpkg', layer='municipios')

print('=== ESTATÍSTICAS DE INDICADORES ===')
print()

# Densidade por área total
d = mun['Dens_Area_Total']
print('Dens_Area_Total:')
print(f'  Média: {d.mean():.4f} km/10000km²')
print(f'  Mediana: {d.median():.4f} km/10000km²')
print(f'  Min: {d.min():.4f} | Max: {d.max():.4f}')
idx_max = d.idxmax()
print(f'  Mun com maior: {mun.loc[idx_max, "NM_MUN"]} ({d.max():.4f})')
print()

# Densidade por população
d = mun['Dens_Pop_Total']
print('Dens_Pop_Total:')
print(f'  Média: {d.mean():.4f} km/10.000hab')
print(f'  Mediana: {d.median():.4f} km/10.000hab')
print(f'  Min: {d.min():.4f} | Max: {d.max():.4f}')
idx_max = d.idxmax()
print(f'  Mun com maior: {mun.loc[idx_max, "NM_MUN"]} ({d.max():.4f})')
print()

# Top 5 densidade área
print('TOP 5 Densidade Área:')
top5 = mun.nlargest(5, 'Dens_Area_Total')[['NM_MUN', 'Dens_Area_Total', 'Area_km2', 'Ext_Total']]
for i, row in top5.iterrows():
    print(f'  {row["NM_MUN"]}: {row["Dens_Area_Total"]:.3f} km/10000km² ({row["Ext_Total"]:.1f} km em {row["Area_km2"]:.0f} km²)')

print()
print('TOP 5 Densidade População:')
top5 = mun.nlargest(5, 'Dens_Pop_Total')[['NM_MUN', 'Dens_Pop_Total', 'Populacao', 'Ext_Total']]
for i, row in top5.iterrows():
    print(f'  {row["NM_MUN"]}: {row["Dens_Pop_Total"]:.3f} km/10.000hab ({row["Ext_Total"]:.1f} km para {row["Populacao"]:.0f} hab)')

# Estatísticas estaduais
print()
print('=== INDICADORES ESTADUAIS ===')
area_total = mun['Area_km2'].sum()
pop_total = mun['Populacao'].sum()
ext_total = mun['Ext_Total'].sum()
print(f'Área Total SP: {area_total:,.0f} km²')
print(f'População Total: {pop_total:,.0f} habitantes')
print(f'Extensão Total: {ext_total:,.2f} km')
print(f'Densidade Área Estadual: {(ext_total/area_total)*10000:.4f} km/10000km²')
print(f'Densidade Pop Estadual: {ext_total/(pop_total/10000):.4f} km/10.000hab')

# Por tipo de administração
print()
print('=== POR TIPO DE ADMINISTRAÇÃO ===')
for tipo, col in [('Concessionada', 'Ext_Concessionada'), ('Não Concessionada', 'Ext_Não_Concessionada')]:
    ext = mun[col].sum()
    dens_area = (ext / area_total) * 10000
    dens_pop = ext / (pop_total / 10000)
    print(f'{tipo}: {ext:,.2f} km | Dens.Área: {dens_area:.4f} km/10000km² | Dens.Pop: {dens_pop:.4f} km/10.000hab')

# Por localização
print()
print('=== POR LOCALIZAÇÃO ===')
for tipo, col in [('Urbano', 'Ext_Urbano'), ('Misto', 'Ext_Misto'), ('Rural', 'Ext_Rural')]:
    ext = mun[col].sum()
    dens_area = (ext / area_total) * 10000
    dens_pop = ext / (pop_total / 10000)
    print(f'{tipo}: {ext:,.2f} km | Dens.Área: {dens_area:.4f} km/10000km² | Dens.Pop: {dens_pop:.4f} km/10.000hab')
