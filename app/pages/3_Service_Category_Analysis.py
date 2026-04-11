from __future__ import annotations

import sys
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.components.layout_helpers import (
    render_empty_data_message,
    render_methodology_info_box,
    render_metric_card,
    render_page_header,
    render_scope_warning_box,
)
from app.components.loaders import (
    load_comparable_contracts,
    load_scored_dataset,
)


def _choose_source_dataset() -> tuple[pd.DataFrame, str]:
    scored_df = load_scored_dataset()
    if not scored_df.empty:
        return scored_df.copy(), "scored benchmark dataset"

    comparable_df = load_comparable_contracts()
    if not comparable_df.empty:
        return comparable_df.copy(), "comparable contracts dataset"

    return pd.DataFrame(), ""


def _prepare_category_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    working_df = df.copy()

    if "mapped_service_category" not in working_df.columns:
        return pd.DataFrame()

    working_df["mapped_service_category"] = (
        working_df["mapped_service_category"]
        .fillna("unmapped")
        .astype(str)
        .str.strip()
        .str.lower()
    )

    working_df.loc[
        working_df["mapped_service_category"].isin({"", "none", "nan"}),
        "mapped_service_category"
    ] = "unmapped"

    if "relevance_score" not in working_df.columns:
        working_df["relevance_score"] = pd.NA

    if "award_amount" not in working_df.columns:
        working_df["award_amount"] = pd.NA

    return working_df


def _build_category_summary(df: pd.DataFrame) -> pd.DataFrame:
    grouped = (
        df.groupby("mapped_service_category", dropna=False)
        .agg(
            record_count=("mapped_service_category", "size"),
            average_relevance_score=("relevance_score", "mean"),
            average_award_amount=("award_amount", "mean"),
        )
        .reset_index()
        .sort_values("record_count", ascending=False)
        .reset_index(drop=True)
    )

    grouped["share_of_records_pct"] = (
        grouped["record_count"] / grouped["record_count"].sum() * 100.0
    )

    return grouped


def _format_category_summary_for_display(summary_df: pd.DataFrame) -> pd.DataFrame:
    display_df = summary_df.copy()

    if "average_relevance_score" in display_df.columns:
        display_df["average_relevance_score"] = display_df[
            "average_relevance_score"
        ].round(3)

    if "average_award_amount" in display_df.columns:
        display_df["average_award_amount"] = display_df[
            "average_award_amount"
        ].round(2)

    if "share_of_records_pct" in display_df.columns:
        display_df["share_of_records_pct"] = display_df[
            "share_of_records_pct"
        ].round(1)

    if "mapped_service_category" in display_df.columns:
        display_df["mapped_service_category"] = (
            display_df["mapped_service_category"]
            .astype(str)
            .str.replace("_", " ", regex=False)
            .str.title()
        )

    display_df = display_df.rename(
        columns={
            "mapped_service_category": "service_category",
            "record_count": "record_count",
            "average_relevance_score": "avg_relevance_score",
            "average_award_amount": "avg_award_amount",
            "share_of_records_pct": "share_of_records_pct",
        }
    )

    return display_df


def _render_topline_metrics(summary_df: pd.DataFrame) -> None:
    total_categories = int(len(summary_df))
    total_records = int(summary_df["record_count"].sum())

    if total_categories > 0:
        top_category = str(summary_df.iloc[0]["mapped_service_category"]).replace("_", " ").title()
        top_category_count = int(summary_df.iloc[0]["record_count"])
    else:
        top_category = "N/A"
        top_category_count = 0

    col1, col2, col3 = st.columns(3)
    with col1:
        render_metric_card("Categories in View", f"{total_categories:,}")
    with col2:
        render_metric_card("Benchmark Records", f"{total_records:,}")
    with col3:
        render_metric_card("Largest Category", f"{top_category} ({top_category_count:,})")


def _render_category_composition_chart(summary_df: pd.DataFrame) -> None:
    chart_df = summary_df[["mapped_service_category", "record_count"]].copy()
    chart_df["category_display"] = (
        chart_df["mapped_service_category"]
        .astype(str)
        .str.replace("_", " ", regex=False)
        .str.title()
    )

    st.subheader("Category Composition View")
    st.caption(
        "This chart shows how benchmark evidence is distributed across service categories. "
        "A strongly dominant category indicates where current comparison coverage is most concentrated."
    )

    chart = (
        alt.Chart(chart_df)
        .mark_bar(color="#ed6622", cornerRadiusTopLeft=4, cornerRadiusTopRight=4)
        .encode(
            x=alt.X("category_display:N", axis=alt.Axis(labelColor="#8a8fa8", titleColor="#8a8fa8", labelAngle=-30), title=None),
            y=alt.Y("record_count:Q", axis=alt.Axis(labelColor="#8a8fa8", titleColor="#8a8fa8", gridColor="#2a2d3a"), title="Records"),
            tooltip=["category_display:N", "record_count:Q"],
        )
        .properties(background="#1a1d27", padding={"left": 10, "right": 10, "top": 10, "bottom": 10})
        .configure_view(strokeWidth=0)
        .configure_axis(domainColor="#3a3d4a")
    )
    st.altair_chart(chart, width="stretch")


def _render_explanatory_notes(summary_df: pd.DataFrame) -> None:
    if summary_df.empty:
        render_methodology_info_box(
            "No category summary is available yet."
        )
        return

    top_category = str(summary_df.iloc[0]["mapped_service_category"])
    top_share = float(summary_df.iloc[0]["share_of_records_pct"])

    render_methodology_info_box(
        (
            f"Interpretation note: the current benchmark dataset is most concentrated in "
            f"**{top_category.replace('_', ' ').title()}**, which represents approximately "
            f"**{top_share:.1f}%** of available records. This indicates where the current "
            "external comparison evidence is strongest. It does not mean that this category is "
            "more valuable than others, only that the benchmark dataset currently contains more "
            "comparable records in that area."
        )
    )

    render_scope_warning_box(
        "Category counts and average scores support interpretation, prioritization, and review. "
        "They should not be treated as standalone proof of savings, impact, or category superiority "
        "without additional business context."
    )


def main() -> None:
    render_page_header(
        "Service Category Analysis",
        (
            "Show how benchmark evidence is distributed across service categories so users can "
            "see where external comparison coverage appears strongest."
        ),
    )

    df, source_label = _choose_source_dataset()

    if df.empty:
        render_empty_data_message("Service category analysis data")
        return

    render_methodology_info_box(
        f"Current source: **{source_label}**. This page summarizes benchmark evidence by mapped service category."
    )

    prepared_df = _prepare_category_dataframe(df)
    if prepared_df.empty:
        st.error(
            "The selected dataset does not contain a 'mapped_service_category' column, "
            "so category analysis cannot be displayed."
        )
        return

    summary_df = _build_category_summary(prepared_df)
    display_df = _format_category_summary_for_display(summary_df)

    top_category = str(summary_df.iloc[0]["mapped_service_category"]) if not summary_df.empty else "N/A"
    top_share = float(summary_df.iloc[0]["share_of_records_pct"]) if not summary_df.empty else 0.0

    st.markdown(
        f"""
### Category Takeaway

The current benchmark dataset is most heavily concentrated in **{top_category.replace('_', ' ').title()}**,  
which accounts for approximately **{top_share:.1f}%** of all currently available benchmark records.

This helps show where external comparison coverage is strongest, while also highlighting where benchmark
coverage may be thinner in other service areas.
"""
    )

    _render_topline_metrics(summary_df)
    st.markdown("---")

    _render_category_composition_chart(summary_df)
    st.markdown("---")

    st.subheader("Per-Category Statistics")
    st.caption(
        "This table summarizes record counts, relative share, and available average metrics by category."
    )
    st.dataframe(display_df, width="stretch", hide_index=True)
    st.markdown("---")

    _render_explanatory_notes(summary_df)


if __name__ == "__main__":
    main()

