from __future__ import annotations

import sys
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.components.filters import (
    apply_common_filters,
    render_agency_filter,
    render_category_filter,
    render_naics_filter,
    render_psc_filter,
    render_year_filter,
)
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


def _apply_extended_filters(
    df: pd.DataFrame,
    *,
    years: list,
    categories: list,
    agencies: list,
    psc_codes: list,
    naics_codes: list,
) -> pd.DataFrame:
    filtered_df = apply_common_filters(
        df,
        years=years,
        categories=categories,
        agencies=agencies,
        year_column="fiscal_year",
        category_column="mapped_service_category",
        agency_column="awarding_agency",
    )

    if psc_codes and "psc_code" in filtered_df.columns:
        filtered_df = filtered_df[filtered_df["psc_code"].isin(psc_codes)]

    if naics_codes and "naics_code" in filtered_df.columns:
        filtered_df = filtered_df[filtered_df["naics_code"].isin(naics_codes)]

    return filtered_df.reset_index(drop=True)


def _build_chart_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    if "predicted_relevance_label" in df.columns:
        chart_df = (
            df["predicted_relevance_label"]
            .map({1: "Predicted Relevant", 0: "Predicted Non-Relevant"})
            .value_counts(dropna=False)
            .rename_axis("label")
            .reset_index(name="count")
        )
        return chart_df

    chart_df = pd.DataFrame(
        {
            "label": ["Filtered Benchmark Records"],
            "count": [len(df)],
        }
    )
    return chart_df


def _select_display_columns(df: pd.DataFrame) -> list[str]:
    preferred_columns = [
        "award_id",
        "description",
        "mapped_service_category",
        "awarding_agency",
        "psc_code",
        "naics_code",
        "award_amount",
        "fiscal_year",
        "relevance_score",
        "predicted_relevance_label",
    ]
    return [col for col in preferred_columns if col in df.columns]


def _to_csv_bytes(df: pd.DataFrame) -> bytes:
    return df.to_csv(index=False).encode("utf-8")


def main() -> None:
    render_page_header(
        "Benchmark Explorer",
        (
            "Interactively filter and inspect benchmark evidence so users can review "
            "comparable contracts and supporting records."
        ),
    )

    df, source_label = _choose_source_dataset()

    if df.empty:
        render_empty_data_message("Benchmark explorer data")
        return

    render_methodology_info_box(
        f"Current source: **{source_label}**. Use the sidebar filters to narrow the evidence set."
    )

    st.markdown(
        """
### How to use this page

- Use the filters on the left to narrow down comparable contracts  
- Review how many records remain after filtering  
- Inspect individual contracts in the table below  
- Use this page to validate and understand the evidence behind benchmark conclusions
"""
    )

    st.sidebar.subheader("Benchmark Explorer Filters")

    years = render_year_filter(df, column="fiscal_year", sidebar=True)
    categories = render_category_filter(
        df,
        column="mapped_service_category",
        sidebar=True,
    )
    agencies = render_agency_filter(
        df,
        column="awarding_agency",
        sidebar=True,
    )
    psc_codes = render_psc_filter(
        df,
        column="psc_code",
        sidebar=True,
    )
    naics_codes = render_naics_filter(
        df,
        column="naics_code",
        sidebar=True,
    )

    filtered_df = _apply_extended_filters(
        df,
        years=years,
        categories=categories,
        agencies=agencies,
        psc_codes=psc_codes,
        naics_codes=naics_codes,
    )

    st.markdown("### Active Filters")

    active_filters = []

    if years:
        active_filters.append(f"Year: {len(years)} selected")
    if categories:
        active_filters.append(f"Category: {len(categories)} selected")
    if agencies:
        active_filters.append(f"Agency: {len(agencies)} selected")
    if psc_codes:
        active_filters.append(f"PSC: {len(psc_codes)} selected")
    if naics_codes:
        active_filters.append(f"NAICS: {len(naics_codes)} selected")

    if active_filters:
        st.markdown(" | ".join(active_filters))
    else:
        st.markdown("No filters applied — showing full dataset.")

    st.subheader("Filtered Evidence Snapshot")

    total_rows = len(filtered_df)

    if "predicted_relevance_label" in filtered_df.columns:
        relevant_rows = int((filtered_df["predicted_relevance_label"] == 1).sum())
        relevant_pct = (relevant_rows / total_rows * 100) if total_rows else 0
    else:
        relevant_rows = None
        relevant_pct = None

    col1, col2, col3 = st.columns(3)

    with col1:
        render_metric_card("Rows in View", f"{total_rows:,}")
    with col2:
        render_metric_card("Relevant Records", f"{relevant_rows:,}" if relevant_rows is not None else "N/A")
    with col3:
        render_metric_card("Relevant Share", f"{relevant_pct:.1f}%" if relevant_pct is not None else "N/A")

    st.caption(f"Source dataset: {source_label}")

    if filtered_df.empty:
        st.warning("No records match the current filter combination.")
        return

    chart_df = _build_chart_dataframe(filtered_df)

    st.markdown(
        """
### Interpretation

This snapshot shows how your current filter selection impacts the benchmark dataset.

- A **higher relevant share** indicates a more focused and comparable subset  
- A **lower relevant share** may indicate broader filters or noisier matches  

Use filters iteratively to refine toward a more decision-useful evidence set.
"""
    )

    st.subheader("Benchmark Summary Chart")
    st.caption(
        "This chart shows how the filtered dataset is distributed between relevant and non-relevant contracts."
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

    st.subheader("Comparable Contract Inspection Table")
    st.caption(
        "Use this table to inspect the currently filtered benchmark records."
    )

    display_columns = _select_display_columns(filtered_df)
    if display_columns:
        st.dataframe(
            filtered_df[display_columns],
            width="stretch",
            hide_index=True,
        )
    else:
        st.dataframe(
            filtered_df,
            width="stretch",
            hide_index=True,
        )

    st.download_button(
        label="Download filtered results as CSV",
        data=_to_csv_bytes(filtered_df),
        file_name="benchmark_explorer_filtered_results.csv",
        mime="text/csv",
    )

    render_scope_warning_box(
        "This page is intended for evidence inspection and benchmark exploration. "
        "Filtered results support review and interpretation but do not by themselves "
        "constitute a formal cost claim."
    )


if __name__ == "__main__":
    main()

