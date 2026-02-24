$ErrorActionPreference = 'Stop'
$base = Split-Path -Parent $MyInvocation.MyCommand.Path
python "$base\content_ops_pipeline.py" --step all
