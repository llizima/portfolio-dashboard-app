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


def _safe_pct(numerator: int, denominator: int) -> float:
    if denominator == 0:
        return 0.0
    return (numerator / denominator) * 100.0


def _build_executive_metrics(scored_df: pd.DataFrame) -> dict[str, float | int]:
    total_records = int(len(scored_df))

    if "predicted_relevance_label" in scored_df.columns:
        relevant_records = int((scored_df["predicted_relevance_label"] == 1).sum())
    else:
        relevant_records = 0

    non_relevant_records = total_records - relevant_records

    if "relevance_score" in scored_df.columns and not scored_df["relevance_score"].empty:
        average_score = float(scored_df["relevance_score"].mean())
    else:
        average_score = 0.0

    relevant_pct = _safe_pct(relevant_records, total_records)

    return {
        "total_records": total_records,
        "relevant_records": relevant_records,
        "non_relevant_records": non_relevant_records,
        "average_score": average_score,
        "relevant_pct": relevant_pct,
    }


def _render_kpi_cards(metrics: dict[str, float | int]) -> None:
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        render_metric_card("Benchmark Records", f"{int(metrics['total_records']):,}")
    with col2:
        render_metric_card("Predicted Relevant", f"{int(metrics['relevant_records']):,}")
    with col3:
        render_metric_card("Relevant Share", f"{metrics['relevant_pct']:.1f}%")
    with col4:
        render_metric_card("Avg Relevance Score", f"{metrics['average_score']:.3f}")


def _render_summary_chart(metrics: dict[str, float | int]) -> None:
    chart_df = pd.DataFrame(
        {
            "label": ["Predicted Relevant", "Predicted Non-Relevant"],
            "count": [
                int(metrics["relevant_records"]),
                int(metrics["non_relevant_records"]),
            ],
        }
    )

    st.subheader("Benchmark Relevance Summary")
    st.caption(
        "This chart shows how the full benchmark dataset is reduced to a smaller, more decision-useful subset of comparable contracts."
    )
    chart = (
        alt.Chart(chart_df)
        .mark_bar(color="#ed6622", cornerRadiusTopLeft=4, cornerRadiusTopRight=4)
        .encode(
            x=alt.X("label:N", axis=alt.Axis(labelColor="#8a8fa8", titleColor="#8a8fa8", labelAngle=0), title=None),
            y=alt.Y("count:Q", axis=alt.Axis(labelColor="#8a8fa8", titleColor="#8a8fa8", gridColor="#2a2d3a"), title="Records"),
            tooltip=["label:N", "count:Q"],
        )
        .properties(background="#1a1d27", padding={"left": 10, "right": 10, "top": 10, "bottom": 10})
        .configure_view(strokeWidth=0)
        .configure_axis(domainColor="#3a3d4a")
    )
    st.altair_chart(chart, width="stretch")


def _render_value_statement(metrics: dict[str, float | int]) -> None:
    total_records = int(metrics["total_records"])
    relevant_records = int(metrics["relevant_records"])
    relevant_pct = float(metrics["relevant_pct"])

    st.subheader("Value Statement")

    st.markdown(
        f"""
        Out of **{total_records:,}** benchmark records currently available for executive review,
        **{relevant_records:,}** were scored as potentially relevant to the SOFWERX value story.
        That means approximately **{relevant_pct:.1f}%** of the current benchmark set is being carried
        forward as meaningful external cost context rather than background noise.
        """
    )

    st.markdown(
        """
        This gives leadership a structured starting point for understanding what comparable external
        work appears to cost in the broader market and how SOFWERX-delivered capability may compare
        against that external context.
        """
    )


def _render_what_this_means_box(metrics: dict[str, float | int]) -> None:
    relevant_records = int(metrics["relevant_records"])
    total_records = int(metrics["total_records"])
    relevant_pct = float(metrics["relevant_pct"])

    render_methodology_info_box(
        (
            f"What this means: {relevant_records:,} out of {total_records:,} benchmark records "
            f"({relevant_pct:.1f}%) are considered sufficiently comparable to support external benchmarking. "
            "This reflects a structured filtering and scoring process designed to isolate meaningful external cost signals. "
            "This is not a claim of savings or ROI, but a defensible narrowing of a broad market dataset into a more decision-useful benchmark reference."
        )
    )


def main() -> None:
    render_page_header(
        "Executive Overview",
        (
            "Provide a fast, leadership-friendly summary of benchmark coverage, scored relevance, "
            "and the practical value of the current benchmark dataset."
        ),
    )

    scored_df = load_scored_dataset()

    if scored_df.empty:
        comparable_df = load_comparable_contracts()

        if comparable_df.empty:
            render_empty_data_message("Executive overview data")
            return

        st.warning(
            "Comparable contracts data is available, but the scored dataset is not available yet. "
            "Run the scoring pipeline to unlock KPI cards and executive relevance summaries."
        )

        st.subheader("Available Benchmark Input")
        col1, col2, col3 = st.columns(3)
        with col1:
            render_metric_card("Comparable Records Available", f"{len(comparable_df):,}")

        render_scope_warning_box(
            "This page is designed to summarize scored benchmark outputs. Until scoring is available, "
            "executive interpretation remains limited."
        )
        return

    required_columns = {"relevance_score", "predicted_relevance_label"}
    missing_columns = required_columns - set(scored_df.columns)

    if missing_columns:
        st.error(
            "The scored dataset is missing required executive-overview columns: "
            + ", ".join(sorted(missing_columns))
        )
        return

    metrics = _build_executive_metrics(scored_df)

    # -----------------------------------------------------------------
    # Executive Takeaway (NEW)
    # -----------------------------------------------------------------
    total_records = int(metrics["total_records"])
    relevant_records = int(metrics["relevant_records"])
    relevant_pct = float(metrics["relevant_pct"])

    st.markdown(
        f"""
### Executive Takeaway

The current benchmark dataset contains **{total_records:,} contracts**, of which  
**{relevant_records:,} ({relevant_pct:.1f}%)** are considered sufficiently comparable  
to support external cost benchmarking.

This indicates a **high-quality, decision-useful dataset**, where the majority of records  
contribute meaningful external cost context rather than noise.
"""
    )

    _render_kpi_cards(metrics)

    st.markdown(
        """
**How to interpret these metrics**

- A **high relevant share** means the filtering and ML pipeline are effectively isolating comparable contracts  
- The **average relevance score** provides a signal of confidence across the dataset  
- Together, these indicate whether the benchmark dataset is strong enough to support decision-making
"""
    )

    st.markdown("---")
    _render_value_statement(metrics)
    st.markdown("---")
    _render_summary_chart(metrics)
    st.markdown("---")
    _render_what_this_means_box(metrics)

    render_scope_warning_box(
        "This page provides benchmark-derived context for leadership. It should be interpreted as "
        "external cost comparison support, not as a formal savings claim or audited ROI calculation."
    )


if __name__ == "__main__":
    main()

