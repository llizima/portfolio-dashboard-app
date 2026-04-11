"""
Clean and normalize raw USAspending contract data into a processed analytical
table.

Purpose
-------
This module reads raw JSON artifacts produced by the ingestion pipeline,
extracts contract rows from USAspending combined or paginated outputs,
normalizes fields into a consistent analytical schema, handles duplicates,
summarizes missingness, and writes processed outputs for downstream benchmark,
ML, and dashboard layers.

This module is intentionally limited to:
- raw file discovery
- raw JSON parsing
- dataframe normalization
- data type cleaning
- duplicate handling
- missingness profiling
- processed dataset persistence

It does NOT perform:
- proxy filtering
- service taxonomy classification
- ML scoring
- KPI aggregation
- dashboard rendering
- business scenario calculations
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import pandas as pd

from src.config.settings import (
    DEFAULT_OUTPUT_FORMAT,
    PROCESSED_DATA_DIR,
    RAW_DATA_DIR,
    ensure_directories,
    validate_settings,
)

LOGGER = logging.getLogger(__name__)


RAW_TO_CLEAN_COLUMN_MAP: dict[str, str] = {
    "Award ID": "award_id",
    "generated_internal_id": "generated_internal_id",
    "Award Amount": "award_amount",
    "Total Outlays": "total_outlays",
    "Description": "description",
    "Contract Award Type": "contract_award_type",
    "Awarding Agency": "awarding_agency",
    "Awarding Agency Code": "awarding_agency_code",
    "Awarding Sub Agency": "awarding_sub_agency",
    "Funding Agency": "funding_agency",
    "Funding Sub Agency": "funding_sub_agency",
    "Recipient Name": "recipient_name",
    "Recipient UEI": "recipient_uei",
    "Start Date": "start_date",
    "End Date": "end_date",
    "Base Obligation Date": "base_obligation_date",
}

NESTED_FIELD_MAP: dict[str, tuple[str, str]] = {
    "PSC": ("psc_code", "psc_description"),
    "NAICS": ("naics_code", "naics_description"),
}

STANDARD_COLUMN_ORDER: list[str] = [
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
]

DATE_COLUMNS = ["start_date", "end_date", "base_obligation_date"]
NUMERIC_COLUMNS = ["award_amount", "total_outlays"]
TEXT_COLUMNS = [
    "award_id",
    "generated_internal_id",
    "description",
    "contract_award_type",
    "awarding_agency",
    "awarding_agency_code",
    "awarding_sub_agency",
    "funding_agency",
    "funding_sub_agency",
    "recipient_name",
    "recipient_uei",
    "psc_code",
    "psc_description",
    "naics_code",
    "naics_description",
    "source_file",
    "run_id",
    "query_name",
]

DEFAULT_DEDUPE_SUBSET: tuple[str, ...] = (
    "award_id",
    "generated_internal_id",
    "award_amount",
    "recipient_name",
    "start_date",
    "end_date",
)

RAW_FILE_PATTERN = re.compile(
    r"(?P<query_name>.+?)_fy(?P<fiscal_year>\d{4})_(?P<run_id>.+?\d{8}T\d{6}Z)",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class RawFileContext:
    """Metadata inferred from a raw artifact path."""

    source_file: Path
    run_id: str | None
    query_name: str | None
    fiscal_year: int | None


@dataclass(frozen=True)
class TransformConfig:
    """Configuration for the raw-to-clean transform stage."""

    raw_root: Path
    processed_dir: Path
    output_stem: str = "usaspending_contracts_cleaned"
    output_format: str = "parquet"
    dedupe_subset: tuple[str, ...] = DEFAULT_DEDUPE_SUBSET


def get_usaspending_raw_root() -> Path:
    """
    Return the default USAspending raw data root.

    The ingestion client defaults to RAW_DATA_DIR / 'usaspending' when saving
    raw responses, so this transform stage follows that convention first.
    """
    return RAW_DATA_DIR / "usaspending"


def discover_raw_json_files(raw_root: Path) -> list[Path]:
    """
    Recursively discover raw USAspending JSON artifacts.

    Preference is given to combined files because they already contain the
    full results set for a run. If no combined files are found, page files
    and other JSON files are considered.
    """
    if not raw_root.exists():
        raise FileNotFoundError(f"Raw root does not exist: {raw_root}")

    all_json = sorted(raw_root.rglob("*.json"))
    if not all_json:
        raise FileNotFoundError(f"No JSON files found under: {raw_root}")

    combined_files = [
        path for path in all_json if path.name.endswith("_combined.json")
    ]
    if combined_files:
        LOGGER.info(
            "Discovered combined raw files",
            extra={"count": len(combined_files)},
        )
        return combined_files

    LOGGER.info(
        "No combined raw files found; using all JSON files",
        extra={"count": len(all_json)},
    )
    return all_json


def parse_raw_file_context(path: Path) -> RawFileContext:
    """
    Infer lineage metadata from a raw file path.

    Expected examples:
    - benchmark_foundry_fy2024_20260326T120000Z_combined.json
    - benchmark_foundry_fy2024_20260326T120000Z_page_1.json
    """
    stem = path.stem
    match = RAW_FILE_PATTERN.search(stem)

    run_id: str | None = None
    query_name: str | None = None
    fiscal_year: int | None = None

    if match:
        query_name = match.group("query_name")
        run_id = match.group("run_id")
        fiscal_year = int(match.group("fiscal_year"))

    return RawFileContext(
        source_file=path,
        run_id=run_id,
        query_name=query_name,
        fiscal_year=fiscal_year,
    )


def read_json_file(path: Path) -> dict[str, Any]:
    """Read a JSON artifact from disk."""
    with path.open("r", encoding="utf-8") as file:
        payload = json.load(file)

    if not isinstance(payload, dict):
        raise ValueError(
            f"Expected top-level JSON object in {path}, got "
            f"{type(payload).__name__}"
        )
    return payload


def extract_results_from_raw_payload(
    payload: dict[str, Any],
) -> list[dict[str, Any]]:
    """
    Extract result rows from a USAspending raw payload.

    Supports:
    - combined outputs with `results`
    - page outputs with `results`
    """
    results = payload.get("results", [])
    if results is None:
        return []
    if not isinstance(results, list):
        raise ValueError("Raw payload 'results' must be a list if present.")
    return [row for row in results if isinstance(row, dict)]


def records_from_raw_file(path: Path) -> list[dict[str, Any]]:
    """
    Extract result records from a raw file and attach lineage metadata.
    """
    payload = read_json_file(path)
    results = extract_results_from_raw_payload(payload)
    context = parse_raw_file_context(path)

    request_metadata = payload.get("request_metadata", {}) or {}
    base_payload = request_metadata.get("base_payload", {}) or {}
    filters = base_payload.get("filters", {}) or {}
    time_period = filters.get("time_period", []) or []

    inferred_fiscal_year = context.fiscal_year
    if inferred_fiscal_year is None and time_period:
        # Weak fallback: use the end date year if available
        last_period = time_period[-1]
        end_date = str(last_period.get("end_date", "")).strip()
        year_match = re.match(r"(\d{4})-\d{2}-\d{2}", end_date)
        if year_match:
            inferred_fiscal_year = int(year_match.group(1))

    query_name = context.query_name
    if query_name is None:
        query_name = str(base_payload.get("query_name", "")).strip() or None

    output_rows: list[dict[str, Any]] = []
    for row in results:
        enriched = dict(row)
        enriched["source_file"] = str(path)
        enriched["run_id"] = context.run_id
        enriched["query_name"] = query_name
        enriched["fiscal_year"] = inferred_fiscal_year
        output_rows.append(enriched)

    return output_rows


def load_raw_records(raw_files: Iterable[Path]) -> list[dict[str, Any]]:
    """
    Load and combine records from many raw files.
    """
    all_rows: list[dict[str, Any]] = []
    for path in raw_files:
        try:
            file_rows = records_from_raw_file(path)
            LOGGER.info(
                "Loaded raw records from file",
                extra={"file": str(path), "row_count": len(file_rows)},
            )
            all_rows.extend(file_rows)
        except Exception as exc:
            LOGGER.exception("Failed to parse raw file: %s", path)
            raise RuntimeError(f"Failed to parse raw file {path}") from exc
    return all_rows


def snake_case(value: str) -> str:
    """
    Convert a string into snake_case.
    """
    cleaned = re.sub(r"[^0-9a-zA-Z]+", "_", value).strip("_")
    cleaned = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", cleaned)
    cleaned = re.sub(r"_+", "_", cleaned)
    return cleaned.lower()


def normalize_column_names(df: pd.DataFrame) -> pd.DataFrame:
    """
    Rename known USAspending fields to stable analytical names, then apply
    snake_case to any remaining columns.
    """
    rename_map: dict[str, str] = {}
    for column in df.columns:
        if column in RAW_TO_CLEAN_COLUMN_MAP:
            rename_map[column] = RAW_TO_CLEAN_COLUMN_MAP[column]
        else:
            rename_map[column] = snake_case(str(column))
    return df.rename(columns=rename_map)


def _extract_code_and_description(value: Any) -> tuple[Any, Any]:
    """
    Extract code and description from a nested dict-like PSC/NAICS field.

    Handles common shapes such as:
    - {"code": "...", "description": "..."}
    - {"id": "...", "description": "..."}
    - strings or nulls
    """
    if isinstance(value, dict):
        code = (
            value.get("code")
            or value.get("id")
            or value.get("value")
            or value.get("naics")
            or value.get("psc")
        )
        description = (
            value.get("description")
            or value.get("desc")
            or value.get("label")
            or value.get("name")
        )
        return code, description

    if value is None:
        return None, None

    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None, None

    return str(value), None


def expand_nested_code_fields(df: pd.DataFrame) -> pd.DataFrame:
    """
    Flatten nested PSC and NAICS columns into separate code and description
    fields.
    """
    for raw_column, (code_column, desc_column) in NESTED_FIELD_MAP.items():
        normalized_source = RAW_TO_CLEAN_COLUMN_MAP.get(
            raw_column,
            snake_case(raw_column),
        )
        source_column = (
            raw_column if raw_column in df.columns else normalized_source
        )

        if source_column not in df.columns:
            if code_column not in df.columns:
                df[code_column] = None
            if desc_column not in df.columns:
                df[desc_column] = None
            continue

        extracted = df[source_column].apply(_extract_code_and_description)
        df[code_column] = extracted.apply(lambda item: item[0])
        df[desc_column] = extracted.apply(lambda item: item[1])

        if source_column not in {code_column, desc_column}:
            df = df.drop(columns=[source_column], errors="ignore")

    return df


def ensure_expected_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Guarantee a stable schema even if some columns are missing from raw data.
    """
    expected_columns = (
        set(STANDARD_COLUMN_ORDER)
        | set(NUMERIC_COLUMNS)
        | set(DATE_COLUMNS)
        | set(TEXT_COLUMNS)
    )
    for column in expected_columns:
        if column not in df.columns:
            df[column] = None
    return df


def normalize_text(value: Any) -> str | None:
    """
    Normalize a scalar text value.

    Returns None for missing/blank values.
    """
    if value is None or pd.isna(value):
        return None

    text = str(value).strip()
    text = re.sub(r"\s+", " ", text)
    return text if text else None


def clean_text_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Normalize whitespace and blank values for configured text columns.
    """
    for column in TEXT_COLUMNS:
        if column in df.columns:
            df[column] = df[column].apply(normalize_text)
    return df


def convert_numeric_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Convert configured numeric columns to numeric dtype.
    """
    for column in NUMERIC_COLUMNS:
        if column in df.columns:
            df[column] = pd.to_numeric(df[column], errors="coerce")
    return df


def convert_date_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Convert configured date columns to pandas datetime.
    """
    for column in DATE_COLUMNS:
        if column in df.columns:
            df[column] = pd.to_datetime(df[column], errors="coerce", utc=False)
    return df


def add_derived_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add analytical convenience fields used by downstream benchmark and ML
    stages.
    """
    if "description" in df.columns:
        df["description_clean"] = (
            df["description"]
            .apply(normalize_text)
            .apply(lambda x: x.lower() if isinstance(x, str) else None)
        )
    else:
        df["description_clean"] = None

    def build_text_all(row: pd.Series) -> str | None:
        parts = [
            normalize_text(row.get("description")),
            normalize_text(row.get("psc_description")),
            normalize_text(row.get("naics_description")),
        ]
        parts = [part for part in parts if part]
        return " | ".join(parts) if parts else None

    df["text_all"] = df.apply(build_text_all, axis=1)

    if "start_date" in df.columns and "end_date" in df.columns:
        duration = df["end_date"] - df["start_date"]
        df["award_duration_days"] = duration.dt.days
    else:
        df["award_duration_days"] = None

    df["processed_at"] = datetime.now(timezone.utc).isoformat()

    return df


def build_record_hash(df: pd.DataFrame, columns: list[str]) -> pd.Series:
    """
    Build a deterministic record hash across selected columns.
    """
    safe_columns = [column for column in columns if column in df.columns]
    if not safe_columns:
        safe_columns = list(df.columns)

    def hash_row(row: pd.Series) -> str:
        payload = "||".join(
            "" if pd.isna(row[col]) else str(row[col]) for col in safe_columns
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    return df.apply(hash_row, axis=1)


def flag_duplicates(
    df: pd.DataFrame,
    subset: tuple[str, ...],
) -> pd.DataFrame:
    """
    Add duplicate flags and record hashes.
    """
    hash_columns = [
        "award_id",
        "generated_internal_id",
        "award_amount",
        "recipient_name",
        "start_date",
        "end_date",
        "description_clean",
        "source_file",
    ]
    df["record_hash"] = build_record_hash(df, hash_columns)

    safe_subset = [column for column in subset if column in df.columns]
    if safe_subset:
        df["is_duplicate_row"] = df.duplicated(
            subset=safe_subset,
            keep="first",
        )
    else:
        df["is_duplicate_row"] = df.duplicated(keep="first")

    return df


def drop_preferred_duplicates(
    df: pd.DataFrame,
    subset: tuple[str, ...],
) -> pd.DataFrame:
    """
    Drop duplicates using a practical subset after sorting for record quality.

    Preference is given to rows with:
    - non-null award_id
    - non-null generated_internal_id
    - longer descriptions
    """
    working = df.copy()

    working["_has_award_id"] = (
        working["award_id"].notna().astype(int)
        if "award_id" in working.columns
        else 0
    )
    working["_has_generated_internal_id"] = (
        working["generated_internal_id"].notna().astype(int)
        if "generated_internal_id" in working.columns
        else 0
    )
    working["_description_len"] = (
        working["description"].fillna("").astype(str).str.len()
        if "description" in working.columns
        else 0
    )

    working = working.sort_values(
        by=["_has_award_id", "_has_generated_internal_id", "_description_len"],
        ascending=[False, False, False],
    )

    safe_subset = [column for column in subset if column in working.columns]
    if safe_subset:
        working = working.drop_duplicates(subset=safe_subset, keep="first")
    else:
        working = working.drop_duplicates(keep="first")

    working = working.drop(
        columns=[
            "_has_award_id",
            "_has_generated_internal_id",
            "_description_len",
        ],
        errors="ignore",
    )
    return working


def build_missingness_summary(df: pd.DataFrame) -> pd.DataFrame:
    """
    Produce a column-level missingness profile.
    """
    rows: list[dict[str, Any]] = []
    total_rows = len(df)

    for column in df.columns:
        missing_count = int(df[column].isna().sum())
        non_null_count = int(total_rows - missing_count)
        missing_pct = (
            float((missing_count / total_rows) * 100) if total_rows else 0.0
        )
        rows.append(
            {
                "column_name": column,
                "dtype": str(df[column].dtype),
                "missing_count": missing_count,
                "non_null_count": non_null_count,
                "missing_pct": round(missing_pct, 4),
            }
        )

    return pd.DataFrame(rows).sort_values(
        by=["missing_pct", "column_name"],
        ascending=[False, True],
    )


def build_processing_summary(
    df_raw: pd.DataFrame,
    df_clean: pd.DataFrame,
    raw_files: list[Path],
    output_path: Path,
    missingness_path: Path,
    duplicates_flagged: int,
    duplicates_removed: int,
) -> dict[str, Any]:
    """
    Build a lightweight processing summary for auditability.
    """
    return {
        "status": "success",
        "processed_at": datetime.now(timezone.utc).isoformat(),
        "schema_version": "1.0",
        "raw_file_count": len(raw_files),
        "raw_files": [str(path) for path in raw_files],
        "raw_row_count": int(len(df_raw)),
        "cleaned_row_count": int(len(df_clean)),
        "duplicates_flagged": int(duplicates_flagged),
        "duplicates_removed": int(duplicates_removed),
        "output_dataset_path": str(output_path),
        "missingness_summary_path": str(missingness_path),
        "columns_present": list(df_clean.columns),
    }


def reorder_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Reorder columns using the standard preferred order, then append any extras.
    """
    preferred = [
        column for column in STANDARD_COLUMN_ORDER if column in df.columns
    ]
    extras = [column for column in df.columns if column not in preferred]
    return df[preferred + extras]


def transform_raw_contract_data(
    raw_files: list[Path],
    *,
    dedupe_subset: tuple[str, ...],
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    """
    Main raw-to-clean transformation pipeline.
    """
    records = load_raw_records(raw_files)
    if not records:
        raise ValueError(
            "No valid records were loaded from the provided raw files."
        )

    df_raw = pd.DataFrame(records)

    df = df_raw.copy()
    df = normalize_column_names(df)
    df = expand_nested_code_fields(df)
    df = ensure_expected_columns(df)
    df = clean_text_columns(df)
    df = convert_numeric_columns(df)
    df = convert_date_columns(df)
    df = add_derived_columns(df)
    df = flag_duplicates(df, subset=dedupe_subset)

    duplicates_flagged = int(
        df["is_duplicate_row"].sum()
        if "is_duplicate_row" in df.columns
        else 0
    )

    cleaned_df = drop_preferred_duplicates(df, subset=dedupe_subset)
    duplicates_removed = int(len(df) - len(cleaned_df))

    cleaned_df = ensure_expected_columns(cleaned_df)
    cleaned_df = reorder_columns(cleaned_df)

    missingness_df = build_missingness_summary(cleaned_df)

    placeholder_output_path = Path("<pending>")
    placeholder_missingness_path = Path("<pending>")

    summary = build_processing_summary(
        df_raw=df_raw,
        df_clean=cleaned_df,
        raw_files=raw_files,
        output_path=placeholder_output_path,
        missingness_path=placeholder_missingness_path,
        duplicates_flagged=duplicates_flagged,
        duplicates_removed=duplicates_removed,
    )

    return cleaned_df, missingness_df, summary


def write_processed_dataset(
    df: pd.DataFrame,
    processed_dir: Path,
    output_stem: str,
    output_format: str,
) -> Path:
    """
    Write the processed analytical dataset to disk.
    """
    processed_dir.mkdir(parents=True, exist_ok=True)

    output_format = output_format.lower().strip()
    if output_format == "parquet":
        output_path = processed_dir / f"{output_stem}.parquet"
        df.to_parquet(output_path, index=False)
        return output_path

    if output_format == "csv":
        output_path = processed_dir / f"{output_stem}.csv"
        df.to_csv(output_path, index=False)
        return output_path

    raise ValueError("output_format must be either 'parquet' or 'csv'.")


def write_missingness_summary(
    summary_df: pd.DataFrame,
    processed_dir: Path,
    output_stem: str,
) -> Path:
    """
    Write the missingness summary CSV.
    """
    processed_dir.mkdir(parents=True, exist_ok=True)
    output_path = processed_dir / f"{output_stem}_missingness.csv"
    summary_df.to_csv(output_path, index=False)
    return output_path


def write_processing_summary(
    summary: dict[str, Any],
    processed_dir: Path,
    output_stem: str,
) -> Path:
    """
    Write the processing summary JSON.
    """
    processed_dir.mkdir(parents=True, exist_ok=True)
    output_path = processed_dir / f"{output_stem}_processing_summary.json"
    with output_path.open("w", encoding="utf-8") as file:
        json.dump(summary, file, indent=2, ensure_ascii=False)
    return output_path


def run_clean_transform(
    *,
    raw_root: Path | None = None,
    output_format: str | None = None,
    output_stem: str = "usaspending_contracts_cleaned",
) -> dict[str, Any]:
    """
    Execute the full raw-to-clean transformation stage.
    """
    validate_settings()
    ensure_directories()

    resolved_raw_root = raw_root or get_usaspending_raw_root()
    resolved_output_format = (
        output_format or DEFAULT_OUTPUT_FORMAT
    ).lower().strip()

    if resolved_output_format not in {"parquet", "csv"}:
        LOGGER.warning(
            (
                "Unsupported default output format for this transform stage; "
                "falling back to parquet."
            ),
            extra={"requested_output_format": resolved_output_format},
        )
        resolved_output_format = "parquet"

    config = TransformConfig(
        raw_root=resolved_raw_root,
        processed_dir=PROCESSED_DATA_DIR,
        output_stem=output_stem,
        output_format=resolved_output_format,
    )

    LOGGER.info(
        "Starting clean transform stage",
        extra={
            "raw_root": str(config.raw_root),
            "processed_dir": str(config.processed_dir),
            "output_stem": config.output_stem,
            "output_format": config.output_format,
        },
    )

    raw_files = discover_raw_json_files(config.raw_root)
    cleaned_df, missingness_df, summary = transform_raw_contract_data(
        raw_files=raw_files,
        dedupe_subset=config.dedupe_subset,
    )

    dataset_path = write_processed_dataset(
        df=cleaned_df,
        processed_dir=config.processed_dir,
        output_stem=config.output_stem,
        output_format=config.output_format,
    )
    missingness_path = write_missingness_summary(
        summary_df=missingness_df,
        processed_dir=config.processed_dir,
        output_stem=config.output_stem,
    )

    summary["output_dataset_path"] = str(dataset_path)
    summary["missingness_summary_path"] = str(missingness_path)

    summary_path = write_processing_summary(
        summary=summary,
        processed_dir=config.processed_dir,
        output_stem=config.output_stem,
    )
    summary["processing_summary_path"] = str(summary_path)

    LOGGER.info(
        "Completed clean transform stage",
        extra={
            "raw_file_count": summary["raw_file_count"],
            "raw_row_count": summary["raw_row_count"],
            "cleaned_row_count": summary["cleaned_row_count"],
            "dataset_path": str(dataset_path),
        },
    )

    return summary


def build_arg_parser() -> argparse.ArgumentParser:
    """
    Build CLI parser for the transform stage.
    """
    parser = argparse.ArgumentParser(
        description=(
            "Clean and normalize raw USAspending data into a processed "
            "analytical table."
        )
    )
    parser.add_argument(
        "--raw-root",
        type=Path,
        default=None,
        help="Optional override for the USAspending raw data root.",
    )
    parser.add_argument(
        "--output-format",
        type=str,
        default=None,
        choices=["csv", "parquet"],
        help="Processed dataset output format.",
    )
    parser.add_argument(
        "--output-stem",
        type=str,
        default="usaspending_contracts_cleaned",
        help="Base filename stem for processed outputs.",
    )
    parser.add_argument(
        "--log-level",
        type=str,
        default="INFO",
        help="Logging level, e.g. DEBUG, INFO, WARNING.",
    )
    return parser


def main() -> None:
    """
    CLI entry point.
    """
    parser = build_arg_parser()
    args = parser.parse_args()

    logging.basicConfig(
        level=getattr(logging, args.log_level.upper(), logging.INFO),
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )

    summary = run_clean_transform(
        raw_root=args.raw_root,
        output_format=args.output_format,
        output_stem=args.output_stem,
    )

    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
