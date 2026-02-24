import json
import datetime as dt
from pathlib import Path
from collections import defaultdict

BASE = Path(__file__).resolve().parents[1]
LOG_PATH = BASE / "data" / "decision_log.jsonl"
OUT_DIR = BASE / "content_out"


def load_rows():
    if not LOG_PATH.exists():
        return []
    out = []
    for ln in LOG_PATH.read_text(encoding="utf-8", errors="ignore").splitlines():
        ln = ln.strip()
        if not ln:
            continue
        try:
            out.append(json.loads(ln))
        except Exception:
            continue
    return out


def last_hours(rows, hours=24):
    now = dt.datetime.now(dt.timezone.utc)
    start = now - dt.timedelta(hours=hours)
    out = []
    for r in rows:
        try:
            t = dt.datetime.fromisoformat(str(r.get("ts_utc", "")).replace("Z", "+00:00")).astimezone(dt.timezone.utc)
        except Exception:
            continue
        if t >= start:
            out.append(r)
    return out


def build_daily_brief(rows):
    by = defaultdict(list)
    for r in rows:
        by[str(r.get("symbol", "-"))].append(r)

    lines = ["📈 Daily Market Brief AlphaLyceum", ""]
    for sym in ["BTCUSD.vx", "XAUUSD.vx"]:
        arr = by.get(sym, [])
        if not arr:
            lines.append(f"• {sym.replace('.vx','')}: belum ada data cukup hari ini")
            continue
        latest = arr[-1]
        status = latest.get("status", "-")
        score = latest.get("quality_score", "-")
        reason = latest.get("reason", "-")
        bias = latest.get("bias", "-")
        lines.append(f"• {sym.replace('.vx','')}: {status} | bias {str(bias).upper()} | score {score}")
        lines.append(f"  alasan: {reason}")
    lines.append("")
    lines.append("⚠️ NFA. Edukasi, bukan ajakan transaksi.")
    return "\n".join(lines)


def build_signal_recap(rows):
    c = defaultdict(lambda: defaultdict(int))
    for r in rows:
        sym = str(r.get("symbol", "-"))
        st = str(r.get("status", "-"))
        c[sym][st] += 1

    lines = ["🧾 Signal Recap 24h", ""]
    for sym in ["BTCUSD.vx", "XAUUSD.vx"]:
        d = c.get(sym, {})
        lines.append(
            f"• {sym.replace('.vx','')}: OK={d.get('OK',0)} | HOLD_NEWS={d.get('HOLD_NEWS',0)} | NO-TRADE={d.get('NO-TRADE',0)}"
        )
    lines.append("")
    lines.append("Fokus: kualitas setup > kuantitas sinyal.")
    return "\n".join(lines)


def build_short_script(rows):
    btc = [r for r in rows if str(r.get("symbol")) == "BTCUSD.vx"]
    xau = [r for r in rows if str(r.get("symbol")) == "XAUUSD.vx"]
    b = btc[-1] if btc else {}
    x = xau[-1] if xau else {}

    return (
        "HOOK: Hari ini market ngasih sinyal jelas atau malah jebakan?\n\n"
        f"BTC sekarang status {b.get('status','-')} dengan score {b.get('quality_score','-')}. "
        f"Alasan utamanya: {b.get('reason','-')}.\n"
        f"Gold/XAU status {x.get('status','-')} dengan score {x.get('quality_score','-')}. "
        f"Catatan penting: {x.get('reason','-')}.\n\n"
        "INTI: kita cuma ambil setup yang lolos quality gate, bukan nebak arah.\n"
        "CTA: Mau lanjut aku bikin breakdown entry plan per pair?"
    )


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    rows = last_hours(load_rows(), 24)

    daily = build_daily_brief(rows)
    recap = build_signal_recap(rows)
    short = build_short_script(rows)

    (OUT_DIR / "daily_market_brief.txt").write_text(daily, encoding="utf-8")
    (OUT_DIR / "signal_recap_24h.txt").write_text(recap, encoding="utf-8")
    (OUT_DIR / "short_script_tiktok.txt").write_text(short, encoding="utf-8")

    print("Generated:")
    print("- content_out/daily_market_brief.txt")
    print("- content_out/signal_recap_24h.txt")
    print("- content_out/short_script_tiktok.txt")


if __name__ == "__main__":
    main()
