import json
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

from telegram_publisher import (
    format_signal_message,
    format_signal_result_message,
    send_telegram_message,
)


def _ts() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def log(msg: str) -> None:
    print(f"[{_ts()}] {msg}", flush=True)


def load_config(config_path: str) -> dict:
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_state(state_file: str) -> dict:
    if not os.path.exists(state_file):
        return {"offset": 0, "sent_ids": [], "active_signals": {}, "closed_results": {}}
    with open(state_file, "r", encoding="utf-8") as f:
        state = json.load(f)
    state.setdefault("active_signals", {})
    state.setdefault("closed_results", {})
    return state


def save_state(state_file: str, state: dict) -> None:
    Path(state_file).parent.mkdir(parents=True, exist_ok=True)
    with open(state_file, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)


def _safe_id(signal: Dict[str, Any]) -> str:
    sid = signal.get("id")
    if sid is None:
        return ""
    return str(sid)


def _to_float(v: Any) -> float | None:
    try:
        if v is None or v == "":
            return None
        return float(v)
    except Exception:
        return None


def _load_price_map(price_file: str) -> Dict[str, Dict[str, Any]]:
    if not price_file or (not os.path.exists(price_file)):
        return {}

    # Supports:
    # 1) JSON object map: {"XAUUSD.vx": {"price": 4688.0, "time": "..."}, ...}
    # 2) JSONL rows: {"pair":"XAUUSD.vx","price":4688.0,"time":"..."}
    try:
        with open(price_file, "r", encoding="utf-8") as f:
            raw = f.read().strip()
        if not raw:
            return {}

        if raw.startswith("{"):
            try:
                obj = json.loads(raw)
                out = {}
                for k, v in (obj or {}).items():
                    if isinstance(v, dict):
                        price = _to_float(v.get("price") or v.get("bid") or v.get("last"))
                        if price is not None:
                            out[str(k)] = {
                                "price": price,
                                "time": str(v.get("time") or v.get("ts") or _ts()),
                            }
                    else:
                        price = _to_float(v)
                        if price is not None:
                            out[str(k)] = {"price": price, "time": _ts()}
                if out:
                    return out
            except Exception:
                # if not a single JSON object, fall through to JSONL parsing
                pass

        out = {}
        for ln in raw.splitlines()[-200:]:
            ln = ln.strip()
            if not ln:
                continue
            try:
                row = json.loads(ln)
            except Exception:
                continue
            pair = str(row.get("pair") or row.get("symbol") or "").strip()
            if not pair:
                continue
            price = _to_float(row.get("price") or row.get("bid") or row.get("last"))
            if price is None:
                continue
            out[pair] = {
                "price": price,
                "time": str(row.get("time") or row.get("ts") or _ts()),
            }
        return out
    except Exception:
        return {}


def _signal_duration_min(signal: Dict[str, Any], hit_time: str) -> float | None:
    st = str(signal.get("signal_time") or "").strip()
    if not st:
        return None
    fmt_candidates = ["%Y.%m.%d %H:%M", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%S"]
    sdt = None
    hdt = None
    for f in fmt_candidates:
        try:
            sdt = datetime.strptime(st, f)
            break
        except Exception:
            continue
    for f in fmt_candidates:
        try:
            hdt = datetime.strptime(hit_time, f)
            break
        except Exception:
            continue
    if not sdt or not hdt:
        return None
    return max(0.0, (hdt - sdt).total_seconds() / 60.0)


def _evaluate_result(signal: Dict[str, Any], price: float) -> str | None:
    side = str(signal.get("side", "")).upper()
    tp = _to_float(signal.get("tp"))
    sl = _to_float(signal.get("sl"))
    if tp is None or sl is None:
        return None

    # conservative order: for BUY check SL then TP, for SELL check SL then TP
    # to avoid over-claiming TP in violent move bars.
    if side == "BUY":
        if price <= sl:
            return "SL_HIT"
        if price >= tp:
            return "TP_HIT"
    elif side == "SELL":
        if price >= sl:
            return "SL_HIT"
        if price <= tp:
            return "TP_HIT"
    return None


def _load_recent_signals(signal_file: str, limit: int = 200) -> list[Dict[str, Any]]:
    if not os.path.exists(signal_file):
        return []
    out = []
    try:
        with open(signal_file, "r", encoding="utf-8") as f:
            lines = f.read().splitlines()
        for ln in lines[-limit:]:
            ln = ln.strip()
            if not ln:
                continue
            try:
                out.append(json.loads(ln))
            except Exception:
                continue
    except Exception:
        return []
    return out


def _bootstrap_active_signals_from_history(signal_file: str, sent_ids: set[str], active_signals: Dict[str, Dict[str, Any]], closed_results: Dict[str, Dict[str, Any]], max_bootstrap: int = 2) -> int:
    if active_signals:
        return 0
    # only bootstrap a small tail to avoid blasting old history results
    recent = _load_recent_signals(signal_file, limit=80)
    added = 0
    for s in reversed(recent):
        sid = _safe_id(s)
        if not sid:
            continue
        if sid not in sent_ids:
            continue
        if sid in closed_results:
            continue
        if sid in active_signals:
            continue
        active_signals[sid] = {
            "id": sid,
            "pair": s.get("pair"),
            "tf": s.get("tf"),
            "side": s.get("side"),
            "entry": s.get("entry"),
            "sl": s.get("sl"),
            "tp": s.get("tp"),
            "signal_time": s.get("signal_time") or s.get("time") or _ts(),
            "opened_at": _ts(),
            "status": "OPEN",
        }
        added += 1
        if added >= max_bootstrap:
            break
    return added


def run_once(config_path: str = "../config/config.json") -> None:
    cfg = load_config(config_path)

    purpose = cfg.get("telegram", {}).get("purpose")
    if purpose and purpose != "alphalyceum_trading_only":
        raise ValueError(
            f"Refusing to send: telegram purpose '{purpose}' is not 'alphalyceum_trading_only'"
        )

    signal_file = cfg["signal_file"]
    state = load_state(cfg["state_file"])

    if not os.path.exists(signal_file):
        log(f"Signal file not found: {signal_file}")
        return

    file_size = os.path.getsize(signal_file)
    offset = int(state.get("offset", 0) or 0)
    if offset > file_size:
        log(f"Offset ({offset}) > file size ({file_size}), reset to 0 (rotation/truncate detected)")
        offset = 0

    sent_ids = set(str(x) for x in state.get("sent_ids", []))
    active_signals: Dict[str, Dict[str, Any]] = dict(state.get("active_signals", {}))
    closed_results: Dict[str, Dict[str, Any]] = dict(state.get("closed_results", {}))

    max_per_run = int(cfg.get("runtime", {}).get("max_messages_per_run", 3))
    sleep_between = float(cfg.get("runtime", {}).get("sleep_between_sends_sec", 1.2))

    monitor_cfg = cfg.get("monitoring", {})
    monitoring_enabled = bool(monitor_cfg.get("enabled", True))
    price_file = str(monitor_cfg.get("price_file", "")).strip()

    filters = cfg.get("filters", {})
    allowed_tf = filters["allowed_tf"]

    # Backward compatible: allow either one symbol (allowed_symbol)
    # or many symbols (allowed_symbols)
    allowed_symbols = set()
    if isinstance(filters.get("allowed_symbols"), list):
        allowed_symbols = {str(x) for x in filters.get("allowed_symbols", []) if str(x).strip()}
    if not allowed_symbols and filters.get("allowed_symbol"):
        allowed_symbols = {str(filters.get("allowed_symbol"))}

    # Bootstrap tracker for previously-sent signals (before lifecycle feature existed)
    boot_added = _bootstrap_active_signals_from_history(signal_file, sent_ids, active_signals, closed_results)
    if boot_added > 0:
        log(f"Bootstrapped active signals from history: {boot_added}")

    sent_count = 0
    scanned_lines = 0
    new_offset = offset

    with open(signal_file, "r", encoding="utf-8") as f:
        f.seek(offset)

        while True:
            line_start = f.tell()
            line = f.readline()
            if not line:
                new_offset = f.tell()
                break

            scanned_lines += 1
            line = line.strip()
            if not line:
                new_offset = f.tell()
                continue

            try:
                s = json.loads(line)
            except json.JSONDecodeError:
                log("Skip malformed JSON line")
                new_offset = f.tell()
                continue

            sid = _safe_id(s)

            # If this run already hit cap, keep offset at current line for next run.
            if sent_count >= max_per_run:
                new_offset = line_start
                log(f"Reached max messages/run ({max_per_run}), will continue next cycle")
                break

            if sid and sid in sent_ids:
                new_offset = f.tell()
                continue

            if s.get("pair") not in allowed_symbols or s.get("tf") != allowed_tf:
                new_offset = f.tell()
                continue

            text = format_signal_message(s)
            try:
                send_telegram_message(
                    cfg["telegram"]["bot_token"],
                    cfg["telegram"]["chat_id"],
                    text,
                )
            except Exception as e:
                # Do not advance offset so the same signal retries on next loop.
                new_offset = line_start
                log(f"Send failed for signal id={sid or '-'}: {e}")
                break

            if sid:
                sent_ids.add(sid)
                # Start lifecycle tracking for TP/SL updates
                active_signals[sid] = {
                    "id": sid,
                    "pair": s.get("pair"),
                    "tf": s.get("tf"),
                    "side": s.get("side"),
                    "entry": s.get("entry"),
                    "sl": s.get("sl"),
                    "tp": s.get("tp"),
                    "signal_time": s.get("signal_time") or s.get("time") or _ts(),
                    "opened_at": _ts(),
                    "status": "OPEN",
                }
            sent_count += 1
            new_offset = f.tell()
            log(f"Sent signal id={sid or '-'} pair={s.get('pair')} tf={s.get('tf')} side={s.get('side')}")

            if sent_count < max_per_run:
                time.sleep(sleep_between)

    # Evaluate active signals against latest MT5 prices and send TP/SL updates.
    lifecycle_updates = 0
    if monitoring_enabled and active_signals:
        price_map = _load_price_map(price_file)
        if not price_map:
            log(f"Monitoring enabled but no price map loaded (price_file='{price_file}')")
        else:
            for sid, sig in list(active_signals.items()):
                pair = str(sig.get("pair") or "")
                px = _to_float((price_map.get(pair) or {}).get("price"))
                hit_time = str((price_map.get(pair) or {}).get("time") or _ts())
                if px is None:
                    continue

                result = _evaluate_result(sig, px)
                if not result:
                    continue

                # avoid duplicate closure posts
                if sid in closed_results:
                    active_signals.pop(sid, None)
                    continue

                duration_min = _signal_duration_min(sig, hit_time)
                msg = format_signal_result_message(sig, result=result, hit_price=px, hit_time=hit_time, duration_min=duration_min)
                try:
                    send_telegram_message(cfg["telegram"]["bot_token"], cfg["telegram"]["chat_id"], msg)
                except Exception as e:
                    log(f"Result send failed for id={sid}: {e}")
                    continue

                closed_results[sid] = {
                    "id": sid,
                    "result": result,
                    "hit_price": px,
                    "hit_time": hit_time,
                    "duration_min": duration_min,
                    "closed_at": _ts(),
                }
                active_signals.pop(sid, None)
                lifecycle_updates += 1
                log(f"Closed signal id={sid} result={result} pair={pair} price={px}")

    # Keep recent IDs in stable order.
    sent_ids_tail = sorted(sent_ids)[-2000:]
    # Keep closed results bounded.
    if len(closed_results) > 4000:
        # approximate trim by key sort
        for k in sorted(closed_results.keys())[:-3000]:
            closed_results.pop(k, None)

    state["offset"] = new_offset
    state["sent_ids"] = sent_ids_tail
    state["active_signals"] = active_signals
    state["closed_results"] = closed_results
    state["last_run_at"] = _ts()
    state["last_run_stats"] = {
        "scanned_lines": scanned_lines,
        "sent_count": sent_count,
        "bootstrapped_active": boot_added,
        "lifecycle_updates": lifecycle_updates,
        "active_open": len(active_signals),
        "offset_before": offset,
        "offset_after": new_offset,
        "file_size": file_size,
    }
    save_state(cfg["state_file"], state)

    log(
        f"Run done: scanned={scanned_lines}, sent={sent_count}, offset {offset}->{new_offset}, file_size={file_size}"
    )


if __name__ == "__main__":
    run_once()
