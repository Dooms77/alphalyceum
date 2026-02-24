from __future__ import annotations

from typing import Any


def _ticker_for_symbol(symbol: str) -> str:
    s = symbol.upper()
    if "BTC" in s:
        return "BTC-USD"
    if "XAU" in s or "GOLD" in s:
        return "GC=F"
    return symbol


def _safe_float(v: Any):
    try:
        if v is None:
            return None
        return float(v)
    except Exception:
        return None


def _fmt_price(x: float | None, symbol: str) -> str:
    if x is None:
        return "-"
    return f"{x:.0f}" if "BTC" in symbol.upper() else f"{x:.2f}"


def _build_from_ohlc(symbol: str, chart_url: str, rows) -> dict:
    close = rows["Close"]
    high = rows["High"]
    low = rows["Low"]

    last_close = _safe_float(close.iloc[-1])
    prev_close = _safe_float(close.iloc[-2]) if len(close) > 1 else last_close
    last_high = _safe_float(high.iloc[-1])
    last_low = _safe_float(low.iloc[-1])

    sma20 = _safe_float(close.tail(20).mean()) if len(close) >= 20 else _safe_float(close.mean())
    sma50 = _safe_float(close.tail(50).mean()) if len(close) >= 50 else _safe_float(close.mean())

    # ATR-like proxy (14)
    tr = (high - low).tail(14)
    atr14 = _safe_float(tr.mean()) if len(tr) else None

    # Swing window ~2 trading days on H1 bars
    swing_high = _safe_float(high.tail(48).max()) if len(high) else None
    swing_low = _safe_float(low.tail(48).min()) if len(low) else None

    bias = "neutral"
    if all(v is not None for v in [last_close, sma20, sma50]):
        if last_close > sma20 > sma50:
            bias = "bullish"
        elif last_close < sma20 < sma50:
            bias = "bearish"

    # Structure
    if bias == "bullish":
        structure = "HH-HL ringan, harga di atas MA20/MA50"
    elif bias == "bearish":
        structure = "LL-LH ringan, harga di bawah MA20/MA50"
    else:
        structure = "range/transition, menunggu break struktur"

    # Dynamic S/R
    if atr14 is None:
        atr14 = 0.0
    resistance = swing_high if swing_high is not None else (last_close + atr14 if last_close is not None else None)
    support = swing_low if swing_low is not None else (last_close - atr14 if last_close is not None else None)

    # Price-action notes
    body = None
    if last_close is not None and prev_close is not None:
        body = last_close - prev_close

    if body is None:
        candle_signal = "data candle belum cukup"
    elif body > 0:
        candle_signal = "close candle terakhir bullish"
    elif body < 0:
        candle_signal = "close candle terakhir bearish"
    else:
        candle_signal = "close candle terakhir netral"

    momentum_note = "momentum naik moderat" if (body is not None and body > 0) else (
        "momentum turun moderat" if (body is not None and body < 0) else "momentum datar"
    )

    invalidation = "invalid jika break support terdekat" if bias == "bullish" else (
        "invalid jika reclaim resistance terdekat" if bias == "bearish" else "invalid setelah breakout palsu"
    )

    return {
        "symbol": symbol,
        "timeframe": "H1",
        "bias": bias,
        "structure": structure,
        "note": f"tv-ohlc: last={_fmt_price(last_close, symbol)} sma20={_fmt_price(sma20, symbol)} sma50={_fmt_price(sma50, symbol)} atr14={_fmt_price(atr14, symbol)}",
        "chart_url": chart_url,
        "resistance": f"{_fmt_price(resistance, symbol)}",
        "support": f"{_fmt_price(support, symbol)}",
        "price_action": {
            "market_phase": "trend continuation" if bias in {"bullish", "bearish"} else "range/transition",
            "candle_signal": candle_signal,
            "momentum_note": momentum_note,
            "invalidation": invalidation,
        },
    }


def get_tradingview_context(symbol: str, config: dict) -> dict:
    chart_urls = (((config or {}).get("sources") or {}).get("tradingview") or {}).get("chart_urls", {})
    chart_url = chart_urls.get(symbol, "")

    try:
        import yfinance as yf

        tk = _ticker_for_symbol(symbol)
        df = yf.Ticker(tk).history(period="7d", interval="60m")
        if df is not None and len(df) >= 30:
            return _build_from_ohlc(symbol, chart_url, df)
    except Exception:
        pass

    # Fallback base context if OHLC fetch fails.
    return {
        "symbol": symbol,
        "timeframe": "H1",
        "bias": "neutral",
        "structure": "menunggu analisa lanjutan",
        "note": "context chart disiapkan untuk analisa LLM",
        "chart_url": chart_url,
    }
