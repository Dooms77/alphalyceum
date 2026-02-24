import argparse
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

from signal_watcher import load_config, run_once, load_state


def append_test_signal(signal_file: str, pair: str, tf: str) -> str:
    test_id = f"HC-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:6]}"
    now_iso = datetime.now(timezone.utc).isoformat()

    payload = {
        "id": test_id,
        "pair": pair,
        "tf": tf,
        "side": "BUY",
        "entry": 99999.0,
        "sl": 99949.0,
        "tp": 100149.0,
        "rr": 3.0,
        "adx": 35.0,
        "rsi": 60.0,
        "signal_time": now_iso,
        "source": "health_check",
    }

    sf = Path(signal_file)
    sf.parent.mkdir(parents=True, exist_ok=True)
    with open(sf, "a", encoding="utf-8") as f:
        f.write(json.dumps(payload, ensure_ascii=False) + "\n")

    return test_id


def main(config_path: str = "../config/config.json") -> int:
    cfg = load_config(config_path)

    purpose = cfg.get("telegram", {}).get("purpose")
    if purpose != "alphalyceum_trading_only":
        raise ValueError(
            "Health-check blocked: telegram purpose must be 'alphalyceum_trading_only'"
        )

    pair = cfg["filters"]["allowed_symbol"]
    tf = cfg["filters"]["allowed_tf"]

    print("[1/3] Menulis test signal ke signal_file...")
    test_id = append_test_signal(cfg["signal_file"], pair, tf)

    print("[2/3] Menjalankan watcher sekali...")
    run_once(config_path)

    print("[3/3] Verifikasi state watcher...")
    state = load_state(cfg["state_file"])
    sent_ids = set(state.get("sent_ids", []))

    if test_id in sent_ids:
        print("✅ HEALTH CHECK OK")
        print(f"   test_id: {test_id}")
        print("   Alur terverifikasi: signal_file -> watcher -> Telegram send")
        return 0

    print("❌ HEALTH CHECK GAGAL")
    print(f"   test_id {test_id} tidak ditemukan di sent_ids")
    return 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="../config/config.json")
    args = parser.parse_args()
    raise SystemExit(main(args.config))
