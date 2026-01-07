param(
  [switch]$Restart
)

$ErrorActionPreference = 'Stop'

$root = Split-Path -Parent $PSScriptRoot
$py = Join-Path $root '.venv\Scripts\python.exe'

if (-not (Test-Path $py)) {
  throw "Python do venv não encontrado em: $py"
}

function Get-ListeningPids([int]$Port) {
  try {
    return @(Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue |
      Select-Object -ExpandProperty OwningProcess -Unique)
  } catch {
    return @()
  }
}

function Stop-Port([int]$Port) {
  $pids = Get-ListeningPids -Port $Port
  foreach ($processId in $pids) {
    try { Stop-Process -Id $processId -Force -ErrorAction Stop } catch {}
  }
}

$port = 8080

if ($Restart) {
  Stop-Port -Port $port
}

if ((Get-ListeningPids -Port $port).Count -eq 0) {
  Start-Process -FilePath $py -ArgumentList @('-m','http.server',"$port") -WorkingDirectory $root -WindowStyle Hidden | Out-Null
}

Start-Process "http://localhost:$port/" | Out-Null
Start-Process "http://localhost:$port/relatorio/" | Out-Null

Write-Host "Servidor OK em http://localhost:$port/ (relatorio: /relatorio/)"