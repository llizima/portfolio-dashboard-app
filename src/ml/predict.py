from __future__ import annotations

import json
import pickle
from pathlib import Path
from typing import Any

import pandas as pd
from scipy.sparse import csr_matrix

from src.ml.features import _structured_feature_rows


DEFAULT_MODEL_PATH = Path("src/models/baseline_logreg_model.pkl")
DEFAULT_METADATA_PATH = Path("src/models/baseline_logreg_metadata.json")
DEFAULT_INPUT_PATH = Path("src/data/processed/comparable_contracts.parquet")
DEFAULT_OUTPUT_PATH = Path("src/data/processed/comparable_contracts_scored.parquet")
DEFAULT_SUMMARY_PATH = Path("reports/evaluation/scoring_summary.md")
DEFAULT_THRESHOLD = 0.50


def load_model_and_metadata(
    model_path: str | Path = DEFAULT_MODEL_PATH,
    metadata_path: str | Path = DEFAULT_METADATA_PATH,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """
    Load the trained model artifact payload and training metadata.
    """
    model_path = Path(model_path)
    metadata_path = Path(metadata_path)

    if not model_path.exists():
        raise FileNotFoundError(f"Model artifact not found: {model_path}")

    if not metadata_path.exists():
        raise FileNotFoundError(f"Model metadata not found: {metadata_path}")

    with open(model_path, "rb") as f:
        payload = pickle.load(f)

    with open(metadata_path, "r", encoding="utf-8") as f:
        metadata = json.load(f)

    required_payload_keys = {
        "model",
        "text_vectorizer",
        "structured_vectorizer",
        "feature_names",
        "mode",
    }
    missing_payload_keys = required_payload_keys - set(payload.keys())
    if missing_payload_keys:
        missing_display = ", ".join(sorted(missing_payload_keys))
        raise ValueError(
            f"Saved model payload is missing required keys: {missing_display}"
        )

    return payload, metadata


def load_scoring_dataset(input_path: str | Path = DEFAULT_INPUT_PATH) -> pd.DataFrame:
    """
    Load a dataset to score.

    Currently supports parquet and CSV.
    """
    path = Path(input_path)
    if not path.exists():
        raise FileNotFoundError(f"Scoring input dataset not found: {path}")

    suffix = path.suffix.lower()

    if suffix == ".parquet":
        df = pd.read_parquet(path)
    elif suffix == ".csv":
        df = pd.read_csv(path)
    else:
        raise ValueError(
            f"Unsupported scoring input format: {suffix}. "
            "Supported formats are .parquet and .csv"
        )

    if df.empty:
        raise ValueError("Scoring input dataset is empty.")

    return df.copy()


def prepare_scoring_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    Normalize the scoring dataframe so required inference columns exist.

    Required for scoring:
    - description

    Optional but useful:
    - psc_code
    - naics_code
    """
    scoring_df = df.copy()
    scoring_df.columns = [str(col).strip().lower() for col in scoring_df.columns]

    if "description" not in scoring_df.columns:
        raise ValueError("Scoring dataset must contain a 'description' column.")

    if "psc_code" not in scoring_df.columns:
        scoring_df["psc_code"] = "MISSING"

    if "naics_code" not in scoring_df.columns:
        scoring_df["naics_code"] = "MISSING"

    scoring_df["description"] = scoring_df["description"].fillna("").astype(str).str.strip()
    scoring_df["psc_code"] = scoring_df["psc_code"].fillna("MISSING").astype(str).str.upper()
    scoring_df["naics_code"] = scoring_df["naics_code"].fillna("MISSING").astype(str).str.upper()

    return scoring_df


def prepare_scoring_features(
    scoring_df: pd.DataFrame,
    payload: dict[str, Any],
) -> csr_matrix:
    """
    Build scoring features using the fitted vectorizers stored in the saved model payload.

    This function assumes the model was trained in hybrid mode.
    """
    text_vectorizer = payload["text_vectorizer"]
    structured_vectorizer = payload["structured_vectorizer"]
    mode = payload["mode"]

    if mode != "hybrid":
        raise ValueError(
            f"Task 19 currently expects a hybrid model artifact, got mode='{mode}'."
        )

    text_matrix = text_vectorizer.transform(
        scoring_df["description"].fillna("").astype(str).tolist()
    )

    structured_records = _structured_feature_rows(
        scoring_df,
        include_baseline_context=False,
    )
    structured_matrix = structured_vectorizer.transform(structured_records)

    from scipy.sparse import hstack

    X = hstack([text_matrix, structured_matrix], format="csr")
    return X.tocsr()


from datetime import UTC, datetime


def score_records(
    X: csr_matrix,
    payload: dict[str, Any],
    threshold: float = DEFAULT_THRESHOLD,
) -> pd.DataFrame:
    """
    Score records using the trained model.

    Returns a dataframe with:
    - relevance_score
    - predicted_relevance_label
    """
    if threshold < 0.0 or threshold > 1.0:
        raise ValueError("threshold must be between 0.0 and 1.0")

    model = payload["model"]
    probabilities = model.predict_proba(X)[:, 1]
    predicted_labels = (probabilities >= threshold).astype(int)

    scored = pd.DataFrame(
        {
            "relevance_score": probabilities.astype(float),
            "predicted_relevance_label": predicted_labels.astype(int),
        }
    )

    return scored


def append_prediction_columns(
    scoring_df: pd.DataFrame,
    scored_df: pd.DataFrame,
    metadata: dict[str, Any],
    threshold: float = DEFAULT_THRESHOLD,
) -> pd.DataFrame:
    """
    Append scoring outputs and metadata columns to the original dataframe.

    Added columns:
    - model_version
    - relevance_score
    - predicted_relevance_label
    - scoring_timestamp
    - threshold_used
    """
    if len(scoring_df) != len(scored_df):
        raise ValueError(
            "scoring_df and scored_df must have the same number of rows."
        )

    output_df = scoring_df.copy().reset_index(drop=True)
    scored_df = scored_df.copy().reset_index(drop=True)

    config = metadata.get("config", {})
    model_version = (
        f"{metadata.get('model_class', 'unknown_model')}"
        f"_rows{metadata.get('row_count', 'unknown')}"
        f"_features{metadata.get('feature_count', 'unknown')}"
        f"_{config.get('mode', 'unknown')}"
    )

    scoring_timestamp = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")

    output_df["model_version"] = model_version
    output_df["relevance_score"] = scored_df["relevance_score"]
    output_df["predicted_relevance_label"] = scored_df[
        "predicted_relevance_label"
    ]
    output_df["scoring_timestamp"] = scoring_timestamp
    output_df["threshold_used"] = float(threshold)

    return output_df


def write_scored_dataset(
    output_df: pd.DataFrame,
    output_path: str | Path = DEFAULT_OUTPUT_PATH,
) -> Path:
    """
    Write the scored dataset to disk.

    Supported output formats:
    - .parquet
    - .csv
    """
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    suffix = path.suffix.lower()

    if suffix == ".parquet":
        output_df.to_parquet(path, index=False)
    elif suffix == ".csv":
        output_df.to_csv(path, index=False)
    else:
        raise ValueError(
            f"Unsupported output format: {suffix}. "
            "Supported formats are .parquet and .csv"
        )

    return path


def write_scoring_summary(
    *,
    summary_path: str | Path = DEFAULT_SUMMARY_PATH,
    input_path: str | Path,
    output_path: str | Path,
    row_count: int,
    threshold: float,
    metadata: dict[str, Any],
    scored_output_df: pd.DataFrame,
) -> Path:
    """
    Write a short markdown summary describing what was scored and how.
    """
    path = Path(summary_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    config = metadata.get("config", {})
    model_version = (
        f"{metadata.get('model_class', 'unknown_model')}"
        f"_rows{metadata.get('row_count', 'unknown')}"
        f"_features{metadata.get('feature_count', 'unknown')}"
        f"_{config.get('mode', 'unknown')}"
    )

    avg_score = float(scored_output_df["relevance_score"].mean())
    min_score = float(scored_output_df["relevance_score"].min())
    max_score = float(scored_output_df["relevance_score"].max())

    positive_count = int(
        (scored_output_df["predicted_relevance_label"] == 1).sum()
    )
    negative_count = int(
        (scored_output_df["predicted_relevance_label"] == 0).sum()
    )

    lines = [
        "# Scoring Summary",
        "",
        "## What was scored",
        "",
        f"- Input dataset: {Path(input_path)}",
        f"- Output dataset: {Path(output_path)}",
        f"- Rows scored: {row_count}",
        "",
        "## Model and scoring settings",
        "",
        f"- Model version: {model_version}",
        f"- Model class: {metadata.get('model_class', 'unknown')}",
        f"- Training mode: {config.get('mode', 'unknown')}",
        f"- Threshold used: {threshold:.2f}",
        "",
        "## Score distribution",
        "",
        f"- Average relevance score: {avg_score:.4f}",
        f"- Minimum relevance score: {min_score:.4f}",
        f"- Maximum relevance score: {max_score:.4f}",
        f"- Predicted relevant rows: {positive_count}",
        f"- Predicted non-relevant rows: {negative_count}",
        "",
        "## Output columns added",
        "",
        "- model_version",
        "- relevance_score",
        "- predicted_relevance_label",
        "- scoring_timestamp",
        "- threshold_used",
        "",
        "## Notes",
        "",
        "- This module applies an existing trained model only.",
        "- No retraining occurs during scoring.",
        "- The scored dataset preserves original input columns and appends prediction metadata.",
        "",
    ]

    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def run_scoring(
    *,
    input_path: str | Path = DEFAULT_INPUT_PATH,
    model_path: str | Path = DEFAULT_MODEL_PATH,
    metadata_path: str | Path = DEFAULT_METADATA_PATH,
    output_path: str | Path = DEFAULT_OUTPUT_PATH,
    summary_path: str | Path = DEFAULT_SUMMARY_PATH,
    threshold: float = DEFAULT_THRESHOLD,
) -> dict[str, Any]:
    """
    Run the full scoring pipeline end to end.
    """
    payload, metadata = load_model_and_metadata(
        model_path=model_path,
        metadata_path=metadata_path,
    )

    raw_df = load_scoring_dataset(input_path)
    scoring_df = prepare_scoring_dataframe(raw_df)
    X = prepare_scoring_features(scoring_df, payload)

    scored_df = score_records(X, payload, threshold=threshold)

    output_df = append_prediction_columns(
        scoring_df=scoring_df,
        scored_df=scored_df,
        metadata=metadata,
        threshold=threshold,
    )

    written_output = write_scored_dataset(output_df, output_path=output_path)

    written_summary = write_scoring_summary(
        summary_path=summary_path,
        input_path=input_path,
        output_path=written_output,
        row_count=len(output_df),
        threshold=threshold,
        metadata=metadata,
        scored_output_df=output_df,
    )

    return {
        "row_count": len(output_df),
        "output_path": str(written_output),
        "summary_path": str(written_summary),
        "threshold_used": float(threshold),
        "predicted_relevant_count": int(
            (output_df["predicted_relevance_label"] == 1).sum()
        ),
        "predicted_non_relevant_count": int(
            (output_df["predicted_relevance_label"] == 0).sum()
        ),
    }


def main() -> None:
    """
    Script entry point for Task 19 scoring.
    """
    results = run_scoring()

    print("Task 19 scoring complete.")
    print(f"Rows scored: {results['row_count']}")
    print(f"Threshold used: {results['threshold_used']:.2f}")
    print(
        f"Predicted relevant rows: {results['predicted_relevant_count']}"
    )
    print(
        f"Predicted non-relevant rows: {results['predicted_non_relevant_count']}"
    )
    print(f"Scored dataset saved to: {results['output_path']}")
    print(f"Summary report saved to: {results['summary_path']}")


if __name__ == "__main__":
    main()
