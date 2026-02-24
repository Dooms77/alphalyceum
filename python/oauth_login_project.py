import argparse
import base64
import hashlib
import json
import os
import secrets
import time
import urllib.parse
import webbrowser
from pathlib import Path

import requests


def b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode().rstrip("=")


def build_pkce_pair() -> tuple[str, str]:
    verifier = b64url(os.urandom(48))
    challenge = b64url(hashlib.sha256(verifier.encode()).digest())
    return verifier, challenge


def main():
    ap = argparse.ArgumentParser(description="Project-local OAuth login for AlphaLyceum V2 (separate GPT account)")
    ap.add_argument("--client-id", default="app_EMoamEEZ73f0CkXaXp7hrann")
    ap.add_argument("--token-url", default="https://auth.openai.com/oauth/token")
    ap.add_argument("--auth-url", default="https://auth.openai.com/oauth/authorize")
    ap.add_argument("--redirect-uri", default="http://localhost:1455/auth/callback")
    ap.add_argument("--scope", default="openid profile email offline_access")
    ap.add_argument("--out", default=r"D:\alphalyceum\v2\config\oauth_project.json")
    ap.add_argument("--no-open", action="store_true", help="Do not auto-open browser")
    args = ap.parse_args()

    verifier, challenge = build_pkce_pair()
    state = secrets.token_hex(16)

    q = {
        "response_type": "code",
        "client_id": args.client_id,
        "redirect_uri": args.redirect_uri,
        "scope": args.scope,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
        "state": state,
    }
    auth_link = f"{args.auth_url}?{urllib.parse.urlencode(q)}"

    print("\nOpen link ini dan login pakai AKUN GPT BARU untuk V2:\n")
    print(auth_link)
    print("\nSetelah approve, copy URL callback penuh dari browser lalu paste di bawah.\n")

    if not args.no_open:
        try:
            webbrowser.open(auth_link)
        except Exception:
            pass

    callback_url = input("Paste callback URL: ").strip()
    if not callback_url:
        raise SystemExit("Callback URL kosong.")

    pu = urllib.parse.urlparse(callback_url)
    params = urllib.parse.parse_qs(pu.query)
    code = (params.get("code") or [""])[0]
    got_state = (params.get("state") or [""])[0]
    if not code:
        raise SystemExit("Tidak ada code di callback URL.")
    if got_state != state:
        raise SystemExit("State mismatch. Ulangi login.")

    token_req = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": args.redirect_uri,
        "client_id": args.client_id,
        "code_verifier": verifier,
    }
    r = requests.post(args.token_url, data=token_req, timeout=30)
    r.raise_for_status()
    tok = r.json() or {}

    access = str(tok.get("access_token", "")).strip()
    refresh = str(tok.get("refresh_token", "")).strip()
    expires_in = int(tok.get("expires_in", 0) or 0)
    if not access:
        raise SystemExit("Token exchange gagal: access_token kosong.")

    now = int(time.time() * 1000)
    out = {
        "access_token": access,
        "refresh_token": refresh,
        "token_type": str(tok.get("token_type", "Bearer")),
        "scope": str(tok.get("scope", args.scope)),
        "obtained_at_ms": now,
        "expires_at_ms": now + (expires_in * 1000),
        "client_id": args.client_id,
        "token_url": args.token_url,
    }

    p = Path(args.out)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"\n✅ OAuth project disimpan ke: {p}")
    print("Sekarang V2 akan pakai kredensial ini (bukan auth OpenClaw default).")


if __name__ == "__main__":
    main()
