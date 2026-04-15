# Executive dummy dashboard — KPI calculations (locked)

These definitions are **normative** for any UI that consumes `src/data/demo/exec_dummy_data.csv` / `exec_dummy_data.df` (modules `src/data/demo/exec_dummy_data.py` and `src/data/demo/exec_dummy_kpis.py` on `sys.path`).  
Do not substitute alternate formulas for the same label without changing this document and the paired Python module.

**Symbols:** Let \(D\) be the dataframe after applying **global filters** (date range, optional `service_category` multi-select). If \(D\) is empty, KPIs are undefined; show empty state, not zeros-as-if-valid.

**Column names** (must exist on each row):  
`month`, `service_category`, `internal_count`, `internal_total_cost`, `internal_avg_cost`, `benchmark_avg_cost`, `benchmark_equivalent_cost`, `estimated_cost_avoidance`, `efficiency_percent`, `event_reach`, `event_registrations`, `event_attendance`, `qualified_followups`, `benchmark_total_spend`, `benchmark_contract_count`.

---

## 1. Row-level identities (validation, not recomputation in UI)

For every non-empty row in the source data:

1. **Internal average cost**  
   \(\text{internal\_avg\_cost} = \text{internal\_total\_cost} / \text{internal\_count}\) when `internal_count > 0`.

2. **Benchmark equivalent cost**  
   \(\text{benchmark\_equivalent\_cost} = \text{benchmark\_avg\_cost} \times \text{internal\_count}\).

3. **Estimated cost avoidance**  
   \(\text{estimated\_cost\_avoidance} = \text{benchmark\_equivalent\_cost} - \text{internal\_total\_cost}\).

4. **Efficiency percent (unit-cost gap vs benchmark)**  
   \(\text{efficiency\_percent} = 100 \times (\text{benchmark\_avg\_cost} - \text{internal\_avg\_cost}) / \text{benchmark\_avg\_cost}\) when `benchmark_avg_cost > 0`.

5. **Events funnel**  
   For `service_category != "Events & Engagement"`, funnel integers are **0**.  
   For Events rows: `event_reach` ≥ `event_registrations` ≥ `event_attendance` ≥ `qualified_followups` (dataset invariant).

---

## 2. Executive headline KPIs (aggregates over filtered `df`)

Apply the same filters as for \(D\); use the resulting frame as `df`.

```
total_internal_cost = df["internal_total_cost"].sum()
total_benchmark_equivalent_cost = df["benchmark_equivalent_cost"].sum()
total_cost_avoidance = df["estimated_cost_avoidance"].sum()
average_efficiency_percent = (df["efficiency_percent"] * df["internal_total_cost"]).sum() / df["internal_total_cost"].sum()
total_services_delivered = df["internal_count"].sum()
highest_value_service_category = df.groupby("service_category")["estimated_cost_avoidance"].sum().idxmax()
```

**Avoidance identity (validation):**  
\(\sum \text{estimated\_cost\_avoidance} \stackrel{?}{=} \sum \text{benchmark\_equivalent\_cost} - \sum \text{internal\_total\_cost}\) within currency tolerance \(10^{-2}\).

---

## 3. Events-only funnel rates (subset \(E \subset D\))

Let \(E\) be rows where `service_category == "Events & Engagement"`. If \(\sum_E \text{event\_reach} = 0\), all rates are **null**.

| Rate | Formula |
|------|---------|
| Registration rate | \(100 \times \sum \text{event\_registrations} / \sum \text{event\_reach}\) |
| Attendance rate (of registered) | \(100 \times \sum \text{event\_attendance} / \sum \text{event\_registrations}\) if \(\sum \text{event\_registrations} > 0\) |
| Qualified follow-up rate (of attended) | \(100 \times \sum \text{qualified\_followups} / \sum \text{event\_attendance}\) if \(\sum \text{event\_attendance} > 0\) |

---

## 4. Non-goals (explicit)

- Do **not** present portfolio metrics as audited savings, ROI, or contract-level truth.
- Do **not** replace `estimated_cost_avoidance` with a recomputation from different base fields unless row-level data changes upstream.
