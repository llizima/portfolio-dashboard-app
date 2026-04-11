# KPI Summary
## SOFWERX Value Dashboard

---

## 1. Purpose

This report summarizes the first reusable benchmark KPI outputs generated from the canonical comparable-contracts dataset.

These outputs are descriptive benchmark summaries intended for downstream dashboard loading and evaluation use. They do not represent audited savings, ROI, or internal SOFWERX cost accounting.

## 2. Input Dataset

- Source dataset: `C:\Users\laliz\Desktop\Internship\SOFWERX\Sofwerx_Value_Dashboard\src\data\processed\comparable_contracts.parquet`
- Total input rows: **2,184**

## 3. Output Artifacts

- Overall KPI JSON: `C:\Users\laliz\Desktop\Internship\SOFWERX\Sofwerx_Value_Dashboard\src\data\processed\kpi_tables\smoke_test\overall_kpis_smoke.json`
- Category KPI table: `C:\Users\laliz\Desktop\Internship\SOFWERX\Sofwerx_Value_Dashboard\src\data\processed\kpi_tables\smoke_test\category_kpis_smoke.parquet`
- Yearly KPI table: `C:\Users\laliz\Desktop\Internship\SOFWERX\Sofwerx_Value_Dashboard\src\data\processed\kpi_tables\smoke_test\yearly_kpis_smoke.parquet`
- Agency KPI table: `C:\Users\laliz\Desktop\Internship\SOFWERX\Sofwerx_Value_Dashboard\src\data\processed\kpi_tables\smoke_test\agency_kpis_smoke.parquet`
- This report: `C:\Users\laliz\Desktop\Internship\SOFWERX\Sofwerx_Value_Dashboard\reports\evaluation\kpi_summary_smoke.md`

## 4. Headline Overall KPIs

- Total comparable contracts: **2,184**
- Total benchmarked dollars: **129,245,405,388.69**
- Median award amount: **30,470,594.47**
- Mean award amount: **59,178,299.17**
- Award amount Q1: **316,885.87**
- Award amount Q3: **66,770,481.57**
- Award amount IQR: **66,453,595.70**
- Mapped contracts: **1,744** (79.8535%)
- Unmapped contracts: **440** (20.1465%)
- Manual review count: **60**

## 5. Table Coverage

- Category KPI rows: **10**
- Yearly KPI rows: **4**
- Agency KPI rows: **23**

## 6. Caveats

- These KPI outputs are descriptive benchmark summaries, not causal or audited financial conclusions.
- `award_amount` is used as the primary benchmark value field for this stage.
- Unmapped contracts may still appear in the canonical comparable dataset and are retained explicitly rather than silently dropped.
- Amount-based metrics are calculated from numeric non-null `award_amount` values.
- This report is intended to support benchmark interpretation and downstream app loading, not internal savings claims.
