#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
from pathlib import Path


def load_rows(path: Path):
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def to_float(v: str | None):
    if v is None:
        return None
    s = str(v).strip()
    if s == "":
        return None
    try:
        return float(s)
    except ValueError:
        return None


def main():
    root = Path(__file__).resolve().parents[1]
    data_dir = root / "output" / "3nf"
    report_dir = root / "output" / "tableau"
    report_dir.mkdir(parents=True, exist_ok=True)

    dim_loan = load_rows(data_dir / "dim_loan.csv")
    fact_event = load_rows(data_dir / "fact_compensafe_event.csv")
    fact_loan_snapshot = load_rows(data_dir / "fact_loan_snapshot.csv")
    dq = load_rows(data_dir / "etl_data_quality_issue.csv")

    loan_numbers = {r.get("loan_number") for r in dim_loan if (r.get("loan_number") or "").strip() != ""}
    loan_count = len(loan_numbers)
    event_count = len(fact_event)

    loan_amount_total = 0.0
    loan_amount_nonnull = 0
    for r in dim_loan:
        x = to_float(r.get("loan_amount"))
        if x is not None:
            loan_amount_total += x
            loan_amount_nonnull += 1

    checks = [
        {
            "name": "Loan Count baseline",
            "actual": loan_count,
            "expected": 2004,
            "passed": loan_count == 2004,
            "note": "COUNTD(dim_loan.loan_number) baseline",
        },
        {
            "name": "Event row baseline",
            "actual": event_count,
            "expected": 10999,
            "passed": event_count == 10999,
            "note": "fact_compensafe_event row count baseline",
        },
        {
            "name": "Loan snapshot grain check",
            "actual": len(fact_loan_snapshot),
            "expected": len(loan_numbers),
            "passed": len(fact_loan_snapshot) == len(loan_numbers),
            "note": "fact_loan_snapshot should be one row per loan in this sample",
        },
    ]

    dq_types = {}
    for row in dq:
        t = row.get("issue_type", "")
        dq_types[t] = dq_types.get(t, 0) + 1

    report = {
        "data_dir": str(data_dir),
        "summary": {
            "loan_count_distinct": loan_count,
            "event_row_count": event_count,
            "loan_amount_total": round(loan_amount_total, 2),
            "loan_amount_nonnull_rows": loan_amount_nonnull,
            "dq_issue_total": len(dq),
            "dq_issue_types": dq_types,
        },
        "checks": checks,
    }

    out_json = report_dir / "vp_dashboard_validation_report.json"
    out_md = report_dir / "vp_dashboard_validation_report.md"

    out_json.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    md_lines = [
        "# VP Dashboard 数据校验报告",
        "",
        f"- 数据目录: `{data_dir}`",
        f"- Distinct Loan Count: `{loan_count}`",
        f"- Event Row Count: `{event_count}`",
        f"- Loan Amount Total (dim_loan): `{round(loan_amount_total, 2)}`",
        f"- DQ Issues: `{len(dq)}`",
        "",
        "## 检查结果",
    ]
    for c in checks:
        status = "PASS" if c["passed"] else "FAIL"
        md_lines.append(f"- [{status}] {c['name']}: actual={c['actual']} expected={c['expected']} ({c['note']})")
    md_lines.append("")
    md_lines.append("## DQ 类型分布")
    for k, v in sorted(dq_types.items(), key=lambda x: (-x[1], x[0])):
        md_lines.append(f"- `{k}`: {v}")
    md_lines.append("")
    out_md.write_text("\n".join(md_lines), encoding="utf-8")

    print(f"Wrote: {out_json}")
    print(f"Wrote: {out_md}")
    for c in checks:
        print(f"{'PASS' if c['passed'] else 'FAIL'} | {c['name']} | actual={c['actual']} expected={c['expected']}")


if __name__ == "__main__":
    main()

