# Script para criar Static Site no Render usando o CLI autenticado
# Uso: .\create-static-site-cli.ps1

$REPO = "https://github.com/vpcapanema/densidade-de-malha"
$BRANCH = "main"
$SERVICE_NAME = "densidade-de-malha-relatorio"
$PUBLISH_PATH = "relatorio"

# Validate that render CLI is logged in
Write-Host "Verificando autenticação do Render CLI..." -ForegroundColor Cyan
$ws_output = render workspace list 2>&1
if ($ws_output -match "not authenticated|no workspaces" -or $null -eq $ws_output) {
  Write-Host "Erro: Render CLI não está autenticado. Execute 'render login' primeiro." -ForegroundColor Red
  exit 1
}

Write-Host "✓ Render CLI autenticado" -ForegroundColor Green

# Get active workspace or set to "My Workspace"
Write-Host "Configurando workspace..." -ForegroundColor Cyan
render workspace set "My Workspace" 2>&1 | Out-Null

# Create Static Site using render.yaml blueprint
Write-Host "Criando Static Site '$SERVICE_NAME'..." -ForegroundColor Cyan
Write-Host "  Repo: $REPO"
Write-Host "  Branch: $BRANCH"
Write-Host "  Publish Path: $PUBLISH_PATH"

# Use 'render deploy' with the render.yaml blueprint to create service
# First, let's check if render has a 'create service' command or if we use the blueprint
$output = render services list --output json 2>&1

if ($output -match $SERVICE_NAME) {
  Write-Host "⚠ Serviço '$SERVICE_NAME' já existe. Pule a criação ou use o dashboard para atualizar." -ForegroundColor Yellow
} else {
  # Since render CLI doesn't have direct 'create service' command, we'll use render.yaml
  # The service will be created when you deploy from the CLI or the blueprint is applied
  Write-Host "Nota: Para criar o serviço, você pode:" -ForegroundColor Yellow
  Write-Host "  1. Usar o dashboard do Render e importar o render.yaml"
  Write-Host "  2. Ou usar a API direto (veja tools/render-create-static-site.mjs)"
}

Write-Host ""
Write-Host "Para usar a API (recomendado para automação):" -ForegroundColor Cyan
Write-Host "  1. Acesse https://dashboard.render.com -> Account Settings -> API Keys"
Write-Host "  2. Crie uma API Key e copie"
Write-Host "  3. Execute:"
Write-Host "     `$env:RENDER_API_KEY = 'SUA_CHAVE_AQUI'"
Write-Host "     node tools/render-create-static-site.mjs --owner-name 'My Workspace'"
