from __future__ import annotations

import pickle
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.metrics import (
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)

from src.ml.features import FeatureArtifacts, get_feature_matrix_and_target
from src.ml.rule_layer import apply_rule_layer


DEFAULT_MODEL_PATH = Path("src/models/baseline_logreg_model.pkl")
DEFAULT_LABEL_PATH = Path("src/data/labels/high_precision_seed.csv")
DEFAULT_REPORT_PATH = Path("reports/evaluation/model_vs_rules_report.md")


def load_model_payload(model_path: str | Path = DEFAULT_MODEL_PATH) -> dict[str, Any]:
    """
    Load the saved model artifact payload from disk.

    Expected payload keys from train.py:
    - model
    - text_vectorizer
    - structured_vectorizer
    - feature_names
    - mode
    """
    path = Path(model_path)
    if not path.exists():
        raise FileNotFoundError(f"Model artifact not found: {path}")

    with open(path, "rb") as f:
        payload = pickle.load(f)

    required_keys = {
        "model",
        "text_vectorizer",
        "structured_vectorizer",
        "feature_names",
        "mode",
    }
    missing = required_keys - set(payload.keys())
    if missing:
        missing_display = ", ".join(sorted(missing))
        raise ValueError(
            f"Saved model payload is missing required keys: {missing_display}"
        )

    return payload


def load_feature_artifacts(
    label_csv_path: str | Path = DEFAULT_LABEL_PATH,
) -> FeatureArtifacts:
    """
    Rebuild the labeled feature matrix using the same hybrid mode used in training.
    """
    return get_feature_matrix_and_target(
        label_csv_path,
        mode="hybrid",
        include_ambiguous=False,
        drop_missing_text=False,
    )


def predict_rules_only(df: pd.DataFrame) -> np.ndarray:
    """
    Produce deterministic rules-only predictions.

    For Task 18 comparison purposes:
    - hard_negative -> 0
    - strong_positive -> 1
    - needs_ml -> 0

    This gives a strict rules-only baseline.
    """
    predictions: list[int] = []

    for description in df["description"].fillna(""):
        result = apply_rule_layer(description)
        rule_label = result["rule_label"]

        if rule_label is None:
            predictions.append(0)
        else:
            predictions.append(int(rule_label))

    return np.array(predictions, dtype=int)


def predict_ml_only(
    payload: dict[str, Any],
    feature_artifacts: FeatureArtifacts,
    threshold: float = 0.50,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Produce ML-only predictions from the trained logistic regression model.
    """
    model = payload["model"]
    X = feature_artifacts.X

    probabilities = model.predict_proba(X)[:, 1]
    predictions = (probabilities >= threshold).astype(int)

    return predictions, probabilities


def predict_hybrid(
    payload: dict[str, Any],
    df: pd.DataFrame,
    feature_artifacts: FeatureArtifacts,
    positive_threshold: float = 0.80,
    negative_threshold: float = 0.30,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Produce hybrid predictions:
    - rule hard negative => 0
    - rule strong positive => 1
    - otherwise fall back to ML probability

    For evaluation purposes, this function always outputs a final 0/1 label.
    The returned probability array is:
    - 0.0 for hard-negative rule decisions
    - 1.0 for strong-positive rule decisions
    - ML probability for needs_ml rows
    """
    model = payload["model"]
    X = feature_artifacts.X
    ml_probabilities = model.predict_proba(X)[:, 1]

    final_predictions: list[int] = []
    final_probabilities: list[float] = []

    descriptions = df["description"].fillna("").tolist()

    for idx, description in enumerate(descriptions):
        rule_result = apply_rule_layer(description)
        rule_label = rule_result["rule_label"]

        if rule_label == 0:
            final_predictions.append(0)
            final_probabilities.append(0.0)
            continue

        if rule_label == 1:
            final_predictions.append(1)
            final_probabilities.append(1.0)
            continue

        ml_probability = float(ml_probabilities[idx])

        if ml_probability >= positive_threshold:
            final_predictions.append(1)
        elif ml_probability <= negative_threshold:
            final_predictions.append(0)
        else:
            # For evaluation we must force a label.
            # We resolve the uncertain middle band using a simple 0.50 split.
            final_predictions.append(int(ml_probability >= 0.50))

        final_probabilities.append(ml_probability)

    return np.array(final_predictions, dtype=int), np.array(final_probabilities)


def compute_binary_metrics(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    y_prob: np.ndarray | None = None,
) -> dict[str, Any]:
    """
    Compute core binary classification metrics for Task 18.
    """
    cm = confusion_matrix(y_true, y_pred)

    metrics: dict[str, Any] = {
        "precision": float(precision_score(y_true, y_pred, zero_division=0)),
        "recall": float(recall_score(y_true, y_pred, zero_division=0)),
        "f1": float(f1_score(y_true, y_pred, zero_division=0)),
        "confusion_matrix": cm.tolist(),
    }

    if y_prob is not None:
        try:
            metrics["roc_auc"] = float(roc_auc_score(y_true, y_prob))
        except ValueError:
            metrics["roc_auc"] = None
    else:
        metrics["roc_auc"] = None

    return metrics


def build_threshold_tradeoff_table(
    y_true: np.ndarray,
    probabilities: np.ndarray,
) -> pd.DataFrame:
    """
    Evaluate ML threshold tradeoffs across a small threshold grid.
    """
    thresholds = [0.10, 0.20, 0.30, 0.40, 0.50, 0.60, 0.70, 0.80, 0.90]
    rows: list[dict[str, float]] = []

    for threshold in thresholds:
        preds = (probabilities >= threshold).astype(int)
        rows.append(
            {
                "threshold": threshold,
                "precision": float(precision_score(y_true, preds, zero_division=0)),
                "recall": float(recall_score(y_true, preds, zero_division=0)),
                "f1": float(f1_score(y_true, preds, zero_division=0)),
            }
        )

    return pd.DataFrame(rows)


def _format_metric_block(title: str, metrics: dict[str, Any]) -> str:
    """
    Format one metric section for the markdown report.
    """
    lines = [
        f"## {title}",
        "",
        f"- Precision: {metrics['precision']:.4f}",
        f"- Recall: {metrics['recall']:.4f}",
        f"- F1: {metrics['f1']:.4f}",
        f"- ROC AUC: {metrics['roc_auc']:.4f}" if metrics["roc_auc"] is not None else "- ROC AUC: N/A",
        f"- Confusion Matrix: {metrics['confusion_matrix']}",
        "",
    ]
    return "\n".join(lines)


def write_evaluation_report(
    *,
    report_path: str | Path,
    rules_metrics: dict[str, Any],
    ml_metrics: dict[str, Any],
    hybrid_metrics: dict[str, Any],
    threshold_df: pd.DataFrame,
) -> Path:
    """
    Write a human-readable markdown report for Task 18.
    """
    path = Path(report_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    lines: list[str] = [
        "# Task 18 — Baseline Rules vs Model Evaluation",
        "",
        "Purpose: determine whether ML adds value beyond deterministic rules.",
        "",
        _format_metric_block("Rules-Only Baseline", rules_metrics),
        _format_metric_block("ML-Only Baseline", ml_metrics),
        _format_metric_block("Hybrid Rules + ML", hybrid_metrics),
        "## Threshold Tradeoff Summary (ML-Only)",
        "",
    ]

    if threshold_df.empty:
        lines.append("No threshold tradeoff data available.")
    else:
        lines.append(threshold_df.to_markdown(index=False))

    lines.append("")
    lines.append("## Interpretation Notes")
    lines.append("")
    lines.append(
        "- Rules-only is expected to be stricter and less flexible because non-matching rows default to negative."
    )
    lines.append(
        "- ML-only shows how much signal the trained classifier can recover from text and structured features."
    )
    lines.append(
        "- Hybrid shows the practical production-style path: deterministic rules first, ML fallback when rules are inconclusive."
    )
    lines.append(
        "- The threshold table helps show the precision/recall tradeoff when adjusting the ML decision boundary."
    )
    lines.append("")

    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def run_evaluation(
    *,
    model_path: str | Path = DEFAULT_MODEL_PATH,
    label_csv_path: str | Path = DEFAULT_LABEL_PATH,
    report_path: str | Path = DEFAULT_REPORT_PATH,
) -> dict[str, Any]:
    """
    Run Task 18 evaluation end-to-end.
    """
    payload = load_model_payload(model_path)
    feature_artifacts = load_feature_artifacts(label_csv_path)
    df = feature_artifacts.modeling_dataframe

    if df is None:
        raise ValueError("Feature artifacts are missing modeling_dataframe.")

    y_true = feature_artifacts.y

    rules_pred = predict_rules_only(df)
    rules_metrics = compute_binary_metrics(y_true, rules_pred)

    ml_pred, ml_prob = predict_ml_only(payload, feature_artifacts, threshold=0.50)
    ml_metrics = compute_binary_metrics(y_true, ml_pred, ml_prob)

    hybrid_pred, hybrid_prob = predict_hybrid(
        payload,
        df,
        feature_artifacts,
        positive_threshold=0.80,
        negative_threshold=0.30,
    )
    hybrid_metrics = compute_binary_metrics(y_true, hybrid_pred, hybrid_prob)

    threshold_df = build_threshold_tradeoff_table(y_true, ml_prob)

    written_report = write_evaluation_report(
        report_path=report_path,
        rules_metrics=rules_metrics,
        ml_metrics=ml_metrics,
        hybrid_metrics=hybrid_metrics,
        threshold_df=threshold_df,
    )

    return {
        "rules_metrics": rules_metrics,
        "ml_metrics": ml_metrics,
        "hybrid_metrics": hybrid_metrics,
        "threshold_tradeoff": threshold_df,
        "report_path": str(written_report),
    }


def main() -> None:
    """
    Script entry point.
    """
    results = run_evaluation()

    print("Task 18 evaluation complete.")
    print(f"Rules precision: {results['rules_metrics']['precision']:.4f}")
    print(f"ML precision: {results['ml_metrics']['precision']:.4f}")
    print(f"Hybrid precision: {results['hybrid_metrics']['precision']:.4f}")
    print(f"Report saved to: {results['report_path']}")


if __name__ == "__main__":
    main()

