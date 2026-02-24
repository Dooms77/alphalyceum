import json, time, multiprocessing as mp, traceback, sys
from pathlib import Path

sys.path.insert(0, r"D:\alphalyceum\v2\python")
cfg = json.loads(Path(r"D:\alphalyceum\v2\config\v2_config.json").read_text(encoding="utf-8"))


def run_news(sym, q):
    try:
        from providers.news_ingest import get_news_context
        t = time.time(); r = get_news_context(sym, cfg)
        q.put(("ok", round(time.time()-t,2), r.get("headline_count"), r.get("note","")))
    except Exception as e:
        q.put(("err", repr(e), traceback.format_exc()))


def run_chart(sym, q):
    try:
        from providers.tradingview_ingest import get_tradingview_context
        from providers.chart_capture import capture_chart_screenshot
        tv = get_tradingview_context(sym, cfg)
        out = Path(r"D:\alphalyceum\v2\data\charts") / f"diag2_{sym.replace('.', '_')}.png"
        t = time.time(); capture_chart_screenshot(tv["chart_url"], str(out), wait_ms=2000)
        q.put(("ok", round(time.time()-t,2), str(out), out.exists(), out.stat().st_size if out.exists() else 0))
    except Exception as e:
        q.put(("err", repr(e), traceback.format_exc()))


def run_ollama(sym, q):
    try:
        from providers.analyzer_llm import analyze_with_ollama
        t = time.time()
        r = analyze_with_ollama(sym, {"bias":"neutral"}, {"bias":"neutral","headlines":[]}, {"regime":"test"}, model=(cfg.get("analysis") or {}).get("ollama_model","deepseek-r1:14b"))
        q.put(("ok", round(time.time()-t,2), list((r or {}).keys())[:8]))
    except Exception as e:
        q.put(("err", repr(e), traceback.format_exc()))


def timed(name, fn, sym, timeout=35):
    q = mp.Queue()
    p = mp.Process(target=fn, args=(sym, q))
    p.start(); p.join(timeout)
    if p.is_alive():
        p.terminate(); p.join(3)
        print(f"{name} {sym}: TIMEOUT>{timeout}s")
        return
    if q.empty():
        print(f"{name} {sym}: no result")
        return
    print(f"{name} {sym}: {q.get()}")


if __name__ == '__main__':
    syms = cfg.get("symbols", ["BTCUSD.vx","XAUUSD.vx"])
    for s in syms:
        timed("NEWS", run_news, s, timeout=30)
    for s in syms:
        timed("CHART", run_chart, s, timeout=45)
    for s in syms:
        timed("OLLAMA", run_ollama, s, timeout=40)
