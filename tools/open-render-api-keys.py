#!/usr/bin/env python3
"""
Abre o navegador na página de criação de API Keys do Render.
Depois de criar, cole a chave no comando:
  $env:RENDER_API_KEY = "SUA_CHAVE_AQUI"
  node tools/render-create-static-site.mjs --owner-name "My Workspace"
"""

import webbrowser
import sys

url = "https://dashboard.render.com/account/api-keys"

print("\n" + "="*70)
print("Abrindo Render Dashboard para criar API Key...")
print("="*70)
print(f"\nURL: {url}\n")
print("Passos:")
print("  1. Clique em '+ Create API Key'")
print("  2. Dê um nome (ex: 'densidade-de-malha')")
print("  3. Copie a chave (ela aparece uma única vez!)")
print("  4. Cole aqui no terminal:")
print("     $env:RENDER_API_KEY = 'COLE_AQUI'")
print("\n" + "="*70 + "\n")

webbrowser.open(url)
print("✓ Navegador aberto. Crie a chave e cole aqui.\n")
