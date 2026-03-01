#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import html
import json
import re
import zipfile
import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path

NS = {
    "a": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "pr": "http://schemas.openxmlformats.org/package/2006/relationships",
}


def clean_text(v):
    if v is None:
        return None
    s = str(v).strip()
    if s == "" or s.upper() == "NULL":
        return None
    return s


def to_num(v):
    s = clean_text(v)
    if s is None:
        return None
    s = s.replace(",", "").replace("$", "")
    try:
        return float(s)
    except ValueError:
        return None


def excel_serial_to_date(v):
    s = clean_text(v)
    if s is None:
        return None
    try:
        x = float(s)
        if x <= 0:
            return None
        d = dt.datetime(1899, 12, 30) + dt.timedelta(days=x)
        return d.date().isoformat()
    except ValueError:
        return s[:10]


def norm(s):
    return re.sub(r"[^a-z0-9]+", "", (s or "").lower())


def col_letters(cell_ref):
    m = re.match(r"([A-Z]+)", cell_ref or "")
    return m.group(1) if m else ""


def col_to_idx(col):
    n = 0
    for ch in col:
        n = n * 26 + (ord(ch) - 64)
    return n - 1


def parse_shared_strings(zf):
    if "xl/sharedStrings.xml" not in zf.namelist():
        return []
    root = ET.fromstring(zf.read("xl/sharedStrings.xml"))
    out = []
    for si in root.findall("a:si", NS):
        t = si.find("a:t", NS)
        if t is not None:
            out.append(t.text or "")
        else:
            out.append("".join((tt.text or "") for tt in si.findall(".//a:t", NS)))
    return out


def first_sheet_path(zf):
    wb = ET.fromstring(zf.read("xl/workbook.xml"))
    rels = ET.fromstring(zf.read("xl/_rels/workbook.xml.rels"))
    rel_map = {r.attrib["Id"]: r.attrib["Target"] for r in rels.findall("pr:Relationship", NS)}
    sheet = wb.find("a:sheets/a:sheet", NS)
    rid = sheet.attrib[f"{{{NS['r']}}}id"]
    return "xl/" + rel_map[rid].lstrip("/")


def cell_value(c, shared):
    t = c.attrib.get("t")
    if t == "s":
        v = c.find("a:v", NS)
        return shared[int(v.text)] if v is not None and v.text else ""
    if t == "inlineStr":
        return "".join((tt.text or "") for tt in c.findall(".//a:t", NS))
    v = c.find("a:v", NS)
    return (v.text or "") if v is not None else ""


def iter_sheet_rows(zf, path, shared):
    with zf.open(path) as fh:
        for _, elem in ET.iterparse(fh, events=("end",)):
            if elem.tag.endswith("}row"):
                row = {}
                for c in elem.findall("a:c", NS):
                    idx = col_to_idx(col_letters(c.attrib.get("r", "")))
                    row[idx] = cell_value(c, shared)
                yield row
                elem.clear()


def pick(headers, *names):
    hs = [norm(h) for h in headers]
    for n in names:
        nn = norm(n)
        for i, h in enumerate(hs):
            if h == nn or nn in h:
                return i
    return None


def get(row, idx):
    if idx is None or idx >= len(row):
        return None
    return clean_text(row[idx])


def merge_max(existing, incoming):
    if incoming is None:
        return existing
    if existing is None:
        return incoming
    return max(existing, incoming)


def write_csv(path: Path, rows, headers):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=headers)
        w.writeheader()
        for r in rows:
            out = {}
            for h in headers:
                v = r.get(h)
                if isinstance(v, float):
                    out[h] = f"{v:.6f}".rstrip("0").rstrip(".")
                elif v is None:
                    out[h] = ""
                else:
                    out[h] = str(v)
            w.writerow(out)


def write_multi_sheet_xlsx(output_file: Path, sheets_data):
    output_file.parent.mkdir(parents=True, exist_ok=True)

    def safe_sheet_name(name, used):
        forbidden = set("[]:*?/\\")
        s = "".join("_" if c in forbidden else c for c in name).strip("'")
        s = (s or "Sheet")[:31]
        base = s
        i = 1
        while s.lower() in used:
            suf = f"_{i}"
            s = base[: 31 - len(suf)] + suf
            i += 1
        used.add(s.lower())
        return s

    def col_ref(n):
        n += 1
        out = ""
        while n:
            n, r = divmod(n - 1, 26)
            out = chr(65 + r) + out
        return out

    used = set()
    sheets = []
    for i, (name, rows, headers) in enumerate(sheets_data, start=1):
        sheets.append(
            {
                "id": i,
                "rid": f"rId{i}",
                "name": safe_sheet_name(name, used),
                "path": f"xl/worksheets/sheet{i}.xml",
                "rows": rows,
                "headers": headers,
            }
        )

    with zipfile.ZipFile(output_file, "w", compression=zipfile.ZIP_DEFLATED) as z:
        overrides = [
            '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>',
            '<Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>',
            '<Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>',
            '<Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>',
        ]
        overrides += [
            f'<Override PartName="/{s["path"]}" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
            for s in sheets
        ]
        z.writestr(
            "[Content_Types].xml",
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
            '<Default Extension="xml" ContentType="application/xml"/>'
            + "".join(overrides)
            + "</Types>",
        )
        z.writestr(
            "_rels/.rels",
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>'
            '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>'
            '<Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" Target="docProps/app.xml"/>'
            "</Relationships>",
        )
        now = dt.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
        z.writestr(
            "docProps/core.xml",
            f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">'
            "<dc:creator>Codex</dc:creator><cp:lastModifiedBy>Codex</cp:lastModifiedBy>"
            f'<dcterms:created xsi:type="dcterms:W3CDTF">{now}</dcterms:created>'
            f'<dcterms:modified xsi:type="dcterms:W3CDTF">{now}</dcterms:modified>'
            "<dc:title>VP Dashboard Data</dc:title></cp:coreProperties>",
        )
        z.writestr(
            "docProps/app.xml",
            f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties" xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes">'
            "<Application>Codex</Application>"
            f'<TitlesOfParts><vt:vector size="{len(sheets)}" baseType="lpstr">'
            + "".join(f"<vt:lpstr>{html.escape(s['name'])}</vt:lpstr>" for s in sheets)
            + "</vt:vector></TitlesOfParts></Properties>",
        )
        z.writestr(
            "xl/styles.xml",
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
            '<fonts count="1"><font><sz val="11"/><name val="Calibri"/></font></fonts>'
            '<fills count="2"><fill><patternFill patternType="none"/></fill><fill><patternFill patternType="gray125"/></fill></fills>'
            '<borders count="1"><border><left/><right/><top/><bottom/><diagonal/></border></borders>'
            '<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>'
            '<cellXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/></cellXfs>'
            '<cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles>'
            "</styleSheet>",
        )
        z.writestr(
            "xl/workbook.xml",
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets>'
            + "".join(f'<sheet name="{html.escape(s["name"])}" sheetId="{s["id"]}" r:id="{s["rid"]}"/>' for s in sheets)
            + "</sheets></workbook>",
        )
        z.writestr(
            "xl/_rels/workbook.xml.rels",
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            + "".join(
                f'<Relationship Id="{s["rid"]}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet{s["id"]}.xml"/>'
                for s in sheets
            )
            + '<Relationship Id="rIdStyles" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>'
            "</Relationships>",
        )

        for s in sheets:
            all_rows = [s["headers"]] + [[r.get(h, "") for h in s["headers"]] for r in s["rows"]]
            rows_xml = []
            for r_idx, row in enumerate(all_rows, start=1):
                cells = []
                for c_idx, val in enumerate(row):
                    txt = "" if val is None else str(val)
                    if txt == "":
                        continue
                    cells.append(
                        f'<c r="{col_ref(c_idx)}{r_idx}" t="inlineStr"><is><t xml:space="preserve">{html.escape(txt)}</t></is></c>'
                    )
                rows_xml.append(f'<row r="{r_idx}">' + "".join(cells) + "</row>")
            z.writestr(
                s["path"],
                '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData>'
                + "".join(rows_xml)
                + "</sheetData></worksheet>",
            )


def detect_source_file(root: Path):
    candidates = sorted(root.glob("*.xlsx"), key=lambda p: p.stat().st_mtime, reverse=True)
    for p in candidates:
        n = p.name.lower()
        if "preliminary" in n:
            continue
        return p
    return None


def main():
    parser = argparse.ArgumentParser(description="Build Tableau-ready VP dashboard datasets from raw Excel.")
    parser.add_argument("--source", type=str, help="Path to source xlsx. Default: newest xlsx in repo root.")
    parser.add_argument("--outdir", type=str, default="output/tableau_ready", help="Output directory.")
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    source = Path(args.source).resolve() if args.source else detect_source_file(root)
    if not source or not source.exists():
        raise SystemExit("No source xlsx found. Provide --source /path/to/file.xlsx")

    outdir = (root / args.outdir).resolve()
    outdir.mkdir(parents=True, exist_ok=True)

    loan_level = {}
    event_monthly = defaultdict(lambda: defaultdict(float))
    hc_monthly = defaultdict(lambda: {"active_sales_hc": None, "active_non_producing_sales_hc": None})
    dq_issues = []
    raw_rows = 0

    with zipfile.ZipFile(source) as zf:
        shared = parse_shared_strings(zf)
        sheet = first_sheet_path(zf)
        it = iter_sheet_rows(zf, sheet, shared)
        header_map = next(it)
        width = max(header_map.keys()) + 1
        headers = [""] * width
        for k, v in header_map.items():
            headers[k] = v

        c = {
            "loan": pick(headers, "Loannumber"),
            "loan_amount": pick(headers, "LoanAmount"),
            "vp": pick(headers, "VP"),
            "bom": pick(headers, "BOM"),
            "fund_date": pick(headers, "FundDate"),
            "state": pick(headers, "SubjectPropertyState"),
            "product": pick(headers, "ProductBucketGroup"),
            "purpose": pick(headers, "Purpose"),
            "comp_bucket": pick(headers, "CompensafeBucket"),
            "active_sales_hc": pick(headers, "ActiveSalesHC"),
            "active_non_hc": pick(headers, "ActiveNonProducingSalesHC"),
            "comp_amt": pick(headers, "Compensafe $"),
            "rent_amt": pick(headers, "Rent $ (BOM)"),
            "payroll_amt": pick(headers, "Payroll Reg Earnings $ (BOM)"),
            "spec_paid_amt": pick(headers, "SPEC Paid $"),
            "cra_paid_amt": pick(headers, "CRA Paid $"),
            "los_rev": pick(headers, "LOS Revenue $"),
            "gl_fee": pick(headers, "GL Fee Income $"),
            "gl_gos": pick(headers, "GL GOS $"),
            "gl_oi": pick(headers, "GL OI $"),
            "gl_exc": pick(headers, "GL Exception $"),
            "los_exc": pick(headers, "LOS Exception $"),
            "llr": pick(headers, "LLR $"),
            "corp_alloc": pick(headers, "Corporate Allocation $"),
        }

        rev_fields = ["los_rev", "gl_fee", "gl_gos", "gl_oi", "gl_exc", "los_exc"]
        exp_loan_fields = ["llr", "corp_alloc"]
        event_cost_fields = ["comp_amt", "rent_amt", "payroll_amt"]
        bonus_fields = ["spec_paid_amt", "cra_paid_amt"]

        for source_row, raw_map in enumerate(it, start=2):
            raw_rows += 1
            row = [""] * width
            for i, v in raw_map.items():
                if i < width:
                    row[i] = v

            loan = get(row, c["loan"])
            vp = get(row, c["vp"]) or "(Unknown VP)"
            bom = excel_serial_to_date(get(row, c["bom"])) or "unknown"
            month_key = (bom, vp)

            # HC monthly (use max to avoid row inflation)
            hc_monthly[month_key]["active_sales_hc"] = merge_max(
                hc_monthly[month_key]["active_sales_hc"], to_num(get(row, c["active_sales_hc"]))
            )
            hc_monthly[month_key]["active_non_producing_sales_hc"] = merge_max(
                hc_monthly[month_key]["active_non_producing_sales_hc"], to_num(get(row, c["active_non_hc"]))
            )

            # Event costs and bonus: row-level sum by VP+month
            for f in event_cost_fields + bonus_fields:
                event_monthly[month_key][f] += to_num(get(row, c[f])) or 0.0

            if (get(row, c["comp_bucket"]) or "") == "No Loan #":
                event_monthly[month_key]["no_loan_bucket_rows"] += 1

            # Loan-level dedupe
            if loan:
                lkey = (loan, vp, bom)
                entry = loan_level.get(lkey)
                rev_vals = {f: to_num(get(row, c[f])) for f in rev_fields}
                exp_loan_vals = {f: to_num(get(row, c[f])) for f in exp_loan_fields}
                if entry is None:
                    loan_level[lkey] = {
                        "loan_number": loan,
                        "vp": vp,
                        "report_month": bom,
                        "fund_date": excel_serial_to_date(get(row, c["fund_date"])),
                        "state": get(row, c["state"]),
                        "product_bucket_group": get(row, c["product"]),
                        "purpose": get(row, c["purpose"]),
                        "loan_amount": to_num(get(row, c["loan_amount"])),
                        **rev_vals,
                        **exp_loan_vals,
                        "row_count": 1,
                    }
                else:
                    entry["row_count"] += 1
                    # keep first non-null dimensions
                    for dim in ["fund_date", "state", "product_bucket_group", "purpose", "loan_amount"]:
                        cur = entry.get(dim)
                        new = (
                            excel_serial_to_date(get(row, c["fund_date"]))
                            if dim == "fund_date"
                            else to_num(get(row, c["loan_amount"]))
                            if dim == "loan_amount"
                            else get(row, c["state"])
                            if dim == "state"
                            else get(row, c["product"])
                            if dim == "product_bucket_group"
                            else get(row, c["purpose"])
                        )
                        if cur is None and new is not None:
                            entry[dim] = new
                        elif cur is not None and new is not None and cur != new:
                            dq_issues.append(
                                {
                                    "issue_type": f"inconsistent_{dim}",
                                    "issue_key": f"{loan}|{vp}|{bom}",
                                    "detail": f"{dim}: {cur} vs {new} at source row {source_row}",
                                }
                            )
                    # numeric fields choose max to avoid duplicated undercount
                    for f in rev_fields + exp_loan_fields:
                        entry[f] = merge_max(entry.get(f), rev_vals.get(f) if f in rev_vals else exp_loan_vals.get(f))

    # Build loan detail output
    loan_rows = []
    for v in loan_level.values():
        rev_total = sum(v.get(f) or 0.0 for f in ["los_rev", "gl_fee", "gl_gos", "gl_oi", "gl_exc", "los_exc"])
        exp_loan = sum(v.get(f) or 0.0 for f in ["llr", "corp_alloc"])
        loan_rows.append(
            {
                "report_month": v["report_month"],
                "vp": v["vp"],
                "loan_number": v["loan_number"],
                "fund_date": v["fund_date"],
                "state": v["state"],
                "product_bucket_group": v["product_bucket_group"],
                "purpose": v["purpose"],
                "loan_amount": v["loan_amount"],
                "revenue_total_loan_level": rev_total,
                "expense_total_loan_level": exp_loan,
                "los_revenue_amt": v.get("los_rev"),
                "gl_fee_income_amt": v.get("gl_fee"),
                "gl_gos_amt": v.get("gl_gos"),
                "gl_oi_amt": v.get("gl_oi"),
                "gl_exception_amt": v.get("gl_exc"),
                "los_exception_amt": v.get("los_exc"),
                "llr_amt": v.get("llr"),
                "corporate_allocation_amt": v.get("corp_alloc"),
                "source_row_count_under_loan_key": v.get("row_count"),
            }
        )

    # Build monthly KPI output
    monthly_acc = {}
    for l in loan_rows:
        key = (l["report_month"], l["vp"])
        m = monthly_acc.get(key)
        if m is None:
            m = {
                "report_month": l["report_month"],
                "vp": l["vp"],
                "loan_count": 0,
                "loan_volume": 0.0,
                "revenue_loan_level": 0.0,
                "expense_loan_level": 0.0,
            }
            monthly_acc[key] = m
        m["loan_count"] += 1
        m["loan_volume"] += l["loan_amount"] or 0.0
        m["revenue_loan_level"] += l["revenue_total_loan_level"] or 0.0
        m["expense_loan_level"] += l["expense_total_loan_level"] or 0.0

    monthly_rows = []
    exception_rows = []
    for key, m in sorted(monthly_acc.items()):
        bom, vp = key
        ev = event_monthly.get(key, {})
        hc = hc_monthly.get(key, {})

        event_cost = (ev.get("comp_amt", 0.0) + ev.get("rent_amt", 0.0) + ev.get("payroll_amt", 0.0))
        bonus_spend = ev.get("spec_paid_amt", 0.0) + ev.get("cra_paid_amt", 0.0)
        total_revenue = m["revenue_loan_level"]
        total_expense = m["expense_loan_level"] + event_cost
        contribution_margin = total_revenue - total_expense
        margin_pct = (contribution_margin / total_revenue) if total_revenue else None
        active_hc = hc.get("active_sales_hc")
        productivity = (total_revenue / active_hc) if active_hc not in (None, 0) else None
        roi = (total_revenue / bonus_spend) if bonus_spend else None

        reason = []
        if (ev.get("no_loan_bucket_rows", 0) or 0) > 0:
            reason.append("contains_no_loan_bucket_rows")
        if margin_pct is not None and (margin_pct < -0.5 or margin_pct > 0.9):
            reason.append("margin_outlier")
        if roi is not None and (roi < 0 or roi > 15):
            reason.append("roi_outlier")

        row = {
            "report_month": bom,
            "vp": vp,
            "loan_count": m["loan_count"],
            "loan_volume": m["loan_volume"],
            "total_revenue": total_revenue,
            "total_expense": total_expense,
            "contribution_margin": contribution_margin,
            "margin_pct": margin_pct,
            "active_sales_hc": active_hc,
            "active_non_producing_sales_hc": hc.get("active_non_producing_sales_hc"),
            "productivity": productivity,
            "bonus_spend_proxy": bonus_spend,
            "roi": roi,
            "event_compensafe_amt": ev.get("comp_amt", 0.0),
            "event_rent_amt": ev.get("rent_amt", 0.0),
            "event_payroll_amt": ev.get("payroll_amt", 0.0),
            "event_no_loan_bucket_rows": ev.get("no_loan_bucket_rows", 0),
            "exception_flag": 1 if reason else 0,
            "exception_reason": ",".join(reason) if reason else None,
        }
        monthly_rows.append(row)
        if reason:
            exception_rows.append(
                {
                    "report_month": bom,
                    "vp": vp,
                    "exception_reason": ",".join(reason),
                    "margin_pct": margin_pct,
                    "roi": roi,
                    "event_no_loan_bucket_rows": ev.get("no_loan_bucket_rows", 0),
                }
            )

    # Add data quality exceptions from dedupe conflicts
    for d in dq_issues:
        exception_rows.append(
            {
                "report_month": None,
                "vp": None,
                "exception_reason": d["issue_type"],
                "margin_pct": None,
                "roi": None,
                "event_no_loan_bucket_rows": None,
                "detail": d["detail"],
                "issue_key": d["issue_key"],
            }
        )

    kpi_headers = [
        "report_month",
        "vp",
        "loan_count",
        "loan_volume",
        "total_revenue",
        "total_expense",
        "contribution_margin",
        "margin_pct",
        "active_sales_hc",
        "active_non_producing_sales_hc",
        "productivity",
        "bonus_spend_proxy",
        "roi",
        "event_compensafe_amt",
        "event_rent_amt",
        "event_payroll_amt",
        "event_no_loan_bucket_rows",
        "exception_flag",
        "exception_reason",
    ]
    loan_headers = [
        "report_month",
        "vp",
        "loan_number",
        "fund_date",
        "state",
        "product_bucket_group",
        "purpose",
        "loan_amount",
        "revenue_total_loan_level",
        "expense_total_loan_level",
        "los_revenue_amt",
        "gl_fee_income_amt",
        "gl_gos_amt",
        "gl_oi_amt",
        "gl_exception_amt",
        "los_exception_amt",
        "llr_amt",
        "corporate_allocation_amt",
        "source_row_count_under_loan_key",
    ]
    exception_headers = [
        "report_month",
        "vp",
        "exception_reason",
        "margin_pct",
        "roi",
        "event_no_loan_bucket_rows",
        "detail",
        "issue_key",
    ]

    write_csv(outdir / "vp_kpi_monthly.csv", monthly_rows, kpi_headers)
    write_csv(outdir / "vp_loan_detail.csv", loan_rows, loan_headers)
    write_csv(outdir / "vp_exception_log.csv", exception_rows, exception_headers)

    write_multi_sheet_xlsx(
        outdir / "vp_dashboard_data.xlsx",
        [
            ("vp_kpi_monthly", monthly_rows, kpi_headers),
            ("vp_loan_detail", loan_rows, loan_headers),
            ("vp_exception_log", exception_rows, exception_headers),
        ],
    )

    summary = {
        "source_file": str(source),
        "generated_at": dt.datetime.now().replace(microsecond=0).isoformat(sep=" "),
        "raw_rows_read": raw_rows,
        "vp_month_rows": len(monthly_rows),
        "loan_detail_rows": len(loan_rows),
        "exception_rows": len(exception_rows),
        "output_files": [
            str(outdir / "vp_kpi_monthly.csv"),
            str(outdir / "vp_loan_detail.csv"),
            str(outdir / "vp_exception_log.csv"),
            str(outdir / "vp_dashboard_data.xlsx"),
        ],
        "run_fingerprint": hashlib.sha1(
            (str(source) + "|" + str(raw_rows) + "|" + str(len(loan_rows)) + "|" + str(len(monthly_rows))).encode(
                "utf-8"
            )
        ).hexdigest(),
    }
    (outdir / "build_summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")

    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()

