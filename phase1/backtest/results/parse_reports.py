import re, pathlib, json
base = pathlib.Path(r"D:/alphalyceum/phase1/backtest/reports")
files = [base/'ReportTester-193886584.html', base/'run_adx30.html', base/'run_adx35.html']
labels = [
    'InpADXMin','Total Net Profit','Profit Factor','Expected Payoff','Total Trades',
    'Balance Drawdown Relative','Equity Drawdown Relative','Short Trades (won %)','Long Trades (won %)'
]
for f in files:
    txt = f.read_text(encoding='utf-16', errors='ignore')
    txt = txt.replace('\x00','')
    print('\n===', f.name, '===')
    for lab in labels:
        m = re.search(re.escape(lab)+r':</td>\s*<td[^>]*><b>(.*?)</b>', txt, flags=re.I|re.S)
        if m:
            v = re.sub(r'\s+',' ',m.group(1)).strip()
            print(f'{lab}: {v}')
