import json
import argparse
import datetime as dt
from pathlib import Path

from v2_signal_router import run_once_payload
from providers.telegram_publish import send_telegram
from providers.message_formatter import format_insight_message
from providers.technical_plan import build_trade_plan
from providers.chart_capture import capture_chart_screenshot
from providers.analyzer_llm import analyze_with_ollama
from providers.market_context import get_latest_market_context
from providers.forexfactory_events import get_upcoming_events
from providers.technical_overlay import draw_overlay_on_image
from providers.ohlc_renderer import render_ohlc_with_zones

CONFIG_PATH = Path(__file__).resolve().parents[1] / "config" / "v2_config.json"
CHART_DIR = Path(__file__).resolve().parents[1] / "data" / "charts"
STATE_PATH = Path(__file__).resolve().parents[1] / "data" / "v2_state.json"
DECISION_LOG_PATH = Path(__file__).resolve().parents[1] / "data" / "decision_log.jsonl"


def load_config():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def _load_state():
    if not STATE_PATH.exists():
        return {"last_sent_at": None, "pair_last_sent_at": {}, "health_last_alert_at": {}}
    try:
        state = json.loads(STATE_PATH.read_text(encoding="utf-8"))
        state.setdefault("pair_last_sent_at", {})
        state.setdefault("health_last_alert_at", {})
        return state
    except Exception:
        return {"last_sent_at": None, "pair_last_sent_at": {}, "health_last_alert_at": {}}


def _save_state(state: dict):
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def _is_placeholder(v) -> bool:
    s = str(v or "").strip().lower()
    if not s:
        return True
    return s in {
        "...",
        "-",
        "angka - angka",
        "bullish|bearish|mixed|neutral",
        "m15|h1|h4",
        "menunggu analisa lanjutan",
        "tunggu analisa lanjutan",
        "waiting for a clear signal to enter the trade",
        "no clear signal",
        "momentum neutral",
    }


def _merge_clean(dst: dict, src: dict):
    for k, v in (src or {}).items():
        if v in [None, "", [], {}]:
            continue
        if isinstance(v, str) and _is_placeholder(v):
            continue
        dst[k] = v


def _infer_structure_from_market(market_ctx: dict) -> str | None:
    side = str((market_ctx or {}).get("last_side") or "").upper()
    if side == "BUY":
        return "struktur cenderung bullish, tunggu konfirmasi break high minor"
    if side == "SELL":
        return "struktur cenderung bearish, tunggu konfirmasi break low minor"
    return None


def _in_session_window(now_utc: dt.datetime) -> bool:
    h = now_utc.hour
    # London approx 07-16 UTC, New York approx 13-22 UTC
    in_london = 7 <= h < 16
    in_newyork = 13 <= h < 22
    return in_london or in_newyork


def _hours_since_pair_last_sent(state: dict, symbol: str, now_utc: dt.datetime) -> float:
    raw = (state.get("pair_last_sent_at") or {}).get(symbol)
    if not raw:
        return 1e9
    try:
        t = dt.datetime.fromisoformat(str(raw).replace("Z", "+00:00")).astimezone(dt.timezone.utc)
        return (now_utc - t).total_seconds() / 3600.0
    except Exception:
        return 1e9


def _pair_quality(payload: dict) -> int:
    plan = payload.get("plan", {}) if isinstance(payload.get("plan"), dict) else {}
    pa = plan.get("price_action", {}) if isinstance(plan.get("price_action"), dict) else {}
    news = payload.get("news", {}) if isinstance(payload.get("news"), dict) else {}

    score = 0
    bias = str(payload.get("bias", "neutral")).lower()
    conv = int(plan.get("conviction", 0) or 0)

    # 1) Bias quality (max 20)
    if bias in {"bullish", "bearish"}:
        score += 20
    elif bias == "mixed":
        score += 10

    # 2) Conviction quality (max 20)
    if conv >= 70:
        score += 20
    elif conv >= 60:
        score += 15
    elif conv >= 50:
        score += 10
    elif conv >= 40:
        score += 6

    # 3) Setup completeness (max 20)
    for k in ["entry_zone", "tp_zone", "sl_zone", "resistance", "support"]:
        if not _is_placeholder(plan.get(k, "")):
            score += 4

    # 4) Momentum/context signal (max 25)
    text = " ".join([
        str(pa.get("candle_signal", "")),
        str(pa.get("momentum_note", "")),
        str(plan.get("scenario", "")),
        str(payload.get("tradingview", {}).get("note", "")),
    ]).lower()
    for kw in ["break", "breakout", "momentum", "trend", "continuation", "rejection", "support", "resistance"]:
        if kw in text:
            score += 3

    # 5) News risk penalty/bonus (max 15)
    risk = str(news.get("risk_level", "medium")).lower()
    if risk == "low":
        score += 15
    elif risk == "medium":
        score += 10
    else:
        score += 4

    return max(0, min(score, 100))


def _enforce_pair_specific(payload: dict):
    sym = str(payload.get("symbol", "")).upper()
    plan = payload.setdefault("plan", {})
    pa = plan.setdefault("price_action", {})
    news = payload.get("news", {}) if isinstance(payload.get("news"), dict) else {}

    if "BTC" in sym:
        pa["momentum_note"] = "fokus volatilitas crypto, arus risk-on/risk-off, dan konfirmasi volume breakout"
        base_scn = str(plan.get("scenario", "")).strip()
        addon = "driver utama: flow crypto + likuiditas USD"
        plan["scenario"] = f"{base_scn} | {addon}" if base_scn else addon
    elif "XAU" in sym or "GOLD" in sym:
        pa["momentum_note"] = "fokus DXY, US yield, dan headline geopolitik safe-haven"
        base_scn = str(plan.get("scenario", "")).strip()
        addon = "driver utama: yield & geopolitik; validasi di area S/R"
        plan["scenario"] = f"{base_scn} | {addon}" if base_scn else addon

    risk = str(news.get("risk_level", "medium")).lower()
    if isinstance(plan.get("conviction"), (int, float)):
        if risk == "high":
            plan["conviction"] = max(35, int(plan.get("conviction", 58)) - 8)
        elif risk == "low":
            plan["conviction"] = min(85, int(plan.get("conviction", 58)) + 4)


def _event_hits_symbol(symbol: str, event: dict) -> bool:
    cur = str((event or {}).get("currency", "")).upper().strip()
    title = str((event or {}).get("title", "")).upper()
    sym = str(symbol).upper()

    # Fallback when FF currency field kosong/"-": infer by title keywords
    usd_major_keywords = ["CPI", "NFP", "FOMC", "FED", "PCE", "NON-FARM", "POWELL", "CONSUMER CONFIDENCE"]
    inferred_usd = any(k in title for k in usd_major_keywords)

    # BTCUSD & XAUUSD both sensitive to USD macro
    if (cur == "USD" or inferred_usd) and ("BTC" in sym or "XAU" in sym):
        return True
    if cur == "XAU" and "XAU" in sym:
        return True
    return False


def _is_major_event(title: str, major_events: list[str]) -> bool:
    t = str(title or "").upper()
    return any(str(x).upper() in t for x in (major_events or []))


def _parse_event_time_utc(event: dict) -> dt.datetime | None:
    raw = event.get("time_utc")
    if not raw:
        return None
    try:
        return dt.datetime.fromisoformat(str(raw).replace("Z", "+00:00")).astimezone(dt.timezone.utc)
    except Exception:
        return None


def _symbol_news_block(symbol: str, ff_events: dict, cfg: dict, now_utc: dt.datetime) -> tuple[bool, str]:
    evs = (ff_events or {}).get("events") or []
    ff_cfg = (((cfg or {}).get("sources") or {}).get("forexfactory") or {})

    default_win = ff_cfg.get("default_block_window_minutes") or {"before": 45, "after": 45}
    major_win = ff_cfg.get("major_block_window_minutes") or {"before": 90, "after": 90}
    major_events = ff_cfg.get("major_events") or ["CPI", "NFP", "FOMC"]

    for e in evs:
        if not _event_hits_symbol(symbol, e):
            continue
        if str(e.get("impact", "")).lower() != "high":
            continue

        title = str(e.get("title", "macro event"))
        et = _parse_event_time_utc(e)
        if not et:
            continue

        use_major = _is_major_event(title, major_events)
        win = major_win if use_major else default_win
        before_m = int(win.get("before", 45))
        after_m = int(win.get("after", 45))

        start = et - dt.timedelta(minutes=before_m)
        end = et + dt.timedelta(minutes=after_m)

        if start <= now_utc <= end:
            tag = "MAJOR" if use_major else "HIGH"
            return True, f"HOLD_NEWS[{tag}] {title} ({before_m}/{after_m}m)"

    return False, "NO_BLOCK"


def _compute_status(payload: dict, quality: int, cfg: dict, news_blocked: bool, news_reason: str) -> tuple[str, str]:
    min_quality = int(((cfg.get("publish_policy") or {}).get("min_quality_score", 75)))
    bias = str(payload.get("bias", "neutral")).lower()
    symbol = str(payload.get("symbol", "")).upper()

    # XAU rescue rule: if bias neutral but setup quality cukup, treat as mixed (watchlist-ready)
    if "XAU" in symbol and bias == "neutral":
        plan = payload.get("plan", {}) if isinstance(payload.get("plan"), dict) else {}
        conv = int(plan.get("conviction", 0) or 0)
        setup_ready = all([
            not _is_placeholder(plan.get("entry_zone", "")),
            not _is_placeholder(plan.get("tp_zone", "")),
            not _is_placeholder(plan.get("sl_zone", "")),
        ])
        if conv >= 60 and setup_ready and quality >= max(65, min_quality - 4):
            bias = "mixed"
            payload["bias"] = "mixed"

    if news_blocked:
        return "HOLD_NEWS", news_reason
    if bias not in {"bullish", "bearish", "mixed"}:
        return "NO-TRADE", "BIAS_NOT_ACTIONABLE"
    if quality < min_quality:
        return "NO-TRADE", f"SCORE_BELOW_GATE ({quality} < {min_quality})"
    return "OK", "PASS_ALL_GATES"


def _allow_publish_for_symbol(symbol: str, status: str, state: dict, now_utc: dt.datetime, cfg: dict) -> tuple[bool, str]:
    policy = cfg.get("publish_policy") or {}
    allowed_status = set(policy.get("publish_only_status", ["OK"]))
    if status not in allowed_status:
        return False, f"status={status} not in publish_only_status"

    pair_cooldowns = policy.get("pair_cooldown_hours") or {}
    min_gap_h = float(pair_cooldowns.get(symbol, policy.get("min_interval_hours", 3)))
    since_h = _hours_since_pair_last_sent(state, symbol, now_utc)
    if since_h < min_gap_h:
        return False, f"pair_cooldown_active ({since_h:.2f}h < {min_gap_h}h)"

    require_session = bool(policy.get("require_session_window", True))
    if require_session and not _in_session_window(now_utc):
        return False, "outside_session_window"

    return True, "publish_allowed"


def _append_decision_log(rows: list[dict]):
    if not rows:
        return
    DECISION_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with DECISION_LOG_PATH.open("a", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def _apply_profile_overrides(cfg: dict, profile_name: str):
    profiles = cfg.get("profiles") or {}
    prof = profiles.get(profile_name) or {}
    if not prof:
        return
    policy = cfg.setdefault("publish_policy", {})
    if "min_quality_score" in prof:
        policy["min_quality_score"] = int(prof["min_quality_score"])
    if "pair_cooldown_hours" in prof and isinstance(prof["pair_cooldown_hours"], dict):
        policy["pair_cooldown_hours"] = prof["pair_cooldown_hours"]


def _hours_since(ts: str | None, now_utc: dt.datetime) -> float:
    if not ts:
        return 1e9
    try:
        t = dt.datetime.fromisoformat(str(ts).replace("Z", "+00:00")).astimezone(dt.timezone.utc)
        return (now_utc - t).total_seconds() / 3600.0
    except Exception:
        return 1e9


def _health_guard_alerts(cfg: dict, state: dict, now_utc: dt.datetime, diagnostics: list[dict]) -> list[dict]:
    hg = cfg.get("health_guard") or {}
    if not bool(hg.get("enabled", False)):
        return []

    no_ok_hours = float(hg.get("no_ok_hours_alert", 12))
    alert_cd_hours = float(hg.get("alert_cooldown_hours", 6))

    out = []
    last_alert = state.setdefault("health_last_alert_at", {})
    for d in diagnostics:
        sym = d.get("symbol")
        status = str(d.get("status", "")).upper()
        if status == "OK":
            continue

        since_ok = _hours_since((state.get("pair_last_sent_at") or {}).get(sym), now_utc)
        since_alert = _hours_since(last_alert.get(sym), now_utc)
        if since_ok >= no_ok_hours and since_alert >= alert_cd_hours:
            out.append({
                "symbol": sym,
                "since_ok_hours": round(since_ok, 2),
                "status": status,
                "reason": d.get("reason"),
            })
            last_alert[sym] = now_utc.isoformat()
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--detail", action="store_true", help="Kirim detail lengkap sebagai follow-up text")
    ap.add_argument("--force-send", action="store_true", help="Bypass publish policy")
    ap.add_argument("--profile", default="balanced", choices=["strict", "balanced", "aggressive"], help="Profil publish policy")
    args = ap.parse_args()

    cfg = load_config()
    _apply_profile_overrides(cfg, args.profile)
    state = _load_state()
    now_utc = dt.datetime.now(dt.timezone.utc)

    symbols = cfg.get("symbols", ["BTCUSD.vx", "XAUUSD.vx"])
    out_msgs = []
    diagnostics = []
    decision_rows = []

    ff_cfg = (((cfg or {}).get("sources") or {}).get("forexfactory") or {})
    ff_events = get_upcoming_events(
        look_ahead_hours=int(ff_cfg.get("look_ahead_hours", 6) or 6),
        currencies=ff_cfg.get("currencies", ["USD", "EUR"]),
        impact_levels=ff_cfg.get("impact_levels", ["high"]),
    )

    for s in symbols:
        payload = run_once_payload(s)
        market_ctx = get_latest_market_context(s)

        tv = payload.setdefault("tradingview", {})
        if str(tv.get("structure", "")).strip().lower() == "menunggu analisa lanjutan":
            inferred = _infer_structure_from_market(market_ctx)
            if inferred:
                tv["structure"] = inferred

        llm_result = {}
        if ((cfg.get("analysis") or {}).get("engine") == "ollama"):
            model = (cfg.get("analysis") or {}).get("ollama_model", "deepseek-r1:14b")
            try:
                llm_result = analyze_with_ollama(
                    s,
                    payload.get("tradingview", {}),
                    payload.get("news", {}),
                    market_ctx,
                    model=model,
                    cfg=cfg,
                )
            except Exception:
                llm_result = {}

        if llm_result.get("bias"):
            cand_bias = str(llm_result.get("bias", payload.get("bias", "neutral"))).lower().strip()
            if cand_bias in {"bullish", "bearish", "mixed", "neutral"}:
                payload["bias"] = cand_bias

        payload["plan"] = build_trade_plan(
            s,
            payload.get("tradingview", {}),
            payload.get("news", {}),
            payload.get("bias", "neutral"),
            market_ctx=market_ctx,
        )

        if isinstance(llm_result.get("price_action"), dict):
            payload["plan"]["price_action"] = llm_result["price_action"]
        if isinstance(llm_result.get("plan"), dict):
            _merge_clean(payload["plan"], llm_result["plan"])
        if llm_result.get("technical_note"):
            payload.setdefault("tradingview", {})["note"] = llm_result.get("technical_note")

        if not llm_result:
            payload.setdefault("tradingview", {})["note"] = (
                f"{payload.get('tradingview', {}).get('note', '')} | llm_fallback=on"
            ).strip(" |")

        _enforce_pair_specific(payload)

        # append macro summary
        evs = (ff_events or {}).get("events") or []
        if evs:
            top = [e for e in evs if _event_hits_symbol(s, e)][:3]
            if top:
                ev_text = [f"{x.get('currency')} {str(x.get('impact')).upper()} {x.get('title')}" for x in top]
                n = payload.setdefault("news", {})
                n["headlines"] = (n.get("headlines") or []) + [f"FF: {t}" for t in ev_text]
                if any(str(x.get("impact", "")).lower() == "high" for x in top):
                    n["risk_level"] = "high"

        quality = _pair_quality(payload)
        blocked, block_reason = _symbol_news_block(s, ff_events, cfg, now_utc)
        status, reason = _compute_status(payload, quality, cfg, blocked, block_reason)

        payload["status"] = status
        payload["reason"] = reason
        payload["quality_score"] = quality

        chart_url = (payload.get("tradingview", {}) or {}).get("chart_url")
        image_path = None
        render_mode = str(((cfg.get("render") or {}).get("mode") or "ohlc")).lower()
        if render_mode == "ohlc":
            try:
                image_path = str(CHART_DIR / f"{s.replace('.', '_')}_ohlc.png")
                out_prec = render_ohlc_with_zones(s, payload, image_path)
                if out_prec:
                    image_path = out_prec
            except Exception as e:
                payload.setdefault("tradingview", {})["note"] = f"{payload.get('tradingview', {}).get('note', '')} | ohlc_render_fail={e}"

        if (not image_path) and chart_url:
            try:
                image_path = str(CHART_DIR / f"{s.replace('.', '_')}.png")
                capture_chart_screenshot(chart_url, image_path)
                image_path = draw_overlay_on_image(image_path, payload)
            except Exception as e:
                payload.setdefault("tradingview", {})["note"] = f"{payload.get('tradingview', {}).get('note', '')} | screenshot_fail={e}"
                image_path = None

        msg = format_insight_message(payload)

        allow_publish, publish_reason = _allow_publish_for_symbol(s, status, state, now_utc, cfg)
        if args.force_send:
            allow_publish = True
            publish_reason = "force-send"

        diag_row = {
            "symbol": s,
            "status": status,
            "reason": reason,
            "quality": quality,
            "publish": allow_publish,
            "publish_reason": publish_reason,
        }
        diagnostics.append(diag_row)

        decision_rows.append({
            "ts_utc": now_utc.isoformat(),
            "symbol": s,
            "status": status,
            "reason": reason,
            "quality_score": quality,
            "bias": payload.get("bias"),
            "entry_zone": payload.get("plan", {}).get("entry_zone"),
            "tp_zone": payload.get("plan", {}).get("tp_zone"),
            "sl_zone": payload.get("plan", {}).get("sl_zone"),
            "publish": allow_publish,
            "publish_reason": publish_reason,
        })

        out_msgs.append((msg, payload, image_path, allow_publish))

    health_alerts = _health_guard_alerts(cfg, state, now_utc, diagnostics)

    if cfg.get("telegram", {}).get("enabled"):
        token = cfg["telegram"].get("bot_token", "")
        chat_id = cfg["telegram"].get("channel", "")
        ops_chat_id = cfg["telegram"].get("ops_channel", "")
        send_non_ok_ops = bool(cfg.get("telegram", {}).get("publish_non_ok_to_ops", False))
        auto_detail = bool(cfg.get("telegram", {}).get("auto_detail_followup", False))
        send_detail = bool(args.detail or auto_detail)

        if token and chat_id:
            pair_state = state.setdefault("pair_last_sent_at", {})
            sent_any = False
            for m, payload, image_path, allow_publish in out_msgs:
                status = str(payload.get("status", "NO-TRADE")).upper()

                if allow_publish:
                    image_url = (payload.get("tradingview", {}) or {}).get("chart_image_url")
                    try:
                        send_telegram(token, chat_id, m, image_url=image_url, image_path=image_path, send_detail_followup=send_detail)
                        pair_state[payload.get("symbol")] = now_utc.isoformat()
                        sent_any = True
                    except Exception as e:
                        diagnostics.append({
                            "symbol": payload.get("symbol"),
                            "status": status,
                            "publish": False,
                            "publish_reason": f"telegram_main_send_fail: {e}",
                        })
                    continue

                if send_non_ok_ops and ops_chat_id and status in {"HOLD_NEWS", "NO-TRADE"}:
                    ops_msg = f"[OPS] {payload.get('symbol')} | {status} | {payload.get('reason')} | score={payload.get('quality_score')}"
                    try:
                        send_telegram(token, ops_chat_id, ops_msg, image_url=None, image_path=None, send_detail_followup=False)
                    except Exception as e:
                        diagnostics.append({
                            "symbol": payload.get("symbol"),
                            "status": status,
                            "publish": False,
                            "publish_reason": f"telegram_ops_send_fail: {e}",
                        })

            if ops_chat_id:
                for a in health_alerts:
                    hmsg = f"[HEALTH] {a['symbol']} no OK >= {a['since_ok_hours']}h | last={a['status']} | {a['reason']}"
                    try:
                        send_telegram(token, ops_chat_id, hmsg, image_url=None, image_path=None, send_detail_followup=False)
                    except Exception as e:
                        diagnostics.append({
                            "symbol": a.get("symbol"),
                            "status": "HEALTH",
                            "publish": False,
                            "publish_reason": f"telegram_health_send_fail: {e}",
                        })

            if sent_any:
                state["last_sent_at"] = now_utc.isoformat()

            _save_state(state)

    _append_decision_log(decision_rows)

    print("V2_POLICY", json.dumps(diagnostics, ensure_ascii=False))
    print("\n\n".join([m for m, _, _, _ in out_msgs]))


if __name__ == "__main__":
    main()
