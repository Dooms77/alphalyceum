#!/usr/bin/env python3
import json, os
from datetime import datetime

signal_path = r"C:/Users/AORUS/AppData/Roaming/MetaQuotes/Terminal/Common/Files/alphalyceum_signals_live_m5.jsonl"
state_path = r"D:/alphalyceum/phase1/logs/state.json"

print("=== Signal File Diagnostic ===")
if not os.path.exists(signal_path):
    print(f"Signal file not found: {signal_path}")
else:
    size = os.path.getsize(signal_path)
    with open(signal_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    print(f"Signal file exists. Lines: {len(lines)}, Bytes: {size}")
    # Show last 3 lines with their timestamps
    print("Last lines:")
    for line in lines[-5:]:
        try:
            obj = json.loads(line)
            id_ = obj.get('id')
            pair = obj.get('pair')
            tf = obj.get('tf')
            side = obj.get('side')
            st = obj.get('signal_time') or obj.get('time')
            print(f"- {id_} | {pair} {tf} {side} @ {st}")
        except Exception as e:
            print(f"- [parse error] {line[:80]}")

print("\n=== State File ===")
if not os.path.exists(state_path):
    print(f"State file not found: {state_path}")
else:
    with open(state_path, 'r') as f:
        state = json.load(f)
    print(json.dumps(state, indent=2))
    offset = state.get('offset', 0)
    last_run = state.get('last_run_at')
    stats = state.get('last_run_stats', {})
    print(f"\nOffset: {offset}")
    print(f"Last run: {last_run}")
    print(f"Stats: scanned={stats.get('scanned_lines')}, sent={stats.get('sent_count')}, offset_before={stats.get('offset_before')}, offset_after={stats.get('offset_after')}, file_size_at_run={stats.get('file_size')}")
    if size < offset:
        print("WARNING: Offset is larger than current file size => file was truncated/rotated. Offset must reset.")
    else:
        remaining = size - offset
        print(f"Remaining bytes after offset: {remaining}")

print("\n=== Check Telegram Bot Token (for signal bot) ===")
cfg_path = r"D:/alphalyceum/phase1/config/config.json"
if os.path.exists(cfg_path):
    with open(cfg_path, 'r') as f:
        cfg = json.load(f)
    tg = cfg.get('telegram', {})
    bot_token = tg.get('bot_token', '')
    chat_id = tg.get('chat_id', '')
    print(f"Signal bot token: {bot_token[:10]}... (len {len(bot_token)})")
    print(f"Target chat_id: {chat_id}")
    allowed = cfg.get('filters', {}).get('allowed_symbols', [])
    print(f"Allowed symbols: {allowed}")
else:
    print(f"Config not found: {cfg_path}")

print("\nTimestamp now:", datetime.now().isoformat())
