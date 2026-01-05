"""
Script para Download e Processamento de Áreas Urbanizadas
==========================================================

Este script baixa os dados de Áreas Urbanizadas do IBGE (2019) e
faz o cruzamento espacial com a malha rodoviária do DER/SP para
uma classificação mais precisa de trechos urbanos e rurais.

Autor: [Seu Nome]
Data: Dezembro/2025
"""

import os
import sys
import zipfile
import warnings
from pathlib import Path
from datetime import datetime

import requests
import pandas as pd
import geopandas as gpd
import numpy as np

warnings.filterwarnings('ignore')

# =============================================================================
# CONFIGURAÇÕES
# =============================================================================

BASE_DIR = Path(r"d:\densidade _de_malha")
DADOS_ENTRADA = BASE_DIR / "dados" / "entrada"
DADOS_SAIDA = BASE_DIR / "dados" / "saida"

PASTA_IBGE_URBANO = DADOS_ENTRADA / "ibge_areas_urbanizadas"
PASTA_IBGE_URBANO.mkdir(parents=True, exist_ok=True)

# URL das Áreas Urbanizadas 2019
URL_AREAS_URBANIZADAS = "https://geoftp.ibge.gov.br/organizacao_do_territorio/tipologias_do_territorio/areas_urbanizadas_do_brasil/2019/Shapefile/AreasUrbanizadas2019_Brasil.zip"

# Arquivos de entrada
MALHA_DER = DADOS_ENTRADA / "der_sp" / "MALHA_OUT.shp"
MUNICIPIOS_SP = DADOS_ENTRADA / "ibge_malha_municipal" / "SP_Municipios_2024.shp"

# =============================================================================
# FUNÇÕES
# =============================================================================

def download_areas_urbanizadas():
    """Baixa os dados de áreas urbanizadas do IBGE."""
    arquivo_zip = PASTA_IBGE_URBANO / "AreasUrbanizadas2019_Brasil.zip"
    
    if arquivo_zip.exists():
        print("   ⏭ Arquivo já existe, pulando download...")
    else:
        print("   ⬇ Baixando Áreas Urbanizadas 2019 (37 MB)...")
        response = requests.get(URL_AREAS_URBANIZADAS, stream=True, timeout=300)
        response.raise_for_status()
        
        total = int(response.headers.get('content-length', 0))
        with open(arquivo_zip, 'wb') as f:
            downloaded = 0
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total:
                        print(f"\r   Progresso: {downloaded/total*100:.1f}%", end="")
            print()
        print("   ✓ Download concluído!")
    
    # Extrair
    print("   📦 Extraindo arquivos...")
    with zipfile.ZipFile(arquivo_zip, 'r') as zip_ref:
        zip_ref.extractall(PASTA_IBGE_URBANO)
    print("   ✓ Extração concluída!")
    
    return PASTA_IBGE_URBANO

def carregar_areas_urbanizadas_sp():
    """Carrega as áreas urbanizadas filtradas para SP."""
    print("\n📂 Carregando áreas urbanizadas...")
    
    # Procurar o shapefile
    shp_files = list(PASTA_IBGE_URBANO.rglob("*.shp"))
    if not shp_files:
        print("   ❌ Shapefile não encontrado!")
        return None
    
    shp_path = shp_files[0]
    print(f"   Arquivo: {shp_path.name}")
    
    # Carregar
    gdf = gpd.read_file(shp_path)
    print(f"   Total de polígonos Brasil: {len(gdf)}")
    
    # Filtrar para SP (código UF = 35)
    col_uf = None
    for col in gdf.columns:
        if 'UF' in col.upper() or 'COD' in col.upper():
            if gdf[col].dtype in ['int64', 'float64', 'object']:
                # Verificar se contém códigos de UF
                sample = gdf[col].astype(str).str[:2]
                if sample.str.match(r'^\d{2}$').any():
                    col_uf = col
                    break
    
    print(f"   Colunas: {gdf.columns.tolist()}")
    
    # Tentar identificar UF
    if 'UF' in gdf.columns:
        gdf_sp = gdf[gdf['UF'] == 'SP'].copy()
    elif 'CD_MUN' in gdf.columns:
        gdf_sp = gdf[gdf['CD_MUN'].astype(str).str.startswith('35')].copy()
    elif 'geocodigo' in gdf.columns:
        gdf_sp = gdf[gdf['geocodigo'].astype(str).str.startswith('35')].copy()
    else:
        # Filtrar espacialmente usando limites de SP
        print("   Filtrando espacialmente para SP...")
        sp_bounds = gpd.read_file(MUNICIPIOS_SP)
        sp_union = sp_bounds.unary_union
        gdf_sp = gdf[gdf.intersects(sp_union)].copy()
    
    print(f"   Polígonos em SP: {len(gdf_sp)}")
    
    return gdf_sp

def classificar_trechos_por_mancha_urbana(malha: gpd.GeoDataFrame, areas_urbanas: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """
    Classifica os trechos de rodovia em Urbano/Rural com base nas manchas urbanas.
    """
    print("\n🔄 Classificando trechos por mancha urbana...")
    
    # Garantir mesmo CRS
    if malha.crs != areas_urbanas.crs:
        print(f"   Reprojetando áreas urbanas de {areas_urbanas.crs} para {malha.crs}...")
        areas_urbanas = areas_urbanas.to_crs(malha.crs)
    
    # Dissolver todas as manchas urbanas em um único polígono
    print("   Dissolvendo manchas urbanas...")
    mancha_urbana_union = areas_urbanas.unary_union
    
    # Verificar interseção de cada trecho
    print("   Calculando interseção com manchas urbanas...")
    
    # Criar coluna de classificação
    malha = malha.copy()
    
    # Método: verificar se o centroide do trecho está dentro da mancha urbana
    # (mais rápido que verificar toda a geometria)
    centroids = malha.geometry.centroid
    malha['Loc_Mancha'] = centroids.within(mancha_urbana_union).map({True: 'Urbano', False: 'Rural'})
    
    # Alternativa: calcular a proporção do trecho dentro da mancha urbana
    print("   Calculando proporção de cada trecho em área urbana...")
    
    def calcular_proporcao_urbana(geom):
        try:
            if geom is None or geom.is_empty:
                return 0.0
            intersecao = geom.intersection(mancha_urbana_union)
            if intersecao.is_empty:
                return 0.0
            return intersecao.length / geom.length
        except:
            return 0.0
    
    malha['Prop_Urbano'] = malha.geometry.apply(calcular_proporcao_urbana)
    
    # Classificar: se mais de 50% está em área urbana, é urbano
    malha['Loc_Mancha_Prop'] = malha['Prop_Urbano'].apply(
        lambda x: 'Urbano' if x > 0.5 else ('Misto' if x > 0.1 else 'Rural')
    )
    
    # Estatísticas
    print("\n   📊 Resultado da classificação por MANCHA URBANA:")
    print("   " + "-"*50)
    
    print("\n   Método 1 - Por centroide:")
    stats1 = malha.groupby('Loc_Mancha')['Extensao'].agg(['count', 'sum'])
    for loc, row in stats1.iterrows():
        print(f"      {loc}: {row['count']:,} trechos, {row['sum']:,.2f} km")
    
    print("\n   Método 2 - Por proporção (>50% = Urbano):")
    stats2 = malha.groupby('Loc_Mancha_Prop')['Extensao'].agg(['count', 'sum'])
    for loc, row in stats2.iterrows():
        print(f"      {loc}: {row['count']:,} trechos, {row['sum']:,.2f} km")
    
    return malha

def comparar_classificacoes(malha: gpd.GeoDataFrame):
    """Compara a classificação original do DER com a nova por manchas urbanas."""
    print("\n📊 COMPARAÇÃO DAS CLASSIFICAÇÕES:")
    print("="*60)
    
    # Classificação original do DER (PerimetroU)
    malha['Loc_DER'] = malha['PerimetroU'].apply(
        lambda x: 'Urbano' if str(x).strip().upper() == 'SIM' else 'Rural'
    )
    
    # Tabela cruzada
    print("\n   Tabela Cruzada (Extensão em km):")
    print("   " + "-"*50)
    
    cross = pd.crosstab(
        malha['Loc_DER'], 
        malha['Loc_Mancha'],
        values=malha['Extensao'],
        aggfunc='sum',
        margins=True
    ).round(2)
    print(cross.to_string())
    
    print("\n   Resumo:")
    print("   " + "-"*50)
    
    # Concordância
    concordantes = malha[malha['Loc_DER'] == malha['Loc_Mancha']]['Extensao'].sum()
    total = malha['Extensao'].sum()
    print(f"   Concordância: {concordantes:,.2f} km ({concordantes/total*100:.1f}%)")
    
    # Diferenças
    der_urbano_mancha_rural = malha[(malha['Loc_DER'] == 'Urbano') & (malha['Loc_Mancha'] == 'Rural')]['Extensao'].sum()
    der_rural_mancha_urbano = malha[(malha['Loc_DER'] == 'Rural') & (malha['Loc_Mancha'] == 'Urbano')]['Extensao'].sum()
    
    print(f"   DER=Urbano, Mancha=Rural: {der_urbano_mancha_rural:,.2f} km")
    print(f"   DER=Rural, Mancha=Urbano: {der_rural_mancha_urbano:,.2f} km")
    
    return malha

def salvar_malha_atualizada(malha: gpd.GeoDataFrame):
    """Salva a malha com as novas classificações."""
    print("\n💾 Salvando malha atualizada...")
    
    # Salvar shapefile
    output_shp = DADOS_SAIDA / "malha_der_classificada.shp"
    malha.to_file(output_shp, encoding='utf-8')
    print(f"   ✓ Shapefile: {output_shp}")
    
    # Salvar GeoPackage
    output_gpkg = DADOS_SAIDA / "malha_der_classificada.gpkg"
    malha.to_file(output_gpkg, driver='GPKG')
    print(f"   ✓ GeoPackage: {output_gpkg}")
    
    return malha

# =============================================================================
# MAIN
# =============================================================================

def main():
    print("="*70)
    print("CLASSIFICAÇÃO URBANO/RURAL POR MANCHAS URBANAS")
    print("="*70)
    print(f"Data/Hora: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    print()
    
    # 1. Baixar áreas urbanizadas
    print("📥 ETAPA 1: Download das Áreas Urbanizadas (IBGE 2019)")
    print("-"*50)
    download_areas_urbanizadas()
    
    # 2. Carregar dados
    print("\n📂 ETAPA 2: Carregando dados")
    print("-"*50)
    
    print("📂 Carregando malha rodoviária do DER/SP...")
    malha = gpd.read_file(MALHA_DER)
    print(f"   Trechos: {len(malha)}")
    
    areas_urbanas = carregar_areas_urbanizadas_sp()
    if areas_urbanas is None:
        print("❌ Erro ao carregar áreas urbanizadas!")
        return 1
    
    # 3. Classificar trechos
    print("\n🔄 ETAPA 3: Classificação dos trechos")
    print("-"*50)
    malha = classificar_trechos_por_mancha_urbana(malha, areas_urbanas)
    
    # 4. Comparar classificações
    print("\n📊 ETAPA 4: Comparação das classificações")
    print("-"*50)
    malha = comparar_classificacoes(malha)
    
    # 5. Salvar
    print("\n💾 ETAPA 5: Salvando resultados")
    print("-"*50)
    salvar_malha_atualizada(malha)
    
    print("\n" + "="*70)
    print("✅ PROCESSAMENTO CONCLUÍDO!")
    print("="*70)
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
