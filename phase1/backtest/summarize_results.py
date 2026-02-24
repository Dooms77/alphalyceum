import csv
from pathlib import Path

BASE = Path(r"D:\alphalyceum\phase1\backtest")
summary_path = BASE / "results" / "summary.csv"
ranking_path = BASE / "results" / "ranking.csv"

# Placeholder parser: report HTML MT5 berbeda format antar broker/build.
# Untuk fase ini, kita ranking dari summary.csv yang nanti diisi runner/atau manual import.

rows = []
if summary_path.exists():
    with open(summary_path, newline='', encoding='utf-8') as f:
        rows = list(csv.DictReader(f))

if not rows:
    print("No rows in summary.csv yet")
    raise SystemExit(0)

for r in rows:
    pf = float(r.get("profit_factor", 0) or 0)
    dd = float(r.get("max_drawdown_pct", 999) or 999)
    trades = float(r.get("trades", 0) or 0)
    oos = float(r.get("oos_ratio", 0) or 0)
    # Robust score (simple weighted)
    r["robust_score"] = round((pf * 40) + (oos * 30) + (min(trades, 300)/300*20) - (dd*0.5), 2)

rows.sort(key=lambda x: float(x["robust_score"]), reverse=True)

with open(ranking_path, 'w', newline='', encoding='utf-8') as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
    w.writeheader()
    w.writerows(rows)

print(f"Ranking saved: {ranking_path}")
