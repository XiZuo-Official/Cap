# Tableau 快速上手（新方案）

## 1) 每次更新数据
如果你换了新的原始 Excel，执行：

```bash
/Users/xizuo/Cap/scripts/refresh_vp_dashboard_data.sh "/你的新Excel路径.xlsx"
```

不传路径时，会自动选项目目录里最新的 `.xlsx`（会跳过 `Preliminary` 文件）。

## 2) Tableau 连接文件
在 Tableau Desktop 里连接：

`/Users/xizuo/Cap/output/tableau_ready/vp_dashboard_data.xlsx`

只用这 3 个 sheet：
- `vp_kpi_monthly`
- `vp_loan_detail`
- `vp_exception_log`

## 3) 推荐用法
- KPI 卡、VP 对比、趋势：`vp_kpi_monthly`
- 贷款明细下钻：`vp_loan_detail`
- 异常提示表：`vp_exception_log`

## 4) 双时间轴字段
- 贷款趋势：`fund_date`（来自 `vp_loan_detail`）
- VP 月度 KPI/成本：`report_month`（来自 `vp_kpi_monthly`）

## 5) 刷新
每次脚本跑完后，在 Tableau 点：
- `Data -> Refresh`

由于输出文件名和 sheet 名固定，Dashboard 会自动读取新数据。

