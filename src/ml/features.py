"""
Feature engineering module for the Applied Government Analytics (AGA) comparable-contract relevance model.

Purpose
-------
This module converts labeled comparable-contract records into reproducible
model-ready features for future supervised learning experiments.

It is intentionally limited to:
- loading labeled CSV data
- validating required columns
- extracting a clean binary relevance target
- building text features from contract descriptions
- building structured features from PSC/NAICS and simple metadata
- combining feature matrices for text-only, structured-only, or hybrid use

It does NOT:
- train a model
- evaluate a model
- write Streamlit UI
- read notebook state
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

import numpy as np
import pandas as pd
from scipy.sparse import csr_matrix, hstack, issparse
from sklearn.feature_extraction import DictVectorizer
from sklearn.feature_extraction.text import TfidfVectorizer


FEATURE_MODE = Literal["text", "structured", "hybrid"]

REQUIRED_LABEL_COLUMNS: tuple[str, ...] = (
    "description",
    "relevance_label",
)

FORBIDDEN_FEATURE_COLUMNS: tuple[str, ...] = (
    "relevance_label",
    "category_label_optional",
    "reviewer_notes",
    "confidence_level",
    "second_review_needed",
    "ambiguity_flag",
    "reviewer_id",
    "review_date",
)

VALID_RELEVANCE_LABELS: tuple[str, ...] = (
    "relevant",
    "not_relevant",
    "ambiguous",
)

DEFAULT_KEYWORD_GROUPS: dict[str, tuple[str, ...]] = {
    "kw_prototyping": (
        "prototype",
        "prototyping",
        "fabrication",
        "fabricate",
        "demonstrator",
        "test article",
        "proof of concept",
        "3d printing",
        "additive manufacturing",
        "build",
    ),
    "kw_engineering": (
        "systems engineering",
        "engineering analysis",
        "modeling",
        "modelling",
        "simulation",
        "trade study",
        "trade studies",
        "cad",
        "design review",
        "feasibility analysis",
        "technical analysis",
        "requirements development",
    ),
    "kw_event": (
        "workshop",
        "conference",
        "symposium",
        "seminar",
        "hackathon",
        "challenge event",
        "industry day",
        "demo day",
        "event planning",
        "event logistics",
        "facilitation",
    ),
    "kw_workspace": (
        "workspace",
        "collaboration space",
        "lab space",
        "innovation lab",
        "makerspace",
        "facility access",
        "shared environment",
        "secure facility",
        "collaborative workspace",
    ),
    "kw_ecosystem": (
        "innovation ecosystem",
        "ecosystem access",
        "startup engagement",
        "startup network",
        "vendor access",
        "vendor network",
        "partner network",
        "technology scouting",
        "solution scouting",
        "technology discovery",
        "accelerator",
        "incubator",
    ),
    "kw_program_support": (
        "program management",
        "management support",
        "project support",
        "program support",
        "logistics support",
        "governance",
        "coordination",
        "reporting",
        "scheduling",
    ),
}


@dataclass(frozen=True)
class FeatureArtifacts:
    """
    Container for feature outputs produced by the pipeline.
    """

    X: csr_matrix
    y: np.ndarray
    feature_names: list[str]
    mode: FEATURE_MODE
    row_count: int
    text_vectorizer: TfidfVectorizer | None = None
    structured_vectorizer: DictVectorizer | None = None
    modeling_dataframe: pd.DataFrame | None = None


def _normalize_text(value: Any) -> str:
    """
    Convert a value into a stripped lowercase-safe string for feature logic.
    """
    if value is None:
        return ""
    if pd.isna(value):
        return ""
    return str(value).strip()


def _normalize_label(value: Any) -> str:
    """
    Normalize label text into the allowed lowercase format.
    """
    return _normalize_text(value).lower()


def _coerce_optional_code(value: Any) -> str:
    """
    Normalize PSC/NAICS-like values into clean strings.
    """
    text = _normalize_text(value)
    return text.upper() if text else "MISSING"


def _validate_required_columns(df: pd.DataFrame) -> None:
    """
    Validate that required columns exist in the dataframe.

    Only description and relevance_label are strictly required.
    Other fields like record_id, psc_code, and naics_code are optional
    and may be created later with safe defaults.
    """
    missing = [col for col in REQUIRED_LABEL_COLUMNS if col not in df.columns]
    if missing:
        missing_display = ", ".join(missing)
        raise ValueError(
            f"Labeled data is missing required columns: {missing_display}"
        )


def _validate_relevance_labels(df: pd.DataFrame) -> None:
    """
    Validate relevance labels.

    Allows:
    - numeric-style labels: 0 / 1 / 0.0 / 1.0
    - string labels: "relevant" / "not_relevant" / "ambiguous"
    """
    observed = {
        str(value).strip().lower()
        for value in df["relevance_label"].dropna().unique()
    }

    allowed = {
        "relevant",
        "not_relevant",
        "ambiguous",
        "0",
        "1",
        "0.0",
        "1.0",
    }

    invalid = sorted(observed - allowed)
    if invalid:
        invalid_display = ", ".join(invalid)
        raise ValueError(
            f"Unsupported relevance_label values found: {invalid_display}"
        )


def _ensure_nonempty_dataframe(df: pd.DataFrame) -> None:
    """
    Ensure the dataframe has at least one row.
    """
    if df.empty:
        raise ValueError("No rows available after labeled data filtering.")


def _build_binary_target(labels: pd.Series) -> np.ndarray:
    """
    Convert labels into a binary target.

    Supports:
    - numeric labels: 1 / 0 / 1.0 / 0.0
    - string labels: "relevant" / "not_relevant"

    Does not allow "ambiguous" rows to be converted directly.
    """
    normalized = labels.astype(str).str.strip().str.lower()

    mapping = {
        "relevant": 1,
        "not_relevant": 0,
        "1": 1,
        "1.0": 1,
        "0": 0,
        "0.0": 0,
    }

    unknown = sorted(set(normalized.unique()) - set(mapping))
    if unknown:
        unknown_display = ", ".join(unknown)
        raise ValueError(
            f"Cannot build binary target from labels: {unknown_display}"
        )

    return normalized.map(mapping).astype(int).to_numpy()


def load_labeled_data(
    csv_path: str | Path,
    *,
    include_ambiguous: bool = False,
    drop_missing_text: bool = False,
) -> pd.DataFrame:
    """
    Load labeled records from CSV and prepare them for feature engineering.

    Parameters
    ----------
    csv_path : str | Path
        Path to labeled CSV file.
    include_ambiguous : bool, default False
        Whether to retain rows labeled as ambiguous.
    drop_missing_text : bool, default False
        Whether to drop rows with blank description text.

    Returns
    -------
    pd.DataFrame
        Cleaned labeled dataframe preserving row order.
    """
    path = Path(csv_path)
    if not path.exists():
        raise FileNotFoundError(f"Labeled CSV not found: {path}")

    df = pd.read_csv(path)
    df.columns = [str(col).strip().lower() for col in df.columns]

    _validate_required_columns(df)
    _validate_relevance_labels(df)

    df = df.copy()

    if "record_id" not in df.columns:
        df["record_id"] = np.arange(1, len(df) + 1)

    if "psc_code" not in df.columns:
        df["psc_code"] = "MISSING"

    if "naics_code" not in df.columns:
        df["naics_code"] = "MISSING"

    df["description"] = df["description"].map(_normalize_text)
    df["psc_code"] = df["psc_code"].map(_coerce_optional_code)
    df["naics_code"] = df["naics_code"].map(_coerce_optional_code)
    df["relevance_label"] = df["relevance_label"].apply(
        lambda value: _normalize_label(value)
        if str(value).strip().lower() not in {"0", "1", "0.0", "1.0"}
        else str(value).strip().lower()
    )

    if not include_ambiguous:
        df = df[df["relevance_label"] != "ambiguous"].copy()

    if drop_missing_text:
        df = df[df["description"].str.len() > 0].copy()

    _ensure_nonempty_dataframe(df)

    return df.reset_index(drop=True)


def build_text_features(
    df: pd.DataFrame,
    *,
    text_column: str = "description",
    max_features: int = 2000,
    ngram_range: tuple[int, int] = (1, 2),
    min_df: int | float = 1,
    lowercase: bool = True,
    stop_words: str | list[str] | None = "english",
) -> tuple[TfidfVectorizer, csr_matrix, list[str]]:
    """
    Build TF-IDF text features from a text column.

    Returns
    -------
    tuple[TfidfVectorizer, csr_matrix, list[str]]
        Fitted vectorizer, sparse text matrix, and feature names.
    """
    if text_column not in df.columns:
        raise ValueError(f"Text column '{text_column}' not found in dataframe.")

    texts = df[text_column].fillna("").astype(str).tolist()

    vectorizer = TfidfVectorizer(
        max_features=max_features,
        ngram_range=ngram_range,
        min_df=min_df,
        lowercase=lowercase,
        stop_words=stop_words,
    )
    matrix = vectorizer.fit_transform(texts)

    feature_names = vectorizer.get_feature_names_out().tolist()
    return vectorizer, matrix.tocsr(), feature_names


def _keyword_hit(description: str, phrases: tuple[str, ...]) -> int:
    """
    Return 1 if any phrase appears in the description, else 0.
    """
    normalized = description.lower()
    return int(any(phrase.lower() in normalized for phrase in phrases))


def _structured_feature_rows(
    df: pd.DataFrame,
    *,
    keyword_groups: dict[str, tuple[str, ...]] | None = None,
    include_baseline_context: bool = False,
) -> list[dict[str, Any]]:
    """
    Convert each row of the dataframe into a structured feature dictionary.
    """
    groups = keyword_groups or DEFAULT_KEYWORD_GROUPS
    rows: list[dict[str, Any]] = []

    for _, row in df.iterrows():
        description = _normalize_text(row.get("description", ""))
        psc_code = _coerce_optional_code(row.get("psc_code"))
        naics_code = _coerce_optional_code(row.get("naics_code"))

        feature_row: dict[str, Any] = {
            "psc_code": psc_code,
            "naics_code": naics_code,
            "desc_char_len": len(description),
            "desc_word_count": len(description.split()),
            "desc_has_text": int(bool(description)),
            "psc_missing": int(psc_code == "MISSING"),
            "naics_missing": int(naics_code == "MISSING"),
        }

        for group_name, phrases in groups.items():
            feature_row[group_name] = _keyword_hit(description, phrases)

        if include_baseline_context:
            baseline_include = row.get("baseline_include_flag", "")
            baseline_primary_category = _normalize_text(
                row.get("baseline_primary_category", "")
            )
            baseline_reason_codes = _normalize_text(
                row.get("baseline_reason_codes", "")
            )

            feature_row["baseline_include_flag"] = _normalize_text(
                baseline_include
            )
            feature_row["baseline_primary_category"] = (
                baseline_primary_category if baseline_primary_category else "MISSING"
            )
            feature_row["baseline_reason_code_count"] = (
                len([part for part in baseline_reason_codes.split("|") if part.strip()])
                if baseline_reason_codes
                else 0
            )

        rows.append(feature_row)

    return rows


def build_structured_features(
    df: pd.DataFrame,
    *,
    keyword_groups: dict[str, tuple[str, ...]] | None = None,
    include_baseline_context: bool = False,
) -> tuple[DictVectorizer, csr_matrix, list[str]]:
    """
    Build structured metadata features using explicit, inspectable logic.

    Returns
    -------
    tuple[DictVectorizer, csr_matrix, list[str]]
        Fitted DictVectorizer, sparse structured matrix, and feature names.
    """
    feature_df = df.drop(
        columns=[col for col in FORBIDDEN_FEATURE_COLUMNS if col in df.columns],
        errors="ignore",
    ).copy()

    records = _structured_feature_rows(
        feature_df,
        keyword_groups=keyword_groups,
        include_baseline_context=include_baseline_context,
    )

    vectorizer = DictVectorizer(sparse=True)
    matrix = vectorizer.fit_transform(records).tocsr()
    feature_names = vectorizer.get_feature_names_out().tolist()

    return vectorizer, matrix, feature_names


def combine_features(
    *,
    text_matrix: csr_matrix | None = None,
    text_feature_names: list[str] | None = None,
    structured_matrix: csr_matrix | None = None,
    structured_feature_names: list[str] | None = None,
    mode: FEATURE_MODE = "hybrid",
) -> tuple[csr_matrix, list[str]]:
    """
    Combine text and structured feature matrices according to the requested mode.
    """
    text_feature_names = text_feature_names or []
    structured_feature_names = structured_feature_names or []

    if mode == "text":
        if text_matrix is None:
            raise ValueError("text_matrix is required for mode='text'.")
        return text_matrix.tocsr(), text_feature_names

    if mode == "structured":
        if structured_matrix is None:
            raise ValueError("structured_matrix is required for mode='structured'.")
        return structured_matrix.tocsr(), structured_feature_names

    if mode == "hybrid":
        if text_matrix is None or structured_matrix is None:
            raise ValueError(
                "Both text_matrix and structured_matrix are required for mode='hybrid'."
            )
        combined = hstack([text_matrix, structured_matrix], format="csr")
        combined_names = list(text_feature_names) + list(structured_feature_names)
        return combined, combined_names

    raise ValueError(f"Unsupported mode: {mode}")


def get_feature_matrix_and_target(
    csv_path: str | Path,
    *,
    mode: FEATURE_MODE = "hybrid",
    include_ambiguous: bool = False,
    drop_missing_text: bool = False,
    text_column: str = "description",
    max_text_features: int = 2000,
    ngram_range: tuple[int, int] = (1, 2),
    min_df: int | float = 1,
    include_baseline_context: bool = False,
) -> FeatureArtifacts:
    """
    End-to-end entry point for generating model-ready X and y.

    Returns
    -------
    FeatureArtifacts
        Structured output containing X, y, feature names, and fitted transformers.
    """
    df = load_labeled_data(
        csv_path,
        include_ambiguous=include_ambiguous,
        drop_missing_text=drop_missing_text,
    )

    if include_ambiguous:
        allowed = {"relevant", "not_relevant"}
        df = df[df["relevance_label"].isin(allowed)].copy()
        _ensure_nonempty_dataframe(df)

    y = _build_binary_target(df["relevance_label"])

    text_vectorizer: TfidfVectorizer | None = None
    structured_vectorizer: DictVectorizer | None = None
    text_matrix: csr_matrix | None = None
    structured_matrix: csr_matrix | None = None
    text_feature_names: list[str] = []
    structured_feature_names: list[str] = []

    if mode in ("text", "hybrid"):
        text_vectorizer, text_matrix, text_feature_names = build_text_features(
            df,
            text_column=text_column,
            max_features=max_text_features,
            ngram_range=ngram_range,
            min_df=min_df,
        )

    if mode in ("structured", "hybrid"):
        structured_vectorizer, structured_matrix, structured_feature_names = (
            build_structured_features(
                df,
                include_baseline_context=include_baseline_context,
            )
        )

    X, feature_names = combine_features(
        text_matrix=text_matrix,
        text_feature_names=text_feature_names,
        structured_matrix=structured_matrix,
        structured_feature_names=structured_feature_names,
        mode=mode,
    )

    if not issparse(X):
        X = csr_matrix(X)

    if X.shape[0] != len(y):
        raise ValueError(
            "Feature matrix row count does not align with target vector length."
        )

    return FeatureArtifacts(
        X=X.tocsr(),
        y=y,
        feature_names=feature_names,
        mode=mode,
        row_count=X.shape[0],
        text_vectorizer=text_vectorizer,
        structured_vectorizer=structured_vectorizer,
        modeling_dataframe=df,
    )
