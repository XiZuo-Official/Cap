# Tableau VP Dashboard 搭建手册（V1：两页）

## 0. 交付范围
- 页1：`VP总览`
- 页2：`VP对比`
- 双时间轴：贷款看 `fund_date`，事件看 `compensafe_event_date`

配套文件：
- 关系模型：`/Users/xizuo/Cap/docs/tableau_relationship_model_zh.md`
- 计算字段：`/Users/xizuo/Cap/docs/tableau_calculated_fields_zh.md`
- 交互动作：`/Users/xizuo/Cap/docs/tableau_filters_actions_zh.md`
- 验收清单：`/Users/xizuo/Cap/docs/tableau_uat_checklist_zh.md`

## 1. 数据源配置
1. 打开 Tableau Desktop
2. 连接文件：`/Users/xizuo/Cap/output/3nf_all_tables.xlsx`
3. 按关系模型文档添加 Sheet，并在逻辑层建立 Relationships
4. 检查字段类型：
- 金额字段：Number (Decimal)
- ID 字段：Number (Whole) 或 String（保持一致）
- 日期字段：Date
5. 创建计算字段（按计算字段清单）

## 2. 页1：VP总览（布局）
建议画布 `1300 x 900`，上中下三层布局。

### 2.1 顶部 KPI 卡（6张）
- 指标：`Revenue Total`, `Contribution Margin`, `Margin %`, `Loan Count`, `Productivity`, `ROI`
- 形式：6 个独立文本卡片
- 格式：
- 货币字段：`$#,##0;($#,##0)`
- 百分比：`0.00%`
- 空值：显示 `-`

### 2.2 中部左：贷款趋势线（双轴）
- Columns：`Fund Date (Month)`
- Rows：`Loan Count` + `Loan Amount Total`（Dual Axis）
- 标记：
- `Loan Count` 用线
- `Loan Amount Total` 用线（次轴）
- 同步轴后，分别设置颜色

### 2.3 中部右：事件成本趋势线
- Columns：`Event Date (Month)`
- Rows：`Expense Total`
- Mark：Line
- Filter：`Event Date (Month)` 非空

### 2.4 下部左：州分布地图
- 地理角色：`dim_state.state_code` 设为 State/Province
- Size：`Revenue Total`
- Color：`Margin %`
- Label：州代码 + Revenue + Margin%

### 2.5 下部中：产品结构条形图
- Rows：`dim_product.product_bucket_group`
- Columns：`Revenue Total`
- Color：`Margin %`
- Sort：按 `Revenue Total` 降序

### 2.6 下部右：异常提示表
- 数据：`etl_data_quality_issue`
- 列：`detected_at`, `issue_type`, `severity`, `source_business_key`, `issue_detail`
- 排序：`detected_at` 降序
- 过滤：Top 20

## 3. 页2：VP对比（布局）
建议画布 `1300 x 900`，上两图下三图布局。

### 3.1 上左：VP 排名条形图
- Rows：`dim_vp.vp_name`
- Columns：`Revenue Total`
- 排序：默认 `Revenue Total` 降序
- 参数切换排序：
- 建参数 `Sort Metric`：`Revenue Total` / `Margin %` / `ROI`
- 建计算 `Sort Value` 映射参数

### 3.2 上右：VP 气泡图
- Columns：`Margin %`
- Rows：`Productivity`
- Size：`Loan Count`
- Color：`Revenue Total`
- Detail：`dim_vp.vp_name`

### 3.3 下左：VP 热力表
- Rows：`dim_vp.vp_name`
- Columns：指标名称（可用 Measure Names）
- Color：标准化分位值（建议建 `Percentile` 计算）
- Text：实际值

### 3.4 下中：ROI vs Expense 散点图
- Columns：`Expense Total`
- Rows：`ROI`
- Detail：`dim_vp.vp_name`
- Color：`Margin %`

### 3.5 下右：VP KPI 明细表
- 列：VP、Revenue、Expense、Margin%、Loan Count、Productivity、ROI
- 支持导出 CSV

## 4. 全局筛选器
放在仪表盘左侧，所有页共用：
- VP
- 州
- 产品组
- 部门
- Compensafe Bucket
- FundDate 区间
- EventDate 区间

## 5. 交互动作
按 `/Users/xizuo/Cap/docs/tableau_filters_actions_zh.md` 配置：
- VP 点击联动
- 贷款时间刷选
- 事件时间刷选
- Tooltip 规范与空值规范

## 6. 发布前核对
逐条执行：`/Users/xizuo/Cap/docs/tableau_uat_checklist_zh.md`

最低通过标准：
- `Loan Count = 2004`
- `fact_compensafe_event` 口径 10999
- 双时间轴行为正确

