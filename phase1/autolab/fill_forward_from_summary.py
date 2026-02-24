import argparse
import csv
from pathlib import Path


def read_csv(path: Path):
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows, fieldnames):
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)


def main():
    p = argparse.ArgumentParser(description="Fill forward_checklist row from summary.csv run_id")
    p.add_argument("--summary", default="results/summary.csv")
    p.add_argument("--forward", default="results/forward_checklist.csv")
    p.add_argument("--run-id", required=True)
    p.add_argument("--row", type=int, default=1, help="1-based row index in forward_checklist")
    args = p.parse_args()

    summary_path = Path(args.summary)
    forward_path = Path(args.forward)

    srows = read_csv(summary_path)
    if not srows:
        raise SystemExit("summary.csv empty")

    match = None
    for r in srows:
        if r.get("run_id") == args.run_id:
            match = r
            break
    if not match:
        available = ", ".join(r.get("run_id", "") for r in srows[:10])
        raise SystemExit(f"run_id not found: {args.run_id}. Sample available: {available}")

    frows = read_csv(forward_path)
    if not frows:
        raise SystemExit("forward_checklist.csv has no data rows")

    idx = max(1, args.row) - 1
    if idx >= len(frows):
        raise SystemExit(f"row out of range: {args.row}")

    row = frows[idx]
    row["trades"] = match.get("total_trades", "")
    row["max_dd_pct"] = match.get("equity_dd_rel_pct", "")
    row["profit_factor"] = match.get("profit_factor", "")
    row["winrate_pct"] = match.get("winrate_pct", "")
    # Estimate expectancy in R from winrate and rr_target when available:
    # E[R] = p*RR - (1-p)*1
    try:
        rr = float(str(row.get("rr_target", "")).strip())
        wr = float(str(row.get("winrate_pct", "")).strip()) / 100.0
        exp_r = wr * rr - (1.0 - wr)
        row["expectancy_r"] = f"{exp_r:.4f}"
    except Exception:
        row["expectancy_r"] = ""

    note = row.get("notes", "").strip()
    add = f"filled from summary run_id={args.run_id}"
    row["notes"] = f"{note}; {add}" if note else add

    fieldnames = list(frows[0].keys())
    write_csv(forward_path, frows, fieldnames)

    print("Updated forward checklist row", args.row)
    print("run_id:", args.run_id)
    print("PF:", row["profit_factor"], "DD:", row["max_dd_pct"], "Trades:", row["trades"], "WR:", row["winrate_pct"])


if __name__ == "__main__":
    main()
