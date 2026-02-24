import json
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout

from providers.tradingview_ingest import get_tradingview_context
from providers.news_ingest import get_news_context
from providers.message_formatter import format_insight_message

CONFIG_PATH = Path(__file__).resolve().parents[1] / "config" / "v2_config.json"


def load_config():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def simple_bias_score(tv: dict, news: dict) -> str:
    tv_bias = (tv.get("bias") or "neutral").lower()
    news_bias = (news.get("bias") or "neutral").lower()

    if tv_bias == news_bias:
        return tv_bias
    if "bullish" in (tv_bias, news_bias) and "bearish" in (tv_bias, news_bias):
        return "mixed"
    return tv_bias if tv_bias != "neutral" else news_bias


def _fallback_news(symbol: str, reason: str = "news fallback") -> dict:
    return {
        "symbol": symbol,
        "bias": "neutral",
        "risk_level": "medium",
        "headline_count": 0,
        "headlines": [],
        "note": reason,
    }


def _get_news_with_timeout(symbol: str, cfg: dict, timeout_sec: int = 20) -> dict:
    with ThreadPoolExecutor(max_workers=1) as ex:
        fut = ex.submit(get_news_context, symbol, cfg)
        try:
            res = fut.result(timeout=timeout_sec)
            if isinstance(res, dict):
                return res
            return _fallback_news(symbol, "news fallback: invalid result")
        except FuturesTimeout:
            return _fallback_news(symbol, f"news timeout>{timeout_sec}s")
        except Exception as e:
            return _fallback_news(symbol, f"news fallback: {e}")


def run_once_payload(symbol: str) -> dict:
    cfg = load_config()
    tv = get_tradingview_context(symbol=symbol, config=cfg)

    news_cfg = (((cfg or {}).get("sources") or {}).get("news") or {})
    if bool(news_cfg.get("enabled", True)):
        timeout_sec = int(news_cfg.get("timeout_sec", 20) or 20)
        news = _get_news_with_timeout(symbol, cfg, timeout_sec=timeout_sec)
    else:
        news = _fallback_news(symbol, "news disabled by config")

    bias = simple_bias_score(tv, news)

    payload = {
        "symbol": symbol,
        "bias": bias,
        "tradingview": tv,
        "news": news,
    }
    return payload


def run_once(symbol: str) -> str:
    return format_insight_message(run_once_payload(symbol))


if __name__ == "__main__":
    for s in ["BTCUSD.vx", "XAUUSD.vx"]:
        print(run_once(s))
