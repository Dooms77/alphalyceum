$ErrorActionPreference = 'Stop'
$base = Split-Path -Parent $MyInvocation.MyCommand.Path
python "$base\report_decisions.py" --hours 24 --out "$base\..\data\decision_report_24h.txt"
