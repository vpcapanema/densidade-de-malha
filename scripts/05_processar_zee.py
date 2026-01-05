# -*- coding: utf-8 -*-
"""
Script para processar as camadas do ZEE (Zoneamento Ecológico-Econômico)
Calcula indicadores de densidade de malha rodoviária para:
1. Regiões Administrativas (16 unidades)
2. Unidades de Análise Integrada (9 grupos)
"""

import geopandas as gpd
import pandas as pd
import warnings
warnings.filterwarnings('ignore')

# Configurações
CRS_PROCESSAMENTO = 'EPSG:5880'  # Sistema de coordenadas para cálculos
CRS_WEB = 'EPSG:4326'  # Sistema para mapas web

print("="*60)
print("PROCESSAMENTO DAS CAMADAS DO ZEE")
print("="*60)

# 1. Carregar a malha rodoviária classificada
print("\n1. Carregando malha rodoviária...")
malha = gpd.read_file('dados/saida/malha_der_classificada.gpkg')
malha_proj = malha.to_crs(CRS_PROCESSAMENTO)
print(f"   Registros: {len(malha_proj)}")

# 2. Carregar dados populacionais dos municípios (para agregar por região)
print("\n2. Carregando dados populacionais...")
municipios = gpd.read_file('dados/saida/densidade_malha.gpkg', layer='municipios')
# Renomear coluna para padronizar
if 'Populacao' in municipios.columns:
    municipios = municipios.rename(columns={'Populacao': 'Pop_2022'})
print(f"   Municípios: {len(municipios)}")

# 3. Carregar e processar Regiões Administrativas
print("\n3. Processando Regiões Administrativas...")
rg_adm = gpd.read_file('dados/entrada/zee/RG2017_rgadm_SP.shp')
rg_adm = rg_adm.to_crs(CRS_PROCESSAMENTO)
print(f"   Regiões: {len(rg_adm)}")

# Calcular área em km²
rg_adm['Area_km2'] = rg_adm.geometry.area / 1_000_000

# Agregar população por RA usando centróide dos municípios
municipios_proj = municipios.to_crs(CRS_PROCESSAMENTO)
municipios_proj['centroid'] = municipios_proj.geometry.centroid
mun_centroids = municipios_proj.set_geometry('centroid')

# Spatial join para associar municípios às RAs
mun_ra = gpd.sjoin(mun_centroids, rg_adm[['RG_ADM', 'geometry']], how='left', predicate='within')

# Agregar população por RA
pop_por_ra = mun_ra.groupby('RG_ADM').agg({
    'Pop_2022': 'sum'
}).reset_index()

# Merge com RAs
rg_adm = rg_adm.merge(pop_por_ra, on='RG_ADM', how='left')
rg_adm['Pop_2022'] = rg_adm['Pop_2022'].fillna(0).astype(int)

print(f"   População total agregada: {rg_adm['Pop_2022'].sum():,.0f}")

# 4. Processar Unidades de Análise Integrada
print("\n4. Processando Unidades de Análise Integrada...")
zee_grupos = gpd.read_file('dados/entrada/zee/ZEE_un_analise_integrada.shp')
zee_grupos = zee_grupos.to_crs(CRS_PROCESSAMENTO)

# Corrigir encoding dos nomes
zee_grupos['grupo'] = zee_grupos['grupo'].str.encode('latin1').str.decode('utf-8', errors='replace')
zee_grupos['RA'] = zee_grupos['RA'].str.strip()

print(f"   Grupos ZEE: {len(zee_grupos)}")

# Calcular área em km²
zee_grupos['Area_km2'] = zee_grupos.geometry.area / 1_000_000

# Agregar população por grupo ZEE
mun_zee = gpd.sjoin(mun_centroids, zee_grupos[['RA', 'geometry']], how='left', predicate='within')
pop_por_zee = mun_zee.groupby('RA').agg({
    'Pop_2022': 'sum'
}).reset_index()

zee_grupos = zee_grupos.merge(pop_por_zee, on='RA', how='left')
zee_grupos['Pop_2022'] = zee_grupos['Pop_2022'].fillna(0).astype(int)

print(f"   População total agregada: {zee_grupos['Pop_2022'].sum():,.0f}")

# 5. Função para calcular extensões por unidade territorial
def calcular_extensoes(unidades, malha, col_nome):
    """Calcula extensão de rodovias por unidade territorial"""
    
    resultados = []
    
    for idx, unidade in unidades.iterrows():
        nome = unidade[col_nome]
        geom = unidade.geometry
        
        # Clip da malha pela unidade
        try:
            malha_clip = gpd.clip(malha, geom)
            
            if len(malha_clip) == 0:
                ext_total = 0
                ext_conc = ext_nconc = 0
                ext_sp = ext_spa = ext_spi = ext_br = 0
                ext_urb = ext_misto = ext_rural = 0
                ext_pav = ext_dup = ext_imp = ext_plan = 0
            else:
                # Calcular extensões
                malha_clip['ext_km'] = malha_clip.geometry.length / 1000
                
                # Extrair tipo de rodovia do nome
                malha_clip['Tipo_Rod'] = malha_clip['Rodovia'].str.extract(r'^([A-Z]+)', expand=False)
                
                ext_total = malha_clip['ext_km'].sum()
                
                # Por administração (Concessionária vs outros)
                ext_conc = malha_clip[malha_clip['Administra'] == 'Concessionária']['ext_km'].sum()
                ext_nconc = malha_clip[malha_clip['Administra'] != 'Concessionária']['ext_km'].sum()
                
                # Por tipo de rodovia
                ext_sp = malha_clip[malha_clip['Tipo_Rod'] == 'SP']['ext_km'].sum()
                ext_spa = malha_clip[malha_clip['Tipo_Rod'] == 'SPA']['ext_km'].sum()
                ext_spi = malha_clip[malha_clip['Tipo_Rod'] == 'SPI']['ext_km'].sum()
                ext_br = malha_clip[malha_clip['Tipo_Rod'] == 'BR']['ext_km'].sum()
                
                # Por localização (usar Loc_Mancha_Prop)
                ext_urb = malha_clip[malha_clip['Loc_Mancha_Prop'] == 'Urbano']['ext_km'].sum()
                ext_misto = malha_clip[malha_clip['Loc_Mancha_Prop'] == 'Misto']['ext_km'].sum()
                ext_rural = malha_clip[malha_clip['Loc_Mancha_Prop'] == 'Rural']['ext_km'].sum()
                
                # Por tipo de pista
                ext_pav = malha_clip[malha_clip['TipoPista'] == 'PAV']['ext_km'].sum()
                ext_dup = malha_clip[malha_clip['TipoPista'] == 'DUP']['ext_km'].sum()
                ext_imp = malha_clip[malha_clip['TipoPista'] == 'IMP']['ext_km'].sum()
                ext_plan = malha_clip[malha_clip['TipoPista'] == 'PLAN']['ext_km'].sum()
            
        except Exception as e:
            print(f"   Erro em {nome}: {e}")
            ext_total = ext_conc = ext_nconc = 0
            ext_sp = ext_spa = ext_spi = ext_br = 0
            ext_urb = ext_misto = ext_rural = 0
            ext_pav = ext_dup = ext_imp = ext_plan = 0
        
        resultados.append({
            col_nome: nome,
            'Ext_Total': round(ext_total, 2),
            'Ext_Conc': round(ext_conc, 2),
            'Ext_NConc': round(ext_nconc, 2),
            'Ext_SP': round(ext_sp, 2),
            'Ext_SPA': round(ext_spa, 2),
            'Ext_SPI': round(ext_spi, 2),
            'Ext_BR': round(ext_br, 2),
            'Ext_Urbano': round(ext_urb, 2),
            'Ext_Misto': round(ext_misto, 2),
            'Ext_Rural': round(ext_rural, 2),
            'Ext_PAV': round(ext_pav, 2),
            'Ext_DUP': round(ext_dup, 2),
            'Ext_IMP': round(ext_imp, 2),
            'Ext_PLAN': round(ext_plan, 2)
        })
        
        print(f"   {nome}: {ext_total:.2f} km")
    
    return pd.DataFrame(resultados)

# 6. Calcular extensões para Regiões Administrativas
print("\n5. Calculando extensões por Região Administrativa...")
ext_ra = calcular_extensoes(rg_adm, malha_proj, 'RG_ADM')

# Merge com RAs
rg_adm = rg_adm.merge(ext_ra, on='RG_ADM', how='left')

# 7. Calcular extensões para Grupos ZEE
print("\n6. Calculando extensões por Grupo ZEE...")
ext_zee = calcular_extensoes(zee_grupos, malha_proj, 'RA')

# Merge com grupos
zee_grupos = zee_grupos.merge(ext_zee, on='RA', how='left')

# 8. Calcular indicadores de densidade
def calcular_indicadores(gdf, col_ext, col_area, col_pop):
    """Calcula indicadores de densidade"""
    
    sufixos = ['Total', 'Conc', 'NConc', 'SP', 'SPA', 'SPI', 'BR', 
               'Urbano', 'Misto', 'Rural', 'PAV', 'DUP', 'IMP', 'PLAN']
    
    for suf in sufixos:
        col_name = f'Ext_{suf}'
        if col_name in gdf.columns:
            # Densidade por área (km/km²)
            gdf[f'Dens_Area_{suf}'] = round(gdf[col_name] / gdf[col_area], 4)
            
            # Densidade por população (km/10.000 hab)
            gdf[f'Dens_Pop_{suf}'] = round(gdf[col_name] / (gdf[col_pop] / 10000), 4)
            gdf[f'Dens_Pop_{suf}'] = gdf[f'Dens_Pop_{suf}'].replace([float('inf'), float('-inf')], 0)
    
    return gdf

print("\n7. Calculando indicadores de densidade...")
rg_adm = calcular_indicadores(rg_adm, 'Ext_Total', 'Area_km2', 'Pop_2022')
zee_grupos = calcular_indicadores(zee_grupos, 'Ext_Total', 'Area_km2', 'Pop_2022')

# 9. Preparar para salvar
print("\n8. Preparando dados para exportação...")

# Renomear coluna de nome para padronizar
rg_adm_save = rg_adm.rename(columns={'RG_ADM': 'Nome'})
rg_adm_save['Nome'] = rg_adm_save['Nome'].str.replace('Região Administrativa de ', '', regex=False)
rg_adm_save['Nome'] = rg_adm_save['Nome'].str.replace('Região Administrativa ', '', regex=False)

zee_grupos_save = zee_grupos.rename(columns={'grupo': 'Nome'})
# Corrigir encoding
try:
    zee_grupos_save['Nome'] = zee_grupos_save['Nome'].apply(
        lambda x: x.encode('latin1').str.decode('utf-8') if isinstance(x, str) else x
    )
except:
    pass

# Selecionar colunas relevantes
cols_manter = ['Nome', 'Area_km2', 'Pop_2022', 'geometry'] + \
              [c for c in rg_adm_save.columns if c.startswith('Ext_') or c.startswith('Dens_')]

rg_adm_save = rg_adm_save[[c for c in cols_manter if c in rg_adm_save.columns]]

cols_manter_zee = ['RA', 'Nome', 'Area_km2', 'Pop_2022', 'geometry'] + \
                  [c for c in zee_grupos_save.columns if c.startswith('Ext_') or c.startswith('Dens_')]

zee_grupos_save = zee_grupos_save[[c for c in cols_manter_zee if c in zee_grupos_save.columns]]

# 10. Salvar no GeoPackage
print("\n9. Salvando no GeoPackage...")

# Converter para WGS84 para salvar
rg_adm_save = rg_adm_save.to_crs(CRS_WEB)
zee_grupos_save = zee_grupos_save.to_crs(CRS_WEB)

rg_adm_save.to_file('dados/saida/densidade_malha.gpkg', layer='regioes_administrativas', driver='GPKG')
print("   Camada 'regioes_administrativas' salva")

zee_grupos_save.to_file('dados/saida/densidade_malha.gpkg', layer='grupos_zee', driver='GPKG')
print("   Camada 'grupos_zee' salva")

# 11. Exportar para Excel
print("\n10. Exportando para Excel...")

# Remover geometria para Excel
rg_adm_excel = rg_adm_save.drop(columns=['geometry'])
zee_grupos_excel = zee_grupos_save.drop(columns=['geometry'])

with pd.ExcelWriter('dados/saida/densidade_zee.xlsx', engine='openpyxl') as writer:
    rg_adm_excel.to_excel(writer, sheet_name='Regiões Administrativas', index=False)
    zee_grupos_excel.to_excel(writer, sheet_name='Grupos ZEE', index=False)

print("   Arquivo 'densidade_zee.xlsx' salvo")

# 12. Estatísticas finais
print("\n" + "="*60)
print("RESUMO DOS RESULTADOS")
print("="*60)

print("\n--- REGIÕES ADMINISTRATIVAS (16 unidades) ---")
print(f"Extensão Total: {rg_adm_save['Ext_Total'].sum():,.2f} km")
print(f"Área Total: {rg_adm_save['Area_km2'].sum():,.2f} km²")
print(f"População Total: {rg_adm_save['Pop_2022'].sum():,.0f} hab")
print(f"Densidade média por área: {rg_adm_save['Dens_Area_Total'].mean():.4f} km/km²")

print("\n--- GRUPOS ZEE (9 unidades) ---")
print(f"Extensão Total: {zee_grupos_save['Ext_Total'].sum():,.2f} km")
print(f"Área Total: {zee_grupos_save['Area_km2'].sum():,.2f} km²")
print(f"População Total: {zee_grupos_save['Pop_2022'].sum():,.0f} hab")
print(f"Densidade média por área: {zee_grupos_save['Dens_Area_Total'].mean():.4f} km/km²")

print("\n" + "="*60)
print("PROCESSAMENTO CONCLUÍDO COM SUCESSO!")
print("="*60)
