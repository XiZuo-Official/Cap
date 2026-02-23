# output/3nf 数据字典（中文）
本文档详细解释 `output/3nf` 文件夹中的每个表及其字段含义。
说明：
- 这些表是基于 `Duke Data V4 (1).xlsx` 按三范式拆分生成。
- 多数字段名称沿用英文，是为了便于和 Tableau / SQL / 源表字段对齐。
- 凡是 `*_id` 字段通常表示外键（或主键），需结合对应维表使用。
- `fact_compensafe_event` 为明细层，`fact_loan_snapshot` 和 `fact_loan_financial_components` 为去重后的贷款+周期层。

### bridge_loan_org_attribution：贷款-组织归属桥表。用于记录某笔贷款在某个报表周期内归属于哪个 VP、员工、部门、州、产品等组织上下文。它解释了为什么同一贷款在源数据中会出现多行。

- **attribution_source**：归属来源说明。当前固定写为 `Duke Data V4`，表示此归属记录来源于该数据集。

- **company_id**：公司维表主键，关联 `dim_company.company_id`。

- **cost_center_manager_name**：成本中心经理名称，来自 `CostCenterManagers`。

- **department_id**：部门维表主键，关联 `dim_department.department_id`。

- **division_manager_name**：Division 经理名称，来自 `DivisionManagerName`。

- **employee_id**：员工维表主键，关联 `dim_employee.employee_id`。

- **loan_id**：贷款维表主键，关联 `dim_loan.loan_id`。

- **loan_org_attr_id**：贷款-组织归属桥表主键。

- **login_bundle_id**：登录名组合维表主键，关联 `dim_login_bundle`。

- **product_id**：产品维表主键，关联 `dim_product.product_id`。

- **region_manager_name**：区域经理名称，来自 `RegionManager`。

- **reporting_period_id**：报表周期维表主键，关联 `dim_reporting_period.reporting_period_id`。

- **state_id**：州维表主键，关联 `dim_state.state_id`。

- **vp_id**：VP 维表主键，关联 `dim_vp.vp_id`。

### bridge_vp_employee_map：VP 与员工实体映射桥表。用于把 `dim_vp` 中的 VP 名称与 `dim_employee` 中的员工记录建立关联（当前主要使用“姓名完全一致”的启发式映射）。

- **employee_id**：员工维表主键，关联 `dim_employee.employee_id`。

- **is_active**：映射是否有效（布尔值）。当前脚本默认置为 `True`。

- **mapping_method**：映射方法。当前主要为 `exact_name_match`（VP 名称与员工姓名完全一致）。

- **vp_employee_map_id**：VP-员工映射桥表主键。

- **vp_id**：VP 维表主键，关联 `dim_vp.vp_id`。

### dim_adj_type：调整类型维表。存放源数据 `Adj Type` 的标准化字典，并可关联到调整类型组。

- **adj_type_group_id**：调整类型组维表主键，关联 `dim_adj_type_group`。

- **adj_type_id**：调整类型维表主键，关联 `dim_adj_type`。

- **adj_type_name**：调整类型名称，来自 `Adj Type`。

### dim_adj_type_group：调整类型组维表。存放源数据 `Adj Type Group` 的字典值。

- **adj_type_group_id**：调整类型组维表主键，关联 `dim_adj_type_group`。

- **adj_type_group_name**：调整类型组名称，来自 `Adj Type Group`。

### dim_allocation_bucket：分配桶维表。存放 `AllocationBucketNew` 的字典值。

- **allocation_bucket_id**：分配桶维表主键，关联 `dim_allocation_bucket`。

- **allocation_bucket_name**：分配桶名称，来自 `AllocationBucketNew`。

### dim_company：公司维表。存放 `CompanyCode` 的字典值。

- **company_code**：公司代码，来自源数据 `CompanyCode`。

- **company_id**：公司维表主键，关联 `dim_company.company_id`。

### dim_compensafe_bucket：Compensafe 桶维表。存放 `CompensafeBucket`（如 `Loan #` / `No Loan #`）的字典值。

- **compensafe_bucket_id**：Compensafe 桶维表主键，关联 `dim_compensafe_bucket`。

- **compensafe_bucket_name**：Compensafe 桶名称，来自 `CompensafeBucket`。

### dim_department：部门维表。存放部门层级字段（Rollup Level 1/2）的组合。

- **department_id**：部门维表主键，关联 `dim_department.department_id`。

- **dept_rollup_level_1**：部门汇总层级 1，来自 `Department Rollup Level 1`。

- **dept_rollup_level_2**：部门汇总层级 2，来自 `Department Rollup Level 2`。

### dim_employee：员工维表。存放员工姓名、入职日期、离职日期、在职状态等主数据。注意这里的入职日期来自 `EmployeeNameStartDate`，不是事件 `StartDate`。

- **employee_id**：员工维表主键，关联 `dim_employee.employee_id`。

- **employee_name**：员工姓名，来自 `EmployeeName`。

- **employee_start_date**：员工入职日期，来自 `EmployeeNameStartDate`（不是事件 `StartDate`）。

- **employment_status**：员工在职状态，来自 `EmploymentStatus`。

- **termination_date**：员工离职日期，来自 `TerminationDate`。

### dim_inclusion_reason：纳入原因维表。存放 `Inclusion Reason` 的字典值。

- **inclusion_reason_id**：纳入原因维表主键，关联 `dim_inclusion_reason`。

- **inclusion_reason_name**：纳入原因名称，来自 `Inclusion Reason`。

### dim_insert_user：数据写入用户维表。存放源数据 `InsertedBy` 的字典值。

- **insert_user_id**：插入用户维表主键，关联 `dim_insert_user`。

- **inserted_by**：源数据写入人，来自 `InsertedBy`。

### dim_loan：贷款主数据维表（贷款主表）。每个 `loan_number` 仅保留一行，用于避免在事件明细层重复统计贷款数量和贷款金额。

- **borrower_last**：借款人姓氏，来自 `BorrowerLast`。

- **builder_name**：Builder 名称，来自 `Builder Name`。

- **fico**：FICO 信用评分，来自 `FICO`。

- **forward_commitment**：Forward Commitment 标记/描述，来自 `Forward Commitment`。

- **fund_date**：贷款放款日期，来自 `FundDate`。

- **loan_amount**：贷款金额，来自 `LoanAmount`。在 3NF 中放在 `dim_loan`，避免在事件明细里重复累计。

- **loan_id**：贷款维表主键。该表以 `loan_number` 为自然键去重后生成。

- **loan_number**：贷款号（贷款自然键），来自 `Loannumber`。

- **purpose**：贷款用途，来自 `Purpose`。

### dim_login_bundle：登录账号组合维表。存放 BM/RM/DM 登录名组合，减少桥表重复文本。

- **bm_login_name_1**：BM 登录名 1，来自 `BM LoginName 1`。

- **bm_login_name_2**：BM 登录名 2，来自 `BM LoginName 2`。

- **bm_login_name_3**：BM 登录名 3，来自 `BM LoginName 3`。

- **dm_login_name_1**：DM 登录名 1，来自 `DM LoginName 1`。

- **login_bundle_id**：登录名组合维表主键，关联 `dim_login_bundle`。

- **rm_login_name_1**：RM 登录名 1，来自 `RM LoginName 1`。

- **rm_login_name_2**：RM 登录名 2，来自 `RM LoginName 2`。

### dim_product：产品特征维表。把产品相关属性（产品组、经济性、是否对冲等）组合成一个产品维度。

- **custom_lo_type**：自定义 Loan Officer 类型，来自 `Custom LO Type`。

- **grx**：GRX 标记，来自 `GRX`。

- **is_hedged**：是否对冲，来自 `isHedged`。

- **non_qm**：是否/类型为 Non-QM，来自 `NonQm`。

- **pnl_loan_type**：P&L 贷款类型，来自 `P&L Loan Type`。

- **product_bucket_group**：产品桶分组，来自 `ProductBucketGroup`。

- **product_id**：产品维表主键，关联 `dim_product.product_id`。

- **product_unit_economics**：产品单位经济性分类，来自 `ProductUnitEconomics`。

- **sdm_fulfilment**：SDM fulfilment 分类，来自 `SDM Fulfilment`。

### dim_reporting_period：报表周期维表。存放 BOM（期初月份）以及报表起止日期。本批数据中仅识别到一个 BOM 周期。

（注释：当前源数据在拆分时仅识别到一个 `BOM` 周期，因此本表只有 1 行，这不代表模型不支持多期。）

- **bom_date**：BOM（Beginning of Month）日期。当前数据用于标识月度快照周期。

- **report_period_end**：报表周期结束日期。源数据中若为空/0，则拆分时保留为空。

- **report_period_start**：报表周期开始日期。源数据中若为空/0，则拆分时保留为空。

- **reporting_period_id**：报表周期维表主键。本批拆分结果中仅有 1 个周期记录。

### dim_state：州维表。存放房产所在州代码（`SubjectPropertyState`）。

- **state_code**：州代码，来自 `SubjectPropertyState`。

- **state_id**：州维表主键，关联 `dim_state.state_id`。

### dim_vp：VP 维表。存放 VP 名称主数据。

- **vp_id**：VP 维表主键，关联 `dim_vp.vp_id`。

- **vp_name**：VP 名称，来自源数据 `VP`。

### etl_data_quality_issue：ETL 数据质量问题表。记录拆分和去重过程中发现的字段冲突、重复哈希等异常，便于审计与回溯。

（注释：该表不是业务事实表，而是 ETL 审计表。建议保留，用于核对去重与字段冲突。）

- **detected_at**：问题检测时间戳。

- **dq_issue_id**：数据质量问题表主键。

- **issue_detail**：问题详细说明，通常包含冲突字段、冲突值和源行号。

- **issue_type**：问题类型（如贷款主数据冲突、去重后字段冲突、重复事件哈希等）。

- **severity**：问题严重级别（如 warning）。

- **source_business_key**：问题对应的业务键（如 `loan_number` 或 `table|dedupe_key`）。用于定位异常记录。

- **source_table_name**：问题来源表/来源数据集名称。当前主要记录为 `Duke Data V4 (1).xlsx`。

### fact_compensafe_event：Compensafe/调整事件事实表（明细层）。基本保留源表每一行事件记录，是成本/调整项分析的核心事实表。

（注释：该表接近源表行数。任何涉及贷款数量/贷款金额的统计，不应直接在此表上做 `count`/`sum(loan_amount)`。）

- **adj_type_group_id**：调整类型组维表主键，关联 `dim_adj_type_group`。

- **adj_type_id**：调整类型维表主键，关联 `dim_adj_type`。

- **allocation_bucket_id**：分配桶维表主键，关联 `dim_allocation_bucket`。

- **company_id**：公司维表主键，关联 `dim_company.company_id`。

- **compensafe_amt**：Compensafe 金额，来自 `Compensafe $`。

- **compensafe_bps**：Compensafe 的 BPS 值，来自 `Compensafe BPS`。

- **compensafe_bucket_id**：Compensafe 桶维表主键，关联 `dim_compensafe_bucket`。

- **compensafe_event_date**：Compensafe/调整事件发生日期，来自源列 `StartDate`。注意这不是员工入职日期。

- **compensafe_event_id**：Compensafe 事件事实表主键（按源行生成）。

- **cra_net_amt**：CRA Net 金额，来自 `CRA Net $`。

- **cra_paid_amt**：CRA Paid 金额，来自 `CRA Paid $`。

- **cra_traded_amt**：CRA Traded 金额，来自 `CRA Traded $`。

- **department_id**：部门维表主键，关联 `dim_department.department_id`。

- **employee_id**：员工维表主键，关联 `dim_employee.employee_id`。

- **inclusion_reason_id**：纳入原因维表主键，关联 `dim_inclusion_reason`。

- **insert_user_id**：插入用户维表主键，关联 `dim_insert_user`。

- **inserted_at**：源数据写入时间（时间戳），来自 `InsertDatetime`。

- **loan_id**：关联到 `dim_loan` 的贷款主键。事件表保留每条源行，因此同一 `loan_id` 会重复出现。

- **net_spec_amt**：Net Spec 金额，来自 `Net Spec $`。

- **payroll_reg_earnings_bom_amt**：BOM 口径常规工资金额，来自 `Payroll Reg Earnings $ (BOM)`。明细层可能重复。

- **product_id**：产品维表主键，关联 `dim_product.product_id`。

- **rent_bom_amt**：BOM 口径房租金额，来自 `Rent $ (BOM)`。该值在明细行可能重复，汇总时需使用快照表或先去重。

- **reporting_period_id**：报表周期维表主键，关联 `dim_reporting_period.reporting_period_id`。

- **source_row_hash**：源行业务哈希（用于识别重复事件行）。由贷款号、事件日期、调整类型、金额、员工等字段组合生成。

- **spec_bulk_adj_amt**：SPEC Bulk Adjustment 金额，来自 `SPEC BulkAdj $`。

- **spec_paid_amt**：SPEC Paid 金额，来自 `SPEC Paid $`。

- **spec_traded_amt**：Spec Traded 金额，来自 `Spec Traded $`。

- **state_id**：州维表主键，关联 `dim_state.state_id`。

- **vp_id**：VP 维表主键，关联 `dim_vp.vp_id`。

### fact_loan_financial_components：贷款财务组件事实表（贷款+周期粒度）。存放 LOS/GL/LLR/Corporate Allocation 等财务构成字段，避免在事件明细表中重复累加。

- **corporate_allocation_after_exclusions_amt**：剔除后 Corporate Allocation 金额，来自 `Corporate Allocation $ (after exclusions)`。

- **corporate_allocation_amt**：Corporate Allocation 金额，来自 `Corporate Allocation $`。

- **corporate_allocation_bps**：Corporate Allocation 的 BPS 值，来自 `Corporate Allocation BPS`。

- **gl_exception_amt**：GL Exception 金额，来自 `GL Exception $`。

- **gl_exception_bps**：GL Exception 的 BPS 值，来自 `GL Exception BPS`。

- **gl_fee_income_amt**：GL Fee Income 金额，来自 `GL Fee Income $`。

- **gl_fee_income_bps**：GL Fee Income 的 BPS 值，来自 `GL Fee Income BPS`。

- **gl_gos_amt**：GL GOS 金额，来自 `GL GOS $`。

- **gl_gos_bps**：GL GOS 的 BPS 值，来自 `GL GOS BPS`。

- **gl_oi_amt**：GL OI 金额，来自 `GL OI $`。

- **gl_oi_bps**：GL OI 的 BPS 值，来自 `GL OI BPS`。

- **llr_amt**：LLR 金额，来自 `LLR $`。

- **llr_bps**：LLR 的 BPS 值，来自 `LLR BPS`。

- **loan_fin_component_id**：贷款财务组件事实表主键。

- **loan_id**：关联到 `dim_loan` 的贷款主键；该表粒度为 `loan + reporting_period`。

- **los_exception_amt**：LOS Exception 金额，来自 `LOS Exception $`。

- **los_exception_bps**：LOS Exception 的 BPS 值，来自 `LOS Exception BPS`。

- **los_revenue_amt**：LOS Revenue 金额，来自 `LOS Revenue $`。

- **los_revenue_bps**：LOS Revenue 的 BPS 值，来自 `LOS Revenue BPS`。

- **reporting_period_id**：报表周期维表主键，关联 `dim_reporting_period.reporting_period_id`。

- **source_insert_datetime**：去重后记录保留的源写入时间，用于追溯该快照/财务记录来自哪条较新的源行。

### fact_loan_snapshot：贷款快照事实表（贷款+周期粒度）。存放贷款在该周期的快照指标（如 funded units/volume 等）及上下文外键。

- **company_id**：公司维表主键，关联 `dim_company.company_id`。

- **forward_commitment**：Forward Commitment 标记/描述，来自 `Forward Commitment`。

- **funded_units_by_vp**：按 VP 粒度的 funded units 指标，来自 `FundedUnitsByVP`。明细层可能重复。

- **funded_units_in_cost_center**：按成本中心粒度的 funded units，来自 `FundedUnitsInCostCenter`。

- **funded_volume_by_vp**：按 VP 粒度的 funded volume 指标，来自 `FundedVolumeByVP`。明细层可能重复。

- **funded_volume_in_cost_center**：按成本中心粒度的 funded volume，来自 `FundedVolumeInCostCenter`。

- **loan_id**：关联到 `dim_loan` 的贷款主键；该表粒度为 `loan + reporting_period`，理论上每个组合只有一行。

- **loan_snapshot_id**：贷款快照事实表主键。

- **product_id**：产品维表主键，关联 `dim_product.product_id`。

- **reporting_period_id**：报表周期维表主键，关联 `dim_reporting_period.reporting_period_id`。

- **source_insert_datetime**：去重后记录保留的源写入时间，用于追溯该快照/财务记录来自哪条较新的源行。

- **state_id**：州维表主键，关联 `dim_state.state_id`。

### fact_workforce_period_snapshot：人效/产能快照事实表（VP/部门/周期粒度）。用于分析 Active HC、人效、部门级产能与相关 BOM 成本字段。

- **active_non_producing_sales_hc**：活跃但非产出型销售人头数，来自 `ActiveNonProducingSalesHC`。

- **active_sales_hc**：活跃销售人头数（Active Sales Headcount），来自 `ActiveSalesHC`。

- **company_id**：公司维表主键，关联 `dim_company.company_id`。

- **department_id**：部门维表主键，关联 `dim_department.department_id`。

- **funded_units_by_vp**：按 VP 粒度的 funded units 指标，来自 `FundedUnitsByVP`。明细层可能重复。

- **funded_units_in_cost_center**：按成本中心粒度的 funded units，来自 `FundedUnitsInCostCenter`。

- **funded_volume_by_vp**：按 VP 粒度的 funded volume 指标，来自 `FundedVolumeByVP`。明细层可能重复。

- **funded_volume_in_cost_center**：按成本中心粒度的 funded volume，来自 `FundedVolumeInCostCenter`。

- **payroll_reg_earnings_bom_amt**：BOM 口径常规工资金额，来自 `Payroll Reg Earnings $ (BOM)`。明细层可能重复。

- **rent_bom_amt**：BOM 口径房租金额，来自 `Rent $ (BOM)`。该值在明细行可能重复，汇总时需使用快照表或先去重。

- **reporting_period_id**：报表周期维表主键，关联 `dim_reporting_period.reporting_period_id`。

- **vp_id**：关联到 `dim_vp` 的主键；该表粒度为 `reporting_period + company + vp + department`。

- **workforce_snapshot_id**：人效/产能快照事实表主键。

# 使用建议：如何在 Tableau / 数据库中使用这些表

## `dim_loan` + `fact_loan_snapshot`：用于贷款数量、贷款金额、州/产品分布分析。

## `fact_compensafe_event`：用于 compensafe、调整项、事件级成本/异常分析。

## `fact_loan_financial_components`：用于收入/成本构成、利润组件拆解。

## `fact_workforce_period_snapshot`：用于人效、产能、HC 分析。

## `etl_data_quality_issue`：用于审计去重冲突与字段不一致问题；做最终 KPI 前建议先抽查。
