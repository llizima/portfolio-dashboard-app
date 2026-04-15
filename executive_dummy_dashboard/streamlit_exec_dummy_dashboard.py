"""
One-page executive dummy dashboard: df, locked KPIs, locked layout.
Charts use Altair (no Plotly required). Run from repo root:
    streamlit run executive_dummy_dashboard/streamlit_exec_dummy_dashboard.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

_HERE = Path(__file__).resolve().parent
_ROOT = _HERE.parent
_DEMO_DATA = _ROOT / "src" / "data" / "demo"
if str(_DEMO_DATA) not in sys.path:
    sys.path.insert(0, str(_DEMO_DATA))

import exec_dummy_data  # noqa: E402
import exec_dummy_kpis as kpi  # noqa: E402

TABLE_COLS = [
    "service_category",
    "internal_count",
    "internal_avg_cost",
    "benchmark_avg_cost",
    "estimated_cost_avoidance",
    "efficiency_percent",
]


def _month_range_ui(df: pd.DataFrame) -> list[str]:
    months = sorted(df["month"].unique().tolist())
    c1, c2 = st.columns(2)
    with c1:
        lo = st.selectbox("Month from", months, index=0)
    with c2:
        hi = st.selectbox("Month through", months, index=len(months) - 1)
    if months.index(lo) > months.index(hi):
        lo, hi = hi, lo
    i0, i1 = months.index(lo), months.index(hi)
    return months[i0 : i1 + 1]


def main() -> None:
    st.set_page_config(page_title="Executive overview (dummy)", layout="wide")

    st.title("Executive overview (dummy data)")
    st.caption(
        "Illustrative benchmark pairing for layout and formula testing—not operational accounting."
    )

    df = exec_dummy_data.df.copy()
    months = _month_range_ui(df)
    cats = sorted(df["service_category"].unique().tolist())
    sel_cat = st.multiselect("Service categories", cats, default=cats)

    d = kpi.apply_filters(df, months=months, categories=sel_cat if sel_cat else None)
    kpis = kpi.compute_executive_kpis(d)

    st.divider()
    if kpis is None:
        st.info("No data in view.")
        return

    k1, k2, k3, k4, k5 = st.columns(5)
    with k1:
        st.metric("Total Internal Cost", kpi.fmt_currency(kpis.total_internal_cost))
    with k2:
        st.metric("Total Benchmark Equivalent Cost", kpi.fmt_currency(kpis.total_benchmark_equivalent_cost))
    with k3:
        st.metric("Total Cost Avoidance", kpi.fmt_currency(kpis.total_cost_avoidance))
    with k4:
        st.metric("Average Efficiency %", kpi.fmt_pct_one(kpis.average_efficiency_percent))
    with k5:
        st.metric("Total Services Delivered", f"{kpis.total_services_delivered:,}")

    if not kpi.avoidance_identity_holds(d):
        st.warning("Avoidance identity check failed for current slice (see KPI_FORMULAS_LOCKED.md).")

    st.divider()
    r2l, r2r = st.columns(2)
    av = (
        d.groupby("service_category", as_index=False)
        .agg(
            internal_avg_cost=("internal_avg_cost", "mean"),
            benchmark_avg_cost=("benchmark_avg_cost", "mean"),
        )
    )
    long_ib = av.melt(
        id_vars=["service_category"],
        value_vars=["internal_avg_cost", "benchmark_avg_cost"],
        var_name="metric",
        value_name="value",
    )
    chart_r2l = (
        alt.Chart(long_ib)
        .mark_bar(cornerRadiusEnd=2)
        .encode(
            x=alt.X("service_category:N", title="service_category"),
            xOffset="metric:N",
            color=alt.Color("metric:N", title=None),
            y=alt.Y("value:Q", title=""),
            tooltip=["service_category", "metric", "value"],
        )
        .properties(height=320, title="Internal vs Benchmark Cost by Service Category")
    )
    with r2l:
        st.altair_chart(chart_r2l, width="stretch")

    avoid_by_cat = d.groupby("service_category", as_index=False)["estimated_cost_avoidance"].sum()
    chart_r2r = (
        alt.Chart(avoid_by_cat)
        .mark_bar(color="#81c784", cornerRadiusEnd=2)
        .encode(
            x=alt.X("estimated_cost_avoidance:Q", title="estimated_cost_avoidance"),
            y=alt.Y("service_category:N", title="service_category", sort="-x"),
            tooltip=["service_category", "estimated_cost_avoidance"],
        )
        .properties(height=320, title="Estimated Cost Avoidance by Service Category")
    )
    with r2r:
        st.altair_chart(chart_r2r, width="stretch")

    st.divider()
    r3l, r3r = st.columns(2)
    monthly = (
        d.groupby("month", as_index=False)
        .agg(
            internal_count=("internal_count", "sum"),
            estimated_cost_avoidance=("estimated_cost_avoidance", "sum"),
        )
        .sort_values("month")
    )
    base_m = alt.Chart(monthly).encode(x=alt.X("month:N", sort=None, title="month"))
    line_ic = base_m.mark_line(point=True, color="#4fc3f7").encode(
        y=alt.Y("internal_count:Q", axis=alt.Axis(title="internal_count")),
        tooltip=["month", "internal_count", "estimated_cost_avoidance"],
    )
    line_ev = base_m.mark_line(point=True, color="#ed6622").encode(
        y=alt.Y(
            "estimated_cost_avoidance:Q",
            axis=alt.Axis(title="estimated_cost_avoidance", orient="right"),
        ),
        tooltip=["month", "internal_count", "estimated_cost_avoidance"],
    )
    chart_r3l = (
        (line_ic + line_ev)
        .resolve_scale(y="independent")
        .properties(height=320, title="Monthly Services vs Estimated Value")
    )
    with r3l:
        st.altair_chart(chart_r3l, width="stretch")

    spend_by_cat = d.groupby("service_category", as_index=False)["benchmark_total_spend"].sum()
    chart_r3r = (
        alt.Chart(spend_by_cat)
        .mark_bar(color="#9575cd", cornerRadiusTopRight=4)
        .encode(
            x=alt.X("service_category:N", title="service_category"),
            y=alt.Y("benchmark_total_spend:Q", title="benchmark_total_spend"),
            tooltip=["service_category", "benchmark_total_spend"],
        )
        .properties(height=320, title="Benchmark Spend by Service Category")
    )
    with r3r:
        st.altair_chart(chart_r3r, width="stretch")

    st.divider()
    r4l, r4r = st.columns(2)
    ev = d[d["service_category"] == kpi.EVENTS_CAT]
    funnel_df = pd.DataFrame(
        {
            "stage": ["reach", "registrations", "attendance", "followups"],
            "count": [
                int(ev["event_reach"].sum()),
                int(ev["event_registrations"].sum()),
                int(ev["event_attendance"].sum()),
                int(ev["qualified_followups"].sum()),
            ],
        }
    )
    chart_r4l = (
        alt.Chart(funnel_df)
        .mark_bar(color="#ba68c8")
        .encode(
            x=alt.X("stage:N", sort=None, title=None),
            y=alt.Y("count:Q", title="Count"),
            tooltip=["stage", "count"],
        )
        .properties(height=300, title="Event Engagement Funnel")
    )
    with r4l:
        st.altair_chart(chart_r4l, width="stretch")

    with r4r:
        st.dataframe(d[TABLE_COLS], width="stretch", hide_index=True)
        st.subheader("Executive takeaway")
        st.markdown(kpi.build_insight_markdown(d, kpis))
        st.caption(
            "Figures reflect dummy benchmark pairing for communication design, not operational accounting."
        )


if __name__ == "__main__":
    main()
