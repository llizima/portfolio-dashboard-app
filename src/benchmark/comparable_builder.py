"""
Canonical comparable-contract dataset builder for the SOFWERX Value Dashboard.

Purpose
-------
This module assembles one canonical benchmark dataset from upstream processed
artifacts so that the Streamlit app, KPI layer, and later ML/evaluation
workflows can all consume a single stable table.

Recommended upstream flow
-------------------------
1. clean_transform.py
   -> cleaned analytical dataset
2. baseline_filters.py
   -> full scored dataset (preferred) and/or filtered comparable subset
3. category_mapper.py
   -> mapped comparable subset with final service categories
4. comparable_builder.py
   -> canonical comparable dataset

This module is intentionally limited to:
- loading upstream processed datasets
- validating schema requirements
- merging benchmark-stage outputs deterministically
- deriving stable app-ready helper fields
- writing canonical processed outputs
- writing compact build summary metadata

It does NOT:
- ingest raw API data
- train or evaluate ML models
- calculate business value estimates
- render dashboard pages
- make accounting or savings claims
"""

from __future__ import annotations

import argparse
import json
import logging
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

from src.config.settings import (
    PROCESSED_DATA_DIR,
    REPORTS_EVALUATION_DIR,
    SERVICE_TAXONOMY_PATH,
    ensure_directories,
    validate_settings,
)

LOGGER = logging.getLogger(__name__)

# ---------------------------------------------------------------------
# Defaults / constants
# ---------------------------------------------------------------------
DEFAULT_OUTPUT_STEM = "comparable_contracts"
DEFAULT_OUTPUT_FORMAT = "parquet"
DEFAULT_BUILDER_VERSION = "0.1.0"

DEFAULT_CLEANED_PATH = PROCESSED_DATA_DIR / "usaspending_contracts_cleaned.parquet"
DEFAULT_BASELINE_FULL_PATH = (
    PROCESSED_DATA_DIR / "usaspending_contracts_baseline_comparables_scored.parquet"
)
DEFAULT_BASELINE_SUBSET_PATH = (
    PROCESSED_DATA_DIR / "usaspending_contracts_baseline_comparables.parquet"
)
DEFAULT_MAPPED_PATH = (
    PROCESSED_DATA_DIR / "usaspending_contracts_category_mapped.parquet"
)
DEFAULT_SUMMARY_JSON_NAME = "comparable_contracts_build_summary.json"

# The cleaned stage standardizes these fields and they should be preserved
# whenever available.
CORE_CONTRACT_COLUMNS: tuple[str, ...] = (
    "award_id",
    "generated_internal_id",
    "award_amount",
    "total_outlays",
    "description",
    "description_clean",
    "text_all",
    "contract_award_type",
    "awarding_agency",
    "awarding_agency_code",
    "awarding_sub_agency",
    "funding_agency",
    "funding_sub_agency",
    "recipient_name",
    "recipient_uei",
    "start_date",
    "end_date",
    "base_obligation_date",
    "award_duration_days",
    "psc_code",
    "psc_description",
    "naics_code",
    "naics_description",
    "source_file",
    "run_id",
    "query_name",
    "fiscal_year",
    "processed_at",
    "record_hash",
    "is_duplicate_row",
)

BASELINE_RESULT_COLUMNS: tuple[str, ...] = (
    "baseline_include",
    "baseline_rule_score",
    "baseline_reason_codes",
    "baseline_reason_text",
    "matched_keywords",
    "matched_psc_codes",
    "matched_naics_codes",
    "baseline_primary_category",
    "baseline_review_flag",
    "baseline_matched_categories",
    "baseline_signal_type_count",
    "baseline_category_match_count",
)

CATEGORY_RESULT_COLUMNS: tuple[str, ...] = (
    "mapped_service_category",
    "category_mapper_score",
    "category_mapper_reason_codes",
    "category_mapper_reason_text",
    "category_mapper_matched_categories",
    "category_mapper_matched_keywords",
    "category_mapper_matched_psc_codes",
    "category_mapper_matched_naics_codes",
    "category_mapper_is_ambiguous",
    "category_mapper_ambiguity_notes",
    "category_mapper_runner_up_categories",
    "category_mapper_signal_type_count",
    "category_mapper_category_match_count",
)

REQUIRED_BASELINE_COLUMNS: tuple[str, ...] = (
    "record_hash",
    "baseline_include",
    "baseline_rule_score",
)

REQUIRED_MAPPED_COLUMNS: tuple[str, ...] = (
    "mapped_service_category",
    "category_mapper_score",
)

JOIN_KEY_CANDIDATES: tuple[str, ...] = (
    "record_hash",
    "generated_internal_id",
    "award_id",
)


# ---------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------
@dataclass(frozen=True)
class ComparableBuilderConfig:
    """Configuration for canonical comparable dataset construction."""

    cleaned_path: Path = DEFAULT_CLEANED_PATH
    baseline_full_path: Path = DEFAULT_BASELINE_FULL_PATH
    baseline_subset_path: Path = DEFAULT_BASELINE_SUBSET_PATH
    mapped_path: Path = DEFAULT_MAPPED_PATH
    taxonomy_path: Path = SERVICE_TAXONOMY_PATH
    output_dir: Path = PROCESSED_DATA_DIR
    report_dir: Path = REPORTS_EVALUATION_DIR
    output_stem: str = DEFAULT_OUTPUT_STEM
    output_format: str = DEFAULT_OUTPUT_FORMAT
    summary_json_name: str = DEFAULT_SUMMARY_JSON_NAME
    keep_all_rows: bool = False
    write_canonical_dataset: bool = True
    write_versioned_output: bool = False
    write_summary_json: bool = False
    builder_version: str = DEFAULT_BUILDER_VERSION


# ---------------------------------------------------------------------
# General helpers
# ---------------------------------------------------------------------
def utc_now_iso() -> str:
    """Return a UTC ISO timestamp with seconds precision."""
    return datetime.now(UTC).replace(microsecond=0).isoformat()


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


def pipe_list_count(value: Any) -> int:
    """Count pipe-delimited values safely."""
    if value is None or pd.isna(value):
        return 0
    text = str(value).strip()
    if not text:
        return 0
    return len([item for item in text.split("|") if item.strip()])


def read_yaml_version(path: Path) -> str | None:
    """Read top-level taxonomy version, if available."""
    if not path.exists():
        return None

    with path.open("r", encoding="utf-8") as file:
        payload = yaml.safe_load(file) or {}

    version = payload.get("version")
    if version is None:
        return None
    return str(version).strip() or None


def _load_input_dataframe(input_path: Path) -> pd.DataFrame:
    """Load supported tabular inputs."""
    suffix = input_path.suffix.lower()

    if suffix == ".parquet":
        return pd.read_parquet(input_path)
    if suffix == ".csv":
        return pd.read_csv(input_path)
    if suffix == ".json":
        return pd.read_json(input_path)

    raise ValueError(
        f"Unsupported input dataset format for {input_path}. "
        "Expected .parquet, .csv, or .json"
    )


def _write_dataframe(df: pd.DataFrame, output_path: Path, output_format: str) -> None:
    """Write dataframe in supported formats."""
    fmt = output_format.lower().strip()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if fmt == "parquet":
        df.to_parquet(output_path, index=False)
        return
    if fmt == "csv":
        df.to_csv(output_path, index=False)
        return
    if fmt == "json":
        df.to_json(output_path, orient="records", indent=2)
        return

    raise ValueError(
        f"Unsupported output format '{output_format}'. "
        "Expected one of: parquet, csv, json"
    )


def validate_required_columns(
    df: pd.DataFrame,
    required_columns: tuple[str, ...],
    dataset_name: str,
) -> None:
    """Fail fast if a dataset is missing required columns."""
    missing = [column for column in required_columns if column not in df.columns]
    if missing:
        raise ValueError(
            f"{dataset_name} is missing required columns: {', '.join(missing)}"
        )


def choose_existing_path(*paths: Path) -> Path:
    """Return the first path that exists."""
    for path in paths:
        if path.exists():
            return path
    raise FileNotFoundError(
        "None of the candidate input paths exist: "
        + ", ".join(str(path) for path in paths)
    )


# ---------------------------------------------------------------------
# Join helpers
# ---------------------------------------------------------------------
def infer_join_key(
    left_df: pd.DataFrame,
    right_df: pd.DataFrame,
    candidate_keys: tuple[str, ...] = JOIN_KEY_CANDIDATES,
) -> str:
    """
    Infer a stable join key shared by both dataframes.

    Preference order:
    1. record_hash
    2. generated_internal_id
    3. award_id

    record_hash is preferred because it is the cleanest cross-stage lineage key
    from the transformed dataset.
    """
    for key in candidate_keys:
        if key in left_df.columns and key in right_df.columns:
            return key

    raise ValueError(
        "Could not infer a shared join key. Checked candidates: "
        + ", ".join(candidate_keys)
    )


def dedupe_for_join(df: pd.DataFrame, join_key: str, dataset_name: str) -> pd.DataFrame:
    """
    Ensure one row per join key before merging.

    If duplicates exist, keep the first deterministic occurrence after stable
    sort. This is conservative and avoids row explosion in the canonical table.
    """
    if join_key not in df.columns:
        raise ValueError(f"{dataset_name} missing join key: {join_key}")

    working = df.copy()

    # Stable ordering so dedupe behavior remains deterministic.
    sort_candidates = [
        column
        for column in (
            join_key,
            "category_mapper_score",
            "baseline_rule_score",
            "award_amount",
            "fiscal_year",
        )
        if column in working.columns
    ]
    if sort_candidates:
        ascending = []
        for column in sort_candidates:
            ascending.append(column not in {"category_mapper_score", "baseline_rule_score", "award_amount"})
        working = working.sort_values(
            by=sort_candidates,
            ascending=ascending,
            kind="mergesort",
        )

    duplicated = int(working.duplicated(subset=[join_key], keep="first").sum())
    if duplicated > 0:
        LOGGER.warning(
            "%s contains duplicate join keys; keeping first occurrence per %s",
            dataset_name,
            join_key,
            extra={"duplicate_join_keys": duplicated},
        )

    return working.drop_duplicates(subset=[join_key], keep="first").copy()


def select_columns_if_present(
    df: pd.DataFrame,
    preferred_columns: tuple[str, ...],
) -> list[str]:
    """Return only preferred columns that actually exist."""
    return [column for column in preferred_columns if column in df.columns]


# ---------------------------------------------------------------------
# Canonical derivations
# ---------------------------------------------------------------------
def derive_amount_band(value: Any) -> str:
    """Bucket award_amount into app-friendly ranges."""
    if pd.isna(value):
        return "unknown"
    amount = float(value)

    if amount < 0:
        return "negative_or_adjustment"
    if amount < 100_000:
        return "under_100k"
    if amount < 500_000:
        return "100k_to_499k"
    if amount < 1_000_000:
        return "500k_to_999k"
    if amount < 5_000_000:
        return "1m_to_4_9m"
    if amount < 10_000_000:
        return "5m_to_9_9m"
    return "10m_plus"


def derive_duration_band(value: Any) -> str:
    """Bucket award duration into app-friendly ranges."""
    if pd.isna(value):
        return "unknown"

    days = float(value)
    if days < 0:
        return "invalid_negative"
    if days <= 30:
        return "0_to_30_days"
    if days <= 90:
        return "31_to_90_days"
    if days <= 180:
        return "91_to_180_days"
    if days <= 365:
        return "181_to_365_days"
    if days <= 730:
        return "1_to_2_years"
    return "2_plus_years"


def derive_agency_scope(row: pd.Series) -> str:
    """
    Derive a simple benchmark scope grouping from agency text.

    This is intentionally lightweight and app-facing, not a formal ontology.
    """
    agency_parts = [
        str(row.get("awarding_agency", "") or "").lower(),
        str(row.get("awarding_sub_agency", "") or "").lower(),
        str(row.get("funding_agency", "") or "").lower(),
        str(row.get("funding_sub_agency", "") or "").lower(),
    ]
    text = " | ".join(agency_parts)

    if "special operations command" in text or "ussocom" in text or "socom" in text:
        return "USSOCOM"
    if "department of defense" in text or "defense" in text or "army" in text or "navy" in text or "air force" in text:
        return "DoD"
    return "Federal Non-DoD"


def derive_category_display_label(value: Any) -> str:
    """Convert snake_case category names into title labels."""
    if value is None or pd.isna(value):
        return "Unmapped"
    text = str(value).strip()
    if not text:
        return "Unmapped"
    return text.replace("_", " ").title()


def apply_canonical_derivations(
    df: pd.DataFrame,
    *,
    builder_version: str,
    taxonomy_version: str | None,
    built_at: str,
) -> pd.DataFrame:
    """Add stable canonical helper columns."""
    output = df.copy()

    if "award_amount" in output.columns:
        output["award_amount_usd"] = pd.to_numeric(output["award_amount"], errors="coerce")
        output["award_amount_band"] = output["award_amount_usd"].map(derive_amount_band)
    else:
        output["award_amount_usd"] = pd.NA
        output["award_amount_band"] = "unknown"

    if "total_outlays" in output.columns:
        output["total_outlays_usd"] = pd.to_numeric(output["total_outlays"], errors="coerce")
        output["has_total_outlays"] = output["total_outlays_usd"].notna()
    else:
        output["total_outlays_usd"] = pd.NA
        output["has_total_outlays"] = False

    if "award_duration_days" in output.columns:
        output["award_duration_days"] = pd.to_numeric(
            output["award_duration_days"], errors="coerce"
        )
        output["award_duration_band"] = output["award_duration_days"].map(derive_duration_band)
    else:
        output["award_duration_band"] = "unknown"

    for date_col in ("start_date", "end_date", "base_obligation_date"):
        if date_col in output.columns:
            output[date_col] = pd.to_datetime(output[date_col], errors="coerce")

    if "base_obligation_date" in output.columns:
        output["base_obligation_year"] = output["base_obligation_date"].dt.year
        output["base_obligation_quarter"] = output["base_obligation_date"].dt.to_period("Q").astype("string")
    else:
        output["base_obligation_year"] = pd.NA
        output["base_obligation_quarter"] = pd.NA

    if "mapped_service_category" in output.columns:
        output["category_display_label"] = output["mapped_service_category"].map(
            derive_category_display_label
        )
        output["is_unmapped"] = (
            output["mapped_service_category"].fillna("unmapped").astype(str) == "unmapped"
        )
        output["is_category_mapped"] = ~output["is_unmapped"]
    else:
        output["category_display_label"] = "Unmapped"
        output["is_unmapped"] = True
        output["is_category_mapped"] = False

    if "category_mapper_is_ambiguous" in output.columns:
        output["needs_manual_review"] = normalize_bool_series(
            output["category_mapper_is_ambiguous"]
        )
    elif "baseline_review_flag" in output.columns:
        output["needs_manual_review"] = normalize_bool_series(
            output["baseline_review_flag"]
        )
    else:
        output["needs_manual_review"] = False

    if "baseline_include" in output.columns:
        output["baseline_include"] = normalize_bool_series(output["baseline_include"])
    else:
        output["baseline_include"] = False

    output["is_comparable_contract"] = output["baseline_include"]
    output["is_benchmark_eligible"] = output["is_comparable_contract"] & (
        output.get("award_amount_usd", pd.Series(index=output.index, dtype="float64")).notna()
    )

    output["benchmark_stage_source"] = output["is_category_mapped"].map(
        lambda is_mapped: "baseline_plus_category_mapper" if is_mapped else "baseline_only"
    )
    output["taxonomy_version"] = taxonomy_version
    output["builder_version"] = builder_version
    output["dataset_version"] = f"comparable_contracts_{built_at.replace(':', '').replace('-', '')}"
    output["built_at"] = built_at

    if "baseline_matched_categories" in output.columns:
        output["baseline_matched_category_count_derived"] = output[
            "baseline_matched_categories"
        ].map(pipe_list_count)
    else:
        output["baseline_matched_category_count_derived"] = 0

    if "category_mapper_runner_up_categories" in output.columns:
        output["category_mapper_runner_up_count"] = output[
            "category_mapper_runner_up_categories"
        ].map(pipe_list_count)
    else:
        output["category_mapper_runner_up_count"] = 0

    output["lineage_has_run_id"] = output["run_id"].notna() if "run_id" in output.columns else False
    output["lineage_has_query_name"] = output["query_name"].notna() if "query_name" in output.columns else False

    return output


def order_canonical_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Apply a stable, readable final column order."""
    ordered_groups = [
        (
            "identifiers_lineage",
            (
                "record_hash",
                "award_id",
                "generated_internal_id",
                "run_id",
                "query_name",
                "source_file",
                "processed_at",
                "built_at",
                "builder_version",
                "dataset_version",
                "taxonomy_version",
                "benchmark_stage_source",
            ),
        ),
        (
            "core_contract",
            (
                "award_amount",
                "award_amount_usd",
                "award_amount_band",
                "total_outlays",
                "total_outlays_usd",
                "has_total_outlays",
                "description",
                "description_clean",
                "text_all",
                "contract_award_type",
                "recipient_name",
                "recipient_uei",
                "awarding_agency",
                "awarding_agency_code",
                "awarding_sub_agency",
                "funding_agency",
                "funding_sub_agency",
                "fiscal_year",
                "agency_scope_level",
                "start_date",
                "end_date",
                "base_obligation_date",
                "base_obligation_year",
                "base_obligation_quarter",
                "award_duration_days",
                "award_duration_band",
                "psc_code",
                "psc_description",
                "naics_code",
                "naics_description",
                "is_duplicate_row",
            ),
        ),
        (
            "baseline",
            (
                "baseline_include",
                "baseline_review_flag",
                "baseline_rule_score",
                "baseline_primary_category",
                "baseline_matched_categories",
                "baseline_signal_type_count",
                "baseline_category_match_count",
                "baseline_matched_category_count_derived",
                "baseline_reason_codes",
                "baseline_reason_text",
                "matched_keywords",
                "matched_psc_codes",
                "matched_naics_codes",
            ),
        ),
        (
            "category_mapping",
            (
                "mapped_service_category",
                "category_display_label",
                "is_category_mapped",
                "is_unmapped",
                "category_mapper_score",
                "category_mapper_is_ambiguous",
                "needs_manual_review",
                "category_mapper_reason_codes",
                "category_mapper_reason_text",
                "category_mapper_matched_categories",
                "category_mapper_matched_keywords",
                "category_mapper_matched_psc_codes",
                "category_mapper_matched_naics_codes",
                "category_mapper_runner_up_categories",
                "category_mapper_runner_up_count",
                "category_mapper_signal_type_count",
                "category_mapper_category_match_count",
                "category_mapper_ambiguity_notes",
            ),
        ),
        (
            "benchmark_flags",
            (
                "is_comparable_contract",
                "is_benchmark_eligible",
                "lineage_has_run_id",
                "lineage_has_query_name",
            ),
        ),
    ]

    ordered: list[str] = []
    for _, group_columns in ordered_groups:
        ordered.extend([column for column in group_columns if column in df.columns])

    remaining = [column for column in df.columns if column not in ordered]
    final_columns = ordered + remaining

    return df.loc[:, final_columns].copy()


# ---------------------------------------------------------------------
# Build summary
# ---------------------------------------------------------------------
def build_summary_payload(
    canonical_df: pd.DataFrame,
    *,
    config: ComparableBuilderConfig,
    source_paths: dict[str, str],
    built_at: str,
    join_key: str,
    source_row_counts: dict[str, int],
) -> dict[str, Any]:
    """Create a compact JSON-friendly build summary."""
    category_counts: dict[str, int] = {}
    if "mapped_service_category" in canonical_df.columns:
        category_counts = {
            str(key): int(value)
            for key, value in canonical_df["mapped_service_category"]
            .fillna("unmapped")
            .value_counts(dropna=False)
            .to_dict()
            .items()
        }

    return {
        "built_at": built_at,
        "builder_version": config.builder_version,
        "dataset_version": (
            canonical_df["dataset_version"].iloc[0]
            if "dataset_version" in canonical_df.columns and not canonical_df.empty
            else None
        ),
        "taxonomy_version": (
            canonical_df["taxonomy_version"].iloc[0]
            if "taxonomy_version" in canonical_df.columns and not canonical_df.empty
            else None
        ),
        "join_key_used": join_key,
        "keep_all_rows": config.keep_all_rows,
        "input_paths": source_paths,
        "source_row_counts": source_row_counts,
        "final_row_count": int(len(canonical_df)),
        "comparable_row_count": int(
            canonical_df["is_comparable_contract"].sum()
            if "is_comparable_contract" in canonical_df.columns
            else 0
        ),
        "benchmark_eligible_row_count": int(
            canonical_df["is_benchmark_eligible"].sum()
            if "is_benchmark_eligible" in canonical_df.columns
            else 0
        ),
        "mapped_row_count": int(
            canonical_df["is_category_mapped"].sum()
            if "is_category_mapped" in canonical_df.columns
            else 0
        ),
        "unmapped_row_count": int(
            canonical_df["is_unmapped"].sum()
            if "is_unmapped" in canonical_df.columns
            else 0
        ),
        "manual_review_row_count": int(
            canonical_df["needs_manual_review"].sum()
            if "needs_manual_review" in canonical_df.columns
            else 0
        ),
        "category_counts": category_counts,
        "columns": list(canonical_df.columns),
    }


def write_summary_json(summary: dict[str, Any], output_path: Path) -> None:
    """Persist summary metadata."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as file:
        json.dump(summary, file, indent=2, default=str)


# ---------------------------------------------------------------------
# Loading / merge orchestration
# ---------------------------------------------------------------------
def load_upstream_datasets(
    config: ComparableBuilderConfig,
) -> tuple[pd.DataFrame, pd.DataFrame, Path, Path]:
    """
    Load the preferred baseline source and mapped comparable dataset.

    Preferred baseline input:
    - full scored baseline dataset, because it contains all cleaned rows plus
      transparent benchmark-screen outputs

    Fallback:
    - baseline comparable subset if the full scored dataset is unavailable
    """
    baseline_path = choose_existing_path(
        config.baseline_full_path,
        config.baseline_subset_path,
    )
    mapped_path = choose_existing_path(config.mapped_path)

    LOGGER.info("Loading baseline dataset from %s", baseline_path)
    baseline_df = _load_input_dataframe(baseline_path)

    LOGGER.info("Loading mapped comparable dataset from %s", mapped_path)
    mapped_df = _load_input_dataframe(mapped_path)

    validate_required_columns(baseline_df, REQUIRED_BASELINE_COLUMNS, "baseline dataset")
    validate_required_columns(mapped_df, REQUIRED_MAPPED_COLUMNS, "mapped dataset")

    return baseline_df, mapped_df, baseline_path, mapped_path


def build_canonical_comparable_dataset(
    config: ComparableBuilderConfig,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Build the canonical comparable benchmark dataframe and summary payload."""
    validate_settings()
    ensure_directories()

    config.output_dir.mkdir(parents=True, exist_ok=True)
    config.report_dir.mkdir(parents=True, exist_ok=True)

    built_at = utc_now_iso()
    taxonomy_version = read_yaml_version(config.taxonomy_path)

    baseline_df, mapped_df, baseline_path, mapped_path = load_upstream_datasets(config)

    join_key = infer_join_key(baseline_df, mapped_df)
    LOGGER.info("Using join key '%s' for canonical benchmark merge", join_key)

    baseline_df = dedupe_for_join(baseline_df, join_key, "baseline dataset")
    mapped_df = dedupe_for_join(mapped_df, join_key, "mapped dataset")

    # Keep the full baseline table, then bring in only the category-mapper fields
    # not already represented in the baseline dataset. This avoids duplicate core
    # contract columns and preserves the baseline dataset as the canonical base.
    mapped_keep_columns = [join_key] + [
        column
        for column in CATEGORY_RESULT_COLUMNS
        if column in mapped_df.columns and column != join_key
    ]

    merged = baseline_df.merge(
        mapped_df.loc[:, mapped_keep_columns],
        how="left",
        on=join_key,
        validate="one_to_one",
    )

    if "mapped_service_category" not in merged.columns:
        merged["mapped_service_category"] = "unmapped"

    if "category_mapper_score" not in merged.columns:
        merged["category_mapper_score"] = 0

    if "category_mapper_is_ambiguous" not in merged.columns:
        merged["category_mapper_is_ambiguous"] = False

    if "category_mapper_reason_codes" not in merged.columns:
        merged["category_mapper_reason_codes"] = ""

    if "category_mapper_reason_text" not in merged.columns:
        merged["category_mapper_reason_text"] = ""

    if "category_mapper_matched_categories" not in merged.columns:
        merged["category_mapper_matched_categories"] = ""

    if "category_mapper_matched_keywords" not in merged.columns:
        merged["category_mapper_matched_keywords"] = ""

    if "category_mapper_matched_psc_codes" not in merged.columns:
        merged["category_mapper_matched_psc_codes"] = ""

    if "category_mapper_matched_naics_codes" not in merged.columns:
        merged["category_mapper_matched_naics_codes"] = ""

    if "category_mapper_ambiguity_notes" not in merged.columns:
        merged["category_mapper_ambiguity_notes"] = ""

    if "category_mapper_runner_up_categories" not in merged.columns:
        merged["category_mapper_runner_up_categories"] = ""

    if "category_mapper_signal_type_count" not in merged.columns:
        merged["category_mapper_signal_type_count"] = 0

    if "category_mapper_category_match_count" not in merged.columns:
        merged["category_mapper_category_match_count"] = 0

    merged["agency_scope_level"] = merged.apply(derive_agency_scope, axis=1)

    canonical_df = apply_canonical_derivations(
        merged,
        builder_version=config.builder_version,
        taxonomy_version=taxonomy_version,
        built_at=built_at,
    )

    # By default this builder outputs the final comparable subset for app/KPI use.
    # The user can override this to keep the full baseline-scored table.
    if not config.keep_all_rows:
        canonical_df = canonical_df.loc[
            canonical_df["is_comparable_contract"].fillna(False)
        ].copy()

    canonical_df = order_canonical_columns(canonical_df).reset_index(drop=True)

    source_row_counts = {
        "baseline_rows": int(len(baseline_df)),
        "mapped_rows": int(len(mapped_df)),
    }

    summary = build_summary_payload(
        canonical_df=canonical_df,
        config=config,
        source_paths={
            "baseline_input": str(baseline_path),
            "mapped_input": str(mapped_path),
            "taxonomy_input": str(config.taxonomy_path),
        },
        built_at=built_at,
        join_key=join_key,
        source_row_counts=source_row_counts,
    )

    return canonical_df, summary


def save_canonical_outputs(
    canonical_df: pd.DataFrame,
    summary: dict[str, Any],
    config: ComparableBuilderConfig,
) -> dict[str, Path]:
    """Write canonical dataset and optional metadata artifacts."""
    outputs: dict[str, Path] = {}
    suffix = config.output_format.lower().strip()

    if config.write_canonical_dataset:
        canonical_path = config.output_dir / f"{config.output_stem}.{suffix}"
        _write_dataframe(canonical_df, canonical_path, config.output_format)
        outputs["canonical_dataset"] = canonical_path

    if config.write_versioned_output:
        dataset_version = str(summary.get("dataset_version") or "unknown_version")
        versioned_name = f"{dataset_version}.{suffix}"
        versioned_path = config.output_dir / versioned_name
        _write_dataframe(canonical_df, versioned_path, config.output_format)
        outputs["versioned_dataset"] = versioned_path

    if config.write_summary_json:
        summary_path = config.report_dir / config.summary_json_name
        write_summary_json(summary, summary_path)
        outputs["summary_json"] = summary_path

    return outputs


def generate_canonical_comparable_dataset(
    config: ComparableBuilderConfig | None = None,
) -> dict[str, Any]:
    """Public orchestration entry point."""
    active_config = config or ComparableBuilderConfig()

    canonical_df, summary = build_canonical_comparable_dataset(active_config)
    outputs = save_canonical_outputs(canonical_df, summary, active_config)

    LOGGER.info(
        "Comparable dataset build complete | final_rows=%s | comparable_rows=%s | mapped_rows=%s",
        len(canonical_df),
        summary.get("comparable_row_count"),
        summary.get("mapped_row_count"),
    )

    return {
        "dataframe": canonical_df,
        "summary": summary,
        "outputs": outputs,
        "config": asdict(active_config),
    }


# ---------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------
def parse_args() -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(
        description="Build canonical comparable benchmark dataset."
    )
    parser.add_argument(
        "--cleaned-path",
        type=Path,
        default=DEFAULT_CLEANED_PATH,
        help="Optional cleaned dataset path retained for config completeness.",
    )
    parser.add_argument(
        "--baseline-full-path",
        type=Path,
        default=DEFAULT_BASELINE_FULL_PATH,
        help="Preferred full scored baseline dataset path.",
    )
    parser.add_argument(
        "--baseline-subset-path",
        type=Path,
        default=DEFAULT_BASELINE_SUBSET_PATH,
        help="Fallback baseline comparable subset path.",
    )
    parser.add_argument(
        "--mapped-path",
        type=Path,
        default=DEFAULT_MAPPED_PATH,
        help="Category-mapped comparable dataset path.",
    )
    parser.add_argument(
        "--taxonomy-path",
        type=Path,
        default=SERVICE_TAXONOMY_PATH,
        help="Service taxonomy YAML path.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=PROCESSED_DATA_DIR,
        help="Directory for canonical dataset outputs.",
    )
    parser.add_argument(
        "--report-dir",
        type=Path,
        default=REPORTS_EVALUATION_DIR,
        help="Directory for summary JSON outputs.",
    )
    parser.add_argument(
        "--output-stem",
        type=str,
        default=DEFAULT_OUTPUT_STEM,
        help="Base filename stem for canonical dataset output.",
    )
    parser.add_argument(
        "--output-format",
        type=str,
        default=DEFAULT_OUTPUT_FORMAT,
        choices=["parquet", "csv", "json"],
        help="Output format for canonical dataset.",
    )
    parser.add_argument(
        "--builder-version",
        type=str,
        default=DEFAULT_BUILDER_VERSION,
        help="Builder version string written into the output dataset.",
    )
    parser.add_argument(
        "--keep-all-rows",
        action="store_true",
        help=(
            "Keep the full baseline-scored population in the canonical output "
            "instead of filtering to comparable contracts only."
        ),
    )
    parser.add_argument(
        "--write-versioned-output",
        action="store_true",
        help="Write a timestamp/versioned copy in addition to the stable canonical output.",
    )
    parser.add_argument(
        "--write-summary-json",
        action="store_true",
        help="Write a compact build summary JSON artifact.",
    )
    parser.add_argument(
        "--summary-json-name",
        type=str,
        default=DEFAULT_SUMMARY_JSON_NAME,
        help="Filename for the summary JSON artifact.",
    )
    parser.add_argument(
        "--log-level",
        type=str,
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Logging verbosity.",
    )
    return parser.parse_args()


def main() -> None:
    """CLI entry point."""
    args = parse_args()

    logging.basicConfig(
        level=getattr(logging, args.log_level.upper(), logging.INFO),
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )

    config = ComparableBuilderConfig(
        cleaned_path=args.cleaned_path,
        baseline_full_path=args.baseline_full_path,
        baseline_subset_path=args.baseline_subset_path,
        mapped_path=args.mapped_path,
        taxonomy_path=args.taxonomy_path,
        output_dir=args.output_dir,
        report_dir=args.report_dir,
        output_stem=args.output_stem,
        output_format=args.output_format,
        summary_json_name=args.summary_json_name,
        keep_all_rows=args.keep_all_rows,
        write_canonical_dataset=True,
        write_versioned_output=args.write_versioned_output,
        write_summary_json=args.write_summary_json,
        builder_version=args.builder_version,
    )

    result = generate_canonical_comparable_dataset(config)

    outputs = result["outputs"]
    if outputs:
        for name, path in outputs.items():
            LOGGER.info("Wrote %s -> %s", name, path)
    else:
        LOGGER.warning("No output files were written because all write flags were disabled.")


if __name__ == "__main__":
    main()
