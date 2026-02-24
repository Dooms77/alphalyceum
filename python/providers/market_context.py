import json
from pathlib import Path

PHASE1_CONFIG = Path("D:/alphalyceum/phase1/config/config.json")


def get_latest_market_context(symbol: str) -> dict:
    out = {
        "symbol": symbol,
        "last_price": None,
        "last_side": None,
        "last_signal_time": None,
        "recent_count": 0,
    }

    try:
        cfg = json.loads(PHASE1_CONFIG.read_text(encoding="utf-8"))
        signal_file = Path(cfg.get("signal_file", ""))
        if not signal_file.exists():
            return out

        lines = signal_file.read_text(encoding="utf-8", errors="ignore").splitlines()
        hit = []
        for ln in reversed(lines):
            ln = ln.strip()
            if not ln:
                continue
            try:
                obj = json.loads(ln)
            except Exception:
                continue
            if str(obj.get("pair")) != symbol:
                continue
            sid = str(obj.get("id", ""))
            if sid.startswith(("TEST-", "HC-", "E2E-")):
                continue
            hit.append(obj)
            if len(hit) >= 15:
                break

        if not hit:
            return out

        last = hit[0]
        out["last_price"] = last.get("entry")
        out["last_side"] = last.get("side")
        out["last_signal_time"] = last.get("signal_time")
        out["recent_count"] = len(hit)
        return out
    except Exception:
        return out
