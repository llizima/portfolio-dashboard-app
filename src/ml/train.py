from __future__ import annotations

import json
import pickle
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report
from sklearn.model_selection import train_test_split

from src.ml.features import FeatureArtifacts, get_feature_matrix_and_target


DEFAULT_LABEL_PATH = Path("src/data/labels/high_precision_seed.csv")
DEFAULT_MODEL_DIR = Path("src/models")


@dataclass(frozen=True)
class TrainingConfig:
    """
    Configuration for baseline model training.
    """

    label_csv_path: str = str(DEFAULT_LABEL_PATH)
    output_dir: str = str(DEFAULT_MODEL_DIR)
    mode: str = "hybrid"
    include_ambiguous: bool = False
    drop_missing_text: bool = False
    text_column: str = "description"
    max_text_features: int = 2000
    ngram_range: tuple[int, int] = (1, 2)
    min_df: int | float = 1
    include_baseline_context: bool = False
    test_size: float = 0.25
    random_state: int = 42
    max_iter: int = 1000
    class_weight: str = "balanced"


@dataclass(frozen=True)
class TrainingArtifacts:
    """
    Output paths and summary statistics from a training run.
    """

    model_path: str
    metadata_path: str
    train_rows: int
    test_rows: int
    feature_count: int
    mode: str


def _ensure_output_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def _serialize_training_metadata(
    *,
    config: TrainingConfig,
    feature_artifacts: FeatureArtifacts,
    train_rows: int,
    test_rows: int,
    model: LogisticRegression,
    report: dict[str, Any],
) -> dict[str, Any]:
    """
    Build a JSON-serializable metadata dictionary for the training run.
    """
    metadata: dict[str, Any] = {
        "config": {
            **asdict(config),
            "ngram_range": list(config.ngram_range),
        },
        "row_count": int(feature_artifacts.row_count),
        "feature_count": int(len(feature_artifacts.feature_names)),
        "mode": feature_artifacts.mode,
        "train_rows": int(train_rows),
        "test_rows": int(test_rows),
        "class_balance": {
            "negative_count": int(np.sum(feature_artifacts.y == 0)),
            "positive_count": int(np.sum(feature_artifacts.y == 1)),
        },
        "model_class": model.__class__.__name__,
        "model_params": model.get_params(),
        "classification_report": report,
    }
    return metadata


def train_baseline_model(
    config: TrainingConfig | None = None,
) -> tuple[LogisticRegression, FeatureArtifacts, TrainingArtifacts]:
    """
    Train a baseline interpretable logistic regression model and persist artifacts.

    Returns
    -------
    tuple
        (trained model, feature artifacts, training artifacts metadata)
    """
    config = config or TrainingConfig()

    feature_artifacts = get_feature_matrix_and_target(
        config.label_csv_path,
        mode=config.mode,  # type: ignore[arg-type]
        include_ambiguous=config.include_ambiguous,
        drop_missing_text=config.drop_missing_text,
        text_column=config.text_column,
        max_text_features=config.max_text_features,
        ngram_range=config.ngram_range,
        min_df=config.min_df,
        include_baseline_context=config.include_baseline_context,
    )

    X = feature_artifacts.X
    y = feature_artifacts.y

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=config.test_size,
        random_state=config.random_state,
        stratify=y,
    )

    model = LogisticRegression(
        max_iter=config.max_iter,
        class_weight=config.class_weight,
    )
    model.fit(X_train, y_train)

    preds = model.predict(X_test)
    report = classification_report(
        y_test,
        preds,
        output_dict=True,
        zero_division=0,
    )

    output_dir = Path(config.output_dir)
    _ensure_output_dir(output_dir)

    model_path = output_dir / "baseline_logreg_model.pkl"
    metadata_path = output_dir / "baseline_logreg_metadata.json"

    payload = {
        "model": model,
        "text_vectorizer": feature_artifacts.text_vectorizer,
        "structured_vectorizer": feature_artifacts.structured_vectorizer,
        "feature_names": feature_artifacts.feature_names,
        "mode": feature_artifacts.mode,
    }

    with open(model_path, "wb") as f:
        pickle.dump(payload, f)

    metadata = _serialize_training_metadata(
        config=config,
        feature_artifacts=feature_artifacts,
        train_rows=X_train.shape[0],
        test_rows=X_test.shape[0],
        model=model,
        report=report,
    )

    with open(metadata_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)

    training_artifacts = TrainingArtifacts(
        model_path=str(model_path),
        metadata_path=str(metadata_path),
        train_rows=int(X_train.shape[0]),
        test_rows=int(X_test.shape[0]),
        feature_count=len(feature_artifacts.feature_names),
        mode=feature_artifacts.mode,
    )

    return model, feature_artifacts, training_artifacts


def main() -> None:
    """
    Train the baseline model and print a concise summary.
    """
    _, _, artifacts = train_baseline_model()

    print("Training complete.")
    print(f"Model saved to: {artifacts.model_path}")
    print(f"Metadata saved to: {artifacts.metadata_path}")
    print(f"Train rows: {artifacts.train_rows}")
    print(f"Test rows: {artifacts.test_rows}")
    print(f"Feature count: {artifacts.feature_count}")
    print(f"Mode: {artifacts.mode}")


if __name__ == "__main__":
    main()
