# Script para criar o Static Site no Render
$env:RENDER_API_KEY = "rnd_EuGyhhngRII85XsgYwJTRitPxn2d"
Write-Host "Criando Static Site no Render..." -ForegroundColor Cyan
node tools/render-create-static-site.mjs --owner-name "My Workspace"
Write-Host "Pronto!" -ForegroundColor Green
