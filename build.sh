#!/bin/bash
# Script para preparar o build para o Render
# Se relatorio existe, copiar para public
if [ -d "relatorio" ]; then
  cp -r relatorio public
  echo "Copiado relatorio -> public"
fi
