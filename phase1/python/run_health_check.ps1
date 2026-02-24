param(
  [string]$Config = "../config/config.json"
)

$ErrorActionPreference = "Stop"

Write-Host "Running AlphaLyceum health check..." -ForegroundColor Cyan
python .\health_check.py --config "$Config"
