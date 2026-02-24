import re, pathlib
f = pathlib.Path(r"D:/alphalyceum/phase1/backtest/reports/v3_run1_adx30_rsi1585_rr2_risk05.html")
txt = f.read_text(encoding='utf-16', errors='ignore').replace('\x00','')
labels=[
'Total Net Profit','Profit Factor','Expected Payoff','Total Trades',
'Balance Drawdown Relative','Equity Drawdown Relative','Short Trades (won %)','Long Trades (won %)'
]
for lab in labels:
    m = re.search(re.escape(lab)+r':</td>\s*<td[^>]*><b>(.*?)</b>', txt, flags=re.I|re.S)
    print(lab+': '+(re.sub(r'\s+',' ',m.group(1)).strip() if m else 'N/A'))
