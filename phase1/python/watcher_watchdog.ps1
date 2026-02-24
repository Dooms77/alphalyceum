param(
  [string]$Config = "..\config\config.json",
  [int]$StaleMinutes = 3,
  [switch]$NoRestart,
  [switch]$NoAlert
)

$ErrorActionPreference = "Stop"
$base = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $base

$logDir = "D:\alphalyceum\phase1\logs"
$pidFile = Join-Path $logDir "watcher.pid"
$outLog = Get-ChildItem $logDir -Filter "watcher_*.out.log" -File -ErrorAction SilentlyContinue |
  Sort-Object LastWriteTime -Descending | Select-Object -First 1

function Send-Alert([string]$msg) {
  if ($NoAlert) { return }
  try {
    $cfg = Get-Content $Config -Raw | ConvertFrom-Json
    $token = $cfg.telegram.bot_token
    $chat  = $cfg.telegram.chat_id
    if ([string]::IsNullOrWhiteSpace($token) -or [string]::IsNullOrWhiteSpace($chat)) { return }

    $url = "https://api.telegram.org/bot$token/sendMessage"
    $body = @{ chat_id = $chat; text = "🚨 WATCHDOG: $msg"; disable_web_page_preview = $true }
    Invoke-RestMethod -Method Post -Uri $url -Body $body -TimeoutSec 20 | Out-Null
  } catch {
    Write-Host "[WARN] Failed to send alert: $($_.Exception.Message)"
  }
}

function Restart-Watcher([string]$reason) {
  Write-Host "[ACTION] Restart watcher: $reason"
  if ($NoRestart) { return }

  if (Test-Path $pidFile) {
    try {
      $watcherPid = [int](Get-Content $pidFile | Select-Object -First 1)
      Stop-Process -Id $watcherPid -Force -ErrorAction SilentlyContinue
    } catch {}
  }

  & powershell -ExecutionPolicy Bypass -File ".\start_watcher_background.ps1" -Config $Config | Out-Host
  Send-Alert "Watcher direstart otomatis. Reason: $reason"
}

if (!(Test-Path $pidFile)) {
  Restart-Watcher "PID file missing"
  exit 1
}

$watcherPid = [int](Get-Content $pidFile | Select-Object -First 1)
$p = Get-Process -Id $watcherPid -ErrorAction SilentlyContinue
if ($null -eq $p) {
  Restart-Watcher "process PID $watcherPid not found"
  exit 1
}

if ($null -eq $outLog) {
  Restart-Watcher "out log missing"
  exit 1
}

$ageMin = ((Get-Date) - $outLog.LastWriteTime).TotalMinutes
if ($ageMin -gt $StaleMinutes) {
  Restart-Watcher ("stale output log ({0:N1} min > {1} min)" -f $ageMin, $StaleMinutes)
  exit 1
}

Write-Host ("OK watcher healthy | PID={0} | outLogAge={1:N1} min" -f $watcherPid, $ageMin)
exit 0
