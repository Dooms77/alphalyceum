import argparse
import csv
from pathlib import Path


def f(v, default=0.0):
    try:
        return float(v)
    except Exception:
        return default


def i(v, default=0):
    try:
        return int(float(v))
    except Exception:
        return default


def evaluate(row: dict) -> tuple[str, list[str]]:
    reasons = []

    required = ["trades", "max_dd_pct", "profit_factor", "winrate_pct", "expectancy_r"]
    missing = [k for k in required if str(row.get(k, "")).strip() == ""]
    if missing:
        return "HOLD", [
            "HOLD: data belum lengkap untuk keputusan final",
            f"Missing metrics: {', '.join(missing)}"
        ]

    trades = i(row.get("trades"))
    max_dd = f(row.get("max_dd_pct"))
    pf = f(row.get("profit_factor"))
    wr = f(row.get("winrate_pct"))
    exp_r = f(row.get("expectancy_r"))
    tg_fail = f(row.get("telegram_fail_pct"))
    bugs = i(row.get("critical_bugs"))

    # Hard no-go
    if max_dd > 10:
        reasons.append("NO-GO: max_dd_pct > 10")
    if pf < 1.10:
        reasons.append("NO-GO: profit_factor < 1.10")
    if trades < 20:
        reasons.append("NO-GO: trades < 20 (insufficient sample)")
    if wr < 25:
        reasons.append("NO-GO: winrate_pct < 25")
    if exp_r <= 0:
        reasons.append("NO-GO: expectancy_r <= 0")
    if tg_fail >= 2:
        reasons.append("NO-GO: telegram_fail_pct >= 2")
    if bugs > 0:
        reasons.append("NO-GO: critical_bugs > 0")

    if any(r.startswith("NO-GO") for r in reasons):
        return "NO-GO", reasons

    # Hard-go gates
    hard_go = (
        max_dd <= 8 and
        pf >= 1.25 and
        trades >= 30 and
        tg_fail < 2 and
        bugs == 0
    )

    quality_go = (wr >= 30) or (exp_r >= 0.15)

    if hard_go and quality_go:
        return "GO", [
            "PASS: DD/PF/Trades/Operations gates passed",
            "PASS: Winrate or Expectancy quality gate passed"
        ]

    # Middle state
    hold_reasons = []
    if 8 < max_dd <= 10:
        hold_reasons.append("HOLD: DD in gray zone (8-10)")
    if 1.10 <= pf < 1.25:
        hold_reasons.append("HOLD: PF acceptable but below GO target")
    if 20 <= trades < 30:
        hold_reasons.append("HOLD: sample moderate, not yet robust")
    if 25 <= wr < 30 and exp_r < 0.15:
        hold_reasons.append("HOLD: edge exists but quality not strong")

    if not hold_reasons:
        hold_reasons.append("HOLD: does not meet full GO criteria yet")

    return "HOLD", hold_reasons


def main():
    p = argparse.ArgumentParser(description="Evaluate forward-test GO/HOLD/NO-GO decision")
    p.add_argument("--csv", default="results/forward_checklist.csv", help="Path to forward checklist CSV")
    p.add_argument("--row", type=int, default=1, help="1-based data row index (excluding header)")
    args = p.parse_args()

    csv_path = Path(args.csv)
    if not csv_path.exists():
        raise SystemExit(f"CSV not found: {csv_path}")

    with open(csv_path, "r", encoding="utf-8-sig", newline="") as f_in:
        rows = list(csv.DictReader(f_in))

    if not rows:
        raise SystemExit("CSV has no data rows")

    idx = max(1, args.row) - 1
    if idx >= len(rows):
        raise SystemExit(f"Row {args.row} out of range. Available rows: {len(rows)}")

    row = rows[idx]
    verdict, reasons = evaluate(row)

    print("=== FORWARD DECISION ===")
    print(f"Row: {args.row}")
    print(f"Period: {row.get('period', '')}")
    print(f"Pair/TF: {row.get('pair', '')} {row.get('timeframe', '')}")
    print(f"Verdict: {verdict}")
    print("Reasons:")
    for r in reasons:
        print(f"- {r}")


if __name__ == "__main__":
    main()
