"""
Script para Download dos Dados de Entrada - Densidade de Malha Rodoviária
==========================================================================

Este script realiza o download automático de todos os dados necessários 
para o cálculo da densidade de malha rodoviária do Estado de São Paulo.

Fontes de Dados:
- DER/SP (Dados Abertos): Malha Rodoviária Estadual
- IBGE: Malha Municipal (área) e População (Censo 2022)

Autor: [Seu Nome]
Data: Dezembro/2025
"""

import os
import sys
import zipfile
import requests
from pathlib import Path
from datetime import datetime

# =============================================================================
# CONFIGURAÇÕES
# =============================================================================

# Diretório base do projeto
BASE_DIR = Path(r"d:\densidade _de_malha")
DADOS_ENTRADA = BASE_DIR / "dados" / "entrada"

# Subpastas para organização
PASTA_DER = DADOS_ENTRADA / "der_sp"
PASTA_IBGE_MALHA = DADOS_ENTRADA / "ibge_malha_municipal"
PASTA_IBGE_POPULACAO = DADOS_ENTRADA / "ibge_populacao"

# =============================================================================
# URLS DOS DADOS
# =============================================================================

# Dados do DER/SP - Sistema Rodoviário Estadual
# Fonte: https://www.der.sp.gov.br/WebSite/Servicos/DadosAbertos.aspx
# NOTA: Os arquivos do DER precisam ser baixados manualmente pois o site usa
# JavaScript para gerar os links de download. Acesse o link acima.
URLS_DER = {
    # Estas URLs são as prováveis - se não funcionarem, baixe manualmente
    "sre_shapefile": "https://www.der.sp.gov.br/WebSite/Arquivos/DadosAbertos/Sistema_Rodoviario_Estadual/SistemaRodoviarioEstadual.zip",
    "sre_xlsx": "https://www.der.sp.gov.br/WebSite/Arquivos/DadosAbertos/Sistema_Rodoviario_Estadual/SistemaRodoviarioEstadual.xlsx",
    "evolucao_sre": "https://www.der.sp.gov.br/WebSite/Arquivos/DadosAbertos/Sistema_Rodoviario_Estadual/EvolucaoSistemaRodoviarioEstadual.xlsx",
}

# Dados do IBGE - Malha Municipal 2024
# Fonte: https://www.ibge.gov.br/geociencias/organizacao-do-territorio/malhas-territoriais/15774-malhas.html
URLS_IBGE_MALHA = {
    "municipios_sp": "https://geoftp.ibge.gov.br/organizacao_do_territorio/malhas_territoriais/malhas_municipais/municipio_2024/UFs/SP/SP_Municipios_2024.zip",
    "rg_imediatas_sp": "https://geoftp.ibge.gov.br/organizacao_do_territorio/malhas_territoriais/malhas_municipais/municipio_2024/UFs/SP/SP_RG_Imediatas_2024.zip",
    "rg_intermediarias_sp": "https://geoftp.ibge.gov.br/organizacao_do_territorio/malhas_territoriais/malhas_municipais/municipio_2024/UFs/SP/SP_RG_Intermediarias_2024.zip",
}

# Dados do IBGE - População Censo 2022
# Fonte: https://ftp.ibge.gov.br/Censos/Censo_Demografico_2022/
URLS_IBGE_POPULACAO = {
    # Arquivo consolidado com população de todos os municípios do Brasil
    "populacao_municipios_xlsx": "https://ftp.ibge.gov.br/Censos/Censo_Demografico_2022/Previa_da_Populacao/POP2022_Municipios_20230622.xls",
    "populacao_municipios_ods": "https://ftp.ibge.gov.br/Censos/Censo_Demografico_2022/Previa_da_Populacao/POP2022_Municipios_20230622.ods",
}

# =============================================================================
# FUNÇÕES AUXILIARES
# =============================================================================

def criar_pastas():
    """Cria a estrutura de pastas necessária."""
    pastas = [PASTA_DER, PASTA_IBGE_MALHA, PASTA_IBGE_POPULACAO]
    for pasta in pastas:
        pasta.mkdir(parents=True, exist_ok=True)
        print(f"✓ Pasta criada/verificada: {pasta}")

def download_arquivo(url: str, pasta_destino: Path, nome_arquivo: str = None) -> Path:
    """
    Realiza o download de um arquivo.
    
    Args:
        url: URL do arquivo para download
        pasta_destino: Pasta onde o arquivo será salvo
        nome_arquivo: Nome do arquivo (se None, usa o nome da URL)
    
    Returns:
        Path do arquivo baixado
    """
    if nome_arquivo is None:
        nome_arquivo = url.split("/")[-1]
    
    caminho_arquivo = pasta_destino / nome_arquivo
    
    # Verifica se o arquivo já existe
    if caminho_arquivo.exists():
        print(f"  ⏭ Arquivo já existe: {nome_arquivo}")
        return caminho_arquivo
    
    print(f"  ⬇ Baixando: {nome_arquivo}...")
    
    try:
        response = requests.get(url, stream=True, timeout=120)
        response.raise_for_status()
        
        # Obtém o tamanho total
        total_size = int(response.headers.get('content-length', 0))
        
        # Salva o arquivo
        with open(caminho_arquivo, 'wb') as f:
            if total_size == 0:
                f.write(response.content)
            else:
                downloaded = 0
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        # Barra de progresso simples
                        percent = (downloaded / total_size) * 100
                        print(f"\r    Progresso: {percent:.1f}%", end="")
                print()  # Nova linha após completar
        
        print(f"  ✓ Download concluído: {nome_arquivo}")
        return caminho_arquivo
        
    except requests.exceptions.RequestException as e:
        print(f"  ✗ Erro no download de {nome_arquivo}: {e}")
        return None

def extrair_zip(caminho_zip: Path, pasta_destino: Path = None):
    """
    Extrai um arquivo ZIP.
    
    Args:
        caminho_zip: Caminho do arquivo ZIP
        pasta_destino: Pasta de destino (se None, extrai na mesma pasta)
    """
    if not caminho_zip or not caminho_zip.exists():
        return
    
    if pasta_destino is None:
        pasta_destino = caminho_zip.parent
    
    try:
        with zipfile.ZipFile(caminho_zip, 'r') as zip_ref:
            zip_ref.extractall(pasta_destino)
        print(f"  ✓ Arquivo extraído: {caminho_zip.name}")
    except zipfile.BadZipFile as e:
        print(f"  ✗ Erro ao extrair {caminho_zip.name}: {e}")

# =============================================================================
# FUNÇÕES DE DOWNLOAD POR FONTE
# =============================================================================

def download_dados_der():
    """Baixa os dados do DER/SP."""
    print("\n" + "="*60)
    print("DOWNLOAD - DER/SP (Sistema Rodoviário Estadual)")
    print("="*60)
    print("Fonte: Dados Abertos DER/SP")
    print("URL: https://www.der.sp.gov.br/WebSite/Servicos/DadosAbertos.aspx")
    print()
    
    for nome, url in URLS_DER.items():
        arquivo = download_arquivo(url, PASTA_DER)
        if arquivo and arquivo.suffix == '.zip':
            extrair_zip(arquivo)

def download_dados_ibge_malha():
    """Baixa os dados de malha municipal do IBGE."""
    print("\n" + "="*60)
    print("DOWNLOAD - IBGE (Malha Municipal 2024)")
    print("="*60)
    print("Fonte: IBGE Geociências")
    print("URL: https://www.ibge.gov.br/geociencias/organizacao-do-territorio/malhas-territoriais/15774-malhas.html")
    print()
    
    for nome, url in URLS_IBGE_MALHA.items():
        arquivo = download_arquivo(url, PASTA_IBGE_MALHA)
        if arquivo and arquivo.suffix == '.zip':
            extrair_zip(arquivo)

def download_dados_ibge_populacao():
    """Baixa os dados de população do IBGE."""
    print("\n" + "="*60)
    print("DOWNLOAD - IBGE (População Censo 2022)")
    print("="*60)
    print("Fonte: IBGE Censo Demográfico 2022")
    print("URL: https://ftp.ibge.gov.br/Censos/Censo_Demografico_2022/")
    print()
    
    for nome, url in URLS_IBGE_POPULACAO.items():
        arquivo = download_arquivo(url, PASTA_IBGE_POPULACAO)
        if arquivo and arquivo.suffix == '.zip':
            extrair_zip(arquivo)

# =============================================================================
# FUNÇÃO PRINCIPAL
# =============================================================================

def main():
    """Função principal do script."""
    print("="*60)
    print("DOWNLOAD DE DADOS - DENSIDADE DE MALHA RODOVIÁRIA")
    print("="*60)
    print(f"Data/Hora: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    print(f"Diretório de destino: {DADOS_ENTRADA}")
    print()
    
    # Cria estrutura de pastas
    print("Criando estrutura de pastas...")
    criar_pastas()
    
    # Download dos dados
    download_dados_der()
    download_dados_ibge_malha()
    download_dados_ibge_populacao()
    
    # Resumo final
    print("\n" + "="*60)
    print("DOWNLOAD CONCLUÍDO!")
    print("="*60)
    print("\nArquivos baixados em:")
    print(f"  • DER/SP: {PASTA_DER}")
    print(f"  • IBGE Malha: {PASTA_IBGE_MALHA}")
    print(f"  • IBGE População: {PASTA_IBGE_POPULACAO}")
    
    print("\n" + "-"*60)
    print("PRÓXIMOS PASSOS:")
    print("-"*60)
    print("1. Verifique se todos os arquivos foram baixados corretamente")
    print("2. Se algum download falhou, tente baixar manualmente:")
    print("   - DER/SP: https://www.der.sp.gov.br/WebSite/Servicos/DadosAbertos.aspx")
    print("   - IBGE: https://www.ibge.gov.br/geociencias/organizacao-do-territorio/malhas-territoriais/15774-malhas.html")
    print("3. Execute o próximo script: 02_processar_dados.py")
    print()
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
