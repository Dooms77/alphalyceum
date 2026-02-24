import csv
import json
from pathlib import Path

BASE = Path(r"D:/alphalyceum/phase1/autolab")
summary = BASE / "results" / "summary.csv"
ranked = BASE / "results" / "ranking.csv"
best = BASE / "results" / "best_run.json"

rows = []
with summary.open(newline="", encoding="utf-8") as f:
    for r in csv.DictReader(f):
        for k in ["net_profit","profit_factor","expected_payoff","total_trades","balance_dd_rel_pct","equity_dd_rel_pct","short_win_pct","long_win_pct"]:
            r[k] = float(r[k] or 0)
        win_avg = (r["short_win_pct"] + r["long_win_pct"]) / 2.0
        # scoring robust: prefer PF, net, DD control, sample size
        score = (r["profit_factor"] * 45) + (max(r["net_profit"], -2000)/100) + (min(r["total_trades"], 300)/300*20) - (r["equity_dd_rel_pct"]*1.2) + (win_avg*0.3)
        r["win_avg_pct"] = round(win_avg, 2)
        r["score"] = round(score, 3)
        rows.append(r)

rows.sort(key=lambda x: x["score"], reverse=True)

with ranked.open("w", newline="", encoding="utf-8") as f:
    fields = list(rows[0].keys()) if rows else []
    if fields:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)

if rows:
    best.write_text(json.dumps(rows[0], indent=2), encoding="utf-8")
    print(f"Best run: {rows[0]['run_id']} | score={rows[0]['score']}")
else:
    print("No rows to optimize")
