# AlphaLyceum V2 (Signal + Insight Engine)

## Objective
Build Bot V2 for **swing + intraday insights** with:
- TradingView chart context
- News context
- Structured Telegram output

## Scope v0.1
1. Ingest chart context (placeholder adapter)
2. Ingest news context (placeholder adapter)
3. Build unified analysis payload
4. Generate Telegram message format (insight-oriented)

## Runtime flow
1. `tradingview_ingest.py` -> chart snapshot/context payload
2. `news_ingest.py` -> macro/news payload
3. `v2_signal_router.py` merges + scores bias
4. `message_formatter.py` formats final Telegram post

## Next integration
- Plug real TradingView source/API
- Plug real news source/API
- Add scheduler (every X minutes)
- Add Telegram publisher binding

## GPT Codex OAuth Fallback (project-local account)
V2 default tetap pakai Ollama (`deepseek-r1:14b`).
Jika output Ollama kosong/timeout, bot fallback ke GPT Codex via OAuth **khusus project V2**
(tanpa pakai auth profile OpenClaw utama).

### Setup akun OAuth terpisah untuk V2
1. Jalankan login helper:
```powershell
python D:\alphalyceum\v2\python\oauth_login_project.py
```
2. Login pakai akun GPT yang ingin dipakai khusus V2.
3. Paste callback URL saat diminta.
4. Token disimpan di:
`D:/alphalyceum/v2/config/oauth_project.json`

Config: `v2/config/v2_config.json` -> `analysis.openai_oauth`
- `enabled`: aktifkan fallback OAuth
- `credentials_file`: lokasi token OAuth project
- `model`: target model fallback (`gpt-5-codex`)
- `token_url`, `client_id`, `scope`: parameter OAuth

Catatan: ini flow OAuth project-local, jadi tidak mengubah konfigurasi OpenClaw global.
