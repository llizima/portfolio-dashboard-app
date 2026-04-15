# Executive dummy dashboard — locked layout (specification only)

Structured one-page layout. No implementation code.

---

## TOP ROW — KPI cards

- **Layout:** Single horizontal row of **five** read-only KPI cards (equal width).
- **Order (fixed):**
  1. Total Internal Cost  
  2. Total Benchmark Equivalent Cost  
  3. Total Cost Avoidance  
  4. Average Efficiency %  
  5. Total Services Delivered  

---

## ROW 2

- **Layout:** Two columns, equal width.

### LEFT — Bar chart

- **Title:** Internal vs Benchmark Cost by Service Category  
- **Chart type:** Vertical bar chart (two series per category).  
- **X-axis:** `service_category`  
- **Y-axis:** `internal_avg_cost` and `benchmark_avg_cost` (both series on the same chart).  
- **Data rule:** Filtered analysis frame; one bar group per distinct `service_category`; where multiple rows share a category, use the **arithmetic mean** of `internal_avg_cost` and the **arithmetic mean** of `benchmark_avg_cost` across those rows for bar heights.

### RIGHT — Horizontal bar chart

- **Title:** Estimated Cost Avoidance by Service Category  
- **Chart type:** Horizontal bar chart.  
- **X-axis:** `estimated_cost_avoidance`  
- **Y-axis:** `service_category`  
- **Data rule:** One bar per `service_category`; bar length = **sum** of `estimated_cost_avoidance` over filtered rows in that category.

---

## ROW 3

- **Layout:** Two columns, equal width.

### LEFT — Line chart

- **Title:** Monthly Services vs Estimated Value  
- **Chart type:** Line chart.  
- **X-axis:** `month` (chronological order).  
- **Y-axis series 1:** `internal_count` (summed per `month` across filtered rows).  
- **Y-axis series 2:** `estimated_cost_avoidance` (summed per `month` across filtered rows).  
- **Scales:** Two independent vertical scales (one per series).

### RIGHT — Bar chart

- **Title:** Benchmark Spend by Service Category  
- **Chart type:** Vertical bar chart.  
- **X-axis:** `service_category`  
- **Y-axis:** `benchmark_total_spend`  
- **Data rule:** One bar per `service_category`; bar height = **sum** of `benchmark_total_spend` over filtered rows in that category.

---

## ROW 4

- **Layout:** Two columns, equal width.

### LEFT — Funnel-style bar chart

- **Title:** Event Engagement Funnel  
- **Chart type:** Funnel-style vertical bar sequence.  
- **Stages (fixed order):** reach → registrations → attendance → followups  
- **Field mapping:** `event_reach` → `event_registrations` → `event_attendance` → `qualified_followups`  
- **Values:** Sums of each field over filtered rows where `service_category` is Events & Engagement only.

### RIGHT — Table and executive takeaway

- **Table**  
  - **Columns (fixed, in order):** `service_category`, `internal_count`, `internal_avg_cost`, `benchmark_avg_cost`, `estimated_cost_avoidance`, `efficiency_percent`  
  - **Rows:** All filtered rows (same grain as the analysis frame).

- **Executive takeaway text box**  
  - **Placement:** Directly below the table within the same right-hand column.  
  - **Content rules:** `INSIGHT_PANEL_CONTROLLED_TEXT.md`; numeric tokens only from `KPI_FORMULAS_LOCKED.md` / `src/data/demo/exec_dummy_kpis.py`.

---

## Page chrome (non-chart)

- **Title line:** Executive overview (dummy data).  
- **Filters:** Month range and `service_category` multi-select applied to all rows above before any KPI or chart.
