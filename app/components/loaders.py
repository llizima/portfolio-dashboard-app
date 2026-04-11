from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st


DEFAULT_PROCESSED_DIR = Path("src/data/processed")
DEFAULT_ALT_PROCESSED_DIR = Path("data/processed")
DEFAULT_REPORTS_EVAL_DIR = Path("reports/evaluation")
DEFAULT_MODELS_DIR = Path("src/models")


def _read_table(path: Path) -> pd.DataFrame | None:
    """
    Safely read a parquet or CSV file. Return None if the file does not exist.
    """
    if not path.exists():
        return None

    suffix = path.suffix.lower()

    try:
        if suffix == ".parquet":
            return pd.read_parquet(path)
        if suffix == ".csv":
            return pd.read_csv(path)
    except Exception:
        return None

    return None


@st.cache_data(show_spinner=False)
def load_comparable_contracts() -> pd.DataFrame:
    """
    Load the comparable contracts dataset if available.
    Returns an empty dataframe when unavailable.
    """
    candidates = [
        DEFAULT_PROCESSED_DIR / "comparable_contracts.parquet",
        DEFAULT_ALT_PROCESSED_DIR / "comparable_contracts.parquet",
        DEFAULT_PROCESSED_DIR / "usaspending_contracts_baseline_comparables.parquet",
    ]

    for path in candidates:
        df = _read_table(path)
        if df is not None:
            return df

    return pd.DataFrame()


@st.cache_data(show_spinner=False)
def load_scored_dataset() -> pd.DataFrame:
    """
    Load the scored comparable contracts dataset if available.
    Returns an empty dataframe when unavailable.
    """
    candidates = [
        DEFAULT_ALT_PROCESSED_DIR / "comparable_contracts_scored.parquet",
        DEFAULT_PROCESSED_DIR / "comparable_contracts_scored.parquet",
        DEFAULT_ALT_PROCESSED_DIR / "comparable_contracts_scored.csv",
        DEFAULT_PROCESSED_DIR / "comparable_contracts_scored.csv",
    ]

    for path in candidates:
        df = _read_table(path)
        if df is not None:
            return df

    return pd.DataFrame()


@st.cache_data(show_spinner=False)
def load_kpi_outputs() -> dict[str, pd.DataFrame]:
    """
    Load common KPI outputs if they exist.
    Missing files are represented by empty dataframes.
    """
    kpi_files = {
        "overall": DEFAULT_ALT_PROCESSED_DIR / "overall_kpis.csv",
        "category": DEFAULT_ALT_PROCESSED_DIR / "category_kpis.csv",
        "yearly": DEFAULT_ALT_PROCESSED_DIR / "yearly_kpis.csv",
        "agency": DEFAULT_ALT_PROCESSED_DIR / "agency_kpis.csv",
    }

    results: dict[str, pd.DataFrame] = {}
    for key, path in kpi_files.items():
        df = _read_table(path)
        results[key] = df if df is not None else pd.DataFrame()

    return results


@st.cache_data(show_spinner=False)
def load_model_metadata() -> dict[str, Any]:
    """
    Load model metadata JSON if available.
    Returns an empty dict when unavailable.
    """
    path = DEFAULT_MODELS_DIR / "baseline_logreg_metadata.json"
    if not path.exists():
        return {}

    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


@st.cache_data(show_spinner=False)
def load_evaluation_report_text() -> str:
    """
    Load the model evaluation markdown report text if available.
    """
    path = DEFAULT_REPORTS_EVAL_DIR / "model_vs_rules_report.md"
    if not path.exists():
        return ""

    try:
        return path.read_text(encoding="utf-8")
    except Exception:
        return ""


@st.cache_data(show_spinner=False)
def load_scoring_summary_text() -> str:
    """
    Load the scoring summary markdown report text if available.
    """
    path = DEFAULT_REPORTS_EVAL_DIR / "scoring_summary.md"
    if not path.exists():
        return ""

    try:
        return path.read_text(encoding="utf-8")
    except Exception:
        return ""


def get_dataset_status_summary() -> dict[str, bool]:
    """
    Return a lightweight availability summary for common app inputs.
    """
    return {
        "comparable_contracts_available": not load_comparable_contracts().empty,
        "scored_dataset_available": not load_scored_dataset().empty,
        "model_metadata_available": bool(load_model_metadata()),
        "evaluation_report_available": bool(load_evaluation_report_text()),
        "scoring_summary_available": bool(load_scoring_summary_text()),
    }

