# Tableau VP Dashboard 验收清单（UAT）

## A. 数据完整性
- [ ] 未筛选时 `Loan Count = 2004`
- [ ] `fact_compensafe_event` 明细行数口径为 `10999`
- [ ] `dim_loan.loan_amount` 空值不被计入 `Loan Amount Total`

## B. 去重与口径
- [ ] 贷款趋势图中切换维度后，`Loan Amount Total` 不出现事件表倍增
- [ ] `Loan Count` 使用 `COUNTD(loan_number)`，非 `COUNT`
- [ ] VP 口径来源可追溯（桥表/事件表方案一致）

## C. 双时间轴
- [ ] 贷款趋势图 X 轴使用 `Fund Date (Month)`
- [ ] 事件成本图 X 轴使用 `Event Date (Month)`
- [ ] FundDate 筛选不会直接替代 EventDate 时间字段定义
- [ ] EventDate 筛选不会直接替代 FundDate 时间字段定义

## D. KPI 公式健壮性
- [ ] `Margin %` 在 `Revenue Total = 0` 时返回空
- [ ] `Productivity` 在 `Active Sales HC = 0` 时返回空
- [ ] `ROI` 在 `Bonus Spend = 0` 时返回空

## E. 交互与体验
- [ ] 点击 VP 后同页图表联动
- [ ] 趋势图刷选后 KPI 卡同步变化
- [ ] Tooltip 包含当前值、占比、同比/N/A
- [ ] 比率空值显示为 `-`

## F. 异常可见性
- [ ] 总览页显示 `etl_data_quality_issue` 前 20 条
- [ ] 支持按 `issue_type` 和 `severity` 快速过滤

## G. 性能
- [ ] 常用筛选组合下响应时间 < 2 秒（本地样本）
- [ ] 切页和筛选无明显卡顿

