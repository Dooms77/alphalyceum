import csv
import json
import argparse
import datetime as dt
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
OPS_DIR = BASE / "content_ops"
CONFIG_PATH = OPS_DIR / "config_content_ops.json"
DB_CSV_PATH = OPS_DIR / "content_db.csv"
OUT_CAROUSEL = OPS_DIR / "out" / "carousel"
OUT_VIDEO = OPS_DIR / "out" / "video"

VALID_STATUS = [
    "IDEA",
    "SCRIPT_DONE",
    "CAROUSEL_DONE",
    "VIDEO_DONE",
    "READY_POST",
    "POSTED",
    "ARCHIVED",
]


def _now_iso():
    return dt.datetime.now(dt.timezone.utc).isoformat()


def load_config():
    if not CONFIG_PATH.exists():
        return {
            "timezone": "Asia/Makassar",
            "default_platform": "telegram",
            "video_duration_sec": 25,
            "enable_auto_ready_post": True,
        }
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def load_rows():
    if not DB_CSV_PATH.exists():
        return []
    with DB_CSV_PATH.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def save_rows(rows):
    DB_CSV_PATH.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "id", "created_at", "date_plan", "pair", "angle", "hook", "caption", "cta",
        "script_short", "carousel_asset", "video_asset", "status", "platform", "posted_at", "post_url", "notes"
    ]
    with DB_CSV_PATH.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in rows:
            row = {k: r.get(k, "") for k in fields}
            if row["status"] not in VALID_STATUS:
                row["status"] = "IDEA"
            w.writerow(row)


def ensure_bootstrap_files():
    OPS_DIR.mkdir(parents=True, exist_ok=True)
    OUT_CAROUSEL.mkdir(parents=True, exist_ok=True)
    OUT_VIDEO.mkdir(parents=True, exist_ok=True)

    if not CONFIG_PATH.exists():
        CONFIG_PATH.write_text(json.dumps({
            "timezone": "Asia/Makassar",
            "default_platform": "telegram",
            "video_duration_sec": 25,
            "enable_auto_ready_post": True
        }, indent=2, ensure_ascii=False), encoding="utf-8")

    if not DB_CSV_PATH.exists():
        save_rows([{
            "id": "CNT-0001",
            "created_at": _now_iso(),
            "date_plan": dt.date.today().isoformat(),
            "pair": "BTCUSD",
            "angle": "Market structure + anti-FOMO",
            "hook": "90% trader hari ini masuk terlalu cepat.",
            "caption": "Struktur masih berat ke seller. Tunggu konfirmasi, jangan kejebak FOMO.",
            "cta": "Ketik BTC kalau mau level invalidation-nya.",
            "script_short": "Hook -> konteks -> skenario -> CTA",
            "carousel_asset": "",
            "video_asset": "",
            "status": "SCRIPT_DONE",
            "platform": "telegram",
            "posted_at": "",
            "post_url": "",
            "notes": "sample row"
        }])


def _slug(x: str):
    return "".join([c if c.isalnum() else "-" for c in (x or "")]).strip("-").lower()[:40]


def generate_carousel(rows):
    changed = 0
    for r in rows:
        if r.get("status") not in {"SCRIPT_DONE"}:
            continue
        cid = r.get("id") or f"CNT-{changed+1:04d}"
        title = f"{r.get('pair','PAIR')} | {r.get('angle','Angle')}"
        content = [
            f"SLIDE1 HOOK: {r.get('hook','')}",
            f"SLIDE2 CONTEXT: {r.get('caption','')}",
            f"SLIDE3 PLAN: Fokus konfirmasi + risk management",
            f"SLIDE4 CTA: {r.get('cta','')}",
        ]
        out = OUT_CAROUSEL / f"{cid}_{_slug(title)}.txt"
        out.write_text("\n".join(content), encoding="utf-8")
        r["carousel_asset"] = str(out)
        r["status"] = "CAROUSEL_DONE"
        changed += 1
    return changed


def generate_short_video(rows, duration_sec=25):
    changed = 0
    for r in rows:
        if r.get("status") not in {"CAROUSEL_DONE", "SCRIPT_DONE"}:
            continue
        cid = r.get("id") or f"CNT-{changed+1:04d}"
        script = (
            f"HOOK: {r.get('hook','')}\n"
            f"BODY: {r.get('caption','')}\n"
            f"PLAN: Tunggu konfirmasi valid, hindari entry emosional.\n"
            f"CTA: {r.get('cta','')}\n"
            f"DURASI_TARGET: {duration_sec}s"
        )
        out = OUT_VIDEO / f"{cid}_short_script.txt"
        out.write_text(script, encoding="utf-8")
        r["video_asset"] = str(out)
        r["status"] = "VIDEO_DONE"
        changed += 1
    return changed


def mark_ready_post(rows, auto=True):
    if not auto:
        return 0
    changed = 0
    for r in rows:
        if r.get("status") == "VIDEO_DONE" and r.get("carousel_asset") and r.get("video_asset"):
            r["status"] = "READY_POST"
            changed += 1
    return changed


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--step", choices=["bootstrap", "carousel", "video", "ready", "all"], default="all")
    args = ap.parse_args()

    ensure_bootstrap_files()
    cfg = load_config()
    rows = load_rows()

    if args.step == "bootstrap":
        save_rows(rows)
        print("bootstrap ok")
        return

    c1 = c2 = c3 = 0
    if args.step in {"carousel", "all"}:
        c1 = generate_carousel(rows)
    if args.step in {"video", "all"}:
        c2 = generate_short_video(rows, duration_sec=int(cfg.get("video_duration_sec", 25)))
    if args.step in {"ready", "all"}:
        c3 = mark_ready_post(rows, auto=bool(cfg.get("enable_auto_ready_post", True)))

    save_rows(rows)
    print(json.dumps({
        "carousel_generated": c1,
        "video_generated": c2,
        "ready_marked": c3,
        "db": str(DB_CSV_PATH)
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
