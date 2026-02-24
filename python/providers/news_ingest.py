import datetime as dt


def _lc_list(values) -> list[str]:
    return [str(v).strip().lower() for v in (values or []) if str(v).strip()]


def _ticker_for_symbol(symbol: str) -> str:
    s = symbol.upper()
    if "BTC" in s:
        return "BTC-USD"
    if "XAU" in s or "GOLD" in s:
        return "GC=F"
    return symbol


def _is_relevant_headline(symbol: str, title: str, cfg_news: dict) -> bool:
    t = title.lower()

    # Global hard excludes (configurable)
    extra_exclude_kw = _lc_list((cfg_news or {}).get("exclude_keywords", []))

    if "BTC" in symbol.upper():
        # Prefer macro BTC context (rates/liquidity/ETF/flows/risk sentiment), avoid altcoin clickbait.
        include_kw = [
            "bitcoin", "btc", "crypto", "etf", "fomc", "fed", "rate", "yield", "dollar",
            "liquidity", "inflation", "cpi", "risk-off", "risk-on", "treasury", "macro"
        ]
        exclude_kw = ["solana", "doge", "memecoin", "airdrop", "nft", "altcoin", "microcap"] + extra_exclude_kw
        if not any(k in t for k in include_kw):
            return False
        if any(k in t for k in exclude_kw):
            return False
        return True

    # XAU/GOLD: keep macro gold + dollar/yield/rates themes, avoid company-specific miner headlines.
    include_kw = ["gold", "xau", "bullion", "fed", "fomc", "rate", "yield", "dollar", "inflation", "cpi", "geopolitical", "treasury"]
    exclude_kw = ["corp", "inc", "ltd", "tsx", "nasdaq", "nyse", "shares", "stock", "mining", "resources"] + extra_exclude_kw

    if not any(k in t for k in include_kw):
        return False
    if any(k in t for k in exclude_kw):
        return False
    return True


def _infer_bias_and_risk(headlines: list[str]) -> tuple[str, str]:
    text = " ".join(headlines).lower()
    bullish_kw = ["rally", "surge", "upside", "support", "bullish", "rebound"]
    bearish_kw = ["drop", "selloff", "downside", "bearish", "falls", "risk-off"]
    high_risk_kw = ["cpi", "fomc", "powell", "nfp", "inflation", "geopolitical", "war"]

    bull = sum(1 for k in bullish_kw if k in text)
    bear = sum(1 for k in bearish_kw if k in text)
    risk = "high" if any(k in text for k in high_risk_kw) else "medium"

    if bull > bear:
        return "bullish", risk
    if bear > bull:
        return "bearish", risk
    return "neutral", risk


def get_news_context(symbol: str, config: dict) -> dict:
    try:
        import yfinance as yf
    except Exception as e:
        return {
            "symbol": symbol,
            "bias": "neutral",
            "risk_level": "medium",
            "headline_count": 0,
            "headlines": [],
            "note": f"yfinance import gagal: {e}",
        }

    tk = _ticker_for_symbol(symbol)
    cfg_news = (((config or {}).get("sources") or {}).get("news") or {})
    lookback_h = cfg_news.get("lookback_hours", 24)
    cutoff = dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=float(lookback_h))

    publisher_blacklist = set(_lc_list(cfg_news.get("publisher_blacklist", [])))

    headlines: list[str] = []
    try:
        ticker = yf.Ticker(tk)
        items = ticker.news or []

        for it in items:
            content = it.get("content") if isinstance(it, dict) else {}
            if not isinstance(content, dict):
                content = {}

            title = (it.get("title") or content.get("title") or "").strip()
            if not title:
                continue

            provider_name = ""
            provider_obj = content.get("provider") if isinstance(content, dict) else None
            if isinstance(provider_obj, dict):
                provider_name = str(provider_obj.get("displayName") or "").strip().lower()

            if provider_name and provider_name in publisher_blacklist:
                continue

            pub_ts = it.get("providerPublishTime") or content.get("providerPublishTime")
            if not pub_ts:
                pub_date = content.get("pubDate")
                if pub_date:
                    try:
                        t = dt.datetime.fromisoformat(str(pub_date).replace("Z", "+00:00"))
                        if t.tzinfo is None:
                            t = t.replace(tzinfo=dt.timezone.utc)
                        if t < cutoff:
                            continue
                    except Exception:
                        pass
            else:
                try:
                    t = dt.datetime.fromtimestamp(int(pub_ts), tz=dt.timezone.utc)
                    if t < cutoff:
                        continue
                except Exception:
                    pass

            if not _is_relevant_headline(symbol, title, cfg_news):
                continue

            headlines.append(title)
            if len(headlines) >= 8:
                break

    except Exception as e:
        return {
            "symbol": symbol,
            "bias": "neutral",
            "risk_level": "medium",
            "headline_count": 0,
            "headlines": [],
            "note": f"yfinance fetch fallback: {e}",
        }

    bias, risk = _infer_bias_and_risk(headlines)
    return {
        "symbol": symbol,
        "bias": bias,
        "risk_level": risk,
        "headline_count": len(headlines),
        "headlines": headlines[:5],
        "note": f"auto-ingest from Yahoo Finance ({tk})",
    }
