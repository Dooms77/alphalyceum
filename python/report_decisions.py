import json
import argparse
import datetime as dt
from pathlib import Path
from collections import Counter, defaultdict

BASE = Path(__file__).resolve().parents[1]
LOG_PATH = BASE / "data" / "decision_log.jsonl"


def _parse_ts(v: str):
    try:
        return dt.datetime.fromisoformat(str(v).replace("Z", "+00:00")).astimezone(dt.timezone.utc)
    except Exception:
        return None


def load_rows(path: Path):
    if not path.exists():
        return []
    rows = []
    for ln in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        ln = ln.strip()
        if not ln:
            continue
        try:
            rows.append(json.loads(ln))
        except Exception:
            continue
    return rows


def build_report(rows: list[dict], hours: int = 24):
    now = dt.datetime.now(dt.timezone.utc)
    start = now - dt.timedelta(hours=hours)

    scoped = []
    for r in rows:
        t = _parse_ts(r.get("ts_utc"))
        if not t:
            continue
        if t >= start:
            scoped.append(r)

    by_symbol = defaultdict(list)
    for r in scoped:
        by_symbol[str(r.get("symbol", "-"))].append(r)

    lines = []
    lines.append(f"AlphaLyceum V2 Decision Report | last {hours}h")
    lines.append(f"Total rows: {len(scoped)}")

    status_all = Counter([str(x.get("status", "-")) for x in scoped])
    if status_all:
        lines.append("Status total: " + ", ".join([f"{k}={v}" for k, v in status_all.items()]))

    for sym, arr in sorted(by_symbol.items()):
        c = Counter([str(x.get("status", "-")) for x in arr])
        q = [int(x.get("quality_score", 0) or 0) for x in arr]
        avg_q = round(sum(q) / len(q), 2) if q else 0
        ok_q = [int(x.get("quality_score", 0) or 0) for x in arr if str(x.get("status", "")).upper() == "OK"]
        lines.append(
            f"- {sym}: n={len(arr)}, avgQ={avg_q}, OK={c.get('OK',0)}, HOLD_NEWS={c.get('HOLD_NEWS',0)}, NO-TRADE={c.get('NO-TRADE',0)}"
        )
        if ok_q:
            lines.append(f"  OK quality avg={round(sum(ok_q)/len(ok_q),2)}")

    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--hours", type=int, default=24)
    ap.add_argument("--out", default="")
    args = ap.parse_args()

    rows = load_rows(LOG_PATH)
    rep = build_report(rows, hours=max(1, args.hours))
    print(rep)

    if args.out:
        outp = Path(args.out)
        outp.parent.mkdir(parents=True, exist_ok=True)
        outp.write_text(rep, encoding="utf-8")


if __name__ == "__main__":
    main()
