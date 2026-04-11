"""
Raw ingestion pipeline for USAspending benchmark pulls.

Purpose
-------
This module is the repeatable raw-ingestion entry point for benchmark-relevant
USAspending contract data. It is intentionally limited to:

- defining named query configurations
- calling the reusable USAspending client
- saving raw JSON outputs
- writing run manifests for auditability and reproducibility

It does NOT perform:
- dataframe normalization
- cleaning / feature engineering
- ML classification
- business KPI calculation
- dashboard transformation

Those belong in downstream pipeline stages.

Expected next step
------------------
A later extraction/normalization step should read these raw JSON artifacts,
flatten records into tabular form, add fiscal-year/agency metadata, and save
cleaned interim outputs for proxy filtering and benchmarking.
"""

from __future__ import annotations

import json
import logging
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.config import (
    DEFAULT_FISCAL_YEAR_END,
    DEFAULT_FISCAL_YEAR_START,
    RAW_DATA_DIR,
    ensure_directories,
    validate_settings,
)
from src.data.usaspending_client import (
    USAspendingClient,
    USAspendingRequestError,
)


LOGGER = logging.getLogger(__name__)


# ---------------------------------------------------------------------
# Query configuration models
# ---------------------------------------------------------------------
@dataclass(frozen=True)
class QueryConfig:
    """
    Named configuration for a single benchmark ingestion pull.

    Attributes
    ----------
    query_name : str
        Stable identifier for the query.
    description : str
        Human-readable purpose of the query.
    payload : dict[str, Any]
        Base USAspending POST payload.
    save_mode : str
        Raw save mode passed to USAspendingClient. Supported by current client:
        "combined" or "pages".
    enabled : bool
        Whether this query should run.
    """

    query_name: str
    description: str
    payload: dict[str, Any]
    save_mode: str = "combined"
    enabled: bool = True


# ---------------------------------------------------------------------
# Constants / default field selections
# ---------------------------------------------------------------------
DEFAULT_FIELDS: list[str] = [
    "Award ID",
    "generated_internal_id",
    "Award Amount",
    "Total Outlays",
    "Description",
    "Contract Award Type",
    "Awarding Agency",
    "Awarding Agency Code",
    "Awarding Sub Agency",
    "Funding Agency",
    "Funding Sub Agency",
    "Recipient Name",
    "Recipient UEI",
    "Start Date",
    "End Date",
    "Base Obligation Date",
    "PSC",
    "NAICS",
]

DEFAULT_AWARD_TYPE_CODES: list[str] = ["A", "B", "C", "D"]


# ---------------------------------------------------------------------
# Time helpers
# ---------------------------------------------------------------------
def fiscal_year_date_range(fiscal_year: int) -> tuple[str, str]:
    """
    Return the federal fiscal-year start and end dates.

    Example
    -------
    FY2024 -> ("2023-10-01", "2024-09-30")
    """
    start_date = f"{fiscal_year - 1}-10-01"
    end_date = f"{fiscal_year}-09-30"
    return start_date, end_date


def utc_now() -> datetime:
    """Return the current UTC timestamp."""
    return datetime.now(timezone.utc)


def build_run_id(prefix: str = "usaspending_ingest") -> str:
    """
    Build a deterministic run identifier using UTC time.

    Format example
    --------------
    usaspending_ingest_20260325T203000Z
    """
    return f"{prefix}_{utc_now().strftime('%Y%m%dT%H%M%SZ')}"


# ---------------------------------------------------------------------
# Directory / manifest helpers
# ---------------------------------------------------------------------
def get_usaspending_raw_root() -> Path:
    """Return the raw root directory for USAspending pulls."""
    return RAW_DATA_DIR / "usaspending"


def get_manifest_dir() -> Path:
    """Return the manifest directory under raw data."""
    return RAW_DATA_DIR / "manifests"


def prepare_run_directories(run_id: str) -> dict[str, Path]:
    """
    Create and return the directory structure for an ingestion run.
    """
    ensure_directories()

    raw_root = get_usaspending_raw_root()
    manifest_dir = get_manifest_dir()
    run_dir = raw_root / run_id

    raw_root.mkdir(parents=True, exist_ok=True)
    manifest_dir.mkdir(parents=True, exist_ok=True)
    run_dir.mkdir(parents=True, exist_ok=True)

    return {
        "raw_root": raw_root,
        "manifest_dir": manifest_dir,
        "run_dir": run_dir,
    }


def sanitize_name(value: str) -> str:
    """
    Convert a name into a filesystem-friendly stem component.
    """
    cleaned = value.strip().lower().replace(" ", "_").replace("-", "_")
    allowed: list[str] = []
    for ch in cleaned:
        if ch.isalnum() or ch == "_":
            allowed.append(ch)
    return "".join(allowed).strip("_")


def build_raw_file_stem(
    *,
    query_name: str,
    fiscal_year: int | None = None,
    run_id: str,
) -> str:
    """
    Build a deterministic raw output stem.

    Example
    -------
    ussocom_benchmark_fy2024_usaspending_ingest_20260325T203000Z
    """
    stem_parts = [sanitize_name(query_name)]
    if fiscal_year is not None:
        stem_parts.append(f"fy{fiscal_year}")
    stem_parts.append(run_id)
    return "_".join(stem_parts)


def summarize_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """
    Produce a compact, manifest-friendly summary of the request payload.
    """
    filters = payload.get("filters", {}) or {}
    agencies = filters.get("agencies", []) or []
    time_period = filters.get("time_period", []) or []

    return {
        "spending_level": payload.get("spending_level"),
        "limit": payload.get("limit"),
        "sort": payload.get("sort"),
        "order": payload.get("order"),
        "fields_count": len(payload.get("fields", []) or []),
        "award_type_codes": filters.get("award_type_codes", []),
        "agency_count": len(agencies),
        "agencies": agencies,
        "time_period": time_period,
    }


def write_manifest(manifest: dict[str, Any], manifest_path: Path) -> Path:
    """
    Save the manifest JSON to disk.
    """
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    with manifest_path.open("w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)
    return manifest_path


# ---------------------------------------------------------------------
# Query builders
# ---------------------------------------------------------------------
def build_base_payload(
    *,
    start_date: str,
    end_date: str,
    agencies: list[dict[str, Any]],
    limit: int = 100,
) -> dict[str, Any]:
    """
    Build the base spending_by_award payload.

    This mirrors the working notebook pattern:
    - contract-focused award types
    - explicit time_period
    - agency filter
    - descending Award Amount sort
    - awards-level spending
    """
    return {
        "filters": {
            "award_type_codes": DEFAULT_AWARD_TYPE_CODES,
            "time_period": [
                {
                    "start_date": start_date,
                    "end_date": end_date,
                }
            ],
            "agencies": agencies,
        },
        "fields": DEFAULT_FIELDS,
        "limit": limit,
        "page": 1,
        "sort": "Award Amount",
        "order": "desc",
        "spending_level": "awards",
    }


def build_default_query_configs(
    *,
    fiscal_year: int,
    include_dod: bool = True,
    include_federal: bool = True,
    page_limit: int = 100,
) -> list[QueryConfig]:
    """
    Build the default benchmark query set for a single fiscal year.

    Current priority is mission-aligned context filtering:
    USSOCOM primary, DoD secondary, federal optional.
    """
    start_date, end_date = fiscal_year_date_range(fiscal_year)

    queries: list[QueryConfig] = [
        QueryConfig(
            query_name="ussocom_benchmark",
            description=(
                "Primary benchmark pull for mission-aligned awards "
                "at the USSOCOM context level."
            ),
            payload=build_base_payload(
                start_date=start_date,
                end_date=end_date,
                agencies=[
                    {
                        "type": "awarding",
                        "tier": "subtier",
                        "name": "U.S. Special Operations Command",
                        "toptier_name": "Department of Defense",
                    }
                ],
                limit=page_limit,
            ),
            save_mode="combined",
        )
    ]

    if include_dod:
        queries.append(
            QueryConfig(
                query_name="dod_benchmark",
                description="Secondary benchmark pull for broader DoD comparison.",
                payload=build_base_payload(
                    start_date=start_date,
                    end_date=end_date,
                    agencies=[
                        {
                            "type": "awarding",
                            "tier": "toptier",
                            "name": "Department of Defense",
                        }
                    ],
                    limit=page_limit,
                ),
                save_mode="combined",
            )
        )

    if include_federal:
        federal_payload = build_base_payload(
            start_date=start_date,
            end_date=end_date,
            agencies=[],
            limit=page_limit,
        )
        # Remove empty agencies filter to avoid passing unnecessary structure.
        federal_payload["filters"].pop("agencies", None)

        queries.append(
            QueryConfig(
                query_name="federal_benchmark",
                description="Broader federal benchmark comparison pull.",
                payload=federal_payload,
                save_mode="combined",
            )
        )

    return queries


# ---------------------------------------------------------------------
# Query execution
# ---------------------------------------------------------------------
def execute_query(
    *,
    client: USAspendingClient,
    query: QueryConfig,
    run_id: str,
    run_dir: Path,
    fiscal_year: int | None = None,
) -> dict[str, Any]:
    """
    Execute one configured query and return manifest-ready metadata.
    """
    raw_file_stem = build_raw_file_stem(
        query_name=query.query_name,
        fiscal_year=fiscal_year,
        run_id=run_id,
    )

    try:
        result = client.search_spending_by_award(
            payload=deepcopy(query.payload),
            save_raw=True,
            raw_save_dir=run_dir,
            raw_file_stem=raw_file_stem,
            save_mode=query.save_mode,
        )

        page_metadata = result.get("page_metadata", {}) or {}
        request_metadata = result.get("request_metadata", {}) or {}
        output_files = request_metadata.get("saved_files", []) or []

        return {
            "query_name": query.query_name,
            "description": query.description,
            "endpoint": client.SEARCH_SPENDING_BY_AWARD_ENDPOINT,
            "payload_summary": summarize_payload(query.payload),
            "total_records": len(result.get("results", []) or []),
            "total_pages": page_metadata.get("pages_fetched", 0),
            "output_files": output_files,
            "status": "success",
            "error_message": None,
            "save_mode": query.save_mode,
            "fiscal_year": fiscal_year,
        }

    except USAspendingRequestError as exc:
        LOGGER.exception("USAspending query failed: %s", query.query_name)

        return {
            "query_name": query.query_name,
            "description": query.description,
            "endpoint": client.SEARCH_SPENDING_BY_AWARD_ENDPOINT,
            "payload_summary": summarize_payload(query.payload),
            "total_records": 0,
            "total_pages": 0,
            "output_files": [],
            "status": "failed",
            "error_message": str(exc),
            "save_mode": query.save_mode,
            "fiscal_year": fiscal_year,
        }


# ---------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------
def build_pipeline_manifest(
    *,
    run_id: str,
    query_results: list[dict[str, Any]],
    fiscal_years: list[int],
) -> dict[str, Any]:
    """
    Build the full run manifest.
    """
    succeeded = [q for q in query_results if q["status"] == "success"]
    failed = [q for q in query_results if q["status"] == "failed"]

    return {
        "run_id": run_id,
        "run_timestamp": utc_now().isoformat(),
        "pipeline_name": "usaspending_raw_ingestion",
        "source_system": "USAspending",
        "endpoint": USAspendingClient.SEARCH_SPENDING_BY_AWARD_ENDPOINT,
        "fiscal_years": fiscal_years,
        "query_run_count": len(query_results),
        "successful_query_count": len(succeeded),
        "failed_query_count": len(failed),
        "total_records_across_queries": sum(
            q["total_records"] for q in succeeded
        ),
        "query_runs": query_results,
        "notes": [
            "This manifest records raw ingestion only.",
            (
                "Downstream extraction should normalize raw JSON into interim "
                "tabular outputs."
            ),
            (
                "Downstream filtering/classification should implement proxy "
                "selection, taxonomy logic, and ML scoring."
            ),
        ],
    }


def run_ingestion_pipeline(
    *,
    fiscal_year_start: int = DEFAULT_FISCAL_YEAR_START,
    fiscal_year_end: int = DEFAULT_FISCAL_YEAR_END,
    include_dod: bool = True,
    include_federal: bool = True,
    page_limit: int = 100,
    log_level: str = "INFO",
) -> dict[str, Any]:
    """
    Run the full raw-ingestion pipeline.

    Parameters
    ----------
    fiscal_year_start : int
        First fiscal year to ingest, inclusive.
    fiscal_year_end : int
        Last fiscal year to ingest, inclusive.
    include_dod : bool
        Whether to include a broader DoD comparison pull.
    include_federal : bool
        Whether to include a broader federal comparison pull.
    page_limit : int
        USAspending page size. Keep 100 for normal full pulls; reduce for
        lighter smoke tests.
    log_level : str
        Logging level string.
    """
    logging.basicConfig(
        level=getattr(logging, log_level.upper(), logging.INFO),
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )

    validate_settings()

    if fiscal_year_start > fiscal_year_end:
        raise ValueError(
            "fiscal_year_start cannot be greater than fiscal_year_end."
        )

    run_id = build_run_id()
    paths = prepare_run_directories(run_id)
    run_dir = paths["run_dir"]
    manifest_path = paths["manifest_dir"] / f"{run_id}_manifest.json"

    LOGGER.info("Starting ingestion pipeline | run_id=%s", run_id)
    LOGGER.info("Run directory: %s", run_dir)

    client = USAspendingClient()
    fiscal_years = list(range(fiscal_year_start, fiscal_year_end + 1))

    query_results: list[dict[str, Any]] = []

    for fiscal_year in fiscal_years:
        LOGGER.info("Processing fiscal year %s", fiscal_year)

        queries = build_default_query_configs(
            fiscal_year=fiscal_year,
            include_dod=include_dod,
            include_federal=include_federal,
            page_limit=page_limit,
        )

        for query in queries:
            if not query.enabled:
                LOGGER.info("Skipping disabled query: %s", query.query_name)
                continue

            LOGGER.info(
                "Running query '%s' for FY%s",
                query.query_name,
                fiscal_year,
            )

            result_meta = execute_query(
                client=client,
                query=query,
                run_id=run_id,
                run_dir=run_dir,
                fiscal_year=fiscal_year,
            )
            query_results.append(result_meta)

    manifest = build_pipeline_manifest(
        run_id=run_id,
        query_results=query_results,
        fiscal_years=fiscal_years,
    )
    write_manifest(manifest, manifest_path)

    LOGGER.info("Manifest written: %s", manifest_path)
    LOGGER.info(
        "Pipeline finished | success=%s | failed=%s",
        manifest["successful_query_count"],
        manifest["failed_query_count"],
    )

    return manifest


def main() -> None:
    """
    Default command-line entry point.

    Current defaults are set for the full benchmark date range in settings.
    For lighter smoke tests, reduce the fiscal-year range or lower page_limit.
    """
    manifest = run_ingestion_pipeline(
        fiscal_year_start=DEFAULT_FISCAL_YEAR_START,
        fiscal_year_end=DEFAULT_FISCAL_YEAR_END,
        include_dod=True,
        include_federal=True,
        page_limit=100,
        log_level="INFO",
    )

    print("\nIngestion complete.")
    print(f"Run ID: {manifest['run_id']}")
    print(f"Manifest queries: {manifest['query_run_count']}")
    print(f"Successful queries: {manifest['successful_query_count']}")
    print(f"Failed queries: {manifest['failed_query_count']}")
    print(
        "Total records across successful queries: "
        f"{manifest['total_records_across_queries']}"
    )


if __name__ == "__main__":
    main()
