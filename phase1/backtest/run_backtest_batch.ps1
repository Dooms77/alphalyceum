$ErrorActionPreference = 'Stop'

$base = 'D:\alphalyceum\phase1\backtest'
$grid = Join-Path $base 'parameter_grid.csv'
$configDir = Join-Path $base 'configs'
$reportDir = Join-Path $base 'reports'
$resultDir = Join-Path $base 'results'
$summary = Join-Path $resultDir 'summary.csv'

New-Item -ItemType Directory -Force -Path $configDir,$reportDir,$resultDir | Out-Null

$terminal = 'C:\Program Files\MetaTrader 5\terminal64.exe'
if(!(Test-Path $terminal)){
  throw "terminal64.exe not found at $terminal"
}

$eaName = 'AlphaLyceumSignalEA.ex5'
$symbol = 'BTCUSD.vx'
$period = 'M15'
$from = '2025.08.01'
$to = '2026.02.14'
$deposit = '10000'
$currency = 'USD'
$leverage = '1:100'

if(!(Test-Path $summary)){
  'run_id,variant,adx_min,rsi_low,rsi_high,rr,sl_mode,atr_mult,session_filter,net_profit,profit_factor,max_drawdown_pct,trades,oos_ratio,notes' | Out-File -FilePath $summary -Encoding utf8
}

$rows = Import-Csv $grid
$idx = 0
foreach($r in $rows){
  $idx++
  $runId = ('run_{0:000}' -f $idx)
  $setPath = Join-Path $configDir "$runId.ini"
  $reportPath = Join-Path $reportDir "$runId"

  $ini = @"
[Tester]
Expert=$eaName
ExpertParameters=
Symbol=$symbol
Period=$period
Model=1
ExecutionMode=28
Optimization=0
FromDate=$from
ToDate=$to
ForwardMode=0
Deposit=$deposit
Currency=$currency
Leverage=$leverage
Report=$reportPath
ReplaceReport=1
ShutdownTerminal=1
Visual=0

[TesterInputs]
InpSymbol=$symbol
InpTF=15
InpEMAPeriod=50
InpRSIPeriod=3
InpRSILow=$($r.rsi_low)
InpRSIHigh=$($r.rsi_high)
InpADXPeriod=5
InpADXMin=$($r.adx_min)
InpSwingLookback=5
InpRR=$($r.rr)
InpUseCommonFile=false
InpOutFile=alphalyceum_signals.jsonl
InpShowIndicators=false
InpShowStatusPanel=false
"@

  $ini | Out-File -FilePath $setPath -Encoding ascii

  Write-Host "Running $runId ..."
  & $terminal /config:$setPath | Out-Null

  # Placeholder result row - isi metrik manual/import parser report nanti
  "$runId,$($r.variant),$($r.adx_min),$($r.rsi_low),$($r.rsi_high),$($r.rr),$($r.sl_mode),$($r.atr_mult),$($r.session_filter),0,0,0,0,0,pending_parse" | Add-Content -Path $summary
}

Write-Host "Batch complete. Summary: $summary"
Write-Host "Next: parse reports lalu isi metric (net_profit, PF, DD, trades, OOS)."
