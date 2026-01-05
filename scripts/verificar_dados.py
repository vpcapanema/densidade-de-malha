"""
Script de Verificação dos Dados de Entrada
===========================================

Este script verifica se todos os dados necessários para o cálculo
da densidade de malha foram baixados corretamente.

Autor: [Seu Nome]
Data: Dezembro/2025
"""

import os
import sys
from pathlib import Path

try:
    import geopandas as gpd
    import pandas as pd
    GEOPANDAS_OK = True
except ImportError:
    GEOPANDAS_OK = False
    print("⚠️ GeoPandas não instalado. Verificação básica apenas.")

# =============================================================================
# CONFIGURAÇÕES
# =============================================================================

BASE_DIR = Path(r"d:\densidade _de_malha")
DADOS_ENTRADA = BASE_DIR / "dados" / "entrada"

PASTA_DER = DADOS_ENTRADA / "der_sp"
PASTA_IBGE_MALHA = DADOS_ENTRADA / "ibge_malha_municipal"
PASTA_IBGE_POPULACAO = DADOS_ENTRADA / "ibge_populacao"

# =============================================================================
# FUNÇÕES DE VERIFICAÇÃO
# =============================================================================

def verificar_arquivo(pasta: Path, padrao: str, obrigatorio: bool = True) -> dict:
    """
    Verifica se existe arquivo com determinado padrão na pasta.
    
    Returns:
        dict com status, arquivo encontrado e tamanho
    """
    arquivos = list(pasta.glob(padrao))
    if arquivos:
        arquivo = arquivos[0]
        tamanho_mb = arquivo.stat().st_size / (1024 * 1024)
        return {
            "status": "OK",
            "arquivo": arquivo.name,
            "caminho": arquivo,
            "tamanho_mb": round(tamanho_mb, 2),
            "obrigatorio": obrigatorio
        }
    else:
        return {
            "status": "FALTANDO" if obrigatorio else "OPCIONAL",
            "arquivo": padrao,
            "caminho": None,
            "tamanho_mb": 0,
            "obrigatorio": obrigatorio
        }

def verificar_shapefile(caminho: Path) -> dict:
    """Verifica se um shapefile pode ser lido corretamente."""
    if not GEOPANDAS_OK:
        return {"leitura": "não verificado", "registros": "?"}
    
    try:
        gdf = gpd.read_file(caminho)
        return {
            "leitura": "OK",
            "registros": len(gdf),
            "colunas": list(gdf.columns),
            "crs": str(gdf.crs) if gdf.crs else "Não definido"
        }
    except Exception as e:
        return {"leitura": f"ERRO: {e}", "registros": 0}

def verificar_excel(caminho: Path) -> dict:
    """Verifica se um arquivo Excel pode ser lido."""
    try:
        df = pd.read_excel(caminho)
        return {
            "leitura": "OK",
            "registros": len(df),
            "colunas": list(df.columns)[:5]  # Primeiras 5 colunas
        }
    except Exception as e:
        return {"leitura": f"ERRO: {e}", "registros": 0}

def print_status(nome: str, resultado: dict):
    """Imprime o status de um arquivo de forma formatada."""
    if resultado["status"] == "OK":
        icone = "✅"
    elif resultado["status"] == "FALTANDO":
        icone = "❌"
    else:
        icone = "⚠️"
    
    print(f"  {icone} {nome}")
    if resultado["status"] == "OK":
        print(f"     Arquivo: {resultado['arquivo']}")
        print(f"     Tamanho: {resultado['tamanho_mb']} MB")
    else:
        print(f"     Padrão esperado: {resultado['arquivo']}")

# =============================================================================
# VERIFICAÇÃO PRINCIPAL
# =============================================================================

def main():
    print("="*70)
    print("VERIFICAÇÃO DOS DADOS DE ENTRADA")
    print("="*70)
    print()
    
    todos_ok = True
    
    # -------------------------------------------------------------------------
    # DER/SP
    # -------------------------------------------------------------------------
    print("📁 DER/SP - Sistema Rodoviário Estadual")
    print("-"*50)
    
    der_checks = [
        ("Shapefile SRE", "*.shp", True),
        ("Excel SRE", "*[Ss]istema*.[xX][lL][sS][xX]", True),
        ("Evolução SRE", "*[Ee]volucao*.[xX][lL][sS][xX]", False),
    ]
    
    for nome, padrao, obrig in der_checks:
        resultado = verificar_arquivo(PASTA_DER, padrao, obrig)
        print_status(nome, resultado)
        if resultado["status"] == "FALTANDO":
            todos_ok = False
        
        # Verificação adicional do conteúdo
        if resultado["status"] == "OK" and resultado["caminho"]:
            if resultado["caminho"].suffix.lower() == ".shp":
                info = verificar_shapefile(resultado["caminho"])
                if info["leitura"] == "OK":
                    print(f"     Registros: {info['registros']}")
                    print(f"     CRS: {info['crs']}")
    print()
    
    # -------------------------------------------------------------------------
    # IBGE - Malha Municipal
    # -------------------------------------------------------------------------
    print("📁 IBGE - Malha Municipal 2024")
    print("-"*50)
    
    ibge_malha_checks = [
        ("Municípios SP", "SP_Municipios*.shp", True),
        ("RG Imediatas", "SP_RG_Imediatas*.shp", False),
        ("RG Intermediárias", "SP_RG_Intermediarias*.shp", False),
    ]
    
    for nome, padrao, obrig in ibge_malha_checks:
        resultado = verificar_arquivo(PASTA_IBGE_MALHA, padrao, obrig)
        print_status(nome, resultado)
        if resultado["status"] == "FALTANDO":
            todos_ok = False
        
        # Info adicional do shapefile
        if resultado["status"] == "OK" and resultado["caminho"]:
            info = verificar_shapefile(resultado["caminho"])
            if info["leitura"] == "OK":
                print(f"     Registros: {info['registros']} municípios")
    print()
    
    # -------------------------------------------------------------------------
    # IBGE - População
    # -------------------------------------------------------------------------
    print("📁 IBGE - População Censo 2022")
    print("-"*50)
    
    ibge_pop_checks = [
        ("População Municípios", "POP2022*.[xX][lL][sS]*", True),
    ]
    
    for nome, padrao, obrig in ibge_pop_checks:
        resultado = verificar_arquivo(PASTA_IBGE_POPULACAO, padrao, obrig)
        print_status(nome, resultado)
        if resultado["status"] == "FALTANDO":
            todos_ok = False
        
        # Info adicional do Excel
        if resultado["status"] == "OK" and resultado["caminho"]:
            info = verificar_excel(resultado["caminho"])
            if info["leitura"] == "OK":
                print(f"     Registros: {info['registros']}")
    print()
    
    # -------------------------------------------------------------------------
    # RESUMO FINAL
    # -------------------------------------------------------------------------
    print("="*70)
    if todos_ok:
        print("✅ TODOS OS DADOS OBRIGATÓRIOS ESTÃO DISPONÍVEIS!")
        print()
        print("Próximo passo: Execute o script 02_processar_dados.py")
        return 0
    else:
        print("❌ FALTAM DADOS OBRIGATÓRIOS!")
        print()
        print("Ações necessárias:")
        print("1. Baixe os dados faltantes do DER/SP manualmente:")
        print("   https://www.der.sp.gov.br/WebSite/Servicos/DadosAbertos.aspx")
        print()
        print("2. Salve os arquivos em:")
        print(f"   {PASTA_DER}")
        print()
        print("3. Execute este script novamente para verificar.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
