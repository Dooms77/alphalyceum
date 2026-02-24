import re, csv
from pathlib import Path
log=Path(r"C:/Users/AORUS/AppData/Roaming/MetaQuotes/Tester/D0E8209F77C8CF37AD8BF550E51FF075/Agent-127.0.0.1-3000/logs/20260214.log")
text=log.read_text(encoding='utf-16',errors='ignore').replace('\x00','')
lines=text.splitlines()
rows=[]
cur={}
for ln in lines:
    m=re.search(r'InpRSILow=([0-9\.]+)',ln)
    if m: cur['rsi_low']=float(m.group(1)); continue
    m=re.search(r'InpRSIHigh=([0-9\.]+)',ln)
    if m: cur['rsi_high']=float(m.group(1)); continue
    m=re.search(r'InpADXMin=([0-9\.]+)',ln)
    if m: cur['adx']=float(m.group(1)); continue
    m=re.search(r'InpRR=([0-9\.]+)',ln)
    if m: cur['rr']=float(m.group(1)); continue
    m=re.search(r'InpRiskPercent=([0-9\.]+)',ln)
    if m: cur['risk_pct']=float(m.group(1)); continue
    m=re.search(r'final balance ([0-9\.]+) USD',ln)
    if m and all(k in cur for k in ('rsi_low','adx','rr')):
        bal=float(m.group(1))
        row=dict(cur)
        row['final_balance']=bal
        row['net_profit']=round(bal-10000,2)
        rows.append(row)
        cur={}

# keep only the recent autolab block around 23:00 onwards where risk exists
filtered=[r for r in rows if r.get('risk_pct') in (0.5,1.0) and r.get('adx') in (25.0,30.0,35.0) and r.get('rr') in (2.0,3.0) and r.get('rsi_low') in (15.0,20.0)]
out=Path(r"D:/alphalyceum/phase1/autolab/results/autolab_balance_scan.csv")
out.parent.mkdir(parents=True,exist_ok=True)
with out.open('w',newline='',encoding='utf-8') as f:
    w=csv.DictWriter(f,fieldnames=['rsi_low','rsi_high','adx','rr','risk_pct','final_balance','net_profit'])
    w.writeheader(); w.writerows(filtered)
print('rows',len(filtered))
if filtered:
    best=max(filtered,key=lambda x:x['net_profit'])
    print('best',best)
