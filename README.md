# AlphaLyceum Monorepo (Bot V1 + Bot V2)

Repository ini sekarang menyatukan 2 engine utama AlphaLyceum supaya tracking fitur, commit history, dan rollback lebih rapi.

## Struktur

- `phase1/` → **Bot V1 (scalping M5, MT5 -> watcher -> Telegram)**
- `python/` + `config/` + `data/` → **Bot V2 (swing/intraday insight engine)**

## Tujuan Tiap Bot

### Bot V1 (`phase1/`)
Fokus eksekusi sinyal real-time dari MT5 ke Telegram:
- watcher signal file
- alert & health checks
- scripts watchdog/smoke/rotation
- toolkit backtest/autolab

### Bot V2 (root repo)
Fokus analisa insight berkualitas dengan gate ketat:
- chart context + news context
- policy status: `OK / HOLD_NEWS / NO-TRADE`
- pair cooldown 3 jam
- quality gate min score 75
- news-gate ForexFactory: default `-45/+45`, major event (CPI/NFP/FOMC) `-90/+90`
- audit trail keputusan per cycle di `data/decision_log.jsonl`
- formatter output Telegram yang terstruktur

## Quick Start

### V2 (current main runner)
```powershell
cd D:\alphalyceum\v2\python
python run_v2_once.py --profile balanced
```

Profile options:
- `strict` (lebih selektif)
- `balanced` (default)
- `aggressive` (lebih cepat publish)

### Decision Report (24h)
```powershell
cd D:\alphalyceum\v2\python
./run_decision_report.ps1
```
Output report: `data/decision_report_24h.txt`

### Content Automation (daily outputs)
```powershell
cd D:\alphalyceum\v2\python
./run_content_automation.ps1
```
Generated files (local, not committed):
- `content_out/daily_market_brief.txt`
- `content_out/signal_recap_24h.txt`
- `content_out/short_script_tiktok.txt`

### V1 (legacy/stable signal pipeline)
Lihat dokumentasi detail di:
- `phase1/README.md`
- `phase1/python/run_phase1.py`

## Security & Secrets

File sensitif/runtimes sudah di-ignore via `.gitignore`, termasuk:
- `config/oauth_project.json`
- `phase1/config/config.json`
- `phase1/logs/`
- generated charts/reports/cache

Gunakan file example/template untuk konfigurasi sebelum run di mesin baru.

## Branching & Commit Convention (recommended)

- `main` → stable branch
- `feature/<scope>-<short-name>` → fitur baru
- `fix/<scope>-<short-name>` → bugfix

Commit style:
- `feat(v2): tambah news gating high-impact`
- `fix(v1): stabilkan watcher restart loop`
- `chore(repo): update readme monorepo`

## Roadmap Ringkas

1. Stabilkan publish policy V2 di kondisi live session
2. Hardening adapter ForexFactory + TradingView
3. Integrasi evaluasi performa silang V1/V2
4. Dashboard ringkas untuk audit sinyal dan quality score
