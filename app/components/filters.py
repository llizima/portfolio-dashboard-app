from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st


def _safe_sorted_unique(df: pd.DataFrame, column: str) -> list[Any]:
    """
    Return sorted unique non-null values for a column.
    """
    if column not in df.columns or df.empty:
        return []

    values = df[column].dropna().tolist()
    unique_values = sorted(set(values))
    return unique_values


def render_year_filter(
    df: pd.DataFrame,
    column: str = "fiscal_year",
    *,
    sidebar: bool = True,
) -> list[Any]:
    """
    Render a reusable year multiselect filter.
    """
    options = _safe_sorted_unique(df, column)

    target = st.sidebar if sidebar else st
    return target.multiselect(
        "Year",
        options=options,
        default=[],
        help="Optional year filter. Leave blank to include all years.",
    )


def render_category_filter(
    df: pd.DataFrame,
    column: str = "mapped_service_category",
    *,
    sidebar: bool = True,
) -> list[Any]:
    """
    Render a reusable service category multiselect filter.
    """
    options = _safe_sorted_unique(df, column)

    target = st.sidebar if sidebar else st
    return target.multiselect(
        "Service Category",
        options=options,
        default=[],
        help=(
            "Optional category filter. Leave blank to include all categories."
        ),
    )


def render_agency_filter(
    df: pd.DataFrame,
    column: str = "awarding_agency",
    *,
    sidebar: bool = True,
) -> list[Any]:
    """
    Render a reusable agency multiselect filter.
    """
    options = _safe_sorted_unique(df, column)

    target = st.sidebar if sidebar else st
    return target.multiselect(
        "Awarding Agency",
        options=options,
        default=[],
        help="Optional agency filter. Leave blank to include all agencies.",
    )


def apply_common_filters(
    df: pd.DataFrame,
    *,
    years: list[Any] | None = None,
    categories: list[Any] | None = None,
    agencies: list[Any] | None = None,
    year_column: str = "fiscal_year",
    category_column: str = "mapped_service_category",
    agency_column: str = "awarding_agency",
) -> pd.DataFrame:
    """
    Apply shared filter selections to a dataframe.
    Blank selections mean no filtering on that dimension.
    """
    filtered_df = df.copy()

    if years and year_column in filtered_df.columns:
        filtered_df = filtered_df[filtered_df[year_column].isin(years)]

    if categories and category_column in filtered_df.columns:
        filtered_df = filtered_df[
            filtered_df[category_column].isin(categories)
        ]

    if agencies and agency_column in filtered_df.columns:
        filtered_df = filtered_df[filtered_df[agency_column].isin(agencies)]

    return filtered_df.reset_index(drop=True)


def render_common_sidebar_filters(
    df: pd.DataFrame,
    *,
    year_column: str = "fiscal_year",
    category_column: str = "mapped_service_category",
    agency_column: str = "awarding_agency",
) -> dict[str, list[Any]]:
    """
    Render the shared sidebar filter block and return current selections.
    """
    st.sidebar.subheader("Common Filters")

    years = render_year_filter(df, column=year_column, sidebar=True)
    categories = render_category_filter(
        df,
        column=category_column,
        sidebar=True,
    )
    agencies = render_agency_filter(df, column=agency_column, sidebar=True)

    return {
        "years": years,
        "categories": categories,
        "agencies": agencies,
    }


def render_psc_filter(
    df: pd.DataFrame,
    column: str = "psc_code",
    *,
    sidebar: bool = True,
) -> list[Any]:
    """
    Render a reusable PSC code multiselect filter.
    """
    options = _safe_sorted_unique(df, column)

    target = st.sidebar if sidebar else st
    return target.multiselect(
        "PSC Code",
        options=options,
        default=[],
        help="Optional PSC filter. Leave blank to include all PSC codes.",
    )


def render_naics_filter(
    df: pd.DataFrame,
    column: str = "naics_code",
    *,
    sidebar: bool = True,
) -> list[Any]:
    """
    Render a reusable NAICS code multiselect filter.
    """
    options = _safe_sorted_unique(df, column)

    target = st.sidebar if sidebar else st
    return target.multiselect(
        "NAICS Code",
        options=options,
        default=[],
        help=(
            "Optional NAICS filter. Leave blank to include all NAICS codes."
        ),
    )
