"""Locked KPI math for exec dummy data. Spec: KPI_FORMULAS_LOCKED.md."""

from __future__ import annotations

from dataclasses import dataclass
import math

import pandas as pd

EVENTS_CAT = "Events & Engagement"
TOL = 0.02


@dataclass(frozen=True)
class ExecutiveKPIs:
    total_internal_cost: float
    total_benchmark_equivalent_cost: float
    total_cost_avoidance: float
    average_efficiency_percent: float
    total_services_delivered: int
    highest_value_service_category: str


def apply_filters(
    df: pd.DataFrame,
    months: list[str] | None,
    categories: list[str] | None,
) -> pd.DataFrame:
    out = df.copy()
    if months is not None and len(months) > 0:
        out = out[out["month"].isin(months)]
    if categories is not None and len(categories) > 0:
        out = out[out["service_category"].isin(categories)]
    return out.reset_index(drop=True)


def compute_executive_kpis(df: pd.DataFrame) -> ExecutiveKPIs | None:
    if df.empty:
        return None
    total_internal_cost = float(df["internal_total_cost"].sum())
    total_benchmark_equivalent_cost = float(df["benchmark_equivalent_cost"].sum())
    total_cost_avoidance = float(df["estimated_cost_avoidance"].sum())
    denom = float(df["internal_total_cost"].sum())
    if denom != 0.0:
        average_efficiency_percent = float(
            (df["efficiency_percent"] * df["internal_total_cost"]).sum() / df["internal_total_cost"].sum()
        )
    else:
        average_efficiency_percent = float("nan")
    total_services_delivered = int(df["internal_count"].sum())
    highest_value_service_category = str(
        df.groupby("service_category")["estimated_cost_avoidance"].sum().idxmax()
    )
    return ExecutiveKPIs(
        total_internal_cost=total_internal_cost,
        total_benchmark_equivalent_cost=total_benchmark_equivalent_cost,
        total_cost_avoidance=total_cost_avoidance,
        average_efficiency_percent=average_efficiency_percent,
        total_services_delivered=total_services_delivered,
        highest_value_service_category=highest_value_service_category,
    )


def avoidance_identity_holds(df: pd.DataFrame) -> bool:
    if df.empty:
        return True
    ti = float(df["internal_total_cost"].sum())
    tb = float(df["benchmark_equivalent_cost"].sum())
    ta = float(df["estimated_cost_avoidance"].sum())
    return abs(ta - (tb - ti)) < TOL


# Backward-compatible name for callers
compute_headline_kpis = compute_executive_kpis


@dataclass(frozen=True)
class EventFunnelRates:
    registration_rate: float | None
    attendance_rate: float | None
    qualified_rate: float | None


def compute_event_funnel_rates(d: pd.DataFrame) -> tuple[pd.Series, EventFunnelRates]:
    ev = d[d["service_category"] == EVENTS_CAT]
    reach = int(ev["event_reach"].sum())
    reg = int(ev["event_registrations"].sum())
    att = int(ev["event_attendance"].sum())
    qf = int(ev["qualified_followups"].sum())
    totals = pd.Series({"Reach": reach, "Registrations": reg, "Attendance": att, "Qualified follow-ups": qf})
    if reach == 0:
        return totals, EventFunnelRates(None, None, None)
    rr = 100.0 * reg / reach
    ar = 100.0 * att / reg if reg > 0 else None
    qr = 100.0 * qf / att if att > 0 else None
    return totals, EventFunnelRates(rr, ar, qr)


def fmt_currency(x: float) -> str:
    return f"${x:,.0f}"


def fmt_pct_one(x: float | None) -> str:
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return "n/a"
    return f"{x:.1f}%"


def build_insight_markdown(d: pd.DataFrame, kpis: ExecutiveKPIs | None) -> str:
    """Exactly four executive bullets; see INSIGHT_PANEL_CONTROLLED_TEXT.md."""
    if d.empty or kpis is None:
        return (
            "- Filtered frame is empty: efficiency, category mix, and trend bullets have no inputs.\n"
            "- Expand the month span or category list until at least one row is in view.\n"
            "- No avoidance leader, growth read, or efficiency gap to cite until data returns.\n"
            "- Include **Events & Engagement** rows if the opportunity bullet should reference funnel conversion."
        )

    tb = kpis.total_benchmark_equivalent_cost
    ti = kpis.total_internal_cost
    gap_pct = 100.0 * (1.0 - ti / tb) if tb > 0 else float("nan")
    eff_line = (
        f"- **Cost efficiency:** Spend-weighted efficiency is {fmt_pct_one(kpis.average_efficiency_percent)}; "
        f"internal totals sit {fmt_pct_one(gap_pct)} under benchmark-equivalent spend on the same in-view volume."
        if not math.isnan(gap_pct)
        else f"- **Cost efficiency:** Spend-weighted efficiency is {fmt_pct_one(kpis.average_efficiency_percent)}; "
        "benchmark-equivalent total is zero in-view, so portfolio gap % is undefined."
    )

    by_cat = d.groupby("service_category")["estimated_cost_avoidance"].sum().sort_values(ascending=False)
    top_cat = str(by_cat.index[0])
    top_amt = float(by_cat.iloc[0])
    tot_av = float(by_cat.sum())
    top_share = 100.0 * top_amt / tot_av if tot_av > 0 else 0.0
    if len(by_cat) > 1:
        run_cat = str(by_cat.index[1])
        run_amt = float(by_cat.iloc[1])
        hv_line = (
            f"- **High-value categories:** **{top_cat}** leads avoidance at {fmt_currency(top_amt)} "
            f"({top_share:.0f}% of in-view category avoidance); **{run_cat}** is second at {fmt_currency(run_amt)}."
        )
    else:
        hv_line = (
            f"- **High-value categories:** **{top_cat}** is the only category in view at "
            f"{fmt_currency(top_amt)} cumulative avoidance."
        )

    mo = sorted(d["month"].unique().tolist())
    series = d.groupby("month")["estimated_cost_avoidance"].sum().reindex(mo)
    if len(mo) >= 2:
        a0 = float(series.iloc[0])
        a1 = float(series.iloc[-1])
        m0, m1 = mo[0], mo[-1]
        if a0 > 0:
            chg = 100.0 * (a1 - a0) / a0
            direction = "up" if a1 > a0 else "down" if a1 < a0 else "flat"
            gr_line = (
                f"- **Growth trend:** Estimated avoidance runs {fmt_currency(a0)} in **{m0}** to "
                f"{fmt_currency(a1)} in **{m1}** (~{chg:+.0f}% {direction} across the selected window)."
            )
        else:
            gr_line = (
                f"- **Growth trend:** Estimated avoidance starts at {fmt_currency(a0)} in **{m0}** and "
                f"reaches {fmt_currency(a1)} in **{m1}**; early-month baseline is zero in this slice."
            )
    else:
        gr_line = (
            "- **Growth trend:** Single month in filter; extend the month span to judge direction on "
            "avoidance or internal count."
        )

    ev = d[d["service_category"] == EVENTS_CAT]
    reach = int(ev["event_reach"].sum())
    reg = int(ev["event_registrations"].sum())
    if reach > 0 and len(ev) > 0:
        rr = 100.0 * reg / reach
        op_line = (
            f"- **Opportunity:** Events reach-to-registration yield is **{rr:.1f}%**; conversion lift "
            "here compounds attendance and qualified follow-ups without adding modeled internal cost rows."
        )
    else:
        mean_eff = d.groupby("service_category")["efficiency_percent"].mean().sort_values()
        weak = str(mean_eff.index[0])
        wval = float(mean_eff.iloc[0])
        op_line = (
            f"- **Opportunity:** **{weak}** posts the lowest mean line-item efficiency ({fmt_pct_one(wval)}) "
            "in-view; scrutinize benchmark pairing or delivery mix there before scaling volume."
        )

    return "\n".join([eff_line, hv_line, gr_line, op_line])
