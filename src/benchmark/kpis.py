"""
Reusable KPI generation for the Applied Government Analytics (AGA) Value Dashboard benchmark layer.

Purpose
-------
This module reads the canonical comparable-contract dataset and produces the
first business-facing KPI tables used by downstream evaluation artifacts and
later Streamlit pages.

This stage is intentionally limited to:
- loading the canonical comparable dataset
- validating required columns
- computing overall benchmark KPIs
- computing category/year/agency benchmark KPI tables
- writing machine-friendly output artifacts
- writing a concise markdown summary

It does NOT:
- render charts
- import Streamlit
- calculate ROI or savings
- perform internal cost accounting
- train or evaluate ML models
"""

from __future__ import annotations

import argparse
import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from src.config.settings import (
    PROCESSED_DATA_DIR,
    REPORTS_EVALUATION_DIR,
    ensure_directories,
    validate_settings,
)

LOGGER = logging.getLogger(__name__)

# ---------------------------------------------------------------------
# Defaults / constants
# ---------------------------------------------------------------------
DEFAULT_INPUT_PATH = PROCESSED_DATA_DIR / "comparable_contracts.parquet"
DEFAULT_OUTPUT_DIR = PROCESSED_DATA_DIR / "kpi_tables"
DEFAULT_REPORT_PATH = REPORTS_EVALUATION_DIR / "kpi_summary.md"

DEFAULT_OVERALL_JSON_NAME = "overall_kpis.json"
DEFAULT_CATEGORY_PARQUET_NAME = "category_kpis.parquet"
DEFAULT_YEARLY_PARQUET_NAME = "yearly_kpis.parquet"
DEFAULT_AGENCY_PARQUET_NAME = "agency_kpis.parquet"

REQUIRED_COLUMNS: tuple[str, ...] = (
    "award_amount",
    "mapped_service_category",
    "fiscal_year",
    "awarding_agency",
)

OPTIONAL_BOOLEAN_COLUMNS: tuple[str, ...] = (
    "is_category_mapped",
    "is_unmapped",
    "needs_manual_review",
)

# Keep metric names stable across all outputs.
COUNT_COL = "contract_count"
TOTAL_COL = "total_award_amount"
MEAN_COL = "mean_award_amount"
MEDIAN_COL = "median_award_amount"
MIN_COL = "min_award_amount"
MAX_COL = "max_award_amount"
Q1_COL = "award_amount_q1"
Q3_COL = "award_amount_q3"
IQR_COL = "award_amount_iqr"
VALID_AMOUNT_COUNT_COL = "valid_award_amount_count"
ZERO_AMOUNT_COUNT_COL = "zero_award_amount_count"
NEGATIVE_AMOUNT_COUNT_COL = "negative_award_amount_count"

LOW_BENCHMARK_COL = "benchmark_low_q1"
MID_BENCHMARK_COL = "benchmark_median"
HIGH_BENCHMARK_COL = "benchmark_high_q3"


# ---------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------
@dataclass(frozen=True)
class KPIConfig:
    """Configuration for benchmark KPI generation."""

    input_path: Path = DEFAULT_INPUT_PATH
    output_dir: Path = DEFAULT_OUTPUT_DIR
    report_path: Path = DEFAULT_REPORT_PATH
    overall_json_name: str = DEFAULT_OVERALL_JSON_NAME
    category_parquet_name: str = DEFAULT_CATEGORY_PARQUET_NAME
    yearly_parquet_name: str = DEFAULT_YEARLY_PARQUET_NAME
    agency_parquet_name: str = DEFAULT_AGENCY_PARQUET_NAME


# ---------------------------------------------------------------------
# General helpers
# ---------------------------------------------------------------------
def setup_logging() -> None:
    """Configure simple repo-friendly logging."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )


def validate_required_columns(df: pd.DataFrame) -> None:
    """Fail fast if the canonical dataset is missing required columns."""
    missing = [col for col in REQUIRED_COLUMNS if col not in df.columns]
    if missing:
        raise ValueError(
            "Comparable dataset is missing required KPI columns: "
            + ", ".join(missing)
        )


def normalize_bool_series(series: pd.Series) -> pd.Series:
    """Robust bool conversion for mixed/object series."""
    if pd.api.types.is_bool_dtype(series):
        return series.fillna(False)

    truthy = {"1", "true", "t", "yes", "y"}
    falsy = {"0", "false", "f", "no", "n", ""}

    def _convert(value: Any) -> bool:
        if pd.isna(value):
            return False
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)):
            return bool(value)
        text = str(value).strip().lower()
        if text in truthy:
            return True
        if text in falsy:
            return False
        return bool(text)

    return series.map(_convert)


def coerce_string_label(value: Any, fallback: str) -> str:
    """Return a stable string label for grouping columns."""
    if value is None or pd.isna(value):
        return fallback
    text = str(value).strip()
    return text if text else fallback


def safe_quantile(series: pd.Series, q: float) -> float | None:
    """Safely compute a quantile from a numeric series."""
    clean = pd.to_numeric(series, errors="coerce").dropna()
    if clean.empty:
        return None
    return float(clean.quantile(q))


def compute_distribution_stats(series: pd.Series) -> dict[str, float | int | None]:
    """
    Compute a stable set of distribution metrics for award amounts.

    All amount-based metrics are based on the numeric, non-null subset.
    Counts for zero/negative values are kept separately for transparency.
    """
    numeric = pd.to_numeric(series, errors="coerce")
    valid = numeric.dropna()

    q1 = safe_quantile(valid, 0.25)
    median = safe_quantile(valid, 0.50)
    q3 = safe_quantile(valid, 0.75)

    iqr = None
    if q1 is not None and q3 is not None:
        iqr = float(q3 - q1)

    return {
        VALID_AMOUNT_COUNT_COL: int(valid.shape[0]),
        TOTAL_COL: float(valid.sum()) if not valid.empty else 0.0,
        MEAN_COL: float(valid.mean()) if not valid.empty else None,
        MEDIAN_COL: median,
        MIN_COL: float(valid.min()) if not valid.empty else None,
        MAX_COL: float(valid.max()) if not valid.empty else None,
        Q1_COL: q1,
        Q3_COL: q3,
        IQR_COL: iqr,
        ZERO_AMOUNT_COUNT_COL: int((valid == 0).sum()) if not valid.empty else 0,
        NEGATIVE_AMOUNT_COUNT_COL: int((valid < 0).sum()) if not valid.empty else 0,
        LOW_BENCHMARK_COL: q1,
        MID_BENCHMARK_COL: median,
        HIGH_BENCHMARK_COL: q3,
    }


def ensure_kpi_ready_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    Normalize the canonical comparable dataset for KPI generation.

    Keeps grouping labels stable and ensures award_amount is numeric.
    """
    validate_required_columns(df)

    output = df.copy()

    output["award_amount"] = pd.to_numeric(output["award_amount"], errors="coerce")
    output["mapped_service_category"] = output["mapped_service_category"].map(
        lambda x: coerce_string_label(x, "unmapped")
    )
    output["awarding_agency"] = output["awarding_agency"].map(
        lambda x: coerce_string_label(x, "unknown_agency")
    )

    # Keep years stable and app-friendly.
    output["fiscal_year"] = output["fiscal_year"].map(
        lambda x: None if pd.isna(x) else int(x)
    )

    for col in OPTIONAL_BOOLEAN_COLUMNS:
        if col in output.columns:
            output[col] = normalize_bool_series(output[col])

    return output


def load_comparable_dataset(path: Path | str) -> pd.DataFrame:
    """Load the canonical comparable dataset."""
    input_path = Path(path)
    if not input_path.exists():
        raise FileNotFoundError(f"Comparable dataset not found: {input_path}")

    suffix = input_path.suffix.lower()
    if suffix == ".parquet":
        df = pd.read_parquet(input_path)
    elif suffix == ".csv":
        df = pd.read_csv(input_path)
    elif suffix == ".json":
        df = pd.read_json(input_path)
    else:
        raise ValueError(
            f"Unsupported input format for {input_path}. "
            "Expected .parquet, .csv, or .json"
        )

    return ensure_kpi_ready_dataframe(df)


# ---------------------------------------------------------------------
# KPI computation helpers
# ---------------------------------------------------------------------
def compute_overall_kpis(df: pd.DataFrame) -> dict[str, Any]:
    """Compute overall benchmark KPIs for the canonical dataset."""
    stats = compute_distribution_stats(df["award_amount"])

    total_rows = int(df.shape[0])
    mapped_count = (
        int(df["is_category_mapped"].sum())
        if "is_category_mapped" in df.columns
        else int((df["mapped_service_category"] != "unmapped").sum())
    )
    unmapped_count = (
        int(df["is_unmapped"].sum())
        if "is_unmapped" in df.columns
        else int((df["mapped_service_category"] == "unmapped").sum())
    )
    manual_review_count = (
        int(df["needs_manual_review"].sum())
        if "needs_manual_review" in df.columns
        else 0
    )

    overall = {
        "total_comparable_contracts": total_rows,
        "mapped_contract_count": mapped_count,
        "unmapped_contract_count": unmapped_count,
        "mapped_contract_pct": round((mapped_count / total_rows * 100), 4)
        if total_rows
        else 0.0,
        "unmapped_contract_pct": round((unmapped_count / total_rows * 100), 4)
        if total_rows
        else 0.0,
        "manual_review_count": manual_review_count,
        **stats,
    }

    return overall


def compute_group_kpis(
    df: pd.DataFrame,
    group_col: str,
    sort_by: str | None = COUNT_COL,
    sort_desc: bool = True,
) -> pd.DataFrame:
    """
    Compute stable benchmark KPI summaries for one grouping column.

    Each output row contains row counts plus distribution metrics over award_amount.
    """
    grouped_rows: list[dict[str, Any]] = []
    total_contracts = int(df.shape[0])

    for group_value, group_df in df.groupby(group_col, dropna=False):
        stats = compute_distribution_stats(group_df["award_amount"])
        row = {
            group_col: group_value,
            COUNT_COL: int(group_df.shape[0]),
            "contract_share_pct": round(
                (group_df.shape[0] / total_contracts * 100), 4
            )
            if total_contracts
            else 0.0,
            **stats,
        }
        grouped_rows.append(row)

    result = pd.DataFrame(grouped_rows)

    if result.empty:
        return result

    if sort_by and sort_by in result.columns:
        result = result.sort_values(
            by=[sort_by, group_col],
            ascending=[not sort_desc, True],
            kind="mergesort",
        ).reset_index(drop=True)

    return result


def compute_category_kpis(df: pd.DataFrame) -> pd.DataFrame:
    """Compute KPI table by mapped service category."""
    category_df = compute_group_kpis(
        df=df,
        group_col="mapped_service_category",
        sort_by=COUNT_COL,
        sort_desc=True,
    )

    if category_df.empty:
        return category_df

    category_df = category_df.rename(
        columns={"mapped_service_category": "category_name"}
    )

    return category_df


def compute_yearly_kpis(df: pd.DataFrame) -> pd.DataFrame:
    """Compute KPI table by fiscal year."""
    working = df.copy()
    working["fiscal_year"] = working["fiscal_year"].fillna(-1).astype(int)

    yearly_df = compute_group_kpis(
        df=working,
        group_col="fiscal_year",
        sort_by="fiscal_year",
        sort_desc=False,
    )

    if yearly_df.empty:
        return yearly_df

    yearly_df["fiscal_year"] = yearly_df["fiscal_year"].map(
        lambda x: None if x == -1 else int(x)
    )

    return yearly_df


def compute_agency_kpis(df: pd.DataFrame) -> pd.DataFrame:
    """Compute KPI table by awarding agency."""
    return compute_group_kpis(
        df=df,
        group_col="awarding_agency",
        sort_by=COUNT_COL,
        sort_desc=True,
    )


# ---------------------------------------------------------------------
# Output helpers
# ---------------------------------------------------------------------
def write_json(payload: dict[str, Any], output_path: Path) -> None:
    """Write a JSON file with stable formatting."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)


def write_dataframe(df: pd.DataFrame, output_path: Path) -> None:
    """Write a dataframe using the output format implied by the file suffix."""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    suffix = output_path.suffix.lower()
    if suffix == ".parquet":
        df.to_parquet(output_path, index=False)
        return
    if suffix == ".csv":
        df.to_csv(output_path, index=False)
        return
    if suffix == ".json":
        df.to_json(output_path, orient="records", indent=2)
        return

    raise ValueError(
        f"Unsupported output format for {output_path}. "
        "Expected .parquet, .csv, or .json"
    )


def build_kpi_summary_markdown(
    *,
    config: KPIConfig,
    source_df: pd.DataFrame,
    overall_kpis: dict[str, Any],
    category_kpis: pd.DataFrame,
    yearly_kpis: pd.DataFrame,
    agency_kpis: pd.DataFrame,
) -> str:
    """Build a concise evaluation markdown summary for the KPI generation stage."""
    lines: list[str] = []

    lines.append("# KPI Summary")
    lines.append("## Applied Government Analytics (AGA) Value Dashboard")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## 1. Purpose")
    lines.append("")
    lines.append(
        "This report summarizes the first reusable benchmark KPI outputs generated "
        "from the canonical comparable-contracts dataset."
    )
    lines.append("")
    lines.append(
        "These outputs are descriptive benchmark summaries intended for downstream "
        "dashboard loading and evaluation use. They do not represent audited savings, "
        "ROI, or internal Applied Government Analytics (AGA) cost accounting."
    )
    lines.append("")
    lines.append("## 2. Input Dataset")
    lines.append("")
    lines.append(f"- Source dataset: `{config.input_path}`")
    lines.append(f"- Total input rows: **{int(source_df.shape[0]):,}**")
    lines.append("")
    lines.append("## 3. Output Artifacts")
    lines.append("")
    lines.append(f"- Overall KPI JSON: `{config.output_dir / config.overall_json_name}`")
    lines.append(
        f"- Category KPI table: `{config.output_dir / config.category_parquet_name}`"
    )
    lines.append(
        f"- Yearly KPI table: `{config.output_dir / config.yearly_parquet_name}`"
    )
    lines.append(
        f"- Agency KPI table: `{config.output_dir / config.agency_parquet_name}`"
    )
    lines.append(f"- This report: `{config.report_path}`")
    lines.append("")
    lines.append("## 4. Headline Overall KPIs")
    lines.append("")
    lines.append(
        f"- Total comparable contracts: **{overall_kpis['total_comparable_contracts']:,}**"
    )
    lines.append(
        f"- Total benchmarked dollars: **{overall_kpis[TOTAL_COL]:,.2f}**"
        if overall_kpis[TOTAL_COL] is not None
        else "- Total benchmarked dollars: **N/A**"
    )
    lines.append(
        f"- Median award amount: **{overall_kpis[MEDIAN_COL]:,.2f}**"
        if overall_kpis[MEDIAN_COL] is not None
        else "- Median award amount: **N/A**"
    )
    lines.append(
        f"- Mean award amount: **{overall_kpis[MEAN_COL]:,.2f}**"
        if overall_kpis[MEAN_COL] is not None
        else "- Mean award amount: **N/A**"
    )
    lines.append(
        f"- Award amount Q1: **{overall_kpis[Q1_COL]:,.2f}**"
        if overall_kpis[Q1_COL] is not None
        else "- Award amount Q1: **N/A**"
    )
    lines.append(
        f"- Award amount Q3: **{overall_kpis[Q3_COL]:,.2f}**"
        if overall_kpis[Q3_COL] is not None
        else "- Award amount Q3: **N/A**"
    )
    lines.append(
        f"- Award amount IQR: **{overall_kpis[IQR_COL]:,.2f}**"
        if overall_kpis[IQR_COL] is not None
        else "- Award amount IQR: **N/A**"
    )
    lines.append(
        f"- Mapped contracts: **{overall_kpis['mapped_contract_count']:,}** "
        f"({overall_kpis['mapped_contract_pct']:.4f}%)"
    )
    lines.append(
        f"- Unmapped contracts: **{overall_kpis['unmapped_contract_count']:,}** "
        f"({overall_kpis['unmapped_contract_pct']:.4f}%)"
    )
    lines.append(
        f"- Manual review count: **{overall_kpis['manual_review_count']:,}**"
    )
    lines.append("")
    lines.append("## 5. Table Coverage")
    lines.append("")
    lines.append(f"- Category KPI rows: **{int(category_kpis.shape[0]):,}**")
    lines.append(f"- Yearly KPI rows: **{int(yearly_kpis.shape[0]):,}**")
    lines.append(f"- Agency KPI rows: **{int(agency_kpis.shape[0]):,}**")
    lines.append("")
    lines.append("## 6. Caveats")
    lines.append("")
    lines.append(
        "- These KPI outputs are descriptive benchmark summaries, not causal or "
        "audited financial conclusions."
    )
    lines.append(
        "- `award_amount` is used as the primary benchmark value field for this stage."
    )
    lines.append(
        "- Unmapped contracts may still appear in the canonical comparable dataset "
        "and are retained explicitly rather than silently dropped."
    )
    lines.append(
        "- Amount-based metrics are calculated from numeric non-null `award_amount` values."
    )
    lines.append(
        "- This report is intended to support benchmark interpretation and downstream "
        "app loading, not internal savings claims."
    )
    lines.append("")

    return "\n".join(lines)


def write_kpi_outputs(
    *,
    config: KPIConfig,
    overall_kpis: dict[str, Any],
    category_kpis: pd.DataFrame,
    yearly_kpis: pd.DataFrame,
    agency_kpis: pd.DataFrame,
    report_markdown: str,
) -> None:
    """Write all KPI artifacts to stable locations."""
    output_dir = config.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    config.report_path.parent.mkdir(parents=True, exist_ok=True)

    write_json(overall_kpis, output_dir / config.overall_json_name)
    write_dataframe(category_kpis, output_dir / config.category_parquet_name)
    write_dataframe(yearly_kpis, output_dir / config.yearly_parquet_name)
    write_dataframe(agency_kpis, output_dir / config.agency_parquet_name)

    with config.report_path.open("w", encoding="utf-8") as f:
        f.write(report_markdown)


# ---------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------
def parse_args() -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(
        description="Generate reusable KPI tables from comparable_contracts."
    )
    parser.add_argument(
        "--input-path",
        type=Path,
        default=DEFAULT_INPUT_PATH,
        help="Path to canonical comparable dataset.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Directory for KPI output tables.",
    )
    parser.add_argument(
        "--report-path",
        type=Path,
        default=DEFAULT_REPORT_PATH,
        help="Path for KPI summary markdown.",
    )
    return parser.parse_args()


def main() -> None:
    """CLI entrypoint."""
    setup_logging()
    validate_settings()
    ensure_directories()

    args = parse_args()
    config = KPIConfig(
        input_path=args.input_path,
        output_dir=args.output_dir,
        report_path=args.report_path,
    )

    LOGGER.info("Loading comparable dataset from %s", config.input_path)
    df = load_comparable_dataset(config.input_path)

    LOGGER.info("Computing overall KPIs")
    overall_kpis = compute_overall_kpis(df)

    LOGGER.info("Computing category KPI table")
    category_kpis = compute_category_kpis(df)

    LOGGER.info("Computing yearly KPI table")
    yearly_kpis = compute_yearly_kpis(df)

    LOGGER.info("Computing agency KPI table")
    agency_kpis = compute_agency_kpis(df)

    LOGGER.info("Building KPI summary markdown")
    report_markdown = build_kpi_summary_markdown(
        config=config,
        source_df=df,
        overall_kpis=overall_kpis,
        category_kpis=category_kpis,
        yearly_kpis=yearly_kpis,
        agency_kpis=agency_kpis,
    )

    LOGGER.info("Writing KPI outputs")
    write_kpi_outputs(
        config=config,
        overall_kpis=overall_kpis,
        category_kpis=category_kpis,
        yearly_kpis=yearly_kpis,
        agency_kpis=agency_kpis,
        report_markdown=report_markdown,
    )

    LOGGER.info(
        "KPI generation complete | rows=%s | category_rows=%s | yearly_rows=%s | agency_rows=%s",
        df.shape[0],
        category_kpis.shape[0],
        yearly_kpis.shape[0],
        agency_kpis.shape[0],
    )


if __name__ == "__main__":
    main()
