#!/usr/bin/env python3
import json, time
from pathlib import Path

signal_file = r"C:/Users/AORUS/AppData/Roaming/MetaQuotes/Terminal/Common/Files/alphalyceum_signals_live_m5.jsonl"
test_entry = {
    "id": "TEST-JARVIS-20260216-2000-BUY",
    "pair": "BTCUSD.vx",
    "tf": "PERIOD_M5",
    "side": "BUY",
    "entry": 68000,
    "sl": 67900,
    "tp": 68200,
    "rr": "1:2",
    "adx": 25,
    "rsi": 50,
    "signal_time": "2026-02-16 20:00:00",
    "source": "jarvis_test"
}
with open(signal_file, 'a', encoding='utf-8') as f:
    f.write(json.dumps(test_entry) + '\n')
print(f"Injected test signal to {signal_file}")
