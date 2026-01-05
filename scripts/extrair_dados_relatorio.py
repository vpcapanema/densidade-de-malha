"""
Script para extrair dados corretos do GeoPackage para o relatório HTML
"""

import geopandas as gpd
import pandas as pd

print("="*60)
print("DADOS PARA ATUALIZAÇÃO DO RELATÓRIO HTML")
print("="*60)

# Carregar dados
mun = gpd.read_file('dados/saida/densidade_malha.gpkg', layer='municipios')
rgi = gpd.read_file('dados/saida/densidade_malha.gpkg', layer='rg_intermediarias')
rgim = gpd.read_file('dados/saida/densidade_malha.gpkg', layer='rg_imediatas')

print("\n=== TOP 10 MUNICÍPIOS (por Ext_Total) ===")
mun_sorted = mun.sort_values('Ext_Total', ascending=False).head(10)
for idx, (i, row) in enumerate(mun_sorted.iterrows(), 1):
    print(f"{idx}. {row['NM_MUN']}: {row['Ext_Total']:.2f} km, dens_area: {row['Dens_Area_Total']:.3f}")

print("\n=== REGIÕES INTERMEDIÁRIAS (11 regiões) ===")
rgi_sorted = rgi.sort_values('Ext_Total', ascending=False)
for i, row in rgi_sorted.iterrows():
    print(f"  {row['NM_RGINT']}: {row['Ext_Total']:.2f} km, area: {row['Area_km2']:.2f}, dens_area: {row['Dens_Area_Total']:.4f}, dens_pop: {row['Dens_Pop_Total']:.4f}")

print("\n=== TOTAIS GERAIS ===")
ext_total = mun['Ext_Total'].sum()
ext_conc = mun['Ext_Concessionada'].sum()
ext_nconc = mun['Ext_Não_Concessionada'].sum()
print(f"Extensão Total: {ext_total:.2f} km")
print(f"Concessionada: {ext_conc:.2f} km ({100*ext_conc/ext_total:.1f}%)")
print(f"Não Concessionada: {ext_nconc:.2f} km ({100*ext_nconc/ext_total:.1f}%)")

ext_urb = mun['Ext_Urbano'].sum()
ext_misto = mun['Ext_Misto'].sum()
ext_rural = mun['Ext_Rural'].sum()
print(f"\nUrbano: {ext_urb:.2f} km ({100*ext_urb/ext_total:.1f}%)")
print(f"Misto: {ext_misto:.2f} km ({100*ext_misto/ext_total:.1f}%)")
print(f"Rural: {ext_rural:.2f} km ({100*ext_rural/ext_total:.1f}%)")

print("\n=== DADOS PARA JS (Top 10 Municípios) ===")
labels = [f"'{row['NM_MUN']}'" for i, row in mun_sorted.iterrows()]
values = [f"{row['Ext_Total']:.2f}" for i, row in mun_sorted.iterrows()]
print(f"labels: [{', '.join(labels)}]")
print(f"data: [{', '.join(values)}]")

print("\n=== DADOS PARA JS (Regiões Intermediárias) ===")
labels_rg = [f"'{row['NM_RGINT']}'" for i, row in rgi_sorted.iterrows()]
values_rg = [f"{row['Ext_Total']:.2f}" for i, row in rgi_sorted.iterrows()]
print(f"labels: [{', '.join(labels_rg)}]")
print(f"data: [{', '.join(values_rg)}]")
