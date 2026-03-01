# VP Dashboard 数据校验报告

- 数据目录: `/Users/xizuo/Cap/output/3nf`
- Distinct Loan Count: `2004`
- Event Row Count: `10999`
- Loan Amount Total (dim_loan): `848699871.86`
- DQ Issues: `5056`

## 检查结果
- [PASS] Loan Count baseline: actual=2004 expected=2004 (COUNTD(dim_loan.loan_number) baseline)
- [PASS] Event row baseline: actual=10999 expected=10999 (fact_compensafe_event row count baseline)
- [PASS] Loan snapshot grain check: actual=2004 expected=2004 (fact_loan_snapshot should be one row per loan in this sample)

## DQ 类型分布
- `conflicting_deduped_fact_value`: 5056
