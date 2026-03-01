# VP Dashboard 重做方案（轻量版，可自动换数）

## 你现在的最终目标
- 用 Tableau 做 VP 绩效 Dashboard（先可用、可维护）
- 不强制 3NF
- 以后换 Excel 文件后，Dashboard 自动展示新数据（通过固定输出文件路径刷新）

## 新方案结构（完全重做）
我们只保留一条数据加工链：

1. 输入：原始 Excel（例如 `Duke Data V4 (1).xlsx`）
2. 脚本：`/Users/xizuo/Cap/scripts/build_vp_dashboard_data.py`
3. 输出（固定路径）：`/Users/xizuo/Cap/output/tableau_ready/`
   - `vp_dashboard_data.xlsx`（Tableau 直接连接这个）
   - `vp_kpi_monthly.csv`
   - `vp_loan_detail.csv`
   - `vp_exception_log.csv`
   - `build_summary.json`

## 三张核心表（在 `vp_dashboard_data.xlsx` 里）

### `vp_kpi_monthly`
粒度：`report_month + vp`  
用途：KPI 卡、VP 对比、趋势图主数据。

关键字段：
- `loan_count`, `loan_volume`
- `total_revenue`, `total_expense`
- `contribution_margin`, `margin_pct`
- `active_sales_hc`, `productivity`
- `bonus_spend_proxy`, `roi`
- `exception_flag`, `exception_reason`

### `vp_loan_detail`
粒度：`loan_number + vp + report_month`  
用途：贷款明细、钻取、州/产品/用途分析。

关键字段：
- `loan_number`, `fund_date`, `state`, `product_bucket_group`, `purpose`
- `loan_amount`
- 各收入/成本组件（`los_revenue_amt`, `gl_*`, `llr_amt`, `corporate_allocation_amt`）

### `vp_exception_log`
粒度：异常记录  
用途：总览页异常提示表。

关键字段：
- `exception_reason`
- `margin_pct`, `roi`
- `detail`, `issue_key`（冲突追踪）

## 口径约定（这版的简化规则）
- 贷款 KPI：
  - `loan_count` 来自贷款去重后计数
  - `loan_volume` 来自去重贷款层的 `loan_amount`
- 收入：
  - 贷款层收入组件汇总（避免事件行重复放大）
- 费用：
  - 贷款层费用组件 + 事件层成本（Compensafe/Rent/Payroll）
- ROI：
  - 用 `spec_paid_amt + cra_paid_amt` 做 bonus 代理分母
- 时间轴：
  - 贷款分析：`fund_date`
  - 事件分析：`report_month`（BOM）+ 异常/事件来源

## Tableau 连接建议
只连一个文件：`/Users/xizuo/Cap/output/tableau_ready/vp_dashboard_data.xlsx`

工作表对应：
- KPI/VP对比：用 `vp_kpi_monthly`
- 贷款钻取：用 `vp_loan_detail`
- 异常表：用 `vp_exception_log`

## 每次换新 Excel 的刷新流程
1. 把新 Excel 放到项目目录（或指定路径）
2. 运行脚本：
```bash
python3 /Users/xizuo/Cap/scripts/build_vp_dashboard_data.py --source "/path/to/new_file.xlsx"
```
3. 打开 Tableau，点 `Data -> Refresh All Extracts`（或 `Refresh`）
4. Dashboard 自动用新数据重算（因为输出文件路径和表名不变）

