# AlphaLyceum Phase 1.5 - Backtest Batch Runner

## Tujuan
Menjalankan backtest batch untuk Strategy V2 (BTCUSD.vx M15) dan ranking setup paling robust.

## File utama
- `parameter_grid.csv` : kombinasi parameter yang diuji
- `run_backtest_batch.ps1` : generator config + executor MT5 tester
- `summarize_results.py` : parser ringkasan report CSV

## Cara jalan
```powershell
cd D:\alphalyceum\phase1\backtest
powershell -ExecutionPolicy Bypass -File .\run_backtest_batch.ps1
```

## Output
- Config tiap test: `backtest/configs/*.ini`
- Report MT5: `backtest/reports/*.htm`
- Ringkasan: `backtest/results/summary.csv`
- Ranking robust: `backtest/results/ranking.csv`

## Catatan
- Pastikan symbol `BTCUSD.vx` tersedia di Market Watch.
- Gunakan data historis cukup panjang (minimal 6-12 bulan untuk awal).
- Fokus pada robustness: PF, DD, trade count, kestabilan lintas parameter.
