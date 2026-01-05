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
