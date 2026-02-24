import re, csv
from pathlib import Path

log = Path(r"C:/Users/AORUS/AppData/Roaming/MetaQuotes/Tester/D0E8209F77C8CF37AD8BF550E51FF075/Agent-127.0.0.1-3000/logs/20260214.log")
text = log.read_text(encoding='utf-16', errors='ignore').replace('\x00', '')
lines = text.splitlines()
rows = []
cur = {}

patterns = {
    'rsi_period': r'InpRSIPeriod=([0-9\.]+)',
    'rsi_low': r'InpRSILow=([0-9\.]+)',
    'rsi_high': r'InpRSIHigh=([0-9\.]+)',
    'adx': r'InpADXMin=([0-9\.]+)',
    'rr': r'InpRR=([0-9\.]+)',
    'risk_pct': r'InpRiskPercent=([0-9\.]+)',
    's_start': r'InpSessionStartHour=([0-9\.]+)',
    's_end': r'InpSessionEndHour=([0-9\.]+)',
    'min_atr': r'InpMinATRPoints=([0-9\.]+)',
    'max_spread': r'InpMaxSpreadPoints=([0-9\.]+)',
}

for ln in lines:
    for key, pat in patterns.items():
        m = re.search(pat, ln)
        if m:
            cur[key] = float(m.group(1))
    m = re.search(r'final balance ([0-9\.]+) USD', ln)
    if m and 'rsi_period' in cur and 's_start' in cur:
        bal = float(m.group(1))
        row = dict(cur)
        row['final_balance'] = bal
        row['net_profit'] = round(bal - 10000, 2)
        rows.append(row)
        cur = {}

# last 36 corresponds to v5 batch
rows = rows[-36:]

for i, r in enumerate(rows, start=1):
    r['run_id'] = f"v5_{i:03d}"

fields = ['run_id','rsi_period','rsi_low','rsi_high','adx','rr','risk_pct','s_start','s_end','min_atr','max_spread','final_balance','net_profit']
out = Path(r"D:/alphalyceum/phase1/autolab/results/v5_balance_scan.csv")
out.parent.mkdir(parents=True, exist_ok=True)
with out.open('w', newline='', encoding='utf-8') as f:
    w = csv.DictWriter(f, fieldnames=fields)
    w.writeheader()
    w.writerows(rows)

print('rows', len(rows))
if rows:
    best = max(rows, key=lambda x: x['net_profit'])
    print('best', best)
