import requests


def _post_text(bot_token: str, chat_id: str, text: str) -> dict:
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    r = requests.post(url, data={"chat_id": chat_id, "text": text}, timeout=20)
    r.raise_for_status()
    return r.json()


def _build_compact_caption(text: str, max_len: int = 950, include_detail_hint: bool = False) -> str:
    lines = [ln for ln in text.splitlines() if ln.strip()]
    keep = []
    for ln in lines:
        if len("\n".join(keep + [ln])) > max_len:
            break
        keep.append(ln)

    caption = "\n".join(keep).strip()
    if not caption:
        caption = text[:max_len]

    if include_detail_hint and len(caption) < len(text):
        caption += "\n\n🧾 Detail lengkap dikirim di pesan berikutnya."
    return caption


def send_telegram(bot_token: str, chat_id: str, text: str, image_url: str | None = None, image_path: str | None = None, send_detail_followup: bool = False) -> dict:
    # Telegram sendPhoto caption limit is 1024 chars.
    need_truncate = len(text) > 1000
    caption = text if not need_truncate else _build_compact_caption(text, max_len=930, include_detail_hint=send_detail_followup)

    if image_path:
        url = f"https://api.telegram.org/bot{bot_token}/sendPhoto"
        with open(image_path, "rb") as f:
            r = requests.post(
                url,
                data={"chat_id": chat_id, "caption": caption},
                files={"photo": f},
                timeout=40,
            )
        r.raise_for_status()
        if send_detail_followup:
            _post_text(bot_token, chat_id, f"🧾 Detail Lengkap Analisa\n\n{text}")
        return r.json()

    if image_url:
        url = f"https://api.telegram.org/bot{bot_token}/sendPhoto"
        r = requests.post(url, data={"chat_id": chat_id, "photo": image_url, "caption": caption}, timeout=25)
        r.raise_for_status()
        if send_detail_followup:
            _post_text(bot_token, chat_id, f"🧾 Detail Lengkap Analisa\n\n{text}")
        return r.json()

    return _post_text(bot_token, chat_id, text)
