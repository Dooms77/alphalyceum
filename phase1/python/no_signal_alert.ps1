param(
  [string]$Config = "..\config\config.json",
  [int]$MaxNoSignalMin = 60,
  [switch]$NoAlert
)

$ErrorActionPreference = "Stop"
$base = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $base

function Send-Tg([string]$text, [object]$cfg) {
  if ($NoAlert) { Write-Host "[NOALERT] $text"; return }
  $token = $cfg.telegram.bot_token
  $chat  = $cfg.telegram.chat_id
  if ([string]::IsNullOrWhiteSpace($token) -or [string]::IsNullOrWhiteSpace($chat)) {
    Write-Host "[WARN] Telegram token/chat_id kosong"
    return
  }
  $url = "https://api.telegram.org/bot$token/sendMessage"
  $body = @{ chat_id = $chat; text = $text; disable_web_page_preview = $true }
  Invoke-RestMethod -Method Post -Uri $url -Body $body -TimeoutSec 20 | Out-Null
}

$cfg = Get-Content $Config -Raw | ConvertFrom-Json
$signalFile = $cfg.signal_file
$statePath = "D:\alphalyceum\phase1\logs\no_signal_alert_state.json"

if (!(Test-Path $signalFile)) {
  Send-Tg "⚠️ ALERT: signal file tidak ditemukan: $signalFile" $cfg
  exit 1
}

$lastReal = $null
$lastRealRaw = $null
$lines = Get-Content $signalFile
for ($i = $lines.Count - 1; $i -ge 0; $i--) {
  $ln = $lines[$i].Trim()
  if ([string]::IsNullOrWhiteSpace($ln)) { continue }
  try { $obj = $ln | ConvertFrom-Json } catch { continue }

  $sid = [string]$obj.id
  if ($sid -match "^(TEST-|HC-|E2E-)") { continue }
  if ($obj.pair -notin @("BTCUSD.vx","XAUUSD.vx")) { continue }
  if ($obj.tf -ne "PERIOD_M5") { continue }

  $lastReal = $obj
  $lastRealRaw = $ln
  break
}

if ($null -eq $lastReal) {
  Send-Tg "⚠️ ALERT: tidak ada sinyal valid BTC/XAU M5 di file (hanya test/invalid)." $cfg
  exit 1
}

$signalTime = $null
try {
  # format: 2026.02.17 07:05
  $signalTime = [datetime]::ParseExact([string]$lastReal.signal_time, "yyyy.MM.dd HH:mm", $null)
} catch {
  $signalTime = $null
}

# Anti false-alert:
# jika sinyal lama baru terkirim/tertulis sekarang, pakai waktu aktivitas file terbaru.
$fileWriteTime = (Get-Item $signalFile).LastWriteTime
$effectiveLastActivity = $fileWriteTime
if ($signalTime -and $signalTime -gt $fileWriteTime) {
  $effectiveLastActivity = $signalTime
}

$gap = ((Get-Date) - $effectiveLastActivity).TotalMinutes

$alertState = @{}
if (Test-Path $statePath) {
  try { $alertState = Get-Content $statePath -Raw | ConvertFrom-Json } catch { $alertState = @{} }
}

$lastAlertKey = [string]$alertState.lastAlertKey
$currKey = "{0}|{1}" -f $lastReal.id, $signalTime.ToString("yyyy-MM-dd HH:mm")

if ($gap -ge $MaxNoSignalMin) {
  if ($lastAlertKey -ne $currKey) {
    $msg = "⚠️ NO-SIGNAL ALERT`nSudah {0:N0} menit tanpa sinyal baru (berdasarkan aktivitas terakhir file/sinyal).`nLast signal: {1} {2} {3} @ {4}`nLast activity: {5}`nPair monitor: BTCUSD.vx + XAUUSD.vx (M5)" -f $gap, $lastReal.pair, $lastReal.tf, $lastReal.side, $lastReal.signal_time, $effectiveLastActivity.ToString("yyyy-MM-dd HH:mm:ss")
    Send-Tg $msg $cfg
    $out = @{ lastAlertKey = $currKey; lastAlertAt = (Get-Date).ToString("s"); recovered = $false } | ConvertTo-Json
    $out | Set-Content -Path $statePath -Encoding UTF8
    Write-Host "ALERT sent"
  } else {
    Write-Host "ALERT already sent for current last signal"
  }
} else {
  # recovery message once
  if ($alertState.recovered -ne $true -and $lastAlertKey) {
    $msg = "✅ RECOVERY: sinyal terdeteksi lagi. Gap sekarang {0:N0} menit. Last signal {1} {2} {3} @ {4}" -f $gap, $lastReal.pair, $lastReal.tf, $lastReal.side, $lastReal.signal_time
    Send-Tg $msg $cfg
  }
  $out = @{ lastAlertKey = $lastAlertKey; lastAlertAt = $alertState.lastAlertAt; recovered = $true; lastCheckedAt = (Get-Date).ToString("s") } | ConvertTo-Json
  $out | Set-Content -Path $statePath -Encoding UTF8
  Write-Host ("OK: gap {0:N1} min" -f $gap)
}
