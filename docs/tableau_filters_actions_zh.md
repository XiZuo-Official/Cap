# Tableau 筛选器与交互动作配置

## 1. 全局筛选器（两页共用）
- VP：`dim_vp.vp_name`
- 州：`dim_state.state_code`
- 产品组：`dim_product.product_bucket_group`
- 部门：`dim_department.dept_rollup_level_1`
- Compensafe Bucket：`dim_compensafe_bucket.compensafe_bucket_name`
- 贷款时间：`Fund Date (Month)` 范围筛选
- 事件时间：`Event Date (Month)` 范围筛选

设置要求：
- 所有筛选器设置为 `Apply to Worksheets -> All Using This Data Source`
- `Compensafe Bucket` 默认全选（包含 `No Loan #`）

## 2. Dashboard Actions

### Action A：VP 高亮联动
- Source：VP 排名图 / VP 气泡图 / VP 热力表
- Target：当前页全部图表
- Run action：`Select`
- Clearing：`Show all values`

### Action B：时间刷选（贷款）
- Source：贷款趋势线
- Target：页内 KPI、州图、产品图
- 字段：`Fund Date (Month)`
- Run action：`Select`

### Action C：时间刷选（事件）
- Source：事件成本趋势线
- Target：页内 KPI、VP 对比图、异常表
- 字段：`Event Date (Month)`
- Run action：`Select`

### Action D：Tooltip 明细跳转（可选）
- Source：VP 排名图
- Target：VP 明细表
- Run action：`Menu`

## 3. Tooltip 规范
每个核心图 Tooltip 必含：
- 当前值（本图主指标）
- 占比（相对当前筛选总量）
- 同比（若无可比基期显示 `N/A`）

实现建议：
- 同比字段做条件判断，缺基期时返回 `NULL`
- Tooltip 中用 `IFNULL(..., "N/A")`

## 4. 空值展示规则
- 所有比率指标（`Margin %`, `ROI`, `Productivity`）空值显示 `-`
- 不显示强制 0，避免误导
- 图例中将 `NULL` 分类命名为 `No Data`

