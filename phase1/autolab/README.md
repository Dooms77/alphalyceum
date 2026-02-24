# AlphaLyceum AUTOLAB

Pipeline otomatis untuk backtest + parse + ranking strategi MT5.

## Struktur
- `configs/autolab.json` : konfigurasi terminal/test range
- `grids/*.csv` : grid parameter
- `run_batch.ps1` : jalankan backtest batch ke MT5
- `parse_reports.py` : baca report HTML MT5 -> summary.csv
- `optimize.py` : ranking hasil + pilih best run
- `results/` : output summary/ranking/best_run

## Jalankan full pipeline
1) Jalankan batch:
```powershell
powershell -ExecutionPolicy Bypass -File D:\alphalyceum\phase1\autolab\run_batch.ps1
```

2) Parse report:
```bash
py D:\alphalyceum\phase1\autolab\parse_reports.py
```

3) Optimasi ranking:
```bash
py D:\alphalyceum\phase1\autolab\optimize.py
```

## Catatan
- Jika MT5 update/restart di tengah batch, rerun batch.
- Report harus tersimpan dalam format HTML di folder `autolab/reports`.
- Fokus evaluasi: PF > 1, DD terkendali, trade count cukup, expectancy positif.
