"""
Script de Processamento - Densidade de Malha Rodoviária
========================================================

Este script processa os dados de entrada e calcula a densidade de malha
rodoviária para o Estado de São Paulo, com as seguintes classificações:

1. Por Administração:
   - Concessionada (Concessionária)
   - Não Concessionada (DER)
   - Federal (DNIT)
   - Municipal (Prefeitura)

2. Por Tipo de Rodovia:
   - SP (Eixo principal)
   - SPA (Acessos)
   - SPI (Interligações)
   - BR (Federais sob gestão estadual)

3. Por Localização:
   - Urbano (dentro de perímetro urbano)
   - Rural (fora de perímetro urbano)

4. Unidades Espaciais:
   - Municipal
   - Região Geográfica Imediata
   - Região Geográfica Intermediária

Autor: [Seu Nome]
Data: Dezembro/2025
"""

import os
import sys
import warnings
from pathlib import Path
from datetime import datetime

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

# Criar pasta de saída
DADOS_SAIDA.mkdir(parents=True, exist_ok=True)

# Caminhos dos arquivos de entrada
MALHA_DER = DADOS_ENTRADA / "der_sp" / "MALHA_OUT.shp"
MUNICIPIOS_SP = DADOS_ENTRADA / "ibge_malha_municipal" / "SP_Municipios_2024.shp"
RG_IMEDIATAS = DADOS_ENTRADA / "ibge_malha_municipal" / "SP_RG_Imediatas_2024.shp"
RG_INTERMEDIARIAS = DADOS_ENTRADA / "ibge_malha_municipal" / "SP_RG_Intermediarias_2024.shp"
POPULACAO = DADOS_ENTRADA / "ibge_populacao" / "POP2022_Municipios_20230622.xls"
AREAS_URBANIZADAS = DADOS_ENTRADA / "ibge_areas_urbanizadas"

# =============================================================================
# FUNÇÕES DE CLASSIFICAÇÃO
# =============================================================================

def classificar_administracao(adm: str) -> str:
    """
    Classifica a administração em Concessionada ou Não Concessionada.
    
    Returns:
        'Concessionada', 'Não Concessionada', 'Federal' ou 'Municipal'
    """
    if pd.isna(adm):
        return 'Não Informado'
    
    adm = str(adm).strip().upper()
    
    if 'CONCESS' in adm:
        return 'Concessionada'
    elif 'DER' in adm:
        return 'Não Concessionada'
    elif 'DNIT' in adm:
        return 'Federal (DNIT)'
    elif 'PREFEIT' in adm or 'MUNIC' in adm:
        return 'Municipal'
    else:
        return 'Outros'

def extrair_tipo_rodovia(rodovia: str) -> str:
    """
    Extrai o tipo de rodovia a partir do código.
    
    Returns:
        'SP', 'SPA', 'SPI', 'BR' ou 'Outros'
    """
    if pd.isna(rodovia):
        return 'Não Informado'
    
    rodovia = str(rodovia).strip().upper()
    
    if rodovia.startswith('SPI'):
        return 'SPI'  # Interligação
    elif rodovia.startswith('SPA'):
        return 'SPA'  # Acesso
    elif rodovia.startswith('SP'):
        return 'SP'   # Eixo principal
    elif rodovia.startswith('BR'):
        return 'BR'   # Federal
    else:
        return 'Outros'

def classificar_localizacao(perimetro_urbano: str) -> str:
    """
    Classifica a localização como Urbano ou Rural (usando campo PerimetroU do DER).
    NOTA: Esta função é mantida para comparação, mas a classificação principal
    agora usa manchas urbanas do IBGE (ver classificar_por_mancha_urbana).
    """
    if pd.isna(perimetro_urbano):
        return 'Rural'
    
    pu = str(perimetro_urbano).strip().upper()
    
    if pu in ['SIM', 'S', 'TRUE', '1', 'URBANO']:
        return 'Urbano'
    else:
        return 'Rural'

def classificar_por_proporcao(proporcao: float) -> str:
    """
    Classifica a localização com base na proporção do trecho em área urbanizada.
    
    Critérios (baseados em boas práticas IBGE):
    - Urbano: >50% do trecho dentro de mancha urbanizada
    - Misto: 10-50% do trecho dentro de mancha urbanizada  
    - Rural: <10% do trecho dentro de mancha urbanizada
    """
    if proporcao > 0.5:
        return 'Urbano'
    elif proporcao >= 0.1:
        return 'Misto'
    else:
        return 'Rural'

# =============================================================================
# FUNÇÕES DE PROCESSAMENTO
# =============================================================================

def carregar_areas_urbanizadas() -> gpd.GeoDataFrame:
    """Carrega as áreas urbanizadas do IBGE."""
    print("📂 Carregando áreas urbanizadas do IBGE...")
    
    # Procurar shapefile
    shp_files = list(AREAS_URBANIZADAS.rglob("*.shp"))
    if not shp_files:
        print("   ⚠️ Shapefile de áreas urbanizadas não encontrado!")
        return None
    
    gdf = gpd.read_file(shp_files[0])
    print(f"   Polígonos carregados: {len(gdf):,}")
    
    return gdf

def classificar_trechos_por_mancha(malha: gpd.GeoDataFrame, areas_urbanas: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """
    Classifica os trechos rodoviários com base na proporção dentro de manchas urbanas.
    
    Metodologia baseada em boas práticas IBGE (Áreas Urbanizadas do Brasil 2015):
    - Urbano: >50% do trecho dentro de mancha urbanizada
    - Misto: 10-50% do trecho dentro de mancha urbanizada
    - Rural: <10% do trecho dentro de mancha urbanizada
    """
    print("\n🔄 Classificando trechos por manchas urbanas (IBGE)...")
    
    # Garantir mesmo CRS
    if malha.crs != areas_urbanas.crs:
        print(f"   Reprojetando áreas urbanas de {areas_urbanas.crs} para {malha.crs}...")
        areas_urbanas = areas_urbanas.to_crs(malha.crs)
    
    # Dissolver manchas urbanas
    print("   Dissolvendo manchas urbanas...")
    mancha_union = areas_urbanas.unary_union
    
    # Calcular proporção de cada trecho em área urbana
    print("   Calculando proporção urbana de cada trecho...")
    
    def calcular_proporcao(geom):
        try:
            if geom is None or geom.is_empty:
                return 0.0
            intersecao = geom.intersection(mancha_union)
            if intersecao.is_empty:
                return 0.0
            return intersecao.length / geom.length
        except:
            return 0.0
    
    malha = malha.copy()
    malha['Prop_Urbano'] = malha.geometry.apply(calcular_proporcao)
    
    # Classificar por proporção
    malha['Localizacao'] = malha['Prop_Urbano'].apply(classificar_por_proporcao)
    
    # Manter classificação antiga para comparação
    malha['Loc_DER'] = malha['PerimetroU'].apply(classificar_localizacao)
    
    # Estatísticas
    print("\n   📊 Classificação por Mancha Urbana (IBGE):")
    stats = malha.groupby('Localizacao')['Extensao'].agg(['count', 'sum'])
    for loc, row in stats.iterrows():
        pct = row['sum'] / malha['Extensao'].sum() * 100
        print(f"      {loc}: {row['count']:,} trechos, {row['sum']:,.2f} km ({pct:.1f}%)")
    
    return malha

def carregar_malha_rodoviaria() -> gpd.GeoDataFrame:
    """Carrega e classifica a malha rodoviária."""
    print("📂 Carregando malha rodoviária do DER/SP...")
    gdf = gpd.read_file(MALHA_DER)
    
    print(f"   Trechos carregados: {len(gdf):,}")
    print(f"   CRS original: {gdf.crs}")
    
    # Aplicar classificações básicas
    print("   Aplicando classificações...")
    gdf['ClasseAdm'] = gdf['Administra'].apply(classificar_administracao)
    gdf['TipoRod'] = gdf['Rodovia'].apply(extrair_tipo_rodovia)
    
    # Classificação inicial por PerimetroU (será sobrescrita por manchas urbanas)
    gdf['Localizacao'] = gdf['PerimetroU'].apply(classificar_localizacao)
    
    # Criar classificação combinada Concessionada/Não Concessionada
    gdf['Concessao'] = gdf['ClasseAdm'].apply(
        lambda x: 'Concessionada' if x == 'Concessionada' else 'Não Concessionada'
    )
    
    # Garantir que Extensao é numérico
    gdf['Extensao'] = pd.to_numeric(gdf['Extensao'], errors='coerce').fillna(0)
    
    return gdf

def carregar_municipios() -> gpd.GeoDataFrame:
    """Carrega a malha municipal do IBGE."""
    print("📂 Carregando municípios do IBGE...")
    gdf = gpd.read_file(MUNICIPIOS_SP)
    
    print(f"   Municípios carregados: {len(gdf)}")
    print(f"   CRS: {gdf.crs}")
    
    # Usar área já existente ou calcular
    if 'AREA_KM2' in gdf.columns:
        gdf['Area_km2'] = gdf['AREA_KM2']
        gdf = gdf.drop(columns=['AREA_KM2'])
    else:
        # Calcular área em km²
        if gdf.crs.is_geographic:
            gdf_proj = gdf.to_crs('EPSG:5880')  # SIRGAS 2000 / Brazil Polyconic
            gdf['Area_km2'] = gdf_proj.geometry.area / 1_000_000
        else:
            gdf['Area_km2'] = gdf.geometry.area / 1_000_000
    
    return gdf

def carregar_regioes() -> tuple:
    """Carrega as regiões geográficas do IBGE."""
    print("📂 Carregando regiões geográficas do IBGE...")
    
    rg_imediatas = gpd.read_file(RG_IMEDIATAS)
    rg_intermediarias = gpd.read_file(RG_INTERMEDIARIAS)
    
    print(f"   Regiões Imediatas: {len(rg_imediatas)}")
    print(f"   Regiões Intermediárias: {len(rg_intermediarias)}")
    
    # Usar área existente ou calcular
    for gdf in [rg_imediatas, rg_intermediarias]:
        if 'AREA_KM2' in gdf.columns:
            gdf['Area_km2'] = gdf['AREA_KM2']
            # Não dropar AREA_KM2 aqui pois modifica o original
        else:
            if gdf.crs.is_geographic:
                gdf_proj = gdf.to_crs('EPSG:5880')
                gdf['Area_km2'] = gdf_proj.geometry.area / 1_000_000
            else:
                gdf['Area_km2'] = gdf.geometry.area / 1_000_000
    
    # Dropar AREA_KM2 após criar Area_km2
    if 'AREA_KM2' in rg_imediatas.columns:
        rg_imediatas = rg_imediatas.drop(columns=['AREA_KM2'])
    if 'AREA_KM2' in rg_intermediarias.columns:
        rg_intermediarias = rg_intermediarias.drop(columns=['AREA_KM2'])
    
    return rg_imediatas, rg_intermediarias

def carregar_populacao() -> pd.DataFrame:
    """Carrega os dados de população do Censo 2022."""
    print("📂 Carregando população (Censo 2022)...")
    
    # O arquivo tem cabeçalho na primeira linha, dados começam na linha 2
    try:
        df = pd.read_excel(POPULACAO, header=1)
        # Remover linhas com notas de rodapé (NaN no código do município)
        df = df.dropna(subset=['COD. MUNIC'])
    except Exception as e:
        print(f"   Erro ao ler Excel: {e}")
        return None
    
    print(f"   Registros carregados: {len(df)}")
    print(f"   Colunas: {df.columns.tolist()}")
    
    return df

def agregar_malha_por_municipio(malha: gpd.GeoDataFrame) -> pd.DataFrame:
    """
    Agrega a extensão da malha por município, com todas as classificações.
    """
    print("\n📊 Agregando malha por município...")
    
    # Criar todas as combinações de agregação
    resultados = []
    
    # Total geral por município
    total = malha.groupby('Municipio').agg({
        'Extensao': 'sum'
    }).reset_index()
    total.columns = ['Municipio', 'Ext_Total']
    
    # Por tipo de concessão
    concessao = malha.pivot_table(
        index='Municipio',
        columns='Concessao',
        values='Extensao',
        aggfunc='sum',
        fill_value=0
    ).reset_index()
    concessao.columns = ['Municipio'] + [f'Ext_{c.replace(" ", "_")}' for c in concessao.columns[1:]]
    
    # Por tipo de rodovia
    tipo_rod = malha.pivot_table(
        index='Municipio',
        columns='TipoRod',
        values='Extensao',
        aggfunc='sum',
        fill_value=0
    ).reset_index()
    tipo_rod.columns = ['Municipio'] + [f'Ext_{c}' for c in tipo_rod.columns[1:]]
    
    # Por localização (urbano/rural)
    localizacao = malha.pivot_table(
        index='Municipio',
        columns='Localizacao',
        values='Extensao',
        aggfunc='sum',
        fill_value=0
    ).reset_index()
    localizacao.columns = ['Municipio'] + [f'Ext_{c}' for c in localizacao.columns[1:]]
    
    # Por ClasseAdm detalhada
    classe_adm = malha.pivot_table(
        index='Municipio',
        columns='ClasseAdm',
        values='Extensao',
        aggfunc='sum',
        fill_value=0
    ).reset_index()
    classe_adm.columns = ['Municipio'] + [f'Ext_Adm_{c.replace(" ", "_").replace("(", "").replace(")", "")}' for c in classe_adm.columns[1:]]
    
    # Juntar todos os resultados
    resultado = total.merge(concessao, on='Municipio', how='outer')
    resultado = resultado.merge(tipo_rod, on='Municipio', how='outer')
    resultado = resultado.merge(localizacao, on='Municipio', how='outer')
    resultado = resultado.merge(classe_adm, on='Municipio', how='outer')
    
    # Preencher NaN com 0
    resultado = resultado.fillna(0)
    
    print(f"   Municípios com rodovias: {len(resultado)}")
    
    return resultado

def preparar_populacao_sp(df_pop: pd.DataFrame) -> pd.DataFrame:
    """Prepara os dados de população, filtrando apenas SP."""
    print("\n📊 Preparando dados de população para SP...")
    
    # Identificar colunas (já sabemos o formato)
    print(f"   Colunas disponíveis: {df_pop.columns.tolist()}")
    
    # Filtrar SP (código UF = 35)
    df_sp = df_pop[df_pop['COD. UF'] == 35].copy()
    
    print(f"   Registros de SP: {len(df_sp)}")
    
    # Criar DataFrame resultado
    resultado = pd.DataFrame()
    resultado['Municipio'] = df_sp['NOME DO MUNICÍPIO']
    resultado['Populacao'] = pd.to_numeric(df_sp['POPULAÇÃO'], errors='coerce')
    resultado['Cod_Municipio'] = df_sp['COD. MUNIC'].astype(str)
    
    return resultado

def normalizar_nome_municipio(nome: str) -> str:
    """Normaliza o nome do município para matching."""
    if pd.isna(nome):
        return ""
    
    import unicodedata
    
    # Converter para string e uppercase
    nome = str(nome).upper().strip()
    
    # Remover acentos
    nome = unicodedata.normalize('NFKD', nome)
    nome = ''.join(c for c in nome if not unicodedata.combining(c))
    
    # Remover caracteres especiais
    nome = nome.replace("'", "").replace("-", " ").replace(".", "")
    
    # Remover múltiplos espaços
    nome = ' '.join(nome.split())
    
    return nome

def juntar_dados_municipios(
    municipios: gpd.GeoDataFrame,
    malha_agregada: pd.DataFrame,
    populacao: pd.DataFrame
) -> gpd.GeoDataFrame:
    """
    Junta todos os dados no nível municipal.
    """
    print("\n🔗 Juntando dados por município...")
    
    # Normalizar nomes para matching
    municipios['Municipio_Norm'] = municipios['NM_MUN'].apply(normalizar_nome_municipio)
    malha_agregada['Municipio_Norm'] = malha_agregada['Municipio'].apply(normalizar_nome_municipio)
    
    if populacao is not None and 'Municipio' in populacao.columns:
        populacao['Municipio_Norm'] = populacao['Municipio'].apply(normalizar_nome_municipio)
    
    # Juntar malha
    resultado = municipios.merge(
        malha_agregada,
        on='Municipio_Norm',
        how='left'
    )
    
    # Juntar população
    if populacao is not None and len(populacao) > 0:
        resultado = resultado.merge(
            populacao[['Municipio_Norm', 'Populacao']],
            on='Municipio_Norm',
            how='left'
        )
    
    # Preencher NaN com 0 para extensões
    ext_cols = [c for c in resultado.columns if c.startswith('Ext_')]
    resultado[ext_cols] = resultado[ext_cols].fillna(0)
    
    # Verificar matching
    sem_malha = resultado['Ext_Total'].isna() | (resultado['Ext_Total'] == 0)
    print(f"   Municípios com rodovias: {(~sem_malha).sum()}")
    print(f"   Municípios sem rodovias estaduais: {sem_malha.sum()}")
    
    return resultado

def calcular_densidades(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """
    Calcula as densidades de malha (por área e por população).
    """
    print("\n📐 Calculando densidades...")
    
    # Identificar colunas de extensão
    ext_cols = [c for c in gdf.columns if c.startswith('Ext_')]
    
    # Densidade por área (km de rodovia / km² de território)
    for col in ext_cols:
        col_dens = col.replace('Ext_', 'Dens_Area_')
        gdf[col_dens] = gdf[col] / gdf['Area_km2']
    
    # Densidade por população (km de rodovia / 1000 habitantes)
    if 'Populacao' in gdf.columns:
        for col in ext_cols:
            col_dens = col.replace('Ext_', 'Dens_Pop_')
            gdf[col_dens] = (gdf[col] / gdf['Populacao']) * 1000
            # Substituir inf por NaN
            gdf[col_dens] = gdf[col_dens].replace([np.inf, -np.inf], np.nan)
    
    return gdf

def agregar_por_regiao(
    municipios: gpd.GeoDataFrame,
    regioes: gpd.GeoDataFrame,
    nome_regiao: str,
    col_nome_regiao: str
) -> gpd.GeoDataFrame:
    """
    Agrega os dados municipais por região geográfica.
    """
    print(f"\n📊 Agregando por {nome_regiao}...")
    
    # Encontrar qual região cada município pertence (spatial join)
    municipios_centroids = municipios.copy()
    municipios_centroids['geometry'] = municipios_centroids.geometry.centroid
    
    # Garantir mesmo CRS
    if municipios_centroids.crs != regioes.crs:
        municipios_centroids = municipios_centroids.to_crs(regioes.crs)
    
    # Remover colunas que possam conflitar
    cols_to_keep = [col_nome_regiao, 'geometry']
    regioes_simple = regioes[cols_to_keep].copy()
    
    # Spatial join - adiciona colunas da região ao município
    mun_com_regiao = gpd.sjoin(
        municipios_centroids,
        regioes_simple,
        how='left',
        predicate='within'
    )
    
    # Verificar qual coluna usar (pode ter sufixo _right se houver conflito)
    col_regiao_final = col_nome_regiao
    if col_nome_regiao not in mun_com_regiao.columns:
        # Procurar com sufixo
        for col in mun_com_regiao.columns:
            if col.startswith(col_nome_regiao):
                col_regiao_final = col
                break
    
    if col_regiao_final not in mun_com_regiao.columns:
        print(f"   ⚠️ Coluna {col_nome_regiao} não encontrada após sjoin")
        return regioes.copy()
    
    # Identificar colunas de extensão
    ext_cols = [c for c in municipios.columns if c.startswith('Ext_')]
    
    # Agregar por região
    agg_dict = {col: 'sum' for col in ext_cols if col in mun_com_regiao.columns}
    agg_dict['Area_km2'] = 'sum'
    if 'Populacao' in mun_com_regiao.columns:
        agg_dict['Populacao'] = 'sum'
    agg_dict['NM_MUN'] = 'count'  # Contar municípios
    
    agregado = mun_com_regiao.groupby(col_regiao_final).agg(agg_dict).reset_index()
    agregado = agregado.rename(columns={'NM_MUN': 'Num_Municipios', col_regiao_final: col_nome_regiao})
    agregado = agregado.rename(columns={'Area_km2': 'Area_km2_mun'})  # Área dos municípios somada
    
    # Juntar com geometria das regiões
    resultado = regioes.merge(agregado, on=col_nome_regiao, how='left')
    
    # Usar AREA_KM2 original das regiões se existir
    if 'AREA_KM2' in resultado.columns:
        resultado['Area_km2'] = resultado['AREA_KM2']
    else:
        # Calcular área das regiões
        if resultado.crs.is_geographic:
            resultado_proj = resultado.to_crs('EPSG:5880')
            resultado['Area_km2'] = resultado_proj.geometry.area / 1_000_000
        else:
            resultado['Area_km2'] = resultado.geometry.area / 1_000_000
    
    # Preencher NaN com 0 para extensões
    for col in ext_cols:
        if col in resultado.columns:
            resultado[col] = resultado[col].fillna(0)
    
    if 'Populacao' in resultado.columns:
        resultado['Populacao'] = resultado['Populacao'].fillna(0)
    if 'Num_Municipios' in resultado.columns:
        resultado['Num_Municipios'] = resultado['Num_Municipios'].fillna(0)
    
    # Calcular densidades
    resultado = calcular_densidades(resultado)
    
    print(f"   Regiões processadas: {len(resultado)}")
    
    return resultado

def gerar_estatisticas(gdf: gpd.GeoDataFrame, nome: str) -> pd.DataFrame:
    """Gera estatísticas resumidas."""
    print(f"\n📈 Estatísticas - {nome}")
    print("-" * 50)
    
    ext_cols = [c for c in gdf.columns if c.startswith('Ext_') and not c.startswith('Ext_Adm_')]
    
    stats = []
    for col in ext_cols:
        categoria = col.replace('Ext_', '')
        total = gdf[col].sum()
        stats.append({
            'Categoria': categoria,
            'Extensao_km': round(total, 2),
            'Percentual': round(total / gdf['Ext_Total'].sum() * 100, 1) if gdf['Ext_Total'].sum() > 0 else 0
        })
    
    df_stats = pd.DataFrame(stats)
    print(df_stats.to_string(index=False))
    
    return df_stats

def salvar_resultados(
    municipios: gpd.GeoDataFrame,
    rg_imediatas: gpd.GeoDataFrame,
    rg_intermediarias: gpd.GeoDataFrame
):
    """Salva os resultados em diversos formatos."""
    print("\n💾 Salvando resultados...")
    
    # Função para limpar colunas duplicadas e problemáticas
    def limpar_geodataframe(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
        gdf = gdf.copy()
        # Remover colunas duplicadas (com sufixo _x, _y, _left, _right)
        cols_to_drop = [c for c in gdf.columns if c.endswith(('_x', '_y', '_left', '_right'))]
        gdf = gdf.drop(columns=cols_to_drop, errors='ignore')
        # Remover colunas de índice do sjoin
        gdf = gdf.drop(columns=['index_right', 'index_left'], errors='ignore')
        return gdf
    
    municipios = limpar_geodataframe(municipios)
    rg_imediatas = limpar_geodataframe(rg_imediatas)
    rg_intermediarias = limpar_geodataframe(rg_intermediarias)
    
    # Shapefiles (nomes de colunas truncados para 10 caracteres)
    print("   Salvando Shapefiles...")
    municipios.to_file(DADOS_SAIDA / "densidade_municipios.shp", encoding='utf-8')
    rg_imediatas.to_file(DADOS_SAIDA / "densidade_rg_imediatas.shp", encoding='utf-8')
    rg_intermediarias.to_file(DADOS_SAIDA / "densidade_rg_intermediarias.shp", encoding='utf-8')
    
    # GeoPackage (formato moderno, suporta nomes longos)
    print("   Salvando GeoPackage...")
    gpkg_path = DADOS_SAIDA / "densidade_malha.gpkg"
    # Remover arquivo existente para evitar conflitos
    if gpkg_path.exists():
        gpkg_path.unlink()
    municipios.to_file(gpkg_path, layer='municipios', driver='GPKG')
    rg_imediatas.to_file(gpkg_path, layer='rg_imediatas', driver='GPKG')
    rg_intermediarias.to_file(gpkg_path, layer='rg_intermediarias', driver='GPKG')
    
    # Excel
    print("   Salvando Excel...")
    with pd.ExcelWriter(DADOS_SAIDA / "densidade_malha.xlsx", engine='openpyxl') as writer:
        # Remover geometria para Excel
        df_mun = municipios.drop(columns=['geometry']).copy()
        df_rgi = rg_imediatas.drop(columns=['geometry']).copy()
        df_rgint = rg_intermediarias.drop(columns=['geometry']).copy()
        
        df_mun.to_excel(writer, sheet_name='Municipios', index=False)
        df_rgi.to_excel(writer, sheet_name='RG_Imediatas', index=False)
        df_rgint.to_excel(writer, sheet_name='RG_Intermediarias', index=False)
    
    print(f"\n✅ Arquivos salvos em: {DADOS_SAIDA}")

# =============================================================================
# FUNÇÃO PRINCIPAL
# =============================================================================

def main():
    print("="*70)
    print("PROCESSAMENTO - DENSIDADE DE MALHA RODOVIÁRIA")
    print("="*70)
    print(f"Data/Hora: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    print()
    
    # 1. Carregar dados
    malha = carregar_malha_rodoviaria()
    municipios = carregar_municipios()
    rg_imediatas, rg_intermediarias = carregar_regioes()
    df_populacao = carregar_populacao()
    
    # 1.1. Carregar e aplicar classificação por manchas urbanas
    areas_urbanas = carregar_areas_urbanizadas()
    if areas_urbanas is not None:
        malha = classificar_trechos_por_mancha(malha, areas_urbanas)
    else:
        print("   ⚠️ Usando classificação PerimetroU do DER (fallback)")
    
    # 2. Preparar população
    if df_populacao is not None:
        populacao_sp = preparar_populacao_sp(df_populacao)
    else:
        populacao_sp = None
    
    # 3. Agregar malha por município
    malha_por_municipio = agregar_malha_por_municipio(malha)
    
    # 4. Juntar todos os dados
    municipios_completo = juntar_dados_municipios(
        municipios, malha_por_municipio, populacao_sp
    )
    
    # 5. Calcular densidades para municípios
    municipios_completo = calcular_densidades(municipios_completo)
    
    # 6. Agregar por regiões
    # Identificar coluna de nome da região
    col_rgi = [c for c in rg_imediatas.columns if 'NM_' in c][0]
    col_rgint = [c for c in rg_intermediarias.columns if 'NM_' in c][0]
    
    rg_imediatas_result = agregar_por_regiao(
        municipios_completo, rg_imediatas, 
        "Regiões Geográficas Imediatas", col_rgi
    )
    
    rg_intermediarias_result = agregar_por_regiao(
        municipios_completo, rg_intermediarias,
        "Regiões Geográficas Intermediárias", col_rgint
    )
    
    # 7. Gerar estatísticas
    print("\n" + "="*70)
    print("RESUMO DOS RESULTADOS")
    print("="*70)
    
    gerar_estatisticas(municipios_completo, "Estado de São Paulo")
    
    # 8. Salvar resultados
    salvar_resultados(
        municipios_completo,
        rg_imediatas_result,
        rg_intermediarias_result
    )
    
    print("\n" + "="*70)
    print("PROCESSAMENTO CONCLUÍDO!")
    print("="*70)
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
