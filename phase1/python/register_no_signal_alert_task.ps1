$taskName = "AlphaLyceum_NoSignalAlert_Every10Min"
$script = "D:\alphalyceum\phase1\python\no_signal_alert.ps1"
$cmd = "powershell.exe -NoProfile -ExecutionPolicy Bypass -File `"$script`""

schtasks /Create /F /TN $taskName /TR $cmd /SC MINUTE /MO 10 | Out-Null
Write-Output "Registered/Updated: $taskName (every 10 minutes)"
