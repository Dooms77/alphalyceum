param(
  [int]$KeepNewest = 20,
  [int]$DeleteOlderThanDays = 7,
  [switch]$WhatIf
)

$ErrorActionPreference = "Stop"
$logDir = "D:\alphalyceum\phase1\logs"
if (!(Test-Path $logDir)) {
  Write-Host "Log dir not found: $logDir"
  exit 0
}

$files = Get-ChildItem $logDir -File -ErrorAction SilentlyContinue |
  Where-Object { $_.Name -match '^watcher_.*\.(out|err)\.log$' } |
  Sort-Object LastWriteTime -Descending

if (-not $files) {
  Write-Host "No watcher logs to rotate."
  exit 0
}

$keep = $files | Select-Object -First $KeepNewest
$toCheck = $files | Select-Object -Skip $KeepNewest
$cutoff = (Get-Date).AddDays(-1 * $DeleteOlderThanDays)
$toDelete = $toCheck | Where-Object { $_.LastWriteTime -lt $cutoff }

Write-Host ("Found={0}, Keep={1}, Candidate={2}, Delete={3}" -f $files.Count, $keep.Count, $toCheck.Count, $toDelete.Count)
foreach ($f in $toDelete) {
  if ($WhatIf) {
    Write-Host "[WhatIf] Delete $($f.FullName)"
  } else {
    Remove-Item -LiteralPath $f.FullName -Force
    Write-Host "Deleted $($f.FullName)"
  }
}
