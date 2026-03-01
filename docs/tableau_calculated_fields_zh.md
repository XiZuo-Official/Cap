# Tableau 计算字段清单（固定口径）

以下字段名与公式按计划锁定，建议原样创建。

## KPI 字段

1. `Loan Count`
```tableau
COUNTD([dim_loan.loan_number])
```

2. `Loan Amount Total`
```tableau
SUM([dim_loan.loan_amount])
```

3. `Revenue Total`
```tableau
SUM([fact_loan_financial_components.los_revenue_amt]) +
SUM([fact_loan_financial_components.gl_fee_income_amt]) +
SUM([fact_loan_financial_components.gl_gos_amt]) +
SUM([fact_loan_financial_components.gl_oi_amt]) +
SUM([fact_loan_financial_components.gl_exception_amt]) +
SUM([fact_loan_financial_components.los_exception_amt])
```

4. `Expense Total`
```tableau
SUM([fact_loan_financial_components.llr_amt]) +
SUM([fact_loan_financial_components.corporate_allocation_amt]) +
SUM([fact_compensafe_event.compensafe_amt]) +
SUM([fact_compensafe_event.rent_bom_amt]) +
SUM([fact_compensafe_event.payroll_reg_earnings_bom_amt])
```

5. `Contribution Margin`
```tableau
[Revenue Total] - [Expense Total]
```

6. `Margin %`
```tableau
IF [Revenue Total] = 0 THEN NULL ELSE [Contribution Margin] / [Revenue Total] END
```

7. `Active Sales HC`
```tableau
SUM([fact_workforce_period_snapshot.active_sales_hc])
```

8. `Productivity`
```tableau
IF [Active Sales HC] = 0 THEN NULL ELSE [Revenue Total] / [Active Sales HC] END
```

9. `Bonus Spend`
```tableau
SUM([fact_compensafe_event.spec_paid_amt]) +
SUM([fact_compensafe_event.cra_paid_amt])
```

10. `ROI`
```tableau
IF [Bonus Spend] = 0 THEN NULL ELSE [Revenue Total] / [Bonus Spend] END
```

## 时间字段（双时间轴）

11. `Event Date (Month)`
```tableau
DATETRUNC('month', [fact_compensafe_event.compensafe_event_date])
```

12. `Fund Date (Month)`
```tableau
DATETRUNC('month', [dim_loan.fund_date])
```

## 展示辅助字段（建议）

13. `Margin % (Display)`
```tableau
IF ISNULL([Margin %]) THEN "-" ELSE STR(ROUND([Margin %] * 100, 2)) + "%" END
```

14. `ROI (Display)`
```tableau
IF ISNULL([ROI]) THEN "-" ELSE STR(ROUND([ROI], 2)) END
```

15. `No Loan Bucket Flag`
```tableau
IF [dim_compensafe_bucket.compensafe_bucket_name] = "No Loan #" THEN "No Loan #" ELSE "Loan #" END
```

