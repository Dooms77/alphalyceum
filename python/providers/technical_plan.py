def _anchor_zone(last_price, bias: str):
    try:
        p = float(last_price)
    except Exception:
        return None

    # Generic percentage envelopes for intraday/swing baseline
    if p > 10000:  # BTC-like
        if bias == "bearish":
            return {
                "entry_zone": f"{p*0.998:.0f} - {p*1.001:.0f}",
                "tp_zone": f"{p*0.985:.0f} - {p*0.978:.0f}",
                "sl_zone": f"{p*1.012:.0f} - {p*1.018:.0f}",
                "resistance": f"{p*1.004:.0f} - {p*1.010:.0f}",
                "support": f"{p*0.992:.0f} - {p*0.986:.0f}",
            }
        return {
            "entry_zone": f"{p*0.999:.0f} - {p*1.002:.0f}",
            "tp_zone": f"{p*1.012:.0f} - {p*1.020:.0f}",
            "sl_zone": f"{p*0.988:.0f} - {p*0.982:.0f}",
            "resistance": f"{p*1.006:.0f} - {p*1.012:.0f}",
            "support": f"{p*0.994:.0f} - {p*0.988:.0f}",
        }

    # Gold-like
    if bias == "bearish":
        return {
            "entry_zone": f"{p*0.999:.2f} - {p*1.002:.2f}",
            "tp_zone": f"{p*0.992:.2f} - {p*0.986:.2f}",
            "sl_zone": f"{p*1.006:.2f} - {p*1.010:.2f}",
            "resistance": f"{p*1.003:.2f} - {p*1.006:.2f}",
            "support": f"{p*0.995:.2f} - {p*0.991:.2f}",
        }
    return {
        "entry_zone": f"{p*0.999:.2f} - {p*1.002:.2f}",
        "tp_zone": f"{p*1.007:.2f} - {p*1.013:.2f}",
        "sl_zone": f"{p*0.994:.2f} - {p*0.989:.2f}",
        "resistance": f"{p*1.004:.2f} - {p*1.008:.2f}",
        "support": f"{p*0.996:.2f} - {p*0.992:.2f}",
    }


def build_trade_plan(symbol: str, tv: dict, news: dict, bias: str, market_ctx: dict | None = None) -> dict:
    market_ctx = market_ctx or {}

    defaults = {
        "timeframe": tv.get("timeframe", "H1"),
        "entry_zone": "Tunggu konfirmasi chart live",
        "tp_zone": "Ikuti struktur S/R terbaru",
        "sl_zone": "Di luar area invalidation",
        "resistance": tv.get("resistance", "belum dipetakan"),
        "support": tv.get("support", "belum dipetakan"),
        "conviction": 58,
        "scenario": "Eksekusi hanya setelah konfirmasi momentum dan struktur"
    }

    plan = dict(defaults)
    plan["bias"] = str(bias).upper()

    risk = str(news.get("risk_level", "medium")).lower()
    if risk == "high":
        plan["conviction"] = max(45, plan["conviction"] - 10)
    elif risk == "low":
        plan["conviction"] = min(80, plan["conviction"] + 5)

    anchored = _anchor_zone(market_ctx.get("last_price"), str(bias).lower())
    if anchored:
        plan.update(anchored)

    pa = tv.get("price_action") if isinstance(tv.get("price_action"), dict) else {}
    plan["price_action"] = {
        "market_phase": pa.get("market_phase", "fase transisi / menunggu break valid"),
        "candle_signal": pa.get("candle_signal", "perhatikan rejection / breakout candle H1"),
        "momentum_note": pa.get("momentum_note", "momentum perlu konfirmasi volume"),
        "invalidation": pa.get("invalidation", "setup batal jika struktur mayor patah")
    }

    return plan
