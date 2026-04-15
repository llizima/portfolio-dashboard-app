from __future__ import annotations

import sys
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

_EXEC_DUMMY_DATA_DIR = PROJECT_ROOT / "src" / "data" / "demo"
if str(_EXEC_DUMMY_DATA_DIR) not in sys.path:
    sys.path.insert(0, str(_EXEC_DUMMY_DATA_DIR))

import exec_dummy_data  # noqa: E402
import exec_dummy_kpis as _exec_dummy_kpi  # noqa: E402

from app.components.layout_helpers import (
    render_data_disclaimer_box,
    render_page_header,
    render_scope_warning_box,
)

_DUMMY_TABLE_COLS = [
    "service_category",
    "internal_count",
    "internal_avg_cost",
    "benchmark_avg_cost",
    "estimated_cost_avoidance",
    "efficiency_percent",
]


def _render_executive_overview_paragraphs() -> None:
    """Two static overview paragraphs (portfolio framing) before the dummy dashboard."""
    st.markdown(
        """
        This page leads with an **illustrative portfolio dashboard** built from synthetic internal and
        benchmark rows so reviewers can validate executive KPIs, category value concentration, timing,
        and event-funnel shape before production feeds replace the dummy slice.
        """
    )
    st.markdown(
        """
        This gives leadership a structured starting point for understanding what comparable external
        work appears to cost in the broader market and how Applied Government Analytics (AGA)-delivered
        capability may compare against that external context.
        """
    )


def _dummy_month_range_ui(df: pd.DataFrame) -> list[str]:
    months = sorted(df["month"].unique().tolist())
    c1, c2 = st.columns(2)
    with c1:
        lo = st.selectbox("Month from", months, index=0, key="exec_dummy_month_lo")
    with c2:
        hi = st.selectbox("Month through", months, index=len(months) - 1, key="exec_dummy_month_hi")
    if months.index(lo) > months.index(hi):
        lo, hi = hi, lo
    i0, i1 = months.index(lo), months.index(hi)
    return months[i0 : i1 + 1]


def _render_dummy_executive_dashboard_section() -> None:
    """Locked-layout dummy executive view (exec_dummy_data + exec_dummy_kpis; Altair)."""
    st.subheader("Executive value view (illustrative dummy data)")
    st.caption(
        "Illustrative benchmark pairing for leadership layout review; not operational accounting."
    )

    df = exec_dummy_data.df.copy()
    months = _dummy_month_range_ui(df)
    cats = sorted(df["service_category"].unique().tolist())
    sel_cat = st.multiselect("Service categories", cats, default=cats, key="exec_dummy_categories")

    d = _exec_dummy_kpi.apply_filters(df, months=months, categories=sel_cat if sel_cat else None)
    kpis = _exec_dummy_kpi.compute_executive_kpis(d)

    if kpis is None:
        st.info("No data in view for the current dummy filters.")
        return

    k1, k2, k3, k4, k5 = st.columns(5)
    with k1:
        st.metric("Total Internal Cost", _exec_dummy_kpi.fmt_currency(kpis.total_internal_cost))
    with k2:
        st.metric(
            "Total Benchmark Equivalent Cost",
            _exec_dummy_kpi.fmt_currency(kpis.total_benchmark_equivalent_cost),
        )
    with k3:
        st.metric("Total Cost Avoidance", _exec_dummy_kpi.fmt_currency(kpis.total_cost_avoidance))
    with k4:
        st.metric("Average Efficiency %", _exec_dummy_kpi.fmt_pct_one(kpis.average_efficiency_percent))
    with k5:
        st.metric("Total Services Delivered", f"{kpis.total_services_delivered:,}")

    if not _exec_dummy_kpi.avoidance_identity_holds(d):
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
            x=alt.X(
                "service_category:N",
                title="service_category",
                axis=alt.Axis(labelAngle=-35),
            ),
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
    st.caption("Blue = Services Delivered (count) | Orange = Estimated Value ($)")
    base_m = alt.Chart(monthly).encode(x=alt.X("month:N", sort=None, title="month"))
    line_ic = base_m.mark_line(point=True, color="#4fc3f7").encode(
        y=alt.Y("internal_count:Q", axis=alt.Axis(title="Services Delivered")),
        tooltip=["month", "internal_count", "estimated_cost_avoidance"],
    )
    line_ev = base_m.mark_line(point=True, color="#ed6622").encode(
        y=alt.Y(
            "estimated_cost_avoidance:Q",
            axis=alt.Axis(title="Estimated Value ($)", orient="right"),
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
            x=alt.X(
                "service_category:N",
                title="service_category",
                axis=alt.Axis(labelAngle=-35),
            ),
            y=alt.Y("benchmark_total_spend:Q", title="benchmark_total_spend"),
            tooltip=["service_category", "benchmark_total_spend"],
        )
        .properties(height=320, title="Benchmark Spend by Service Category")
    )
    with r3r:
        st.altair_chart(chart_r3r, width="stretch")

    st.divider()
    r4l, r4r = st.columns(2)
    ev = d[d["service_category"] == _exec_dummy_kpi.EVENTS_CAT]
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
        st.dataframe(d[_DUMMY_TABLE_COLS], width="stretch", hide_index=True)
        st.subheader("Executive takeaway")
        st.markdown(_exec_dummy_kpi.build_insight_markdown(d, kpis))
        st.caption(
            "Figures reflect dummy benchmark pairing for communication design, not operational accounting."
        )


def main() -> None:
    render_page_header(
        "Executive Overview",
        (
            "Portfolio view of simulated internal delivery versus benchmark reference costs, "
            "category-level value, timing, and engagement funnel signals for leadership review."
        ),
    )

    render_data_disclaimer_box()

    _render_executive_overview_paragraphs()

    _render_dummy_executive_dashboard_section()

    render_scope_warning_box(
        "This page provides illustrative portfolio context for leadership. It should be interpreted as "
        "dummy benchmarking for layout and narrative testing, not as a formal savings claim or audited ROI calculation."
    )


if __name__ == "__main__":
    main()
