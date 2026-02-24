#!/usr/bin/env python3
import requests, json, sys

token = '8395986688:AAE73m_t5CHbclci5tEC96hQ7a7S3HE3IFM'
chat_id = '@ALPHALYCEUM77'

# 1) Check bot validity
try:
    r = requests.get(f'https://api.telegram.org/bot{token}/getMe', timeout=10)
    print('getMe status:', r.status_code)
    if r.ok:
        me = r.json()
        print('Bot info:', json.dumps(me, ensure_ascii=False))
    else:
        print('getMe failed:', r.text)
except Exception as e:
    print('ERROR getMe:', e)

# 2) Try send a test message (non-intrusive)
test_text = 'AlphaLyceum signal bot test - please ignore'
try:
    payload = {'chat_id': chat_id, 'text': test_text}
    r = requests.post(f'https://api.telegram.org/bot{token}/sendMessage', data=payload, timeout=10)
    print('sendMessage status:', r.status_code)
    if r.ok:
        resp = r.json()
        print('Sent ok, message_id:', resp.get('result', {}).get('message_id'))
    else:
        print('sendMessage failed:', r.text)
except Exception as e:
    print('ERROR sendMessage:', e)
