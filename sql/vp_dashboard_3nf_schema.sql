-- VP Dashboard 3NF schema (PostgreSQL-friendly)
-- Source: Duke Data V4 (1).xlsx

create schema if not exists vp_dash;

-- =========================
-- 1) Reference / Master Data
-- =========================

create table if not exists vp_dash.dim_company (
  company_id bigserial primary key,
  company_code text not null unique
);

create table if not exists vp_dash.dim_vp (
  vp_id bigserial primary key,
  vp_name text not null unique
);

create table if not exists vp_dash.dim_state (
  state_id bigserial primary key,
  state_code text not null unique
);

create table if not exists vp_dash.dim_reporting_period (
  reporting_period_id bigserial primary key,
  bom_date date,
  report_period_start date,
  report_period_end date,
  unique (bom_date, report_period_start, report_period_end)
);

create table if not exists vp_dash.dim_department (
  department_id bigserial primary key,
  dept_rollup_level_1 text,
  dept_rollup_level_2 text,
  unique (dept_rollup_level_1, dept_rollup_level_2)
);

create table if not exists vp_dash.dim_product (
  product_id bigserial primary key,
  product_bucket_group text,
  product_unit_economics text,
  non_qm text,
  grx text,
  is_hedged text,
  pnl_loan_type text,
  sdm_fulfilment text,
  custom_lo_type text,
  unique (
    product_bucket_group,
    product_unit_economics,
    non_qm,
    grx,
    is_hedged,
    pnl_loan_type,
    sdm_fulfilment,
    custom_lo_type
  )
);

create table if not exists vp_dash.dim_compensafe_bucket (
  compensafe_bucket_id bigserial primary key,
  compensafe_bucket_name text not null unique
);

create table if not exists vp_dash.dim_adj_type_group (
  adj_type_group_id bigserial primary key,
  adj_type_group_name text not null unique
);

create table if not exists vp_dash.dim_adj_type (
  adj_type_id bigserial primary key,
  adj_type_name text not null,
  adj_type_group_id bigint references vp_dash.dim_adj_type_group(adj_type_group_id),
  unique (adj_type_name, adj_type_group_id)
);

create table if not exists vp_dash.dim_allocation_bucket (
  allocation_bucket_id bigserial primary key,
  allocation_bucket_name text not null unique
);

create table if not exists vp_dash.dim_inclusion_reason (
  inclusion_reason_id bigserial primary key,
  inclusion_reason_name text not null unique
);

create table if not exists vp_dash.dim_insert_user (
  insert_user_id bigserial primary key,
  inserted_by text not null unique
);

create table if not exists vp_dash.dim_login_bundle (
  login_bundle_id bigserial primary key,
  bm_login_name_1 text,
  bm_login_name_2 text,
  bm_login_name_3 text,
  rm_login_name_1 text,
  rm_login_name_2 text,
  dm_login_name_1 text,
  unique (
    bm_login_name_1,
    bm_login_name_2,
    bm_login_name_3,
    rm_login_name_1,
    rm_login_name_2,
    dm_login_name_1
  )
);

create table if not exists vp_dash.dim_employee (
  employee_id bigserial primary key,
  employee_name text not null,
  employee_start_date date,
  termination_date date,
  employment_status text,
  unique (employee_name, employee_start_date)
);

create table if not exists vp_dash.dim_loan (
  loan_id bigserial primary key,
  loan_number text not null unique,
  borrower_last text,
  fund_date date,
  loan_amount numeric(18,2),
  fico integer,
  forward_commitment text,
  builder_name text,
  purpose text
);

-- =========================
-- 2) Relationship / Attribution
-- =========================

create table if not exists vp_dash.bridge_loan_org_attribution (
  loan_org_attr_id bigserial primary key,
  loan_id bigint not null references vp_dash.dim_loan(loan_id),
  reporting_period_id bigint not null references vp_dash.dim_reporting_period(reporting_period_id),
  company_id bigint references vp_dash.dim_company(company_id),
  vp_id bigint references vp_dash.dim_vp(vp_id),
  employee_id bigint references vp_dash.dim_employee(employee_id),
  department_id bigint references vp_dash.dim_department(department_id),
  state_id bigint references vp_dash.dim_state(state_id),
  product_id bigint references vp_dash.dim_product(product_id),
  login_bundle_id bigint references vp_dash.dim_login_bundle(login_bundle_id),
  cost_center_manager_name text,
  region_manager_name text,
  division_manager_name text,
  attribution_source text default 'Duke Data V4',
  -- uniqueness with nullable foreign keys is enforced by a unique index below
);

create table if not exists vp_dash.bridge_vp_employee_map (
  vp_employee_map_id bigserial primary key,
  vp_id bigint not null references vp_dash.dim_vp(vp_id),
  employee_id bigint not null references vp_dash.dim_employee(employee_id),
  mapping_method text not null, -- e.g. exact_name_match
  is_active boolean default true,
  unique (vp_id, employee_id, mapping_method)
);

-- =========================
-- 3) Facts
-- =========================

create table if not exists vp_dash.fact_loan_snapshot (
  loan_snapshot_id bigserial primary key,
  loan_id bigint not null references vp_dash.dim_loan(loan_id),
  reporting_period_id bigint not null references vp_dash.dim_reporting_period(reporting_period_id),
  company_id bigint references vp_dash.dim_company(company_id),
  state_id bigint references vp_dash.dim_state(state_id),
  product_id bigint references vp_dash.dim_product(product_id),
  funded_units_by_vp numeric(18,4),
  funded_volume_by_vp numeric(18,2),
  funded_units_in_cost_center numeric(18,4),
  funded_volume_in_cost_center numeric(18,2),
  forward_commitment text,
  source_insert_datetime timestamp,
  unique (loan_id, reporting_period_id)
);

create table if not exists vp_dash.fact_loan_financial_components (
  loan_fin_component_id bigserial primary key,
  loan_id bigint not null references vp_dash.dim_loan(loan_id),
  reporting_period_id bigint not null references vp_dash.dim_reporting_period(reporting_period_id),
  los_revenue_bps numeric(18,6),
  los_revenue_amt numeric(18,2),
  gl_fee_income_bps numeric(18,6),
  gl_fee_income_amt numeric(18,2),
  gl_gos_bps numeric(18,6),
  gl_gos_amt numeric(18,2),
  gl_oi_bps numeric(18,6),
  gl_oi_amt numeric(18,2),
  gl_exception_bps numeric(18,6),
  gl_exception_amt numeric(18,2),
  llr_bps numeric(18,6),
  llr_amt numeric(18,2),
  corporate_allocation_bps numeric(18,6),
  corporate_allocation_amt numeric(18,2),
  corporate_allocation_after_exclusions_amt numeric(18,2),
  los_exception_bps numeric(18,6),
  los_exception_amt numeric(18,2),
  source_insert_datetime timestamp,
  unique (loan_id, reporting_period_id)
);

create table if not exists vp_dash.fact_compensafe_event (
  compensafe_event_id bigserial primary key,
  loan_id bigint not null references vp_dash.dim_loan(loan_id),
  reporting_period_id bigint references vp_dash.dim_reporting_period(reporting_period_id),
  company_id bigint references vp_dash.dim_company(company_id),
  vp_id bigint references vp_dash.dim_vp(vp_id),
  employee_id bigint references vp_dash.dim_employee(employee_id),
  department_id bigint references vp_dash.dim_department(department_id),
  state_id bigint references vp_dash.dim_state(state_id),
  product_id bigint references vp_dash.dim_product(product_id),
  compensafe_event_date date, -- source column StartDate
  compensafe_bucket_id bigint references vp_dash.dim_compensafe_bucket(compensafe_bucket_id),
  adj_type_group_id bigint references vp_dash.dim_adj_type_group(adj_type_group_id),
  adj_type_id bigint references vp_dash.dim_adj_type(adj_type_id),
  allocation_bucket_id bigint references vp_dash.dim_allocation_bucket(allocation_bucket_id),
  inclusion_reason_id bigint references vp_dash.dim_inclusion_reason(inclusion_reason_id),
  insert_user_id bigint references vp_dash.dim_insert_user(insert_user_id),
  compensafe_bps numeric(18,6),
  compensafe_amt numeric(18,2),
  rent_bom_amt numeric(18,2),
  payroll_reg_earnings_bom_amt numeric(18,2),
  cra_traded_amt numeric(18,2),
  spec_traded_amt numeric(18,2),
  spec_bulk_adj_amt numeric(18,2),
  spec_paid_amt numeric(18,2),
  cra_paid_amt numeric(18,2),
  net_spec_amt numeric(18,2),
  cra_net_amt numeric(18,2),
  inserted_at timestamp,
  source_row_hash text,
  unique (source_row_hash)
);

create table if not exists vp_dash.fact_workforce_period_snapshot (
  workforce_snapshot_id bigserial primary key,
  reporting_period_id bigint not null references vp_dash.dim_reporting_period(reporting_period_id),
  company_id bigint references vp_dash.dim_company(company_id),
  vp_id bigint references vp_dash.dim_vp(vp_id),
  department_id bigint references vp_dash.dim_department(department_id),
  active_sales_hc numeric(18,4),
  active_non_producing_sales_hc numeric(18,4),
  funded_units_in_cost_center numeric(18,4),
  funded_volume_in_cost_center numeric(18,2),
  funded_units_by_vp numeric(18,4),
  funded_volume_by_vp numeric(18,2),
  rent_bom_amt numeric(18,2),
  payroll_reg_earnings_bom_amt numeric(18,2)
);

-- =========================
-- 4) Data Quality / Audit
-- =========================

create table if not exists vp_dash.etl_data_quality_issue (
  dq_issue_id bigserial primary key,
  issue_type text not null,              -- e.g. inconsistent_loan_amount
  source_table_name text not null default 'Duke Data V4 (1).xlsx',
  source_business_key text,              -- e.g. loan_number or loan_number|period
  severity text not null default 'warning',
  issue_detail text,
  detected_at timestamp not null default now()
);

create index if not exists idx_fact_comp_event_loan on vp_dash.fact_compensafe_event (loan_id);
create index if not exists idx_fact_comp_event_date on vp_dash.fact_compensafe_event (compensafe_event_date);
create index if not exists idx_fact_comp_event_vp on vp_dash.fact_compensafe_event (vp_id);
create index if not exists idx_fact_loan_fin_loan_period on vp_dash.fact_loan_financial_components (loan_id, reporting_period_id);
create index if not exists idx_workforce_period_vp on vp_dash.fact_workforce_period_snapshot (reporting_period_id, vp_id);
create unique index if not exists uq_bridge_loan_org_attr_business
  on vp_dash.bridge_loan_org_attribution (
    loan_id,
    reporting_period_id,
    coalesce(vp_id, -1),
    coalesce(employee_id, -1),
    coalesce(department_id, -1),
    coalesce(state_id, -1),
    coalesce(product_id, -1)
  );
create unique index if not exists uq_workforce_period_snapshot_business
  on vp_dash.fact_workforce_period_snapshot (
    reporting_period_id,
    coalesce(company_id, -1),
    coalesce(vp_id, -1),
    coalesce(department_id, -1)
  );
