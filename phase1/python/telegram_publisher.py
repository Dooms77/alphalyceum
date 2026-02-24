import html
import time
from typing import Any, Dict

import requests


def _to_float(value: Any) -> float | None:
    try:
        if value is None or value == "":
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _fmt_num(value: Any, digits: int = 2) -> str:
    n = _to_float(value)
    if n is None:
        return "-"
    return f"{n:.{digits}f}"


def _fmt_rr(signal: Dict[str, Any]) -> str:
    raw = signal.get("rr")

    # Preserve ratio style from EA, e.g. "1:3"
    if isinstance(raw, str):
        cleaned = raw.strip()
        if cleaned:
            if ":" in cleaned:
                return cleaned
            n = _to_float(cleaned)
            if n is not None:
                return f"{n:.2f}"

    # Numeric RR provided directly
    n = _to_float(raw)
    if n is not None:
        return f"{n:.2f}"

    # Fallback: estimate RR from price levels
    entry = _to_float(signal.get("entry"))
    sl = _to_float(signal.get("sl"))
    tp = _to_float(signal.get("tp"))
    side = str(signal.get("side", "")).upper()

    if entry is None or sl is None or tp is None:
        return "-"

    if side == "BUY":
        risk = entry - sl
        reward = tp - entry
    elif side == "SELL":
        risk = sl - entry
        reward = entry - tp
    else:
        risk = abs(entry - sl)
        reward = abs(tp - entry)

    if risk <= 0:
        return "-"

    rr = reward / risk
    if rr <= 0:
        return "-"

    return f"{rr:.2f}"


def send_telegram_message(bot_token: str, chat_id: str, text: str, max_retries: int = 5) -> None:
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }

    backoff = 1
    for attempt in range(max_retries + 1):
        try:
            r = requests.post(url, json=payload, timeout=20)

            # Respect Telegram rate limits
            if r.status_code == 429:
                retry_after = 3
                try:
                    data = r.json()
                    retry_after = int(data.get("parameters", {}).get("retry_after", 3))
                except Exception:
                    pass

                if attempt >= max_retries:
                    r.raise_for_status()
                time.sleep(max(1, retry_after))
                continue

            # Retry transient server-side errors
            if r.status_code >= 500:
                if attempt >= max_retries:
                    r.raise_for_status()
                time.sleep(backoff)
                backoff = min(backoff * 2, 15)
                continue

            r.raise_for_status()
            return

        except requests.RequestException:
            if attempt >= max_retries:
                raise
            time.sleep(backoff)
            backoff = min(backoff * 2, 15)


def format_signal_message(signal: Dict[str, Any]) -> str:
    pair = html.escape(str(signal.get("pair", "-")))
    tf = html.escape(str(signal.get("tf", "-")).replace("PERIOD_", ""))
    side_raw = str(signal.get("side", "-")).upper()
    side = html.escape(side_raw)
    side_icon = "🟢" if side_raw == "BUY" else "🔴" if side_raw == "SELL" else "⚪"

    signal_id = html.escape(str(signal.get("id", "-")))
    signal_time = html.escape(str(signal.get("signal_time") or signal.get("time") or "-"))

    entry = _fmt_num(signal.get("entry"), digits=2)
    sl = _fmt_num(signal.get("sl"), digits=2)
    tp = _fmt_num(signal.get("tp"), digits=2)
    rr = html.escape(_fmt_rr(signal))
    adx = _fmt_num(signal.get("adx"), digits=2)
    rsi = _fmt_num(signal.get("rsi"), digits=2)

    return (
        "📡 <b>ALPHALYCEUM LIVE SIGNAL SCALPING TF 5M</b>\n"
        f"{side_icon} Pair: <b>{pair}</b> ({tf})\n"
        f"Arah: <b>{side}</b>\n"
        f"Entry: <b>{entry}</b>\n"
        f"SL: <b>{sl}</b>\n"
        f"TP: <b>{tp}</b> (RR {rr})\n"
        f"ADX: {adx} | RSI: {rsi}\n"
        f"Waktu: {signal_time}\n"
        f"ID: <code>{signal_id}</code>\n\n"
        "<i>Disclaimer: edukasi, bukan financial advice. Selalu pakai risk management.</i>"
    )
