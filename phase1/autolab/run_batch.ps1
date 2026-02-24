param(
  [string]$ConfigPath = "D:\alphalyceum\phase1\autolab\configs\autolab.json"
)

$ErrorActionPreference = 'Stop'

if(!(Test-Path $ConfigPath)){ throw "Config not found: $ConfigPath" }
$config = Get-Content $ConfigPath -Raw | ConvertFrom-Json

$terminal = $config.terminal_path
$grid = $config.grid_file
$reportsDir = $config.reports_dir
$runsDir = "D:\alphalyceum\phase1\autolab\runs"

New-Item -ItemType Directory -Force -Path $reportsDir,$runsDir | Out-Null
if(!(Test-Path $terminal)){ throw "terminal64 not found: $terminal" }
if(!(Test-Path $grid)){ throw "Grid not found: $grid" }

$rows = Import-Csv $grid
foreach($r in $rows){
  $runId = $r.run_id
  $iniPath = Join-Path $runsDir "$runId.ini"
  $reportBase = Join-Path $reportsDir ($runId + '.htm')

  $testerInputs = @()
  foreach($p in $r.PSObject.Properties){
    if($p.Name -eq 'run_id'){ continue }
    $testerInputs += "$($p.Name)=$($p.Value)"
  }
  $testerInputs += "InpRunId=$runId"

  $ini = @"
[Tester]
Expert=$($config.expert_name)
Symbol=$($config.symbol)
Period=$($config.period)
Model=$($config.model)
ExecutionMode=$($config.execution_mode)
Optimization=0
FromDate=$($config.from_date)
ToDate=$($config.to_date)
ForwardMode=0
Deposit=$($config.deposit)
Currency=$($config.currency)
Leverage=$($config.leverage)
Report=$reportBase
ReplaceReport=$($config.replace_report)
ShutdownTerminal=$($config.shutdown_terminal)
Visual=$($config.visual)

[TesterInputs]
$($testerInputs -join "`n")
"@

  $ini | Set-Content -Path $iniPath -Encoding ASCII
  Write-Host "[AUTOLAB] Running $runId"
  & $terminal "/config:$iniPath" | Out-Null
}

Write-Host "[AUTOLAB] Batch finished. Reports at $reportsDir"
