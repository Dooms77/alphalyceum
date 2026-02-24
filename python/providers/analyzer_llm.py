import json
import os
import re
import time
from pathlib import Path
import requests

_OLLAMA_OK_CACHE = {"ts": 0, "ok": None}


def _extract_json(text: str) -> dict:
    raw = (text or "").strip()
    if not raw:
        return {}

    raw = re.sub(r"^```(?:json)?", "", raw).strip()
    raw = re.sub(r"```$", "", raw).strip()

    try:
        data = json.loads(raw)
        return data if isinstance(data, dict) else {}
    except Exception:
        pass

    try:
        start = raw.find("{")
        end = raw.rfind("}")
        if start >= 0 and end > start:
            data = json.loads(raw[start : end + 1])
            return data if isinstance(data, dict) else {}
    except Exception:
        pass

    return {}


def _is_placeholder(value: str) -> bool:
    v = str(value or "").strip().lower()
    if not v:
        return True
    return v in {
        "...",
        "-",
        "angka - angka",
        "bullish|bearish|mixed|neutral",
        "m15|h1|h4",
        "menunggu analisa lanjutan",
        "tunggu analisa lanjutan",
        "no clear signal",
        "momentum neutral",
        "waiting for a clear signal to enter the trade",
    }


def _has_signal(data: dict) -> bool:
    if not isinstance(data, dict) or not data:
        return False

    # Reject malformed payloads that look like tradingview context passthrough
    has_plan = isinstance(data.get("plan"), dict)
    has_pa = isinstance(data.get("price_action"), dict)
    has_note = not _is_placeholder(data.get("technical_note", ""))
    if not (has_plan or has_pa or has_note):
        return False

    plan = data.get("plan") if has_plan else {}
    pa = data.get("price_action") if has_pa else {}

    bias = str(data.get("bias", "")).strip().lower()
    if bias in {"bullish", "bearish", "mixed"}:
        return True

    if any(not _is_placeholder(plan.get(k, "")) for k in ["entry_zone", "tp_zone", "sl_zone", "resistance", "support", "scenario", "timeframe"]):
        return True
    if any(not _is_placeholder(pa.get(k, "")) for k in ["market_phase", "candle_signal", "momentum_note", "invalidation"]):
        return True
    return has_note


def _build_prompt(symbol: str, tv: dict, news: dict, market_ctx: dict) -> str:
    sym = str(symbol).upper()
    pair_rules = ""
    if "BTC" in sym:
        pair_rules = (
            "Fokus driver BTC: risk-on/risk-off, arus ETF/crypto flow, likuiditas USD, dan volatilitas intraday. "
            "Hindari narasi emas/geopolitik sebagai driver utama kecuali ada bukti jelas di headlines."
        )
    elif "XAU" in sym or "GOLD" in sym:
        pair_rules = (
            "Fokus driver XAU: DXY, US yield, ekspektasi suku bunga/FED, dan geopolitik safe-haven. "
            "Hindari narasi crypto flow sebagai driver utama."
        )

    return f"""
Kamu analis trading influencer Indonesia: bahasanya modern, lugas, tidak kaku, tetap profesional.
Tugas: hasilkan analisa {symbol} untuk swing/intraday berbasis konteks chart+news+market terakhir.

Aturan pair-spesifik:
{pair_rules}

Konteks chart:
{json.dumps(tv, ensure_ascii=False)}

Konteks news:
{json.dumps(news, ensure_ascii=False)}

Konteks market terbaru:
{json.dumps(market_ctx, ensure_ascii=False)}

Aturan keras:
1) Balas JSON VALID SAJA (tanpa markdown/codefence).
2) Jangan output template kosong/default.
3) Zone angka harus masuk akal terhadap last_price jika tersedia.
4) Conviction 0-100 berdasarkan kualitas konfirmasi.
5) Gunakan kalimat Indonesia modern untuk field naratif.
6) Jangan copy kalimat yang sama antar pair; narasi harus relevan ke pair ini.

Format WAJIB:
{{
  "bias": "bullish|bearish|mixed|neutral",
  "price_action": {{
    "market_phase": "...",
    "candle_signal": "...",
    "momentum_note": "...",
    "invalidation": "..."
  }},
  "plan": {{
    "timeframe": "M15|H1|H4",
    "entry_zone": "angka - angka",
    "tp_zone": "angka - angka",
    "sl_zone": "angka - angka",
    "resistance": "angka - angka",
    "support": "angka - angka",
    "conviction": 0,
    "scenario": "..."
  }},
  "technical_note": "..."
}}
""".strip()


def _ollama_available(ttl_sec: int = 20) -> bool:
    now = time.time()
    if _OLLAMA_OK_CACHE["ok"] is not None and (now - _OLLAMA_OK_CACHE["ts"]) < ttl_sec:
        return bool(_OLLAMA_OK_CACHE["ok"])
    try:
        r = requests.get("http://127.0.0.1:11434/api/tags", timeout=2)
        ok = r.ok
    except Exception:
        ok = False
    _OLLAMA_OK_CACHE["ts"] = now
    _OLLAMA_OK_CACHE["ok"] = ok
    return ok


def _call_ollama(payload: dict, timeout: int = 25) -> dict:
    r = requests.post("http://127.0.0.1:11434/api/generate", json=payload, timeout=timeout)
    r.raise_for_status()
    return _extract_json((r.json() or {}).get("response", "{}"))


def _parse_expires_to_ms(raw) -> int:
    try:
        v = int(str(raw).strip())
        return v * 1000 if v < 10_000_000_000 else v
    except Exception:
        return 0


def _token_valid(expires_ms: int, skew_sec: int = 90) -> bool:
    if not expires_ms:
        return True
    return expires_ms > int(time.time() * 1000) + (skew_sec * 1000)


def _oauth_file_path(oauth_cfg: dict) -> Path | None:
    p = str(oauth_cfg.get("credentials_file", "")).strip()
    if not p:
        return None
    return Path(p)


def _load_project_oauth(oauth_cfg: dict) -> dict:
    p = _oauth_file_path(oauth_cfg)
    if not p or not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_project_oauth(oauth_cfg: dict, data: dict):
    p = _oauth_file_path(oauth_cfg)
    if not p:
        return
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _refresh_from_refresh_token(refresh_token: str, oauth_cfg: dict) -> dict:
    token_url = str(oauth_cfg.get("token_url", "https://auth.openai.com/oauth/token")).strip()
    client_id = str(oauth_cfg.get("client_id", "")).strip()

    data = {
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
    }
    if client_id:
        data["client_id"] = client_id

    client_secret_env = oauth_cfg.get("client_secret_env")
    if client_secret_env:
        sec = os.getenv(str(client_secret_env), "").strip()
        if sec:
            data["client_secret"] = sec

    scope = str(oauth_cfg.get("scope", "")).strip()
    if scope:
        data["scope"] = scope

    r = requests.post(token_url, data=data, timeout=20)
    r.raise_for_status()
    return r.json() or {}


def _get_oauth_access_token(oauth_cfg: dict) -> str:
    # 1) direct access token in env
    env_access = oauth_cfg.get("access_token_env")
    if env_access:
        tok = os.getenv(str(env_access), "").strip()
        if tok:
            return tok

    # 2) project-local oauth json (for separate GPT account)
    local = _load_project_oauth(oauth_cfg)
    local_access = str(local.get("access_token", "")).strip()
    local_refresh = str(local.get("refresh_token", "")).strip()
    local_exp_ms = _parse_expires_to_ms(local.get("expires_at_ms"))

    if local_access and _token_valid(local_exp_ms):
        return local_access

    # 3) refresh from project-local refresh token
    if local_refresh:
        try:
            new_tok = _refresh_from_refresh_token(local_refresh, oauth_cfg)
            access = str(new_tok.get("access_token", "")).strip()
            refresh = str(new_tok.get("refresh_token", "")).strip() or local_refresh
            expires_in = int(new_tok.get("expires_in", 0) or 0)
            if access:
                merged = dict(local)
                merged.update({
                    "access_token": access,
                    "refresh_token": refresh,
                    "token_type": str(new_tok.get("token_type", "Bearer")),
                    "scope": str(new_tok.get("scope", local.get("scope", ""))),
                    "obtained_at_ms": int(time.time() * 1000),
                    "expires_at_ms": int(time.time() * 1000) + max(expires_in, 0) * 1000,
                })
                _save_project_oauth(oauth_cfg, merged)
                return access
        except Exception:
            pass

    # 4) env refresh fallback
    env_refresh = oauth_cfg.get("refresh_token_env")
    refresh_env_val = os.getenv(str(env_refresh), "").strip() if env_refresh else ""
    if refresh_env_val:
        try:
            tok = _refresh_from_refresh_token(refresh_env_val, oauth_cfg)
            return str(tok.get("access_token", "")).strip()
        except Exception:
            pass

    return ""


def _call_gpt_oauth(prompt: str, cfg: dict) -> dict:
    oauth_cfg = ((cfg or {}).get("analysis") or {}).get("openai_oauth") or {}
    if not bool(oauth_cfg.get("enabled", False)):
        return {}

    token = _get_oauth_access_token(oauth_cfg)
    if not token:
        return {}

    base_url = str(oauth_cfg.get("base_url", "https://api.openai.com/v1")).rstrip("/")
    model = str(oauth_cfg.get("model", "gpt-5-codex"))
    timeout_sec = int(oauth_cfg.get("timeout_sec", 45))

    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    # Use responses API first
    r = requests.post(
        f"{base_url}/responses",
        headers=headers,
        json={
            "model": model,
            "input": prompt,
            "max_output_tokens": int(oauth_cfg.get("max_tokens", 900)),
        },
        timeout=timeout_sec,
    )
    if r.ok:
        out = (r.json() or {}).get("output") or []
        chunks = []
        for item in out:
            for c in (item.get("content") or []):
                if c.get("type") in {"output_text", "text"}:
                    chunks.append(c.get("text", ""))
        data = _extract_json("\n".join([x for x in chunks if x]))
        if data:
            return data

    # Fallback chat.completions
    r2 = requests.post(
        f"{base_url}/chat/completions",
        headers=headers,
        json={
            "model": model,
            "messages": [
                {"role": "system", "content": "Balas JSON valid tanpa markdown."},
                {"role": "user", "content": prompt},
            ],
            "temperature": float(oauth_cfg.get("temperature", 0.2)),
            "max_tokens": int(oauth_cfg.get("max_tokens", 900)),
        },
        timeout=timeout_sec,
    )
    r2.raise_for_status()
    raw = (((r2.json() or {}).get("choices") or [{}])[0].get("message") or {}).get("content", "")
    return _extract_json(raw)


def analyze_with_ollama(symbol: str, tv: dict, news: dict, market_ctx: dict, model: str = "deepseek-r1:14b", cfg: dict | None = None) -> dict:
    cfg = cfg or {}
    analysis_cfg = (cfg.get("analysis") or {})
    prompt = _build_prompt(symbol, tv, news, market_ctx)

    if _ollama_available():
        payload_1 = {"model": model, "prompt": prompt, "stream": False, "format": "json", "options": {"temperature": 0.15}}
        try:
            d1 = _call_ollama(payload_1, timeout=25)
            if _has_signal(d1):
                return d1
        except Exception:
            pass

        # Local ollama fallback model (faster)
        fallback_model = str(analysis_cfg.get("ollama_fallback_model", "llama3.2:3b")).strip()
        if fallback_model and fallback_model != model:
            payload_2 = {"model": fallback_model, "prompt": prompt, "stream": False, "format": "json", "options": {"temperature": 0.15}}
            try:
                d2 = _call_ollama(payload_2, timeout=20)
                if _has_signal(d2):
                    return d2
            except Exception:
                pass

    # Fast fallback to OAuth to avoid long hangs when local model is unavailable/slow.
    try:
        d3 = _call_gpt_oauth(prompt, cfg)
        if _has_signal(d3):
            return d3
    except Exception:
        pass

    return {}
