import datetime as dt
import requests

FF_URL = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"


def _to_dt(v):
    if not v:
        return None
    try:
        # expected unix seconds
        if isinstance(v, (int, float)):
            return dt.datetime.fromtimestamp(int(v), tz=dt.timezone.utc)
        s = str(v).strip()
        if s.isdigit():
            return dt.datetime.fromtimestamp(int(s), tz=dt.timezone.utc)
        return dt.datetime.fromisoformat(s.replace("Z", "+00:00")).astimezone(dt.timezone.utc)
    except Exception:
        return None


def get_upcoming_events(look_ahead_hours: int = 3, currencies=None, impact_levels=None):
    currencies = {str(x).upper() for x in (currencies or ["USD", "EUR", "XAU", "JPY", "GBP"])}
    impact_levels = {str(x).lower() for x in (impact_levels or ["high", "medium"])}

    now = dt.datetime.now(dt.timezone.utc)
    end = now + dt.timedelta(hours=max(1, int(look_ahead_hours)))

    try:
        r = requests.get(FF_URL, timeout=12)
        r.raise_for_status()
        data = r.json() or []
    except Exception:
        return {"ok": False, "events": [], "note": "forexfactory fetch failed"}

    out = []
    for ev in data:
        cur = str(ev.get("currency") or "").upper()
        impact = str(ev.get("impact") or "").lower()
        if cur and cur not in currencies:
            continue
        if impact and impact not in impact_levels:
            continue

        t = _to_dt(ev.get("timestamp") or ev.get("date") or ev.get("time"))
        if t is None:
            continue
        if t < now or t > end:
            continue

        out.append({
            "title": str(ev.get("title") or ev.get("event") or "macro event"),
            "currency": cur or "-",
            "impact": impact or "-",
            "time_utc": t.isoformat(),
        })

    out.sort(key=lambda x: x["time_utc"])
    return {"ok": True, "events": out[:20], "note": f"ff events <= {look_ahead_hours}h"}
