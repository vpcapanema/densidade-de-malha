"""
Script de Download Manual - Dados DER/SP
=========================================

Os dados do DER/SP precisam ser baixados manualmente pois o site
utiliza JavaScript para gerar os links de download dinâmicos.

Este script abre as páginas necessárias e fornece instruções.

Autor: [Seu Nome]
Data: Dezembro/2025
"""

import webbrowser
import os
from pathlib import Path

# Diretório de destino
PASTA_DER = Path(r"d:\densidade _de_malha\dados\entrada\der_sp")
PASTA_DER.mkdir(parents=True, exist_ok=True)

def main():
    print("="*70)
    print("DOWNLOAD MANUAL - DADOS DER/SP")
    print("="*70)
    print()
    print("Os arquivos do DER/SP precisam ser baixados manualmente.")
    print("Vou abrir as páginas necessárias no seu navegador.")
    print()
    print("-"*70)
    print("INSTRUÇÕES:")
    print("-"*70)
    print()
    print("1. SISTEMA RODOVIÁRIO ESTADUAL (MALHA)")
    print("   Página: Sistema Rodoviário Estadual")
    print("   Downloads necessários:")
    print("   - SHP (Shapefile) - arquivo principal com geometrias")
    print("   - XLSX (Excel) - dados tabulares")
    print()
    print("2. EVOLUÇÃO DO SISTEMA RODOVIÁRIO")
    print("   Página: Evolução do Sistema Rodoviário Estadual")  
    print("   Downloads necessários:")
    print("   - XLSX (Excel) - série histórica da malha")
    print()
    print("-"*70)
    print(f"SALVE OS ARQUIVOS EM: {PASTA_DER}")
    print("-"*70)
    print()
    
    input("Pressione ENTER para abrir as páginas no navegador...")
    
    # URLs das páginas de dados
    urls = [
        # Página principal de Dados Abertos
        "https://www.der.sp.gov.br/WebSite/Servicos/DadosAbertos.aspx",
        # Página específica do Sistema Rodoviário Estadual
        "https://www.der.sp.gov.br/WebSite/Servicos/ConjuntoDados.aspx?tema=Sistema_Rodoviario_Estadual&conjunto=Sistema_Rodoviario_Estadual",
        # Página de Evolução do SRE
        "https://www.der.sp.gov.br/WebSite/Servicos/ConjuntoDados.aspx?tema=Sistema_Rodoviario_Estadual&conjunto=Evolucao_do_Sistema_Rodoviario_Estadual",
    ]
    
    for url in urls:
        print(f"Abrindo: {url}")
        webbrowser.open(url)
    
    print()
    print("="*70)
    print("ARQUIVOS ESPERADOS:")
    print("="*70)
    print("""
    Na pasta der_sp, você deve ter:
    
    1. SistemaRodoviarioEstadual.shp (ou .zip contendo o shapefile)
       - Contém a geometria das rodovias estaduais
       - Campos importantes: código da rodovia, extensão, tipo, etc.
    
    2. SistemaRodoviarioEstadual.xlsx
       - Dados tabulares do sistema rodoviário
       - Extensões por rodovia, classificação, etc.
    
    3. EvolucaoSistemaRodoviarioEstadual.xlsx  
       - Série histórica da evolução da malha
       - Extensões por ano desde 2014
    """)
    print()
    print("Após baixar os arquivos, execute o script 01_download_dados.py")
    print("para verificar se todos os dados estão completos.")
    print()
    
    # Abre a pasta de destino
    os.startfile(PASTA_DER)

if __name__ == "__main__":
    main()
