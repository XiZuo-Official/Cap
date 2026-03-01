# Tableau 数据关系配置清单（VP Dashboard）

数据源文件：`/Users/xizuo/Cap/output/3nf_all_tables.xlsx`

建模方式：**Relationships（逻辑层）**，不做物理扁平 Join。

## 1. 需要加载的 Sheet
- `fact_loan_snapshot`
- `fact_compensafe_event`
- `fact_loan_financial_components`
- `fact_workforce_period_snapshot`
- `bridge_loan_org_attribution`
- `dim_loan`
- `dim_vp`
- `dim_state`
- `dim_product`
- `dim_department`
- `dim_reporting_period`
- `dim_compensafe_bucket`
- `dim_adj_type`
- `dim_adj_type_group`
- `etl_data_quality_issue`

## 2. 关系键（按此顺序配置）
1. `fact_loan_snapshot.loan_id = dim_loan.loan_id`
2. `fact_loan_financial_components.loan_id = dim_loan.loan_id`
3. `fact_compensafe_event.loan_id = dim_loan.loan_id`
4. `fact_workforce_period_snapshot.vp_id = dim_vp.vp_id`
5. `fact_workforce_period_snapshot.department_id = dim_department.department_id`
6. `fact_workforce_period_snapshot.reporting_period_id = dim_reporting_period.reporting_period_id`
7. `fact_compensafe_event.vp_id = dim_vp.vp_id`
8. `fact_compensafe_event.state_id = dim_state.state_id`
9. `fact_compensafe_event.product_id = dim_product.product_id`
10. `fact_compensafe_event.department_id = dim_department.department_id`
11. `fact_compensafe_event.reporting_period_id = dim_reporting_period.reporting_period_id`
12. `fact_compensafe_event.compensafe_bucket_id = dim_compensafe_bucket.compensafe_bucket_id`
13. `fact_compensafe_event.adj_type_id = dim_adj_type.adj_type_id`
14. `fact_compensafe_event.adj_type_group_id = dim_adj_type_group.adj_type_group_id`
15. `fact_loan_snapshot.loan_id + fact_loan_snapshot.reporting_period_id` 对 `bridge_loan_org_attribution.loan_id + bridge_loan_org_attribution.reporting_period_id`
16. `bridge_loan_org_attribution.vp_id = dim_vp.vp_id`
17. `bridge_loan_org_attribution.state_id = dim_state.state_id`
18. `bridge_loan_org_attribution.product_id = dim_product.product_id`
19. `bridge_loan_org_attribution.department_id = dim_department.department_id`
20. `bridge_loan_org_attribution.reporting_period_id = dim_reporting_period.reporting_period_id`

## 3. 关键口径约束
- 贷款数量只用：`COUNTD([dim_loan.loan_number])`
- 贷款金额只用：`SUM([dim_loan.loan_amount])`
- 不在 `fact_compensafe_event` 上直接统计贷款金额
- VP 口径优先取 `bridge_loan_org_attribution -> dim_vp`；VP 明细趋势可用 `fact_compensafe_event.vp_id`

## 4. 时间口径（双时间轴）
- 贷款时间轴：`dim_loan.fund_date`
- 事件时间轴：`fact_compensafe_event.compensafe_event_date`
- 报表快照时间：`dim_reporting_period.bom_date`

## 5. 推荐命名规范（Tableau 数据窗格）
- 文件夹 `KPI`：所有计算字段
- 文件夹 `Time`：`Fund Date (Month)`, `Event Date (Month)`, `bom_date`
- 文件夹 `Dims`：VP/州/产品/部门/Bucket
- 文件夹 `QA`：`etl_data_quality_issue` 字段

