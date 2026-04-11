from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from src.ml.features import load_labeled_data


DEFAULT_LABEL_PATH = Path("src/data/labels/high_precision_seed.csv")
DEFAULT_METADATA_PATH = Path("src/models/baseline_logreg_metadata.json")

EXPECTED_REQUIRED_COLUMNS: tuple[str, ...] = (
    "description",
    "relevance_label",
)

OPTIONAL_CATEGORY_COLUMNS: tuple[str, ...] = (
    "category_label_optional",
    "mapped_service_category",
)

VALID_RELEVANCE_LABELS: set[str] = {
    "relevant",
    "not_relevant",
    "ambiguous",
    "0",
    "1",
    "0.0",
    "1.0",
}


@dataclass(frozen=True)
class RetrainCheckConfig:
    """
    Configuration for lightweight retraining recommendation logic.
    """

    label_csv_path: str = str(DEFAULT_LABEL_PATH)
    metadata_path: str = str(DEFAULT_METADATA_PATH)

    # Retrain if labeled rows increased by at least this many rows
    min_new_labeled_rows: int = 25

    # Retrain if labeled rows increased by at least this fraction
    min_labeled_growth_pct: float = 0.20

    # Retrain if positive-class precision falls below this absolute floor
    min_precision_floor: float = 0.85

    # Retrain if precision drops by this many absolute points relative to prior metadata
    max_precision_drop: float = 0.05

    # Retrain if recall drops by this many absolute points relative to prior metadata
    max_recall_drop: float = 0.08

    # Retrain if too many rows have category labels outside the prior known category universe
    max_unknown_category_pct: float = 0.15


@dataclass(frozen=True)
class RetrainCheckResult:
    """
    Result of the retraining recommendation check.
    """

    recommend_retrain: bool
    reasons: list[str]
    checks: dict[str, Any]


def load_existing_model_metadata(
    metadata_path: str | Path = DEFAULT_METADATA_PATH,
) -> dict[str, Any]:
    """
    Load previously saved model metadata written by train.py.
    """
    path = Path(metadata_path)
    if not path.exists():
        raise FileNotFoundError(f"Model metadata not found: {path}")

    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def load_current_labeled_dataframe(
    label_csv_path: str | Path = DEFAULT_LABEL_PATH,
) -> pd.DataFrame:
    """
    Load current labeled data using the existing feature-engineering loader.
    """
    return load_labeled_data(
        label_csv_path,
        include_ambiguous=True,
        drop_missing_text=False,
    )


def check_schema_drift(df: pd.DataFrame) -> tuple[bool, list[str], dict[str, Any]]:
    """
    Check whether the labeled CSV has required columns and acceptable label values.
    """
    reasons: list[str] = []

    missing_required = [
        col for col in EXPECTED_REQUIRED_COLUMNS if col not in df.columns
    ]
    if missing_required:
        reasons.append(
            "Missing required labeled-data columns: "
            + ", ".join(missing_required)
        )

    observed_labels = set(df["relevance_label"].astype(str).str.strip().str.lower().unique())
    unknown_labels = sorted(observed_labels - VALID_RELEVANCE_LABELS)
    if unknown_labels:
        reasons.append(
            "Unexpected relevance labels found: " + ", ".join(unknown_labels)
        )

    passed = len(reasons) == 0

    return passed, reasons, {
        "missing_required_columns": missing_required,
        "observed_labels": sorted(observed_labels),
        "unknown_labels": unknown_labels,
    }


def check_labeled_volume_growth(
    current_df: pd.DataFrame,
    metadata: dict[str, Any],
    config: RetrainCheckConfig,
) -> tuple[bool, list[str], dict[str, Any]]:
    """
    Check whether labeled-data volume has grown enough to justify retraining.
    """
    reasons: list[str] = []

    current_rows = int(len(current_df))
    prior_rows = int(metadata.get("row_count", 0))
    row_delta = current_rows - prior_rows
    growth_pct = (row_delta / prior_rows) if prior_rows > 0 else 0.0

    triggered = False
    if row_delta >= config.min_new_labeled_rows:
        triggered = True
        reasons.append(
            f"Labeled data increased by {row_delta} rows (threshold: {config.min_new_labeled_rows})."
        )

    if prior_rows > 0 and growth_pct >= config.min_labeled_growth_pct:
        triggered = True
        reasons.append(
            f"Labeled data grew by {growth_pct:.1%} (threshold: {config.min_labeled_growth_pct:.1%})."
        )

    return not triggered, reasons, {
        "prior_row_count": prior_rows,
        "current_row_count": current_rows,
        "row_delta": row_delta,
        "growth_pct": round(growth_pct, 4),
    }


def check_performance_drop(
    metadata: dict[str, Any],
    config: RetrainCheckConfig,
    current_metrics: dict[str, float] | None = None,
) -> tuple[bool, list[str], dict[str, Any]]:
    """
    Check for performance degradation relative to prior saved metadata.

    Notes
    -----
    - If current_metrics is not supplied, this check is informational only.
    - Expected keys in current_metrics:
      - precision
      - recall
      - f1_score (optional)
    """
    reasons: list[str] = []

    prior_report = metadata.get("classification_report", {})
    prior_precision = None
    prior_recall = None

    try:
        prior_precision = float(prior_report["1"]["precision"])
    except Exception:
        pass

    try:
        prior_recall = float(prior_report["1"]["recall"])
    except Exception:
        pass

    if current_metrics is None:
        return True, [], {
            "prior_precision": prior_precision,
            "prior_recall": prior_recall,
            "current_metrics_available": False,
        }

    current_precision = current_metrics.get("precision")
    current_recall = current_metrics.get("recall")

    triggered = False

    if current_precision is not None:
        if current_precision < config.min_precision_floor:
            triggered = True
            reasons.append(
                f"Current precision {current_precision:.3f} is below floor {config.min_precision_floor:.3f}."
            )

        if prior_precision is not None and (prior_precision - current_precision) > config.max_precision_drop:
            triggered = True
            reasons.append(
                f"Precision dropped from {prior_precision:.3f} to {current_precision:.3f}."
            )

    if current_recall is not None and prior_recall is not None:
        if (prior_recall - current_recall) > config.max_recall_drop:
            triggered = True
            reasons.append(
                f"Recall dropped from {prior_recall:.3f} to {current_recall:.3f}."
            )

    return not triggered, reasons, {
        "prior_precision": prior_precision,
        "prior_recall": prior_recall,
        "current_precision": current_precision,
        "current_recall": current_recall,
        "current_metrics_available": True,
    }


def check_category_drift(
    current_df: pd.DataFrame,
    config: RetrainCheckConfig,
) -> tuple[bool, list[str], dict[str, Any]]:
    """
    Check whether labeled data contains unexpected or drifting category values.

    This is a lightweight drift check based on optional category columns.
    """
    reasons: list[str] = []

    category_col = None
    for col in OPTIONAL_CATEGORY_COLUMNS:
        if col in current_df.columns:
            category_col = col
            break

    if category_col is None:
        return True, [], {
            "category_column_used": None,
            "unknown_category_pct": 0.0,
            "unknown_categories": [],
        }

    working = current_df.copy()
    non_null = working[category_col].dropna().astype(str).str.strip().str.lower()
    non_blank = non_null[non_null != ""]

    if non_blank.empty:
        return True, [], {
            "category_column_used": category_col,
            "unknown_category_pct": 0.0,
            "unknown_categories": [],
        }

    allowed_categories = {
        "prototyping",
        "engineering_design_support",
        "project_program_support",
        "event_hosting",
        "workspace_collaboration",
        "innovation_ecosystem_access",
        "integrated_service_delivery",
        "technical_advisory_services",
        "development_program_services",
        "professional_services_support",
    }

    unknown_categories = sorted(set(non_blank.unique()) - allowed_categories)
    unknown_count = int(non_blank.isin(unknown_categories).sum()) if unknown_categories else 0
    unknown_pct = (unknown_count / len(non_blank)) if len(non_blank) > 0 else 0.0

    triggered = False
    if unknown_pct > config.max_unknown_category_pct:
        triggered = True
        reasons.append(
            f"Unknown category share is {unknown_pct:.1%}, above threshold {config.max_unknown_category_pct:.1%}."
        )

    return not triggered, reasons, {
        "category_column_used": category_col,
        "unknown_category_pct": round(unknown_pct, 4),
        "unknown_categories": unknown_categories,
    }


def run_retrain_check(
    config: RetrainCheckConfig | None = None,
    current_metrics: dict[str, float] | None = None,
) -> RetrainCheckResult:
    """
    Run all retraining recommendation checks and return a structured result.
    """
    config = config or RetrainCheckConfig()

    metadata = load_existing_model_metadata(config.metadata_path)
    current_df = load_current_labeled_dataframe(config.label_csv_path)

    all_reasons: list[str] = []
    checks: dict[str, Any] = {}

    schema_ok, schema_reasons, schema_details = check_schema_drift(current_df)
    checks["schema_drift"] = {
        "passed": schema_ok,
        "details": schema_details,
    }
    if not schema_ok:
        all_reasons.extend(schema_reasons)

    volume_ok, volume_reasons, volume_details = check_labeled_volume_growth(
        current_df=current_df,
        metadata=metadata,
        config=config,
    )
    checks["labeled_volume_growth"] = {
        "passed": volume_ok,
        "details": volume_details,
    }
    if not volume_ok:
        all_reasons.extend(volume_reasons)

    perf_ok, perf_reasons, perf_details = check_performance_drop(
        metadata=metadata,
        config=config,
        current_metrics=current_metrics,
    )
    checks["performance_drop"] = {
        "passed": perf_ok,
        "details": perf_details,
    }
    if not perf_ok:
        all_reasons.extend(perf_reasons)

    category_ok, category_reasons, category_details = check_category_drift(
        current_df=current_df,
        config=config,
    )
    checks["category_drift"] = {
        "passed": category_ok,
        "details": category_details,
    }
    if not category_ok:
        all_reasons.extend(category_reasons)

    recommend_retrain = len(all_reasons) > 0

    return RetrainCheckResult(
        recommend_retrain=recommend_retrain,
        reasons=all_reasons,
        checks=checks,
    )


def main() -> None:
    """
    CLI entry point for Task 29 retraining recommendation checks.
    """
    result = run_retrain_check()

    print("Retrain recommendation summary")
    print(f"Recommend retrain: {result.recommend_retrain}")

    if result.reasons:
        print("Reasons:")
        for reason in result.reasons:
            print(f"- {reason}")
    else:
        print("Reasons: none")

    print("Check details:")
    print(json.dumps(result.checks, indent=2))


if __name__ == "__main__":
    main()
