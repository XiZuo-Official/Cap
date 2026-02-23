# VP Dashboard 数据库三范式拆表方案（基于 `Duke Data V4 (1).xlsx`）

## 目标
把当前 `Duke Data` 单表（79列、事件明细+贷款属性+组织属性混合）拆成 3NF 结构，避免：

- `Loannumber` / `LoanAmount` 重复导致贷款数和贷款金额重复统计
- 组织字段、产品字段、枚举字段在明细表中大量冗余
- Tableau 直接连宽表时出现重复汇总和口径不一致

## 关键前提（已验证）

- `StartDate` = `compensafe` 事件发生日期（不是员工入职日期）
- `EmployeeNameStartDate` 才是人员入职相关字段
- `Loannumber` 在源表中高度重复，属于“一笔贷款对应多条事件/费用明细”

## 3NF 拆表总览

建议分为 4 类表：

1. 主数据维表（实体）
2. 代码/枚举维表（字典）
3. 关系/归属表（带时间）
4. 事实表（贷款快照、事件明细、人效快照）

---

## 1) 主数据维表（实体）

### `dim_company`
- 来源：`CompanyCode`
- 唯一键：`company_code`

### `dim_employee`
- 来源：`EmployeeName`, `EmployeeNameStartDate`, `TerminationDate`, `EmploymentStatus`
- 说明：源数据没有稳定 `employee_id`，建议生成代理键；自然键可暂用 `(employee_name, employee_name_start_date)`
- 唯一键建议：`(employee_name, employee_start_date)`

### `dim_vp`
- 来源：`VP`
- 说明：VP 是角色主体，先独立成表；后续可与 `dim_employee` 做映射
- 唯一键：`vp_name`

### `dim_manager`
- 来源：`CostCenterManagers`, `RegionManager`, `DivisionManagerName`
- 说明：若后续需要完整组织层级管理，建议统一“管理者实体”；第一版可不拆，直接放在组织归属表

### `dim_loan`
- 来源：`Loannumber`, `BorrowerLast`, `FundDate`, `LoanAmount`, `FICO`, `Forward Commitment`, `Builder Name`, `Purpose`
- 粒度：1行=1笔贷款（`Loannumber`）
- 唯一键：`loan_number`

### `dim_state`
- 来源：`SubjectPropertyState`
- 唯一键：`state_code`

### `dim_reporting_period`
- 来源：`BOM`, `ReportPeriodStart`, `ReportPeriodEnd`
- 粒度：月度/报表周期
- 唯一键建议：`(report_period_start, report_period_end, bom_date)`

---

## 2) 代码/枚举维表（字典）

这些列重复率高，且取值集合有限，按 3NF 应抽出：

### `dim_product`
- 来源：
  - `ProductBucketGroup`
  - `ProductUnitEconomics`
  - `NonQm`
  - `GRX`
  - `isHedged`
  - `P&L Loan Type`
  - `Custom LO Type`
  - `SDM Fulfilment`
- 说明：也可以拆成多个小字典表；第一版可合并成一个产品特征组合维表

### `dim_department`
- 来源：
  - `Department Rollup Level 1`
  - `Department Rollup Level 2`
- 唯一键建议：`(dept_rollup_lv1, dept_rollup_lv2)`

### `dim_compensafe_bucket`
- 来源：`CompensafeBucket`

### `dim_adj_type_group`
- 来源：`Adj Type Group`

### `dim_adj_type`
- 来源：`Adj Type`
- 外键：`adj_type_group_id`（如果业务上固定隶属）

### `dim_allocation_bucket`
- 来源：`AllocationBucketNew`

### `dim_inclusion_reason`
- 来源：`Inclusion Reason`

### `dim_insert_user`
- 来源：`InsertedBy`

### `dim_login_bundle`（可选）
- 来源：`BM LoginName 1/2/3`, `RM LoginName 1/2`, `DM LoginName 1`
- 说明：如果只是审计展示可放在归属表；如果需要规范化可拆成单独登录账号桥表

---

## 3) 关系/归属表（带时间）

### `bridge_loan_org_attribution`
- 作用：一笔贷款在某报表周期内归属到哪个 VP/Division/Region/员工/部门
- 粒度建议：`loan + reporting_period + employee + org context`
- 来源字段：
  - `Loannumber`
  - `VP`
  - `EmployeeName`
  - `Department Rollup Level 1/2`
  - `CostCenterManagers`
  - `RegionManager`
  - `DivisionManagerName`
  - `CompanyCode`
  - `BOM` / `ReportPeriodStart` / `ReportPeriodEnd`
- 说明：
  - 这是解释“同一贷款多行”的关键桥表
  - 不能用它直接统计贷款金额总和（需要去重到贷款粒度）

### `bridge_vp_employee_map`（可选，增强）
- 作用：把 `VP` 名称和 `dim_employee` 对应起来（当 `VP == EmployeeName` 时可自动映射）
- 用途：后续处理 VP 本人入离职口径时更稳

---

## 4) 事实表（核心）

### `fact_loan_snapshot`
- 粒度：`loan + reporting_period`（或 `loan + bom`）
- 作用：存贷款层稳定属性与贷款级指标，避免事件明细重复汇总
- 来源字段（典型）：
  - `LoanAmount`
  - `FundDate`
  - `SubjectPropertyState`
  - `FICO`
  - `Purpose`
  - 产品相关字段（经 `dim_product` 外键）
  - `FundedUnitsByVP`, `FundedVolumeByVP`（若确认为贷款/周期级）
- 唯一键建议：`(loan_id, reporting_period_id)`
- 去重规则：
  - 源表同一 `Loannumber + reporting_period` 多行时，贷款级字段取一致值
  - 若不一致，写入异常表并保留最新 `InsertDatetime`

### `fact_compensafe_event`
- 粒度：`1行 = 1条 compensafe/adjustment 事件`
- 作用：保留事件日期、调整类型、费用/补偿等明细
- 来源字段：
  - `StartDate`（事件日期）
  - `CompensafeBucket`
  - `Compensafe BPS`
  - `Compensafe $`
  - `Adj Type`
  - `Adj Type Group`
  - `AllocationBucketNew`
  - `Corporate Allocation $ (after exclusions)`
  - `Inclusion Reason`
  - `InsertedBy`, `InsertDatetime`
  - 关联 `loan_id`, `employee_id`, `vp_id`, `reporting_period_id`
- 说明：
  - 这是重复 `Loannumber` 的主要来源
  - Tableau 做成本/事件分析应使用此表或其月度汇总

### `fact_loan_financial_components`
- 粒度：`loan + reporting_period`
- 作用：存贷款层收入/成本组件（避免在事件明细中重复）
- 来源字段：
  - `LOS Revenue BPS`, `LOS Revenue $`
  - `GL Fee Income BPS`, `GL Fee Income $`
  - `GL GOS BPS`, `GL GOS $`
  - `GL OI BPS`, `GL OI $`
  - `GL Exception BPS`, `GL Exception $`
  - `LLR BPS`, `LLR $`
  - `Corporate Allocation BPS`, `Corporate Allocation $`
  - `LOS Exception BPS`, `LOS Exception $`
- 唯一键建议：`(loan_id, reporting_period_id)`
- 备注：
  - 若这些值在同一贷款+周期跨行不一致，需定义聚合规则（通常 `MAX` 或按事件汇总，先做异常审计）

### `fact_workforce_period_snapshot`
- 粒度：`vp + reporting_period`（或 `org unit + reporting_period`）
- 作用：人效与容量分析
- 来源字段：
  - `ActiveSalesHC`
  - `ActiveNonProducingSalesHC`
  - `FundedUnitsInCostCenter`
  - `FundedVolumeInCostCenter`
  - `FundedUnitsByVP`
  - `FundedVolumeByVP`
  - `Rent $ (BOM)`
  - `Payroll Reg Earnings $ (BOM)`
- 唯一键建议：`(vp_id, reporting_period_id)` 或 `(vp_id, department_id, reporting_period_id)` 视业务口径
- 备注：
  - 源表中这些字段大概率在明细上重复，必须先去重到 VP+Period 粒度后再汇总

---

## 源表列到 3NF 目标表映射（按列分配）

### A. `dim_loan`
- `Loannumber`
- `BorrowerLast`
- `FundDate`
- `LoanAmount`
- `FICO`
- `Forward Commitment`
- `Builder Name`
- `Purpose`

### B. `dim_vp`
- `VP`

### C. `dim_employee`
- `EmployeeName`
- `EmployeeNameStartDate`
- `TerminationDate`
- `EmploymentStatus`

### D. `dim_reporting_period`
- `BOM`
- `ReportPeriodStart`
- `ReportPeriodEnd`

### E. `dim_state`
- `SubjectPropertyState`

### F. `dim_product`
- `ProductBucketGroup`
- `ProductUnitEconomics`
- `NonQm`
- `GRX`
- `isHedged`
- `P&L Loan Type`
- `SDM Fulfilment`
- `Custom LO Type`

### G. `dim_department`
- `Department Rollup Level 1`
- `Department Rollup Level 2`

### H. 字典表
- `CompensafeBucket` -> `dim_compensafe_bucket`
- `Adj Type Group` -> `dim_adj_type_group`
- `Adj Type` -> `dim_adj_type`
- `AllocationBucketNew` -> `dim_allocation_bucket`
- `Inclusion Reason` -> `dim_inclusion_reason`
- `InsertedBy` -> `dim_insert_user`

### I. `bridge_loan_org_attribution`
- `Loannumber`
- `VP`
- `EmployeeName`
- `CompanyCode`
- `CostCenterManagers`
- `RegionManager`
- `DivisionManagerName`
- `BM LoginName 1/2/3`
- `RM LoginName 1/2`
- `DM LoginName 1`
- `Department Rollup Level 1/2`
- `BOM`, `ReportPeriodStart`, `ReportPeriodEnd`

### J. `fact_loan_financial_components`
- 所有 `LOS/GL/LLR/Corporate Allocation/LOS Exception` 的 `BPS/$` 组件列

### K. `fact_compensafe_event`
- `StartDate`（事件日期）
- `CompensafeBucket`
- `Compensafe BPS`
- `Compensafe $`
- `Adj Type`
- `Adj Type Group`
- `AllocationBucketNew`
- `Corporate Allocation $ (after exclusions)`
- `Inclusion Reason`
- `InsertedBy`
- `InsertDatetime`

### L. `fact_workforce_period_snapshot`
- `Rent $ (BOM)`
- `Payroll Reg Earnings $ (BOM)`
- `ActiveSalesHC`
- `ActiveNonProducingSalesHC`
- `FundedUnitsInCostCenter`
- `FundedVolumeInCostCenter`
- `FundedUnitsByVP`
- `FundedVolumeByVP`
- 可选：`CRA Traded $`, `Spec Traded $`, `SPEC BulkAdj $`, `SPEC Paid $`, `CRA Paid $`, `Net Spec $`, `CRA Net $`

---

## 去重与装载规则（必须执行）

### 1. 贷款主表去重（`dim_loan`）
- 键：`Loannumber`
- 规则：
  - `LoanAmount/FundDate/FICO/...` 应一致
  - 不一致则记录到异常表 `etl_data_quality_issue`

### 2. 贷款周期快照去重（`fact_loan_snapshot` / `fact_loan_financial_components`）
- 键：`Loannumber + ReportPeriodStart + ReportPeriodEnd`（或 `+ BOM`）
- 规则：
  - 同键多行时，贷款级字段不重复累加
  - 优先取非空值；冲突时按 `InsertDatetime` 最新记录

### 3. 事件事实保留明细（`fact_compensafe_event`）
- 不去重（除非发现完全重复行）
- 建议生成哈希键用于判重：
  - `loan_number + start_date + adj_type + comp_bucket + comp_amount + employee_name + insert_datetime`

### 4. 人效快照去重（`fact_workforce_period_snapshot`）
- 键建议：`vp + report_period + dept(optional)`
- 规则：
  - 明细行上的 `HC`/`Rent`/`Payroll` 字段通常重复，不可直接求和
  - 先 dedupe 到快照粒度，再汇总到 VP 月度

---

## 给 Tableau 的使用建议（在 3NF 之后）

3NF 是底座；真正给 Tableau 连的建议是二层数据集：

- `mart_vp_monthly_kpi`（VP 月度汇总）
- `mart_loan_analysis`（贷款粒度分析）
- `mart_compensafe_events`（事件明细/异常）

这样既满足审计和治理，又不影响 Tableau 性能。

