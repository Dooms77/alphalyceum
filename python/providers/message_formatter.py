def format_insight_message(payload: dict) -> str:
    symbol = payload.get("symbol")
    symbol_title = str(symbol).replace('.vx', '') if symbol else '-'
    bias = payload.get("bias", "netral").upper()
    status = str(payload.get("status", "NO-TRADE")).upper()
    reason = str(payload.get("reason", "-")).strip()
    q = payload.get("quality_score", "-")

    tv = payload.get("tradingview", {})
    news = payload.get("news", {})
    plan = payload.get("plan", {})

    headlines = news.get("headlines") or []
    ringkasan_news = "\n".join([f"- {h}" for h in headlines[:3]]) if headlines else "- Belum ada headline kuat di sesi ini"
    pa = plan.get("price_action", {})

    status_emoji = {
        "OK": "✅",
        "HOLD_NEWS": "⏸️",
        "NO-TRADE": "🔴",
    }.get(status, "⚪")

    return (
        f"📌 ALPHALYCEUM V2.1 — {symbol_title}\n"
        f"Status: {status} {status_emoji} | Score: {q}/100\n"
        f"Reason: {reason}\n\n"
        f"1) Bias Arah\n"
        f"- Bias utama: {bias}\n"
        f"- Struktur: {tv.get('structure', '-')}\n"
        f"- Resistance: {plan.get('resistance', '-')}\n"
        f"- Support: {plan.get('support', '-')}\n\n"
        f"2) Analisa Price Action\n"
        f"- Fase market: {pa.get('market_phase', '-')}\n"
        f"- Sinyal candle: {pa.get('candle_signal', '-')}\n"
        f"- Catatan momentum: {pa.get('momentum_note', '-')}\n"
        f"- Invalidation: {pa.get('invalidation', '-')}\n\n"
        f"3) Setup Futures (Rencana Utama)\n"
        f"- Entry zone: {plan.get('entry_zone', '-')}\n"
        f"- TP zone: {plan.get('tp_zone', '-')}\n"
        f"- SL zone: {plan.get('sl_zone', '-')}\n"
        f"- Conviction: {plan.get('conviction', 0)}%\n"
        f"- Skenario: {plan.get('scenario', '-')}\n\n"
        f"4) Analisa Teknikal\n"
        f"- {tv.get('note', '-')}\n\n"
        f"5) Analisa News\n"
        f"- Risk level: {str(news.get('risk_level', '-')).upper()}\n"
        f"{ringkasan_news}\n\n"
        f"Link chart: {tv.get('chart_url', '-')}\n\n"
        f"⚠️ Disclaimer: NFA (Not Financial Advice). Ini konten edukasi, bukan ajakan beli/jual. Selalu pakai risk management."
    )
