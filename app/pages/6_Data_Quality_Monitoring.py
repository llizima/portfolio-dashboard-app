from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

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
    load_evaluation_report_text,
    load_model_metadata,
    load_scored_dataset,
    load_scoring_summary_text,
)


def _choose_monitoring_dataset() -> tuple[pd.DataFrame, str]:
    scored_df = load_scored_dataset()
    if not scored_df.empty:
        return scored_df.copy(), "scored benchmark dataset"

    comparable_df = load_comparable_contracts()
    if not comparable_df.empty:
        return comparable_df.copy(), "comparable contracts dataset"

    return pd.DataFrame(), ""


def _first_non_null_value(df: pd.DataFrame, columns: list[str]) -> Any:
    for col in columns:
        if col in df.columns:
            series = df[col].dropna()
            if not series.empty:
                return series.iloc[0]
    return None


def _extract_refresh_value(df: pd.DataFrame) -> str:
    candidate_columns = [
        "scoring_timestamp",
        "built_at",
        "processed_at",
        "base_obligation_date",
    ]
    value = _first_non_null_value(df, candidate_columns)
    if value is None:
        return "N/A"
    return str(value)


def _extract_model_version(df: pd.DataFrame, metadata: dict[str, Any]) -> str:
    if "model_version" in df.columns:
        series = df["model_version"].dropna()
        if not series.empty:
            return str(series.iloc[0])

    model_class = metadata.get("model_class")
    row_count = metadata.get("row_count")
    feature_count = metadata.get("feature_count")
    mode = metadata.get("mode")

    if model_class:
        return f"{model_class}_rows{row_count}_features{feature_count}_{mode}"

    return "N/A"


def _build_last_evaluation_summary(metadata: dict[str, Any]) -> dict[str, str]:
    report = metadata.get("classification_report", {})

    precision = "N/A"
    recall = "N/A"
    f1_score = "N/A"
    accuracy = "N/A"

    try:
        precision = f"{float(report['1']['precision']):.2f}"
    except Exception:
        pass

    try:
        recall = f"{float(report['1']['recall']):.2f}"
    except Exception:
        pass

    try:
        f1_score = f"{float(report['1']['f1-score']):.2f}"
    except Exception:
        pass

    try:
        accuracy = f"{float(report['accuracy']):.2f}"
    except Exception:
        pass

    return {
        "precision": precision,
        "recall": recall,
        "f1_score": f1_score,
        "accuracy": accuracy,
    }


def _build_coverage_panel(df: pd.DataFrame) -> pd.DataFrame:
    candidate_fields = [
        "description",
        "mapped_service_category",
        "award_amount",
        "awarding_agency",
        "psc_code",
        "naics_code",
        "relevance_score",
        "predicted_relevance_label",
        "model_version",
        "scoring_timestamp",
    ]

    rows: list[dict[str, Any]] = []
    total_rows = len(df)

    for field in candidate_fields:
        if field not in df.columns:
            rows.append(
                {
                    "field": field,
                    "available": "No",
                    "non_null_count": 0,
                    "coverage_pct": 0.0,
                    "missing_count": total_rows,
                }
            )
            continue

        non_null_count = int(df[field].notna().sum())
        missing_count = int(total_rows - non_null_count)
        coverage_pct = (non_null_count / total_rows * 100.0) if total_rows else 0.0

        rows.append(
            {
                "field": field,
                "available": "Yes",
                "non_null_count": non_null_count,
                "coverage_pct": round(coverage_pct, 1),
                "missing_count": missing_count,
            }
        )

    return pd.DataFrame(rows)


def _render_freshness_section(df: pd.DataFrame, source_label: str) -> None:
    st.subheader("Refresh & Freshness Signals")

    refresh_value = _extract_refresh_value(df)

    col1, col2 = st.columns(2)
    with col1:
        render_metric_card("Current Source", source_label)
    with col2:
        render_metric_card("Latest Refresh Signal", refresh_value)

    st.caption(
        "Refresh signal is taken from the best available artifact timestamp field "
        "(for example scoring timestamp, build timestamp, or processed timestamp)."
    )


def _render_model_version_section(df: pd.DataFrame, metadata: dict[str, Any]) -> None:
    st.subheader("Model Version")

    model_version = _extract_model_version(df, metadata)
    short_model_version = (
        model_version if len(str(model_version)) <= 32 else str(model_version)[:32] + "..."
    )
    train_rows = metadata.get("train_rows", "N/A")
    test_rows = metadata.get("test_rows", "N/A")
    feature_count = metadata.get("feature_count", "N/A")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        render_metric_card("Model Version", short_model_version)
    with col2:
        render_metric_card("Train Rows", str(train_rows))
    with col3:
        render_metric_card("Test Rows", str(test_rows))
    with col4:
        render_metric_card("Feature Count", str(feature_count))


def _render_evaluation_section(metadata: dict[str, Any]) -> None:
    st.subheader("Last Evaluation Summary")

    summary = _build_last_evaluation_summary(metadata)

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        render_metric_card("Precision", summary["precision"])
    with col2:
        render_metric_card("Recall", summary["recall"])
    with col3:
        render_metric_card("F1 Score", summary["f1_score"])
    with col4:
        render_metric_card("Accuracy", summary["accuracy"])

    evaluation_text = load_evaluation_report_text()
    if evaluation_text:
        with st.expander("View saved evaluation report text", expanded=False):
            st.text(evaluation_text[:4000])


def _render_coverage_section(df: pd.DataFrame) -> None:
    st.subheader("Data Coverage / Missingness Panel")

    coverage_df = _build_coverage_panel(df)

    low_coverage_fields = coverage_df[coverage_df["coverage_pct"] < 95.0]
    if low_coverage_fields.empty:
        st.caption("All monitored fields currently show strong coverage (95%+).")
    else:
        field_list = ", ".join(low_coverage_fields["field"].astype(str).tolist())
        st.caption(
            f"Some fields have lower coverage and may need attention: {field_list}."
        )

    st.dataframe(coverage_df, width="stretch", hide_index=True)

    chart_df = coverage_df.sort_values("coverage_pct", ascending=True)[["field", "coverage_pct"]].copy()
    chart_df = chart_df.rename(columns={"coverage_pct": "coverage"})
    chart = (
        alt.Chart(chart_df)
        .mark_bar(color="#ed6622", cornerRadiusTopLeft=4, cornerRadiusTopRight=4)
        .encode(
            x=alt.X("coverage:Q", axis=alt.Axis(labelColor="#8a8fa8", titleColor="#8a8fa8", gridColor="#2a2d3a"), title="Coverage (%)"),
            y=alt.Y("field:N", axis=alt.Axis(labelColor="#8a8fa8", titleColor="#8a8fa8"), title=None, sort="-x"),
            tooltip=["field:N", "coverage:Q"],
        )
        .properties(background="#1a1d27", padding={"left": 10, "right": 10, "top": 10, "bottom": 10})
        .configure_view(strokeWidth=0)
        .configure_axis(domainColor="#3a3d4a")
    )
    st.altair_chart(chart, width="stretch")


def _render_scoring_summary_section() -> None:
    scoring_summary_text = load_scoring_summary_text()
    if not scoring_summary_text:
        return

    st.subheader("Latest Scoring Summary")
    with st.expander("View scoring summary text", expanded=False):
        st.text(scoring_summary_text[:4000])


def main() -> None:
    render_page_header(
        "Data Quality Monitoring",
        (
            "Show data freshness, model version context, latest evaluation signals, "
            "and dataset coverage / missingness for lightweight monitoring."
        ),
    )

    df, source_label = _choose_monitoring_dataset()
    metadata = load_model_metadata()

    if df.empty and not metadata:
        render_empty_data_message("Monitoring page artifacts")
        return

    st.subheader("System Health Snapshot")

    data_status = "Available" if not df.empty else "Missing"
    metadata_status = "Available" if metadata else "Missing"

    if metadata:
        eval_summary = _build_last_evaluation_summary(metadata)
        model_status = (
            "Healthy"
            if eval_summary["precision"] != "N/A" and float(eval_summary["precision"]) >= 0.85
            else "Needs Review"
        )
    else:
        model_status = "Unknown"

    col1, col2, col3 = st.columns(3)
    with col1:
        render_metric_card("Data Artifacts", data_status)
    with col2:
        render_metric_card("Model Metadata", metadata_status)
    with col3:
        render_metric_card("Model Health Signal", model_status)

    st.markdown("---")

    render_methodology_info_box(
        "This page provides MLOps-lite monitoring signals for the dashboard. "
        "It is intended to support trust, freshness awareness, and artifact inspection."
    )

    refresh_value = _extract_refresh_value(df) if not df.empty else "N/A"
    evaluation_summary = _build_last_evaluation_summary(metadata) if metadata else {
        "precision": "N/A",
        "recall": "N/A",
        "f1_score": "N/A",
        "accuracy": "N/A",
    }

    st.markdown("### Monitoring Takeaway")

    st.markdown(
        f"""
- **Current data source:** {source_label if source_label else "N/A"}  
- **Latest refresh signal:** {refresh_value}  
- **Precision / Recall:** {evaluation_summary["precision"]} / {evaluation_summary["recall"]}  
- **Current posture:** this dashboard appears to be running from populated scored artifacts with usable model metadata and evaluation signals.
"""
    )

    if not df.empty:
        _render_freshness_section(df, source_label)
        st.markdown("---")
        _render_coverage_section(df)
        st.markdown("---")
    else:
        st.warning(
            "Dataset artifacts were not available, so data freshness and coverage panels "
            "are limited."
        )

    if metadata:
        _render_model_version_section(df if not df.empty else pd.DataFrame(), metadata)
        st.markdown("---")
        _render_evaluation_section(metadata)
        st.markdown("---")
    else:
        st.warning("Model metadata was not available, so model/evaluation monitoring is limited.")

    _render_scoring_summary_section()

    st.subheader("Retraining Context")

    st.markdown(
        """
Current monitoring signals suggest whether the model artifacts remain usable for dashboard interpretation.

A stronger MLOps loop could later incorporate:
- fresh evaluation against newly labeled data
- retraining recommendation checks
- schema drift and category drift alerts
"""
    )

    render_scope_warning_box(
        "These monitoring signals help users understand data freshness, model context, "
        "and coverage limitations. They do not represent a full production MLOps monitoring stack."
    )


if __name__ == "__main__":
    main()

