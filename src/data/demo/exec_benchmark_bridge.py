"""Benchmark bridge for executive dummy categories.

This module builds a small, auditable bridge table that maps executive dummy
service categories to benchmark pipeline categories and derives a per-unit
benchmark proxy using median award_amount by mapped_service_category.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import pandas as pd


EXEC_TO_BENCHMARK_CATEGORY: dict[str, str] = {
    "Rapid Prototyping": "prototyping",
    "Project Support": "project_program_support",
    "Events & Engagement": "event_hosting",
    "Facility Utilization": "workspace_collaboration",
}

EXPECTED_BENCHMARK_COLS: tuple[str, ...] = (
    "mapped_service_category",
    "award_amount",
)


@dataclass(frozen=True)
class BenchmarkSourceInfo:
    source_name: str
    row_count: int


def _require_columns(df: pd.DataFrame, cols: Iterable[str]) -> None:
    missing = [col for col in cols if col not in df.columns]
    if missing:
        raise ValueError(
            "Benchmark dataset is missing required columns: " + ", ".join(missing)
        )


def load_benchmark_source() -> tuple[pd.DataFrame, BenchmarkSourceInfo]:
    """Load benchmark dataset using locked source priority."""
    from app.components.loaders import (
        load_comparable_contracts,
        load_scored_dataset,
    )

    comparable_df = load_comparable_contracts()
    if not comparable_df.empty:
        _require_columns(comparable_df, EXPECTED_BENCHMARK_COLS)
        return comparable_df.copy(), BenchmarkSourceInfo(
            source_name="load_comparable_contracts",
            row_count=int(len(comparable_df)),
        )

    scored_df = load_scored_dataset()
    if not scored_df.empty:
        _require_columns(scored_df, EXPECTED_BENCHMARK_COLS)
        return scored_df.copy(), BenchmarkSourceInfo(
            source_name="load_scored_dataset",
            row_count=int(len(scored_df)),
        )

    raise ValueError(
        "No benchmark source is available: load_comparable_contracts() and "
        "load_scored_dataset() both returned empty dataframes."
    )


def _derive_benchmark_per_unit(benchmark_df: pd.DataFrame) -> pd.DataFrame:
    """Derive median award_amount by mapped_service_category."""
    working = benchmark_df.copy()
    working["mapped_service_category"] = (
        working["mapped_service_category"].astype("string").str.strip().str.lower()
    )
    working["award_amount"] = pd.to_numeric(
        working["award_amount"],
        errors="coerce",
    )

    working = working.dropna(
        subset=["mapped_service_category", "award_amount"]
    )
    working = working[working["mapped_service_category"] != ""]

    if working.empty:
        raise ValueError(
            "Benchmark dataset has no usable rows after coercing award_amount "
            "and mapped_service_category."
        )

    medians = (
        working.groupby(
            "mapped_service_category",
            as_index=False,
        )["award_amount"]
        .median()
        .rename(columns={"award_amount": "benchmark_per_unit"})
    )
    return medians


def build_exec_benchmark_bridge(exec_df: pd.DataFrame) -> pd.DataFrame:
    """Return bridge table with service_category -> benchmark_per_unit."""
    if "service_category" not in exec_df.columns:
        raise ValueError("Executive dataframe must include service_category.")

    exec_categories = sorted(
        exec_df["service_category"].dropna().astype(str).unique()
    )
    unmapped_exec = [
        cat for cat in exec_categories if cat not in EXEC_TO_BENCHMARK_CATEGORY
    ]
    if unmapped_exec:
        raise ValueError(
            "Executive categories missing mapping entries: " + ", ".join(unmapped_exec)
        )

    benchmark_df, _source = load_benchmark_source()
    benchmark_rates = _derive_benchmark_per_unit(benchmark_df)

    mapping_df = pd.DataFrame(
        [
            {"service_category": exec_cat, "benchmark_category": bench_cat}
            for exec_cat, bench_cat in EXEC_TO_BENCHMARK_CATEGORY.items()
        ]
    )

    bridge = mapping_df.merge(
        benchmark_rates,
        how="left",
        left_on="benchmark_category",
        right_on="mapped_service_category",
    ).drop(columns=["mapped_service_category"])

    missing_benchmark_categories = bridge[bridge["benchmark_per_unit"].isna()][
        "benchmark_category"
    ].tolist()
    if missing_benchmark_categories:
        raise ValueError(
            "Benchmark categories missing median award_amount values: "
            + ", ".join(sorted(set(missing_benchmark_categories)))
        )

    bridge["benchmark_per_unit"] = bridge["benchmark_per_unit"].astype(float)
    bridge = bridge[
        ["service_category", "benchmark_category", "benchmark_per_unit"]
    ]
    return bridge.sort_values("service_category").reset_index(drop=True)
