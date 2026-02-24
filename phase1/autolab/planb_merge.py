import csv
from pathlib import Path

grid = list(csv.DictReader(open(r"D:\alphalyceum\phase1\autolab\grids\v4_rr_strict_5y.csv", encoding="utf-8-sig")))
scan = list(csv.DictReader(open(r"D:\alphalyceum\phase1\autolab\results\v4_balance_scan.csv", encoding="utf-8-sig")))

out = []
for gr, br in zip(grid, scan):
    out.append({
        "run_id": gr["run_id"],
        "rr": br["rr"],
        "rsi_low": br["rsi_low"],
        "rsi_high": br["rsi_high"],
        "adx": br["adx"],
        "session": f"{int(float(br['s_start']))}-{int(float(br['s_end']))}",
        "min_atr": br["min_atr"],
        "max_spread": br["max_spread"],
        "risk_pct": br["risk_pct"],
        "final_balance": br["final_balance"],
        "net_profit": br["net_profit"],
    })

out.sort(key=lambda x: float(x["net_profit"]), reverse=True)
out_path = Path(r"D:\alphalyceum\phase1\autolab\results\v4_planb_summary.csv")
with out_path.open("w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=list(out[0].keys()))
    w.writeheader()
    w.writerows(out)

print(out_path)
for r in out[:3]:
    print(r)
