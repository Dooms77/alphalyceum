from pathlib import Path


def _ticker_for_symbol(symbol: str) -> str:
    s = symbol.upper()
    if "BTC" in s:
        return "BTC-USD"
    if "XAU" in s or "GOLD" in s:
        return "GC=F"
    return symbol


def _parse_zone(z):
    import re
    vals = [float(x) for x in re.findall(r"[-+]?\d*\.?\d+", str(z or ""))]
    if not vals:
        return None, None
    if len(vals) == 1:
        return vals[0], vals[0]
    a, b = vals[0], vals[1]
    return (a, b) if a <= b else (b, a)


def render_ohlc_with_zones(symbol: str, payload: dict, out_path: str, bars: int = 80) -> str | None:
    try:
        import yfinance as yf
        from PIL import Image, ImageDraw
    except Exception:
        return None

    tk = _ticker_for_symbol(symbol)
    df = yf.Ticker(tk).history(period="10d", interval="60m")
    if df is None or len(df) < 20:
        return None
    df = df.tail(max(20, bars)).copy()

    o = df["Open"].tolist()
    h = df["High"].tolist()
    l = df["Low"].tolist()
    c = df["Close"].tolist()

    pmin = min(l)
    pmax = max(h)
    pad = (pmax - pmin) * 0.08 if pmax > pmin else 1
    pmin -= pad
    pmax += pad

    w, hh = 1600, 900
    m_left, m_right, m_top, m_bot = 80, 40, 70, 120
    cw = w - m_left - m_right
    ch = hh - m_top - m_bot

    img = Image.new("RGB", (w, hh), (10, 12, 16))
    d = ImageDraw.Draw(img)

    def y_of(price: float) -> int:
        return int(m_top + (pmax - price) / (pmax - pmin) * ch)

    # grid
    for i in range(6):
        y = m_top + int(i * ch / 5)
        d.line([(m_left, y), (w - m_right, y)], fill=(35, 38, 44), width=1)

    n = len(c)
    step = max(4, int(cw / n))
    body_w = max(2, int(step * 0.62))

    # candles
    for i in range(n):
        x = m_left + i * step + step // 2
        yo, yh, yl, yc = y_of(o[i]), y_of(h[i]), y_of(l[i]), y_of(c[i])
        up = c[i] >= o[i]
        col = (63, 201, 122) if up else (230, 88, 88)
        d.line([(x, yh), (x, yl)], fill=col, width=1)
        y1, y2 = min(yo, yc), max(yo, yc)
        if y2 == y1:
            y2 += 1
        d.rectangle([(x - body_w // 2, y1), (x + body_w // 2, y2)], outline=col, fill=col)

    plan = payload.get("plan", {}) if isinstance(payload.get("plan"), dict) else {}

    # zones
    entry_lo, entry_hi = _parse_zone(plan.get("entry_zone"))
    tp_lo, tp_hi = _parse_zone(plan.get("tp_zone"))
    sl_lo, sl_hi = _parse_zone(plan.get("sl_zone"))

    def draw_zone(lo, hi, color, label):
        if lo is None or hi is None:
            return
        y1, y2 = y_of(hi), y_of(lo)
        d.rectangle([(m_left, y1), (w - m_right, y2)], outline=color, width=2)
        d.text((m_left + 8, y1 + 4), f"{label}: {lo:.2f}-{hi:.2f}", fill=color)

    draw_zone(entry_lo, entry_hi, (240, 210, 90), "ENTRY")
    draw_zone(tp_lo, tp_hi, (92, 220, 120), "TP")
    draw_zone(sl_lo, sl_hi, (240, 120, 120), "SL")

    # support/resistance lines
    for key, col in [("support", (110, 220, 150)), ("resistance", (240, 130, 130))]:
        lo, hi = _parse_zone(plan.get(key))
        if lo is None:
            continue
        mid = (lo + hi) / 2 if hi is not None else lo
        y = y_of(mid)
        d.line([(m_left, y), (w - m_right, y)], fill=col, width=2)
        d.text((w - m_right - 360, y - 16), f"{key.upper()}: {plan.get(key)}", fill=col)

    bias = str(payload.get("bias", "neutral")).upper()
    conv = int(plan.get("conviction", 0) or 0)
    d.text((m_left, 20), f"{symbol} | H1 OHLC Precision | {bias} | Conviction {conv}%", fill=(235, 235, 235))

    p = Path(out_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    img.save(str(p), format="PNG")
    return str(p)
