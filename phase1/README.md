# AlphaLyceum - Phase 1 (Signal Bot First)

## Scope fase 1
- MT5 **signal-only EA** (tidak auto execute order)
- Rule: EMA50 + RSI3(20/80 cross) + ADX5>30 + candle confirmation
- Output signal ke file JSONL
- Python watcher kirim signal ke Telegram

## Struktur
- `mt5/AlphaLyceumSignalEA.mq5` -> EA sinyal
- `python/signal_watcher.py` -> baca sinyal baru & kirim Telegram
- `python/run_phase1.py` -> runner sekali atau loop 60 detik
- `python/news_fetcher.py` -> fetch kalender high-impact (opsional fase 1.5)
- `config/config.example.json` -> template config
- `logs/state.json` -> state offset + dedup

## 1) Setup MT5 EA
1. Buka MetaEditor
2. Copy `mt5/AlphaLyceumSignalEA.mq5` ke:
   `MQL5/Experts/`
3. Compile EA
4. Attach EA ke chart `XAUUSD M15`
5. Enable Algo Trading

EA akan menulis sinyal ke file common:
`C:/Users/AORUS/AppData/Roaming/MetaQuotes/Terminal/Common/Files/alphalyceum_signals.jsonl`

## 2) Setup Python publisher
```bash
cd D:/alphalyceum/phase1/python
py -m pip install -r requirements.txt
```

Copy config:
```bash
copy D:\alphalyceum\phase1\config\config.example.json D:\alphalyceum\phase1\config\config.json
```

Lalu isi:
- `telegram.bot_token`
- `telegram.chat_id`

## 3) Run
Sekali jalan:
```bash
cd D:/alphalyceum/phase1/python
py run_phase1.py --config ../config/config.json
```

Loop 24/7 (cek tiap 60 detik):
```bash
py run_phase1.py --config ../config/config.json --loop
```

## 4) Rekomendasi operasi
- Jalankan MT5 + Python worker bersamaan
- Windows Power plan: Never Sleep
- Pakai Task Scheduler untuk auto-start saat boot

### Hardening ops (baru)
Script tambahan di `python/`:
- `watcher_watchdog.ps1` -> cek health watcher; auto-restart jika mati/stale
- `rotate_watcher_logs.ps1` -> bersihin log watcher lama
- `smoke_check.ps1` -> smoke check file signal/state + process watcher

Contoh manual run:
```bash
cd D:/alphalyceum/phase1/python
powershell -ExecutionPolicy Bypass -File .\watcher_watchdog.ps1 -Config ..\config\config.json
powershell -ExecutionPolicy Bypass -File .\rotate_watcher_logs.ps1 -WhatIf
powershell -ExecutionPolicy Bypass -File .\smoke_check.ps1 -Config ..\config\config.json
```

## Catatan
- Ini fase 1 untuk validasi signal di akun dummy
- Auto-trading order execution belum diaktifkan
- Semua rule bisa dioptimasi setelah 14 hari forward test
