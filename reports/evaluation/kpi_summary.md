# KPI Summary
## Applied Government Analytics (AGA) Value Dashboard

---

## 1. Purpose

This report summarizes the first reusable benchmark KPI outputs generated from the canonical comparable-contracts dataset.

These outputs are descriptive benchmark summaries intended for downstream dashboard loading and evaluation use. They do not represent audited savings, ROI, or internal Applied Government Analytics (AGA) cost accounting.

## 2. Input Dataset

- Source dataset: `C:\Users\laliz\Desktop\Internship\Applied_Government_Analytics\AGA_Value_Dashboard\Value_Dashboard_DEPLOY\src\data\processed\comparable_contracts.parquet`
- Total input rows: **1,764**

## 3. Output Artifacts

- Overall KPI JSON: `C:\Users\laliz\Desktop\Internship\Applied_Government_Analytics\AGA_Value_Dashboard\Value_Dashboard_DEPLOY\src\data\processed\kpi_tables\overall_kpis.json`
- Category KPI table: `C:\Users\laliz\Desktop\Internship\Applied_Government_Analytics\AGA_Value_Dashboard\Value_Dashboard_DEPLOY\src\data\processed\kpi_tables\category_kpis.parquet`
- Yearly KPI table: `C:\Users\laliz\Desktop\Internship\Applied_Government_Analytics\AGA_Value_Dashboard\Value_Dashboard_DEPLOY\src\data\processed\kpi_tables\yearly_kpis.parquet`
- Agency KPI table: `C:\Users\laliz\Desktop\Internship\Applied_Government_Analytics\AGA_Value_Dashboard\Value_Dashboard_DEPLOY\src\data\processed\kpi_tables\agency_kpis.parquet`
- This report: `C:\Users\laliz\Desktop\Internship\Applied_Government_Analytics\AGA_Value_Dashboard\Value_Dashboard_DEPLOY\reports\evaluation\kpi_summary.md`

## 4. Headline Overall KPIs

- Total comparable contracts: **1,764**
- Total benchmarked dollars: **136,658,417,771.42**
- Median award amount: **35,662,965.81**
- Mean award amount: **77,470,758.37**
- Award amount Q1: **213,027.63**
- Award amount Q3: **73,263,505.09**
- Award amount IQR: **73,050,477.47**
- Mapped contracts: **1,585** (89.8526%)
- Unmapped contracts: **179** (10.1474%)
- Manual review count: **53**

## 5. Table Coverage

- Category KPI rows: **10**
- Yearly KPI rows: **4**
- Agency KPI rows: **24**

## 6. Caveats

- These KPI outputs are descriptive benchmark summaries, not causal or audited financial conclusions.
- `award_amount` is used as the primary benchmark value field for this stage.
- Unmapped contracts may still appear in the canonical comparable dataset and are retained explicitly rather than silently dropped.
- Amount-based metrics are calculated from numeric non-null `award_amount` values.
- This report is intended to support benchmark interpretation and downstream app loading, not internal savings claims.
