import json, time, traceback, requests
from pathlib import Path
import sys
sys.path.insert(0, r"D:\alphalyceum\v2\python")

from providers.news_ingest import get_news_context
from providers.tradingview_ingest import get_tradingview_context
from providers.chart_capture import capture_chart_screenshot
from providers.analyzer_llm import analyze_with_ollama

cfg_path = Path(r"D:\alphalyceum\v2\config\v2_config.json")
cfg = json.loads(cfg_path.read_text(encoding="utf-8"))

symbols = cfg.get("symbols", ["BTCUSD.vx","XAUUSD.vx"])

print("[1] Telegram getMe test")
t0=time.time()
try:
    tok=cfg["telegram"]["bot_token"]
    r=requests.get(f"https://api.telegram.org/bot{tok}/getMe", timeout=15)
    print("  status:", r.status_code, "ok:", r.ok, "sec:", round(time.time()-t0,2))
except Exception as e:
    print("  FAIL", e)

for s in symbols:
    print(f"\n[2] Symbol {s}")
    t=time.time()
    tv = get_tradingview_context(s, cfg)
    print("  tv context ok sec:", round(time.time()-t,2), "chart_url:", bool(tv.get('chart_url')))

    t=time.time()
    try:
        news = get_news_context(s, cfg)
        print("  news ok sec:", round(time.time()-t,2), "headlines:", news.get("headline_count"), "note:", news.get("note",""))
    except Exception as e:
        print("  news FAIL sec:", round(time.time()-t,2), e)
        news = {"bias":"neutral","headlines":[]}

    if tv.get("chart_url"):
        out = Path(r"D:\alphalyceum\v2\data\charts") / f"diag_{s.replace('.', '_')}.png"
        t=time.time()
        try:
            capture_chart_screenshot(tv["chart_url"], str(out), wait_ms=3000)
            print("  chart ok sec:", round(time.time()-t,2), "file:", out.exists(), "size:", out.stat().st_size if out.exists() else 0)
        except Exception as e:
            print("  chart FAIL sec:", round(time.time()-t,2), repr(e))

    t=time.time()
    try:
        # quick ollama health
        h=requests.get("http://127.0.0.1:11434/api/tags", timeout=8)
        print("  ollama tags:", h.status_code, "sec:", round(time.time()-t,2))
    except Exception as e:
        print("  ollama health FAIL:", e)

    t=time.time()
    try:
        res = analyze_with_ollama(s, tv, news, {"regime":"test"}, model=(cfg.get("analysis") or {}).get("ollama_model", "deepseek-r1:14b"))
        print("  ollama analyze sec:", round(time.time()-t,2), "keys:", list(res.keys())[:6])
    except Exception as e:
        print("  ollama analyze FAIL sec:", round(time.time()-t,2), repr(e))
        traceback.print_exc()
