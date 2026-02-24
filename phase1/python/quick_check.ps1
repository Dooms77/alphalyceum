$logDir = "D:\alphalyceum\phase1\logs"
$latest = Get-ChildItem -Path $logDir -Filter "watcher_*.out.log" | Sort-Object LastWriteTime -Descending | Select-Object -First 1
if($latest){ Write-Output "Latest out log: $($latest.FullName)"; Get-Content -Path $latest.FullName -Tail 20 } else { Write-Output "No watcher out log found" }
$latestErr = Get-ChildItem -Path $logDir -Filter "watcher_*.err.log" | Sort-Object LastWriteTime -Descending | Select-Object -First 1
if($latestErr){ Write-Output "`nLatest err log: $($latestErr.FullName)"; Get-Content -Path $latestErr.FullName -Tail 20 } else { Write-Output "No watcher err log found" }
