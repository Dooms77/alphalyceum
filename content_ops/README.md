# Content Ops Bot (AlphaLyceum)

Workflow konten automation berbasis database (CSV/Excel-friendly):

## 1) Database
File utama: `content_ops/content_db.csv`

Init cepat:
1. Copy `content_ops/content_db.template.csv` -> `content_ops/content_db.csv`
2. Edit via Excel sesuai kebutuhan.

Kolom inti:
- `id`, `date_plan`, `pair`, `angle`
- `hook`, `caption`, `cta`, `script_short`
- `carousel_asset`, `video_asset`
- `status` (`IDEA -> SCRIPT_DONE -> CAROUSEL_DONE -> VIDEO_DONE -> READY_POST -> POSTED -> ARCHIVED`)
- `posted_at`, `post_url`, `notes`

> Kamu bisa edit file ini pakai Excel langsung (CSV).

## 2) Generate asset
Jalankan:

```powershell
cd D:\alphalyceum\v2\python
./run_content_ops_pipeline.ps1
```

Output:
- Draft carousel: `content_ops/out/carousel/*.txt`
- Draft short-video script: `content_ops/out/video/*.txt`
- DB diupdate otomatis statusnya.

## 3) Integrasi bot Telegram (yang kamu bangun)
Saat row `status=READY_POST`, bot Telegram kamu bisa:
1. baca row tersebut,
2. kirim caption + asset,
3. update `status=POSTED`, isi `posted_at`, `post_url`.

## Fitur canggih yang disarankan
- A/B hook per konten (`hook_a`, `hook_b`) + tracking performa
- Compliance checker (hindari klaim berlebihan)
- Auto repurpose: 1 ide jadi carousel + short + telegram longpost
- Ranking konten berdasarkan performa (view, save, share, watchtime)
