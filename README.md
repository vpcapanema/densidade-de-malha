# Densidade de Malha — Relatório

Este repositório publica o relatório HTML gerado em `relatorio/`.

## Estrutura

- `relatorio/`: site estático (página inicial em `relatorio/index.html`).
- `scripts/`: scripts de processamento (não executados no Render).
- `dados/`: **não versionado** (entrada/saída) para manter o repositório leve.

## Abrir localmente

Você pode abrir o arquivo `relatorio/index.html` diretamente no navegador.

Opcionalmente, para servir localmente (evita problemas de CORS em alguns browsers):

```bash
python -m http.server 8000
```

E acesse `http://localhost:8000/relatorio/`.

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
