#!/usr/bin/env python3
from __future__ import annotations

import csv
import datetime as dt
import hashlib
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


def norm(s: str | None) -> str:
    return re.sub(r"[^a-z0-9]+", "", (s or "").lower())


def clean_text(v: str | None) -> str | None:
    if v is None:
        return None
    s = str(v).strip()
    if s == "":
        return None
    if s.upper() == "NULL":
        return None
    return s


def parse_num(v: str | None) -> float | None:
    s = clean_text(v)
    if s is None:
        return None
    s = s.replace(",", "").replace("$", "")
    if s.endswith("%"):
        s = s[:-1]
    try:
        return float(s)
    except ValueError:
        return None


def parse_int(v: str | None) -> int | None:
    x = parse_num(v)
    if x is None:
        return None
    try:
        return int(round(x))
    except Exception:
        return None


def excel_serial_to_date(v: str | None) -> str | None:
    s = clean_text(v)
    if s is None:
        return None
    try:
        x = float(s)
    except ValueError:
        # Already text date
        try:
            return dt.date.fromisoformat(s[:10]).isoformat()
        except Exception:
            return s
    if x <= 0:
        return None
    d = dt.datetime(1899, 12, 30) + dt.timedelta(days=x)
    return d.date().isoformat()


def excel_serial_to_timestamp(v: str | None) -> str | None:
    s = clean_text(v)
    if s is None:
        return None
    try:
        x = float(s)
    except ValueError:
        return s
    if x <= 0:
        return None
    d = dt.datetime(1899, 12, 30) + dt.timedelta(days=x)
    return d.replace(microsecond=0).isoformat(sep=" ")


def col_letters(cell_ref: str) -> str:
    m = re.match(r"([A-Z]+)", cell_ref or "")
    return m.group(1) if m else ""


def col_to_idx(col: str) -> int:
    n = 0
    for ch in col:
        n = n * 26 + (ord(ch) - 64)
    return n - 1


def parse_shared_strings(zf: zipfile.ZipFile) -> list[str]:
    if "xl/sharedStrings.xml" not in zf.namelist():
        return []
    root = ET.fromstring(zf.read("xl/sharedStrings.xml"))
    out: list[str] = []
    for si in root.findall("a:si", NS):
        t = si.find("a:t", NS)
        if t is not None:
            out.append(t.text or "")
        else:
            out.append("".join((tt.text or "") for tt in si.findall(".//a:t", NS)))
    return out


def first_sheet_path(zf: zipfile.ZipFile) -> str:
    wb = ET.fromstring(zf.read("xl/workbook.xml"))
    rels = ET.fromstring(zf.read("xl/_rels/workbook.xml.rels"))
    rel_map = {r.attrib["Id"]: r.attrib["Target"] for r in rels.findall("pr:Relationship", NS)}
    sheet = wb.find("a:sheets/a:sheet", NS)
    rid = sheet.attrib[f"{{{NS['r']}}}id"]
    target = rel_map[rid]
    return "xl/" + target.lstrip("/")


def cell_value(c: ET.Element, shared: list[str]) -> str:
    t = c.attrib.get("t")
    if t == "s":
        v = c.find("a:v", NS)
        return shared[int(v.text)] if v is not None and v.text else ""
    if t == "inlineStr":
        return "".join((tt.text or "") for tt in c.findall(".//a:t", NS))
    v = c.find("a:v", NS)
    return (v.text or "") if v is not None else ""


def iter_sheet_rows(zf: zipfile.ZipFile, sheet_path: str, shared: list[str]):
    with zf.open(sheet_path) as fh:
        for _, elem in ET.iterparse(fh, events=("end",)):
            if elem.tag.endswith("}row"):
                row: dict[int, str] = {}
                for c in elem.findall("a:c", NS):
                    idx = col_to_idx(col_letters(c.attrib.get("r", "")))
                    row[idx] = cell_value(c, shared)
                yield row
                elem.clear()


class TableWriter:
    def __init__(self, out_dir: Path):
        self.out_dir = out_dir
        self.rows: dict[str, list[dict]] = defaultdict(list)

    def add(self, table: str, row: dict):
        self.rows[table].append(row)

    def flush(self):
        self.out_dir.mkdir(parents=True, exist_ok=True)
        manifest = []
        for table, rows in sorted(self.rows.items()):
            path = self.out_dir / f"{table}.csv"
            headers = sorted({k for r in rows for k in r.keys()})
            with path.open("w", newline="", encoding="utf-8") as f:
                w = csv.DictWriter(f, fieldnames=headers)
                w.writeheader()
                for r in rows:
                    w.writerow({k: _fmt_csv_value(r.get(k)) for k in headers})
            manifest.append({"table": table, "rows": len(rows), "path": str(path)})
        with (self.out_dir / "manifest.json").open("w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2)


def _fmt_csv_value(v):
    if v is None:
        return ""
    if isinstance(v, float):
        if v.is_integer():
            return str(int(v))
        return f"{v:.6f}".rstrip("0").rstrip(".")
    return str(v)


class KeyedDim:
    def __init__(self, table: str, id_col: str, field_names: list[str], writer: TableWriter):
        self.table = table
        self.id_col = id_col
        self.field_names = field_names
        self.writer = writer
        self.key_to_id: dict[tuple, int] = {}
        self.next_id = 1

    def get_id(self, values: tuple):
        if all(v is None for v in values):
            return None
        if values in self.key_to_id:
            return self.key_to_id[values]
        new_id = self.next_id
        self.next_id += 1
        self.key_to_id[values] = new_id
        row = {self.id_col: new_id}
        for k, v in zip(self.field_names, values):
            row[k] = v
        self.writer.add(self.table, row)
        return new_id


def pick(headers: list[str], *patterns: str) -> int | None:
    norms = [norm(h) for h in headers]
    for p in patterns:
        pn = norm(p)
        for i, n in enumerate(norms):
            if n == pn or pn in n:
                return i
    return None


def row_get(row: list[str], idx: int | None) -> str | None:
    if idx is None or idx >= len(row):
        return None
    return clean_text(row[idx])


def stable_hash(parts: list[object]) -> str:
    payload = "|".join("" if p is None else str(p) for p in parts)
    return hashlib.sha1(payload.encode("utf-8")).hexdigest()


def main():
    root = Path(__file__).resolve().parents[1]
    src = root / "Duke Data V4 (1).xlsx"
    out_dir = root / "output" / "3nf"
    writer = TableWriter(out_dir)

    dq_rows = []

    # Dimensions
    dim_company = KeyedDim("dim_company", "company_id", ["company_code"], writer)
    dim_vp = KeyedDim("dim_vp", "vp_id", ["vp_name"], writer)
    dim_state = KeyedDim("dim_state", "state_id", ["state_code"], writer)
    dim_reporting_period = KeyedDim(
        "dim_reporting_period",
        "reporting_period_id",
        ["bom_date", "report_period_start", "report_period_end"],
        writer,
    )
    dim_department = KeyedDim(
        "dim_department",
        "department_id",
        ["dept_rollup_level_1", "dept_rollup_level_2"],
        writer,
    )
    dim_product = KeyedDim(
        "dim_product",
        "product_id",
        [
            "product_bucket_group",
            "product_unit_economics",
            "non_qm",
            "grx",
            "is_hedged",
            "pnl_loan_type",
            "sdm_fulfilment",
            "custom_lo_type",
        ],
        writer,
    )
    dim_comp_bucket = KeyedDim(
        "dim_compensafe_bucket", "compensafe_bucket_id", ["compensafe_bucket_name"], writer
    )
    dim_adj_group = KeyedDim("dim_adj_type_group", "adj_type_group_id", ["adj_type_group_name"], writer)
    dim_allocation_bucket = KeyedDim(
        "dim_allocation_bucket", "allocation_bucket_id", ["allocation_bucket_name"], writer
    )
    dim_inclusion_reason = KeyedDim(
        "dim_inclusion_reason", "inclusion_reason_id", ["inclusion_reason_name"], writer
    )
    dim_insert_user = KeyedDim("dim_insert_user", "insert_user_id", ["inserted_by"], writer)
    dim_login_bundle = KeyedDim(
        "dim_login_bundle",
        "login_bundle_id",
        [
            "bm_login_name_1",
            "bm_login_name_2",
            "bm_login_name_3",
            "rm_login_name_1",
            "rm_login_name_2",
            "dm_login_name_1",
        ],
        writer,
    )
    dim_employee = KeyedDim(
        "dim_employee",
        "employee_id",
        ["employee_name", "employee_start_date", "termination_date", "employment_status"],
        writer,
    )
    dim_loan = KeyedDim(
        "dim_loan",
        "loan_id",
        [
            "loan_number",
            "borrower_last",
            "fund_date",
            "loan_amount",
            "fico",
            "forward_commitment",
            "builder_name",
            "purpose",
        ],
        writer,
    )
    # adj type depends on adj group id, so use separate helper keying on (name, group_id)
    dim_adj_type = KeyedDim("dim_adj_type", "adj_type_id", ["adj_type_name", "adj_type_group_id"], writer)

    # Aggregation stores for deduped facts
    loan_snapshot_acc: dict[tuple, dict] = {}
    loan_fin_acc: dict[tuple, dict] = {}
    workforce_acc: dict[tuple, dict] = {}
    bridge_keys = set()
    vp_emp_map_keys = set()
    fact_event_hashes = set()

    # Track conflicts for DQ
    loan_master_seen: dict[str, dict] = {}

    with zipfile.ZipFile(src) as zf:
        shared = parse_shared_strings(zf)
        path = first_sheet_path(zf)
        rows = iter_sheet_rows(zf, path, shared)
        header_map = next(rows)
        width = max(header_map.keys()) + 1
        headers = [""] * width
        for i, v in header_map.items():
            headers[i] = v

        c = {
            "bom": pick(headers, "BOM"),
            "fund_date": pick(headers, "FundDate"),
            "company_code": pick(headers, "CompanyCode"),
            "loan_number": pick(headers, "Loannumber"),
            "borrower_last": pick(headers, "BorrowerLast"),
            "vp": pick(headers, "VP"),
            "comp_event_date": pick(headers, "StartDate"),
            "termination_date": pick(headers, "TerminationDate"),
            "employment_status": pick(headers, "EmploymentStatus"),
            "cost_center_manager": pick(headers, "CostCenterManagers"),
            "region_manager": pick(headers, "RegionManager"),
            "division_manager": pick(headers, "DivisionManagerName"),
            "bm1": pick(headers, "BM LoginName 1"),
            "bm2": pick(headers, "BM LoginName 2"),
            "bm3": pick(headers, "BM LoginName 3"),
            "rm1": pick(headers, "RM LoginName 1"),
            "rm2": pick(headers, "RM LoginName 2"),
            "dm1": pick(headers, "DM LoginName 1"),
            "state": pick(headers, "SubjectPropertyState"),
            "fico": pick(headers, "FICO"),
            "product_bucket_group": pick(headers, "ProductBucketGroup"),
            "product_unit_econ": pick(headers, "ProductUnitEconomics"),
            "non_qm": pick(headers, "NonQm"),
            "grx": pick(headers, "GRX"),
            "is_hedged": pick(headers, "isHedged"),
            "pnl_loan_type": pick(headers, "P&L Loan Type"),
            "sdm_fulfilment": pick(headers, "SDM Fulfilment"),
            "custom_lo_type": pick(headers, "Custom LO Type"),
            "loan_amount": pick(headers, "LoanAmount"),
            "los_revenue_bps": pick(headers, "LOS Revenue BPS"),
            "los_revenue_amt": pick(headers, "LOS Revenue $"),
            "gl_fee_income_bps": pick(headers, "GL Fee Income BPS"),
            "gl_fee_income_amt": pick(headers, "GL Fee Income $"),
            "gl_gos_bps": pick(headers, "GL GOS BPS"),
            "gl_gos_amt": pick(headers, "GL GOS $"),
            "gl_oi_bps": pick(headers, "GL OI BPS"),
            "gl_oi_amt": pick(headers, "GL OI $"),
            "gl_exception_bps": pick(headers, "GL Exception BPS"),
            "gl_exception_amt": pick(headers, "GL Exception $"),
            "llr_bps": pick(headers, "LLR BPS"),
            "llr_amt": pick(headers, "LLR $"),
            "corp_alloc_bps": pick(headers, "Corporate Allocation BPS"),
            "corp_alloc_amt": pick(headers, "Corporate Allocation $"),
            "los_exception_bps": pick(headers, "LOS Exception BPS"),
            "los_exception_amt": pick(headers, "LOS Exception $"),
            "rent_bom_amt": pick(headers, "Rent $ (BOM)"),
            "payroll_reg_bom_amt": pick(headers, "Payroll Reg Earnings $ (BOM)"),
            "cra_traded_amt": pick(headers, "CRA Traded $"),
            "spec_traded_amt": pick(headers, "Spec Traded $"),
            "spec_bulk_adj_amt": pick(headers, "SPEC BulkAdj $"),
            "spec_paid_amt": pick(headers, "SPEC Paid $"),
            "cra_paid_amt": pick(headers, "CRA Paid $"),
            "net_spec_amt": pick(headers, "Net Spec $"),
            "cra_net_amt": pick(headers, "CRA Net $"),
            "active_sales_hc": pick(headers, "ActiveSalesHC"),
            "active_non_producing_sales_hc": pick(headers, "ActiveNonProducingSalesHC"),
            "funded_units_in_cost_center": pick(headers, "FundedUnitsInCostCenter"),
            "funded_volume_in_cost_center": pick(headers, "FundedVolumeInCostCenter"),
            "funded_units_by_vp": pick(headers, "FundedUnitsByVP"),
            "funded_volume_by_vp": pick(headers, "FundedVolumeByVP"),
            "employee_name": pick(headers, "EmployeeName"),
            "employee_name_start_date": pick(headers, "EmployeeNameStartDate"),
            "dept1": pick(headers, "Department Rollup Level 1"),
            "dept2": pick(headers, "Department Rollup Level 2"),
            "adj_type": pick(headers, "Adj Type"),
            "adj_type_group": pick(headers, "Adj Type Group"),
            "allocation_bucket": pick(headers, "AllocationBucketNew"),
            "compensafe_bucket": pick(headers, "CompensafeBucket"),
            "compensafe_bps": pick(headers, "Compensafe BPS"),
            "compensafe_amt": pick(headers, "Compensafe $"),
            "report_period_start": pick(headers, "ReportPeriodStart"),
            "report_period_end": pick(headers, "ReportPeriodEnd"),
            "corp_alloc_after_excl_amt": pick(headers, "Corporate Allocation $ (after exclusions)"),
            "inclusion_reason": pick(headers, "Inclusion Reason"),
            "forward_commitment": pick(headers, "Forward Commitment"),
            "builder_name": pick(headers, "Builder Name"),
            "inserted_by": pick(headers, "InsertedBy"),
            "insert_datetime": pick(headers, "InsertDatetime"),
            "purpose": pick(headers, "Purpose"),
        }

        for source_row_num, row_map in enumerate(rows, start=2):
            row = [""] * width
            for i, v in row_map.items():
                if i < width:
                    row[i] = v

            # Read / standardize source values
            company_code = row_get(row, c["company_code"])
            vp_name = row_get(row, c["vp"])
            state_code = row_get(row, c["state"])
            bom_date = excel_serial_to_date(row_get(row, c["bom"]))
            report_period_start = excel_serial_to_date(row_get(row, c["report_period_start"]))
            report_period_end = excel_serial_to_date(row_get(row, c["report_period_end"]))
            dept1 = row_get(row, c["dept1"])
            dept2 = row_get(row, c["dept2"])
            product_key = (
                row_get(row, c["product_bucket_group"]),
                row_get(row, c["product_unit_econ"]),
                row_get(row, c["non_qm"]),
                row_get(row, c["grx"]),
                row_get(row, c["is_hedged"]),
                row_get(row, c["pnl_loan_type"]),
                row_get(row, c["sdm_fulfilment"]),
                row_get(row, c["custom_lo_type"]),
            )
            employee_name = row_get(row, c["employee_name"])
            employee_start_date = excel_serial_to_date(row_get(row, c["employee_name_start_date"]))
            termination_date = excel_serial_to_date(row_get(row, c["termination_date"]))
            employment_status = row_get(row, c["employment_status"])

            loan_number = row_get(row, c["loan_number"])
            borrower_last = row_get(row, c["borrower_last"])
            fund_date = excel_serial_to_date(row_get(row, c["fund_date"]))
            loan_amount = parse_num(row_get(row, c["loan_amount"]))
            fico = parse_int(row_get(row, c["fico"]))
            forward_commitment = row_get(row, c["forward_commitment"])
            builder_name = row_get(row, c["builder_name"])
            purpose = row_get(row, c["purpose"])

            company_id = dim_company.get_id((company_code,))
            vp_id = dim_vp.get_id((vp_name,))
            state_id = dim_state.get_id((state_code,))
            reporting_period_id = dim_reporting_period.get_id((bom_date, report_period_start, report_period_end))
            department_id = dim_department.get_id((dept1, dept2))
            product_id = dim_product.get_id(product_key)
            employee_id = dim_employee.get_id(
                (employee_name, employee_start_date, termination_date, employment_status)
            )
            login_bundle_id = dim_login_bundle.get_id(
                (
                    row_get(row, c["bm1"]),
                    row_get(row, c["bm2"]),
                    row_get(row, c["bm3"]),
                    row_get(row, c["rm1"]),
                    row_get(row, c["rm2"]),
                    row_get(row, c["dm1"]),
                )
            )

            # Loan dimension with conflict checks (merge-by-loan_number)
            loan_id = None
            if loan_number is not None:
                loan_master = {
                    "borrower_last": borrower_last,
                    "fund_date": fund_date,
                    "loan_amount": loan_amount,
                    "fico": fico,
                    "forward_commitment": forward_commitment,
                    "builder_name": builder_name,
                    "purpose": purpose,
                }
                prior = loan_master_seen.get(loan_number)
                if prior is None:
                    loan_master_seen[loan_number] = dict(loan_master)
                else:
                    for k, v in loan_master.items():
                        if v is None:
                            continue
                        pv = prior.get(k)
                        if pv is None:
                            prior[k] = v
                        elif pv != v:
                            dq_rows.append(
                                {
                                    "dq_issue_id": len(dq_rows) + 1,
                                    "issue_type": "inconsistent_loan_master_value",
                                    "source_table_name": "Duke Data V4 (1).xlsx",
                                    "source_business_key": loan_number,
                                    "severity": "warning",
                                    "issue_detail": f"{k}: {pv} vs {v} (source_row={source_row_num})",
                                    "detected_at": dt.datetime.now().replace(microsecond=0).isoformat(sep=" "),
                                }
                            )
                merged = loan_master_seen[loan_number]
                loan_id = dim_loan.get_id(
                    (
                        loan_number,
                        merged.get("borrower_last"),
                        merged.get("fund_date"),
                        merged.get("loan_amount"),
                        merged.get("fico"),
                        merged.get("forward_commitment"),
                        merged.get("builder_name"),
                        merged.get("purpose"),
                    )
                )

            # Dict dimensions for event coding
            comp_bucket_id = dim_comp_bucket.get_id((row_get(row, c["compensafe_bucket"]),))
            adj_group_id = dim_adj_group.get_id((row_get(row, c["adj_type_group"]),))
            adj_type_id = dim_adj_type.get_id((row_get(row, c["adj_type"]), adj_group_id))
            allocation_bucket_id = dim_allocation_bucket.get_id((row_get(row, c["allocation_bucket"]),))
            inclusion_reason_id = dim_inclusion_reason.get_id((row_get(row, c["inclusion_reason"]),))
            insert_user_id = dim_insert_user.get_id((row_get(row, c["inserted_by"]),))

            # bridge_loan_org_attribution (deduped)
            if loan_id is not None:
                bridge_key = (
                    loan_id,
                    reporting_period_id,
                    company_id,
                    vp_id,
                    employee_id,
                    department_id,
                    state_id,
                    product_id,
                )
                if bridge_key not in bridge_keys:
                    bridge_keys.add(bridge_key)
                    writer.add(
                        "bridge_loan_org_attribution",
                        {
                            "loan_org_attr_id": len(bridge_keys),
                            "loan_id": loan_id,
                            "reporting_period_id": reporting_period_id,
                            "company_id": company_id,
                            "vp_id": vp_id,
                            "employee_id": employee_id,
                            "department_id": department_id,
                            "state_id": state_id,
                            "product_id": product_id,
                            "login_bundle_id": login_bundle_id,
                            "cost_center_manager_name": row_get(row, c["cost_center_manager"]),
                            "region_manager_name": row_get(row, c["region_manager"]),
                            "division_manager_name": row_get(row, c["division_manager"]),
                            "attribution_source": "Duke Data V4",
                        },
                    )

            # bridge_vp_employee_map (heuristic exact-name match)
            if vp_id is not None and employee_id is not None and vp_name == employee_name:
                key = (vp_id, employee_id, "exact_name_match")
                if key not in vp_emp_map_keys:
                    vp_emp_map_keys.add(key)
                    writer.add(
                        "bridge_vp_employee_map",
                        {
                            "vp_employee_map_id": len(vp_emp_map_keys),
                            "vp_id": vp_id,
                            "employee_id": employee_id,
                            "mapping_method": "exact_name_match",
                            "is_active": True,
                        },
                    )

            # fact_compensafe_event (keep every source row)
            if loan_id is not None:
                event_hash = stable_hash(
                    [
                        loan_number,
                        excel_serial_to_date(row_get(row, c["comp_event_date"])),
                        row_get(row, c["adj_type_group"]),
                        row_get(row, c["adj_type"]),
                        row_get(row, c["compensafe_bucket"]),
                        row_get(row, c["compensafe_amt"]),
                        employee_name,
                        row_get(row, c["insert_datetime"]),
                        source_row_num,
                    ]
                )
                if event_hash in fact_event_hashes:
                    dq_rows.append(
                        {
                            "dq_issue_id": len(dq_rows) + 1,
                            "issue_type": "duplicate_source_row_hash",
                            "source_table_name": "Duke Data V4 (1).xlsx",
                            "source_business_key": loan_number,
                            "severity": "warning",
                            "issue_detail": f"duplicate event hash at source_row={source_row_num}",
                            "detected_at": dt.datetime.now().replace(microsecond=0).isoformat(sep=" "),
                        }
                    )
                else:
                    fact_event_hashes.add(event_hash)
                writer.add(
                    "fact_compensafe_event",
                    {
                        "compensafe_event_id": source_row_num - 1,
                        "loan_id": loan_id,
                        "reporting_period_id": reporting_period_id,
                        "company_id": company_id,
                        "vp_id": vp_id,
                        "employee_id": employee_id,
                        "department_id": department_id,
                        "state_id": state_id,
                        "product_id": product_id,
                        "compensafe_event_date": excel_serial_to_date(row_get(row, c["comp_event_date"])),
                        "compensafe_bucket_id": comp_bucket_id,
                        "adj_type_group_id": adj_group_id,
                        "adj_type_id": adj_type_id,
                        "allocation_bucket_id": allocation_bucket_id,
                        "inclusion_reason_id": inclusion_reason_id,
                        "insert_user_id": insert_user_id,
                        "compensafe_bps": parse_num(row_get(row, c["compensafe_bps"])),
                        "compensafe_amt": parse_num(row_get(row, c["compensafe_amt"])),
                        "rent_bom_amt": parse_num(row_get(row, c["rent_bom_amt"])),
                        "payroll_reg_earnings_bom_amt": parse_num(row_get(row, c["payroll_reg_bom_amt"])),
                        "cra_traded_amt": parse_num(row_get(row, c["cra_traded_amt"])),
                        "spec_traded_amt": parse_num(row_get(row, c["spec_traded_amt"])),
                        "spec_bulk_adj_amt": parse_num(row_get(row, c["spec_bulk_adj_amt"])),
                        "spec_paid_amt": parse_num(row_get(row, c["spec_paid_amt"])),
                        "cra_paid_amt": parse_num(row_get(row, c["cra_paid_amt"])),
                        "net_spec_amt": parse_num(row_get(row, c["net_spec_amt"])),
                        "cra_net_amt": parse_num(row_get(row, c["cra_net_amt"])),
                        "inserted_at": excel_serial_to_timestamp(row_get(row, c["insert_datetime"])),
                        "source_row_hash": event_hash,
                    },
                )

            # Deduped fact_loan_snapshot (loan + period)
            if loan_id is not None:
                snap_key = (loan_id, reporting_period_id)
                snap_row = {
                    "loan_snapshot_id": None,  # assigned later
                    "loan_id": loan_id,
                    "reporting_period_id": reporting_period_id,
                    "company_id": company_id,
                    "state_id": state_id,
                    "product_id": product_id,
                    "funded_units_by_vp": parse_num(row_get(row, c["funded_units_by_vp"])),
                    "funded_volume_by_vp": parse_num(row_get(row, c["funded_volume_by_vp"])),
                    "funded_units_in_cost_center": parse_num(row_get(row, c["funded_units_in_cost_center"])),
                    "funded_volume_in_cost_center": parse_num(row_get(row, c["funded_volume_in_cost_center"])),
                    "forward_commitment": forward_commitment,
                    "source_insert_datetime": excel_serial_to_timestamp(row_get(row, c["insert_datetime"])),
                }
                merge_record(loan_snapshot_acc, snap_key, snap_row, "fact_loan_snapshot", dq_rows, source_row_num)

                fin_key = (loan_id, reporting_period_id)
                fin_row = {
                    "loan_fin_component_id": None,  # assigned later
                    "loan_id": loan_id,
                    "reporting_period_id": reporting_period_id,
                    "los_revenue_bps": parse_num(row_get(row, c["los_revenue_bps"])),
                    "los_revenue_amt": parse_num(row_get(row, c["los_revenue_amt"])),
                    "gl_fee_income_bps": parse_num(row_get(row, c["gl_fee_income_bps"])),
                    "gl_fee_income_amt": parse_num(row_get(row, c["gl_fee_income_amt"])),
                    "gl_gos_bps": parse_num(row_get(row, c["gl_gos_bps"])),
                    "gl_gos_amt": parse_num(row_get(row, c["gl_gos_amt"])),
                    "gl_oi_bps": parse_num(row_get(row, c["gl_oi_bps"])),
                    "gl_oi_amt": parse_num(row_get(row, c["gl_oi_amt"])),
                    "gl_exception_bps": parse_num(row_get(row, c["gl_exception_bps"])),
                    "gl_exception_amt": parse_num(row_get(row, c["gl_exception_amt"])),
                    "llr_bps": parse_num(row_get(row, c["llr_bps"])),
                    "llr_amt": parse_num(row_get(row, c["llr_amt"])),
                    "corporate_allocation_bps": parse_num(row_get(row, c["corp_alloc_bps"])),
                    "corporate_allocation_amt": parse_num(row_get(row, c["corp_alloc_amt"])),
                    "corporate_allocation_after_exclusions_amt": parse_num(
                        row_get(row, c["corp_alloc_after_excl_amt"])
                    ),
                    "los_exception_bps": parse_num(row_get(row, c["los_exception_bps"])),
                    "los_exception_amt": parse_num(row_get(row, c["los_exception_amt"])),
                    "source_insert_datetime": excel_serial_to_timestamp(row_get(row, c["insert_datetime"])),
                }
                merge_record(
                    loan_fin_acc, fin_key, fin_row, "fact_loan_financial_components", dq_rows, source_row_num
                )

            # Deduped workforce snapshot (vp + period + dept + company)
            wf_key = (reporting_period_id, company_id, vp_id, department_id)
            wf_row = {
                "workforce_snapshot_id": None,  # assigned later
                "reporting_period_id": reporting_period_id,
                "company_id": company_id,
                "vp_id": vp_id,
                "department_id": department_id,
                "active_sales_hc": parse_num(row_get(row, c["active_sales_hc"])),
                "active_non_producing_sales_hc": parse_num(row_get(row, c["active_non_producing_sales_hc"])),
                "funded_units_in_cost_center": parse_num(row_get(row, c["funded_units_in_cost_center"])),
                "funded_volume_in_cost_center": parse_num(row_get(row, c["funded_volume_in_cost_center"])),
                "funded_units_by_vp": parse_num(row_get(row, c["funded_units_by_vp"])),
                "funded_volume_by_vp": parse_num(row_get(row, c["funded_volume_by_vp"])),
                "rent_bom_amt": parse_num(row_get(row, c["rent_bom_amt"])),
                "payroll_reg_earnings_bom_amt": parse_num(row_get(row, c["payroll_reg_bom_amt"])),
            }
            merge_record(
                workforce_acc, wf_key, wf_row, "fact_workforce_period_snapshot", dq_rows, source_row_num
            )

    # Flush deduped accumulators to tables with assigned IDs
    for i, rec in enumerate(loan_snapshot_acc.values(), start=1):
        rec["loan_snapshot_id"] = i
        writer.add("fact_loan_snapshot", rec)
    for i, rec in enumerate(loan_fin_acc.values(), start=1):
        rec["loan_fin_component_id"] = i
        writer.add("fact_loan_financial_components", rec)
    for i, rec in enumerate(workforce_acc.values(), start=1):
        rec["workforce_snapshot_id"] = i
        writer.add("fact_workforce_period_snapshot", rec)
    for row in dq_rows:
        writer.add("etl_data_quality_issue", row)

    writer.flush()
    print(f"Wrote {len(writer.rows)} tables to {out_dir}")
    for table, rows in sorted(writer.rows.items()):
        print(f"{table}: {len(rows)} rows")


def merge_record(
    store: dict[tuple, dict],
    key: tuple,
    new_row: dict,
    table_name: str,
    dq_rows: list[dict],
    source_row_num: int,
):
    if key not in store:
        store[key] = dict(new_row)
        return
    existing = store[key]
    for k, v in new_row.items():
        if k.endswith("_id") and k in ("loan_snapshot_id", "loan_fin_component_id", "workforce_snapshot_id"):
            continue
        if v is None:
            continue
        ev = existing.get(k)
        if ev is None:
            existing[k] = v
        elif ev != v:
            # keep existing, log conflict
            dq_rows.append(
                {
                    "dq_issue_id": len(dq_rows) + 1,
                    "issue_type": "conflicting_deduped_fact_value",
                    "source_table_name": "Duke Data V4 (1).xlsx",
                    "source_business_key": f"{table_name}|{key}",
                    "severity": "warning",
                    "issue_detail": f"{k}: {ev} vs {v} (source_row={source_row_num})",
                    "detected_at": dt.datetime.now().replace(microsecond=0).isoformat(sep=" "),
                }
            )


if __name__ == "__main__":
    main()
