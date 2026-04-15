# Executive insight panel — controlled text

**Format:** Exactly **four** Markdown bullets (`- …`), in fixed order. No preamble or closing copy inside the panel.

**Order (maps to dataset patterns):**

1. **Cost efficiency** — `average_efficiency_percent` (KPI) and portfolio gap \(100 \times (1 - \sum internal\_total\_cost / \sum benchmark\_equivalent\_cost)\) when denominator \(> 0\).
2. **High-value categories** — `groupby("service_category")["estimated_cost_avoidance"].sum()`: leader, share of in-view avoidance, runner-up when more than one category remains after filters.
3. **Growth trend** — First vs last `month` in the filtered frame on `estimated_cost_avoidance` summed by month; if one month only, state that the window is insufficient for direction.
4. **Opportunity** — If Events rows exist and \(\sum event\_reach > 0\): reach→registration rate on filtered Events rows; else category with lowest mean `efficiency_percent` in the filtered frame.

**Empty filtered frame:** Four bullets instruct to widen filters (implemented in `src/data/demo/exec_dummy_kpis.py` → `build_insight_markdown`).

**Disallowed in bullets:** Audit claims, ROI guarantees, competitor comparisons, causal language beyond the dummy framing.
