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
from src.data.demo.exec_benchmark_bridge import build_exec_benchmark_bridge  # noqa: E402

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


def _build_rapid_prototyping_audit_markdown(d: pd.DataFrame) -> str:
    rp = d[d["service_category"] == "Rapid Prototyping"].copy()
    if rp.empty:
        return "Rapid Prototyping is not present in the current filtered slice."

    row_count = int(len(rp))
    total_internal_count = int(rp["internal_count"].sum())
    total_internal_cost = float(rp["internal_total_cost"].sum())
    total_benchmark_equivalent_cost = float(rp["benchmark_equivalent_cost"].sum())
    total_estimated_cost_avoidance = float(rp["estimated_cost_avoidance"].sum())
    mean_avoidance = float(rp["estimated_cost_avoidance"].mean())
    median_avoidance = float(rp["estimated_cost_avoidance"].median())

    benchmark_units = sorted(
        rp["benchmark_per_unit"].dropna().astype(float).unique().tolist()
    )
    benchmark_per_unit_display = (
        _exec_dummy_kpi.fmt_currency(benchmark_units[0])
        if len(benchmark_units) == 1
        else ", ".join(_exec_dummy_kpi.fmt_currency(v) for v in benchmark_units[:3])
        + (" ..." if len(benchmark_units) > 3 else "")
    )

    other = d[d["service_category"] != "Rapid Prototyping"].copy()
    rp_avg_bench_unit = float(rp["benchmark_per_unit"].mean())
    other_avg_bench_unit = float(other["benchmark_per_unit"].mean()) if not other.empty else float("nan")
    avg_internal_count_rp = float(rp["internal_count"].mean())
    avg_internal_count_other = float(other["internal_count"].mean()) if not other.empty else float("nan")

    reasons: list[str] = []
    if len(benchmark_units) > 1:
        reasons.append("possible inconsistency: more than one benchmark_per_unit value appears in-slice")
    if total_estimated_cost_avoidance < 0:
        reasons.append("possible inconsistency: total estimated cost avoidance is negative")
    if row_count >= max(3, int(len(d) * 0.4)):
        reasons.append("many rows")
    if other_avg_bench_unit == other_avg_bench_unit and rp_avg_bench_unit > (other_avg_bench_unit * 1.5):
        reasons.append("high benchmark_per_unit")
    if avg_internal_count_other == avg_internal_count_other and avg_internal_count_rp > (avg_internal_count_other * 1.5):
        reasons.append("high internal_count")
    if not reasons:
        reasons.append("mixed drivers with no single dominant outlier signal")

    if "possible inconsistency: more than one benchmark_per_unit value appears in-slice" in reasons:
        interpretation = "Diagnostic read: this result may require further scrutiny before drawing conclusions."
    elif "possible inconsistency: total estimated cost avoidance is negative" in reasons:
        interpretation = "Diagnostic read: this result may require further scrutiny before drawing conclusions."
    elif "high benchmark_per_unit" in reasons and "high internal_count" not in reasons:
        interpretation = "Diagnostic read: this result appears primarily benchmark-rate-driven."
    elif "high internal_count" in reasons and "high benchmark_per_unit" not in reasons:
        interpretation = "Diagnostic read: this result appears primarily volume-driven."
    elif "many rows" in reasons and "high benchmark_per_unit" not in reasons:
        interpretation = "Diagnostic read: this result appears primarily scale-driven."
    else:
        interpretation = "Diagnostic read: this result appears to reflect mixed drivers."

    return (
        f"{interpretation}\n\n"
        f"- Row count: {row_count:,}\n"
        f"- Total internal_count: {total_internal_count:,}\n"
        f"- Total internal_total_cost: {_exec_dummy_kpi.fmt_currency(total_internal_cost)}\n"
        f"- Benchmark_per_unit used: {benchmark_per_unit_display}\n"
        f"- Total benchmark_equivalent_cost: {_exec_dummy_kpi.fmt_currency(total_benchmark_equivalent_cost)}\n"
        f"- Total estimated_cost_avoidance: {_exec_dummy_kpi.fmt_currency(total_estimated_cost_avoidance)}\n"
        f"- Mean estimated_cost_avoidance per row: {_exec_dummy_kpi.fmt_currency(mean_avoidance)}\n"
        f"- Median estimated_cost_avoidance per row: {_exec_dummy_kpi.fmt_currency(median_avoidance)}\n"
        f"- Likely primary driver(s): {', '.join(reasons)}."
    )


def _render_dummy_executive_dashboard_section() -> None:
    """Locked-layout dummy executive view (exec_dummy_data + exec_dummy_kpis; Altair)."""
    st.subheader("Executive value view (illustrative dummy data)")
    st.caption(
        "Illustrative benchmark pairing for leadership layout review; not operational accounting."
    )
    st.caption(
        "Methodology: Internal activity and cost values are simulated for portfolio modeling; "
        "external benchmark estimates are derived from real USAspending-based comparable contracts; "
        "estimated cost avoidance is computed dynamically as benchmark_equivalent_cost minus internal_total_cost."
    )

    df = exec_dummy_data.df.copy()
    months = _dummy_month_range_ui(df)
    cats = sorted(df["service_category"].unique().tolist())
    sel_cat = st.multiselect("Service categories", cats, default=cats, key="exec_dummy_categories")

    d = _exec_dummy_kpi.apply_filters(df, months=months, categories=sel_cat if sel_cat else None)
    bridge_df = build_exec_benchmark_bridge(d)
    d = d.merge(bridge_df, on="service_category", how="left")
    if d["benchmark_per_unit"].isna().any():
        missing_categories = sorted(
            d.loc[d["benchmark_per_unit"].isna(), "service_category"].dropna().astype(str).unique().tolist()
        )
        st.warning(
            "Missing benchmark_per_unit for service categories: "
            + ", ".join(missing_categories)
            + ". Dynamic benchmark-equivalent values cannot be computed for this slice."
        )
        return
    d["benchmark_equivalent_cost"] = d["internal_count"] * d["benchmark_per_unit"]
    d["estimated_cost_avoidance"] = d["benchmark_equivalent_cost"] - d["internal_total_cost"]
    row_identity_ok = (
        (
            d["estimated_cost_avoidance"]
            - (d["benchmark_equivalent_cost"] - d["internal_total_cost"])
        )
        .abs()
        .le(1e-6)
    )
    if not bool(row_identity_ok.all()):
        failed_rows = int((~row_identity_ok).sum())
        st.warning(
            "Dynamic avoidance verification check failed for "
            f"{failed_rows} row(s): estimated_cost_avoidance != "
            "(benchmark_equivalent_cost - internal_total_cost) within tolerance."
        )
    kpis = _exec_dummy_kpi.compute_executive_kpis(d)

    if kpis is None:
        st.info("No data in view for the current dummy filters.")
        return

    with st.expander("Calculation debug summary", expanded=False):
        st.markdown(
            f"- Total internal cost: {_exec_dummy_kpi.fmt_currency(float(d['internal_total_cost'].sum()))}\n"
            f"- Total benchmark equivalent cost: {_exec_dummy_kpi.fmt_currency(float(d['benchmark_equivalent_cost'].sum()))}\n"
            f"- Total estimated cost avoidance: {_exec_dummy_kpi.fmt_currency(float(d['estimated_cost_avoidance'].sum()))}\n"
            f"- Row count: {len(d):,}\n"
            f"- Service categories present: {', '.join(sorted(d['service_category'].dropna().astype(str).unique().tolist()))}"
        )
    with st.expander("Rapid Prototyping audit", expanded=False):
        st.markdown(_build_rapid_prototyping_audit_markdown(d))

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

    opp_vs_spend = (
        d.groupby("service_category", as_index=False)
        .agg(
            benchmark_total_spend=("benchmark_total_spend", "sum"),
            estimated_cost_avoidance=("estimated_cost_avoidance", "sum"),
        )
    )
    points = alt.Chart(opp_vs_spend).mark_circle(color="#9575cd", size=140, opacity=0.85).encode(
        x=alt.X("benchmark_total_spend:Q", title="benchmark_total_spend"),
        y=alt.Y("estimated_cost_avoidance:Q", title="estimated_cost_avoidance"),
        tooltip=["service_category", "benchmark_total_spend", "estimated_cost_avoidance"],
    )
    labels = alt.Chart(opp_vs_spend).mark_text(
        align="left",
        baseline="middle",
        dx=8,
        dy=-8,
        fontSize=11,
        color="#37474f",
    ).encode(
        x=alt.X("benchmark_total_spend:Q"),
        y=alt.Y("estimated_cost_avoidance:Q"),
        text=alt.Text("service_category:N"),
    )
    chart_r3r = (points + labels).properties(
        height=320, title="Strategic Opportunity by Service Category"
    )
    with r3r:
        st.caption(
            "Categories farther toward the upper-right combine larger benchmark markets with higher estimated value opportunity."
        )
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
