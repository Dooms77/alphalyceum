param(
  [string]$Config = "..\config\config.json",
  [int]$SignalFileMaxAgeMin = 180,
  [int]$StateMaxAgeMin = 180,
  [switch]$NoAlert
)

$ErrorActionPreference = "Stop"
$base = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $base

function Send-Alert([string]$msg) {
  if ($NoAlert) { return }
  try {
    $cfg = Get-Content $Config -Raw | ConvertFrom-Json
    $token = $cfg.telegram.bot_token
    $chat  = $cfg.telegram.chat_id
    if ([string]::IsNullOrWhiteSpace($token) -or [string]::IsNullOrWhiteSpace($chat)) { return }

    $url = "https://api.telegram.org/bot$token/sendMessage"
    $body = @{ chat_id = $chat; text = "⚠️ SMOKE CHECK: $msg"; disable_web_page_preview = $true }
    Invoke-RestMethod -Method Post -Uri $url -Body $body -TimeoutSec 20 | Out-Null
  } catch {
    Write-Host "[WARN] Failed to send alert: $($_.Exception.Message)"
  }
}

$cfg = Get-Content $Config -Raw | ConvertFrom-Json
$signalFile = $cfg.signal_file
$stateFile  = $cfg.state_file

$issues = @()

if (!(Test-Path $signalFile)) {
  $issues += "signal file missing: $signalFile"
} else {
  $sf = Get-Item $signalFile
  $age = ((Get-Date) - $sf.LastWriteTime).TotalMinutes
  if ($age -gt $SignalFileMaxAgeMin) {
    $issues += ("signal file stale: {0:N1} min" -f $age)
  }
}

if (!(Test-Path $stateFile)) {
  $issues += "state file missing: $stateFile"
} else {
  $st = Get-Item $stateFile
  $age2 = ((Get-Date) - $st.LastWriteTime).TotalMinutes
  if ($age2 -gt $StateMaxAgeMin) {
    $issues += ("state file stale: {0:N1} min" -f $age2)
  }
}

# watcher process check
$pidFile = "D:\alphalyceum\phase1\logs\watcher.pid"
if (!(Test-Path $pidFile)) {
  $issues += "watcher.pid missing"
} else {
  $watcherPid = [int](Get-Content $pidFile | Select-Object -First 1)
  $proc = Get-Process -Id $watcherPid -ErrorAction SilentlyContinue
  if ($null -eq $proc) {
    $issues += "watcher process not running (PID $watcherPid)"
  }
}

if ($issues.Count -eq 0) {
  Write-Host "OK smoke check passed"
  exit 0
}

$msg = ($issues -join " | ")
Write-Host "FAIL: $msg"
Send-Alert $msg
exit 1
