param(
  [string]$Config = "..\config\config.json"
)

$ErrorActionPreference = "Stop"
$base = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $base

$logDir = "D:\alphalyceum\phase1\logs"
New-Item -ItemType Directory -Force -Path $logDir | Out-Null

$ts = Get-Date -Format "yyyyMMdd_HHmmss"
$outLog = Join-Path $logDir "watcher_$ts.out.log"
$errLog = Join-Path $logDir "watcher_$ts.err.log"
$pidFile = Join-Path $logDir "watcher.pid"

$p = Start-Process -FilePath "python" -ArgumentList ".\run_phase1.py --loop --config $Config" -RedirectStandardOutput $outLog -RedirectStandardError $errLog -PassThru -WindowStyle Hidden

Set-Content -Path $pidFile -Value $p.Id -Encoding ascii
Write-Host "Watcher started in background"
Write-Host "PID: $($p.Id)"
Write-Host "OUT: $outLog"
Write-Host "ERR: $errLog"
