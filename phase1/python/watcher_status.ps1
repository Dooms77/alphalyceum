$logDir = "D:\alphalyceum\phase1\logs"
$pidFile = Join-Path $logDir "watcher.pid"

if (!(Test-Path $pidFile)) {
  Write-Host "Watcher PID file not found"
  exit 1
}

$watcherPid = [int](Get-Content $pidFile | Select-Object -First 1)
$p = Get-Process -Id $watcherPid -ErrorAction SilentlyContinue
if ($null -eq $p) {
  Write-Host "Watcher NOT running (PID $watcherPid not found)"
  exit 1
}

Write-Host "Watcher running: PID $watcherPid"
$err = Get-ChildItem $logDir -Filter "watcher_*.err.log" -File | Sort-Object LastWriteTime -Descending | Select-Object -First 1
if ($err) {
  Write-Host "Latest ERR log: $($err.FullName)"
  Get-Content $err.FullName -Tail 20
}
