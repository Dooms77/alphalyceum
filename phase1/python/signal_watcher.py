import json
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

from telegram_publisher import format_signal_message, send_telegram_message


def _ts() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def log(msg: str) -> None:
    print(f"[{_ts()}] {msg}", flush=True)


def load_config(config_path: str) -> dict:
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_state(state_file: str) -> dict:
    if not os.path.exists(state_file):
        return {"offset": 0, "sent_ids": []}
    with open(state_file, "r", encoding="utf-8") as f:
        return json.load(f)


def save_state(state_file: str, state: dict) -> None:
    Path(state_file).parent.mkdir(parents=True, exist_ok=True)
    with open(state_file, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)


def _safe_id(signal: Dict[str, Any]) -> str:
    sid = signal.get("id")
    if sid is None:
        return ""
    return str(sid)


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
    max_per_run = int(cfg.get("runtime", {}).get("max_messages_per_run", 3))
    sleep_between = float(cfg.get("runtime", {}).get("sleep_between_sends_sec", 1.2))

    filters = cfg.get("filters", {})
    allowed_tf = filters["allowed_tf"]

    # Backward compatible: allow either one symbol (allowed_symbol)
    # or many symbols (allowed_symbols)
    allowed_symbols = set()
    if isinstance(filters.get("allowed_symbols"), list):
        allowed_symbols = {str(x) for x in filters.get("allowed_symbols", []) if str(x).strip()}
    if not allowed_symbols and filters.get("allowed_symbol"):
        allowed_symbols = {str(filters.get("allowed_symbol"))}

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
            sent_count += 1
            new_offset = f.tell()
            log(f"Sent signal id={sid or '-'} pair={s.get('pair')} tf={s.get('tf')} side={s.get('side')}")

            if sent_count < max_per_run:
                time.sleep(sleep_between)

    # Keep recent IDs in stable order.
    sent_ids_tail = sorted(sent_ids)[-2000:]
    state["offset"] = new_offset
    state["sent_ids"] = sent_ids_tail
    state["last_run_at"] = _ts()
    state["last_run_stats"] = {
        "scanned_lines": scanned_lines,
        "sent_count": sent_count,
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
