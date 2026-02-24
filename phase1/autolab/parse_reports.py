import argparse
import csv
import json
import re
from pathlib import Path

BASE = Path(r"D:/alphalyceum/phase1/autolab")
CFG = json.loads((BASE / "configs" / "autolab.json").read_text(encoding="utf-8"))

FIELDS = [
    "run_id", "net_profit", "profit_factor", "expected_payoff", "total_trades",
    "balance_dd_rel_pct", "equity_dd_rel_pct", "short_win_pct", "long_win_pct", "winrate_pct"
]


def find(pattern, text):
    m = re.search(pattern, text, re.I | re.S)
    return m.group(1).strip() if m else ""


def to_float(x):
    x = str(x).replace(" ", "").replace("%", "")
    try:
        return float(x)
    except Exception:
        return 0.0


def parse_reports(reports_dir: Path):
    rows = []
    report_files = sorted(list(reports_dir.glob("*.html")) + list(reports_dir.glob("*.htm")))
    for html in report_files:
        raw = html.read_text(encoding="utf-16", errors="ignore").replace("\x00", "")

        def get(label):
            return find(re.escape(label) + r':</td>\s*<td[^>]*><b>(.*?)</b>', raw)

        run_id = html.stem
        net_profit = to_float(get("Total Net Profit"))
        profit_factor = to_float(get("Profit Factor"))
        expected_payoff = to_float(get("Expected Payoff"))
        total_trades = to_float(get("Total Trades"))

        bdd = get("Balance Drawdown Relative")
        edd = get("Equity Drawdown Relative")
        sw = get("Short Trades (won %)")
        lw = get("Long Trades (won %)")
        pw = get("Profit Trades (% of total)")

        bdd_pct = to_float(find(r'([0-9\.]+%)', bdd) or bdd)
        edd_pct = to_float(find(r'([0-9\.]+%)', edd) or edd)
        sw_pct = to_float(find(r'\(([0-9\.]+%)\)', sw))
        lw_pct = to_float(find(r'\(([0-9\.]+%)\)', lw))
        winrate_pct = to_float(find(r'\(([0-9\.]+%)\)', pw))

        rows.append({
            "run_id": run_id,
            "net_profit": net_profit,
            "profit_factor": profit_factor,
            "expected_payoff": expected_payoff,
            "total_trades": total_trades,
            "balance_dd_rel_pct": bdd_pct,
            "equity_dd_rel_pct": edd_pct,
            "short_win_pct": sw_pct,
            "long_win_pct": lw_pct,
            "winrate_pct": winrate_pct,
        })
    return rows


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--reports-dir", default=CFG["reports_dir"])
    p.add_argument("--out", default=str(Path(CFG["results_dir"]) / "summary.csv"))
    args = p.parse_args()

    reports_dir = Path(args.reports_dir)
    out = Path(args.out)

    rows = parse_reports(reports_dir)

    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)

    print(f"Parsed {len(rows)} report(s) -> {out}")


if __name__ == "__main__":
    main()
