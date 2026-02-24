from pathlib import Path
import re


def _nums(s: str):
    vals = re.findall(r"[-+]?\d*\.?\d+", str(s or ""))
    return [float(v) for v in vals]


def _zone_mid(text: str):
    arr = _nums(text)
    if not arr:
        return None
    if len(arr) == 1:
        return arr[0]
    return sum(arr[:2]) / 2.0


def draw_overlay_on_image(image_path: str, payload: dict) -> str:
    """Draw lightweight technical lines/labels on existing chart image.
    Uses relative positioning (not exact TV pixel-price mapping) but clearly marks plan zones.
    """
    from PIL import Image, ImageDraw

    p = Path(image_path)
    if not p.exists():
        return image_path

    img = Image.open(p).convert("RGB")
    d = ImageDraw.Draw(img)
    w, h = img.size

    plan = payload.get("plan", {}) if isinstance(payload.get("plan"), dict) else {}
    bias = str(payload.get("bias", "neutral")).upper()
    sym = str(payload.get("symbol", "-"))
    conv = int(plan.get("conviction", 0) or 0)

    # Header
    d.rectangle([(0, 0), (w, 44)], fill=(12, 12, 12))
    d.text((10, 12), f"{sym} | {bias} | Conviction {conv}%", fill=(240, 240, 240))

    # Visual guide bands (top/mid/bottom)
    top = int(h * 0.22)
    mid = int(h * 0.50)
    bot = int(h * 0.78)

    # Resistance / support primary lines
    d.line([(0, top), (w, top)], fill=(255, 120, 120), width=2)
    d.text((10, top - 18), f"R: {plan.get('resistance', '-')}", fill=(255, 150, 150))

    d.line([(0, bot), (w, bot)], fill=(120, 255, 160), width=2)
    d.text((10, bot + 4), f"S: {plan.get('support', '-')}", fill=(140, 255, 180))

    # Entry/TP/SL markers around middle
    d.line([(0, mid), (w, mid)], fill=(255, 215, 120), width=2)
    d.text((10, mid - 18), f"Entry: {plan.get('entry_zone', '-')}", fill=(255, 230, 160))

    d.text((w - 420, 12), f"TP: {plan.get('tp_zone', '-')}", fill=(120, 255, 120))
    d.text((w - 420, 28), f"SL: {plan.get('sl_zone', '-')}", fill=(255, 130, 130))

    out = str(p.with_name(p.stem + "_overlay.png"))
    img.save(out, format="PNG")
    return out
