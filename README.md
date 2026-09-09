# Densidade de Malha — Relatório

Este repositório publica o relatório HTML gerado em `relatorio/`.

## Estrutura

- `relatorio/`: site estático (página inicial em `relatorio/index.html`).
- `scripts/`: scripts de processamento (não executados no Render).
- `dados/`: **não versionado** (entrada/saída) para manter o repositório leve.

## Abrir localmente

Sirva o diretório por HTTP. O dashboard carrega arquivos JSON e GeoJSON e não deve ser aberto por `file://`:

```bash
python -m http.server 8000
```

E acesse `http://localhost:8000/relatorio/`.

O painel está em `relatorio/dashboard.html`; os métodos e achados da revisão estão em `relatorio/metodologia.html`.

## Revisão técnica e reprodução

O universo revisado contém 4.782 registros e 21.682,703 km **cadastrais**, incluindo PLAN. Não é uma medida de comprimento físico único nem somente de vias em operação. A população é a do Censo 2022, tabela SIDRA 4714. RAs e ZEE são agregações municipais; a associação ao ZEE é aproximada nas bordas. Os limites e a composição do universo estão explicados na aplicação.

Os arquivos em `fontes/` preservam a extração dos indicadores e geometrias do relatório anterior, a consulta populacional e hashes de proveniência. O ZIP `dados/Sistema Rodoviário Estadual.zip` é o insumo rodoviário fornecido. Não troque sua versão sem revisar a auditoria.

```powershell
python -m pip install -r requirements-auditoria.txt
python scripts/baixar_fontes_auditoria.py
python scripts/auditar_e_construir_dashboard.py
python scripts/publicar_paginas_auditadas.py
python scripts/atualizar_contexto_visual.py
python scripts/validar_dashboard.py
```

Esses comandos geram somente arquivos locais. O site publicado continua estático, sem Python no servidor. As dependências Leaflet são locais. Os scripts antigos de processamento foram preservados como histórico; a reprodução da revisão usa os comandos acima.

O teste opcional `scripts/validar_interface_dashboard.py` requer Playwright, Edge e um servidor em `http://127.0.0.1:8768/` servindo `relatorio/`. Ele verifica páginas, mapas, recortes, filtros, exportação e apresentação em três larguras.

## Deploy no Render (Static Site)

Este repo inclui `render.yaml` configurado para publicar `relatorio/` como site estático.
No Render, basta conectar o repositório e criar o serviço.

### Deploy via API / automação

O Render expõe uma API pública (https://api.render.com/v1). Para automatizar a criação do Static Site, você pode usar o script em [tools/render-create-static-site.mjs](tools/render-create-static-site.mjs).

Pré-requisito: criar um API key no Render e exportar em `RENDER_API_KEY`.

```bash
node tools/render-create-static-site.mjs --owner-name "<NOME_DO_WORKSPACE>"
```

O script cria um Static Site Git-backed apontando para este repositório e publica a pasta `relatorio/`.
