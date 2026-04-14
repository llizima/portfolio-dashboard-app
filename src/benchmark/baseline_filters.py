"""
Transparent baseline rule filters for comparable-contract benchmarking.

Purpose
-------
This module implements the non-ML baseline comparable-contract screen for the
Applied Government Analytics (AGA) Value Dashboard. It applies deterministic, inspectable rules using:

- PSC code signals
- NAICS code signals
- taxonomy-driven keywords / phrases
- combined text fields such as `text_all`

This stage exists before ML classification so the project has a transparent
benchmark baseline that can be reviewed, challenged, and compared against later
model-based filtering.

It is intentionally limited to:
- loading the service taxonomy
- building a rule library from taxonomy hints
- scoring baseline evidence
- generating explainability columns
- returning a filtered comparable subset
- optionally saving outputs and summaries

It does NOT:
- train ML models
- perform TF-IDF / vector classification
- calculate business value estimates
- render dashboard pages
"""

from __future__ import annotations

import argparse
import json
import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

from src.config.settings import (
    PROCESSED_DATA_DIR,
    SERVICE_TAXONOMY_PATH,
    ensure_directories,
    validate_settings,
)

LOGGER = logging.getLogger(__name__)


# ---------------------------------------------------------------------
# Required / optional schema fields
# ---------------------------------------------------------------------
REQUIRED_INPUT_COLUMNS: tuple[str, ...] = (
    "psc_code",
    "naics_code",
    "text_all",
)

OPTIONAL_TEXT_COLUMNS: tuple[str, ...] = (
    "description",
    "description_clean",
    "psc_description",
    "naics_description",
)

DEFAULT_OUTPUT_STEM = "usaspending_contracts_baseline_comparables"

# Conservative default rule thresholds:
# - include when evidence is fairly strong
# - review when there is at least some plausible relevance
DEFAULT_INCLUDE_THRESHOLD = 3
DEFAULT_REVIEW_THRESHOLD = 1

DEFAULT_MIN_AWARD_AMOUNT = 0_000

DEFAULT_MAX_COMPARABLE_AWARD_AMOUNT = 250_000_000

# Weighted rule strengths. These are intentionally simple and inspectable.
RULE_WEIGHTS: dict[str, int] = {
    "psc_match": 2,
    "naics_match": 2,
    "keyword_match": 1,
    "multi_signal_bonus": 1,
    "integrated_multi_category_bonus": 1,
}

# Broad PSC codes can be useful but are often too coarse to stand alone.
# They may contribute evidence, but should not be treated the same as a more
# targeted code unless supported by other signals.
BROAD_PSC_CODES: set[str] = {
    "R499",
    "R425",
    "R706",
    "U099",
    
}

# Broad NAICS codes can also be useful but too coarse to stand alone.
BROAD_NAICS_CODES: set[str] = {
    "541330",
    "541715",
}

# Common broad / ambiguous terms that should not count on their own unless
# reinforced by code signals or multiple phrases.
# "analysis" is intentionally included because it is very broad
# in contract text.
LOW_SPECIFICITY_KEYWORDS: set[str] = {
    "analysis",
    "event",
    "conference",
    "workshop",
    "coordination",
    "support",
}

STRONG_PROTOTYPE_KEYWORDS: set[str] = {
    "prototype",
    "prototyping",
    "rapid prototyping",
    "proof of concept",
    "poc",
    "fabrication",
    "additive manufacturing",
    "3d printing",
    "build and test",
    "sbir",
    "phase i",
    "phase ii",
}

VERY_STRONG_PROTOTYPE_KEYWORDS: set[str] = {
    "sbir",
    "phase i",
    "phase ii",
    "phase iii",
    "prototype",
    "prototyping",
    "rapid prototyping",
    "proof of concept",
    "fabrication",
    "build and test",
}


# ---------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------
@dataclass(frozen=True)
class CategoryRule:
    """Rule definition derived from a single taxonomy category."""

    name: str
    definition: str
    keywords: tuple[str, ...]
    psc_hints: tuple[str, ...]
    naics_hints: tuple[str, ...]
    ambiguity_notes: str | None = None


@dataclass(frozen=True)
class BaselineFilterConfig:
    """Configuration for the baseline comparable-contract screen."""

    taxonomy_path: Path = SERVICE_TAXONOMY_PATH
    output_dir: Path = PROCESSED_DATA_DIR
    output_stem: str = DEFAULT_OUTPUT_STEM
    include_threshold: int = DEFAULT_INCLUDE_THRESHOLD
    review_threshold: int = DEFAULT_REVIEW_THRESHOLD
    write_filtered_subset: bool = False
    write_full_scored_dataset: bool = False
    include_review_rows_in_subset: bool = False
    output_format: str = "parquet"


# ---------------------------------------------------------------------
# Text normalization helpers
# ---------------------------------------------------------------------
_WHITESPACE_RE = re.compile(r"\s+")
_NON_ALNUM_RE = re.compile(r"[^a-z0-9]+")


def normalize_text(value: Any) -> str:
    """
    Normalize a text-like value for robust, deterministic matching.

    This intentionally favors interpretability over aggressive NLP behavior.
    """
    if value is None:
        return ""
    if pd.isna(value):
        return ""
    text = str(value).strip().lower()
    if not text:
        return ""
    text = _NON_ALNUM_RE.sub(" ", text)
    text = _WHITESPACE_RE.sub(" ", text).strip()
    return text


def normalize_code(value: Any) -> str:
    """Normalize PSC/NAICS code strings."""
    if value is None:
        return ""
    if pd.isna(value):
        return ""
    return str(value).strip().upper()


def phrase_in_text(phrase: str, text: str) -> bool:
    """
    Phrase matcher using word-boundary-style normalization.

    Because both phrase and text are normalized, checking for the phrase with
    padded spaces keeps matching behavior simple and inspectable.
    """
    normalized_phrase = normalize_text(phrase)
    if not normalized_phrase or not text:
        return False
    padded_text = f" {text} "
    padded_phrase = f" {normalized_phrase} "
    return padded_phrase in padded_text


# ---------------------------------------------------------------------
# Taxonomy loading / rule library
# ---------------------------------------------------------------------
def load_service_taxonomy(
    taxonomy_path: Path | str = SERVICE_TAXONOMY_PATH,
) -> list[CategoryRule]:
    """
    Load service taxonomy YAML and convert it into category rules.

    Expected YAML shape:
        version: 1.0
        categories:
          - name: ...
            definition: ...
            keywords: [...]
            psc_hints: [...]
            naics_hints: [...]
            ambiguity_notes: ...
    """
    path = Path(taxonomy_path)
    if not path.exists():
        raise FileNotFoundError(f"Service taxonomy not found: {path}")

    with path.open("r", encoding="utf-8") as f:
        payload = yaml.safe_load(f) or {}

    categories = payload.get("categories", []) or []
    if not categories:
        raise ValueError("Service taxonomy contains no categories.")

    rules: list[CategoryRule] = []
    for raw in categories:
        name = str(raw.get("name", "")).strip()
        if not name:
            continue

        rule = CategoryRule(
            name=name,
            definition=str(raw.get("definition", "")).strip(),
            keywords=tuple(
                normalize_text(k)
                for k in (raw.get("keywords", []) or [])
                if normalize_text(k)
            ),
            psc_hints=tuple(
                normalize_code(code)
                for code in (raw.get("psc_hints", []) or [])
                if normalize_code(code)
            ),
            naics_hints=tuple(
                normalize_code(code)
                for code in (raw.get("naics_hints", []) or [])
                if normalize_code(code)
            ),
            ambiguity_notes=(
                str(raw.get("ambiguity_notes", "")).strip() or None
            ),
        )
        rules.append(rule)

    if not rules:
        raise ValueError("No valid taxonomy categories were parsed.")

    return rules


def build_baseline_rule_library(
    category_rules: list[CategoryRule],
) -> dict[str, CategoryRule]:
    """
    Build a simple category-name keyed rule library.

    Keeping this as a plain dict makes review easy.
    """
    return {rule.name: rule for rule in category_rules}


# ---------------------------------------------------------------------
# Schema / preprocessing helpers
# ---------------------------------------------------------------------
def validate_input_dataframe(df: pd.DataFrame) -> None:
    """Validate required input schema."""
    missing = [
        column for column in REQUIRED_INPUT_COLUMNS if column not in df.columns
    ]
    if missing:
        raise ValueError(
            "Input dataframe is missing required baseline filter columns: "
            + ", ".join(missing)
        )


def ensure_baseline_text_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Create normalized helper text columns used by deterministic rules.
    """
    output = df.copy()

    for column in OPTIONAL_TEXT_COLUMNS:
        if column not in output.columns:
            output[column] = ""

    output["baseline_text_all_norm"] = output["text_all"].map(normalize_text)
    output["baseline_description_norm"] = output["description"].map(
        normalize_text
    )
    output["baseline_description_clean_norm"] = output["description_clean"].map(
        normalize_text
    )
    output["baseline_psc_code_norm"] = output["psc_code"].map(normalize_code)
    output["baseline_naics_code_norm"] = output["naics_code"].map(
        normalize_code
    )

    return output


def apply_min_award_amount_filter(
    df: pd.DataFrame,
    *,
    min_award_amount: float = DEFAULT_MIN_AWARD_AMOUNT,
) -> pd.DataFrame:
    """
    Return a copy of the dataframe keeping only rows with a valid numeric
    award_amount greater than or equal to the minimum threshold.
    """
    if "award_amount" not in df.columns:
        raise ValueError("Dataframe does not contain required column: award_amount")

    working = df.copy()
    award_amount_numeric = pd.to_numeric(working["award_amount"], errors="coerce")
    mask = award_amount_numeric.notna() & (award_amount_numeric >= min_award_amount)
    return working.loc[mask].copy()


def apply_max_award_amount_filter(
    df: pd.DataFrame,
    *,
    max_award_amount: float = DEFAULT_MAX_COMPARABLE_AWARD_AMOUNT,
) -> pd.DataFrame:
    """
    Return a copy of the dataframe keeping only rows with a valid numeric
    award_amount less than or equal to the comparable-contract maximum.
    """
    if "award_amount" not in df.columns:
        raise ValueError("Dataframe does not contain required column: award_amount")

    working = df.copy()
    award_amount_numeric = pd.to_numeric(working["award_amount"], errors="coerce")
    mask = award_amount_numeric.notna() & (award_amount_numeric <= max_award_amount)
    return working.loc[mask].copy()


# ---------------------------------------------------------------------
# Matching helpers
# ---------------------------------------------------------------------
def get_keyword_matches_for_category(
    *,
    text_all_norm: str,
    description_clean_norm: str,
    category_rule: CategoryRule,
) -> list[str]:
    """
    Return matched keywords for one category.

    Matching priority:
    1. exact normalized phrase in description_clean
    2. exact normalized phrase in text_all

    A keyword is only counted once even if it appears in both places.
    """
    matches: list[str] = []

    for keyword in category_rule.keywords:
        matched = False

        if description_clean_norm and phrase_in_text(
            keyword,
            description_clean_norm,
        ):
            matched = True
        elif text_all_norm and phrase_in_text(keyword, text_all_norm):
            matched = True

        if matched:
            matches.append(keyword)

    return sorted(set(matches))


def category_signal_details(
    *,
    row: pd.Series,
    category_rule: CategoryRule,
) -> dict[str, Any]:
    """
    Compute all baseline signals for one row against one category.
    """
    psc_code = row["baseline_psc_code_norm"]
    naics_code = row["baseline_naics_code_norm"]
    text_all_norm = row["baseline_text_all_norm"]
    description_clean_norm = row["baseline_description_clean_norm"]

    matched_psc_codes = [
        code for code in category_rule.psc_hints if code == psc_code
    ]
    matched_naics_codes = [
        code for code in category_rule.naics_hints if code == naics_code
    ]
    matched_keywords = get_keyword_matches_for_category(
        text_all_norm=text_all_norm,
        description_clean_norm=description_clean_norm,
        category_rule=category_rule,
    )

    signal_types = 0
    if matched_psc_codes:
        signal_types += 1
    if matched_naics_codes:
        signal_types += 1
    if matched_keywords:
        signal_types += 1

    score = 0
    reason_codes: list[str] = []

    if matched_psc_codes:
        # Broad PSC codes may contribute evidence,
        # but they are weaker when unsupported.
        if any(code in BROAD_PSC_CODES for code in matched_psc_codes):
            score += 1
            reason_codes.append("PSC_BROAD_MATCH")
        else:
            score += RULE_WEIGHTS["psc_match"]
            reason_codes.append("PSC_MATCH")

    if matched_naics_codes:
        if any(code in BROAD_NAICS_CODES for code in matched_naics_codes):
            score += 1
            reason_codes.append("NAICS_BROAD_MATCH")
        else:
            score += RULE_WEIGHTS["naics_match"]
            reason_codes.append("NAICS_MATCH")

    if matched_keywords:
        # Weight keywords conservatively:
        # - 1 point if any matched keyword is present
        # - low-specificity keywords should not dominate by themselves
        specificity_bonus = 0
        if any(
            keyword not in LOW_SPECIFICITY_KEYWORDS
            for keyword in matched_keywords
        ):
            specificity_bonus = RULE_WEIGHTS["keyword_match"]
        else:
            specificity_bonus = 0

        score += specificity_bonus

        if (
            category_rule.name == "prototyping"
            and any(
                keyword in STRONG_PROTOTYPE_KEYWORDS
                for keyword in matched_keywords
            )
        ):
            score += 1
            reason_codes.append("STRONG_PROTOTYPE_KEYWORD_MATCH")

        if (
            category_rule.name == "prototyping"
            and any(
                keyword in VERY_STRONG_PROTOTYPE_KEYWORDS
                for keyword in matched_keywords
            )
        ):
            score += 1
            reason_codes.append("VERY_STRONG_PROTOTYPE_KEYWORD_MATCH")

        if specificity_bonus > 0:
            reason_codes.append("KEYWORD_MATCH")
        else:
            reason_codes.append("LOW_SPECIFICITY_KEYWORD_ONLY")

    if signal_types >= 2:
        score += RULE_WEIGHTS["multi_signal_bonus"]
        reason_codes.append("MULTI_SIGNAL")

    return {
        "category_name": category_rule.name,
        "score": score,
        "signal_types": signal_types,
        "matched_keywords": matched_keywords,
        "matched_psc_codes": matched_psc_codes,
        "matched_naics_codes": matched_naics_codes,
        "reason_codes": reason_codes,
        "ambiguity_notes": category_rule.ambiguity_notes,
    }


def assign_baseline_primary_category(
    category_details: list[dict[str, Any]],
) -> str | None:
    """
    Select the strongest baseline category for a row.

    Tie-break order:
    1. highest score
    2. most signal types
    3. most matched keywords
    4. lexical category name (deterministic)
    """
    if not category_details:
        return None

    ranked = sorted(
        category_details,
        key=lambda item: (
            item["score"],
            item["signal_types"],
            len(item["matched_keywords"]),
            item["category_name"],
        ),
        reverse=True,
    )

    best = ranked[0]
    if best["score"] <= 0:
        return None
    return str(best["category_name"])


def build_reason_text(
    *,
    include: bool,
    review_flag: bool,
    primary_category: str | None,
    matched_psc_codes: list[str],
    matched_naics_codes: list[str],
    matched_keywords: list[str],
    multi_category: bool,
) -> str:
    """
    Build a concise human-readable explanation for one row.
    """
    status = "included"
    if not include and review_flag:
        status = "flagged for review"
    elif not include:
        status = "excluded"

    parts: list[str] = [f"Baseline row {status}"]

    if primary_category:
        parts.append(f"primary category: {primary_category}")

    if matched_psc_codes:
        parts.append(f"PSC signals: {', '.join(matched_psc_codes)}")

    if matched_naics_codes:
        parts.append(f"NAICS signals: {', '.join(matched_naics_codes)}")

    if matched_keywords:
        preview = ", ".join(matched_keywords[:6])
        if len(matched_keywords) > 6:
            preview += ", ..."
        parts.append(f"keyword signals: {preview}")

    if multi_category:
        parts.append("multiple service categories matched")

    return " | ".join(parts)


# ---------------------------------------------------------------------
# Core row scoring
# ---------------------------------------------------------------------
def score_row_against_taxonomy(
    row: pd.Series,
    rule_library: dict[str, CategoryRule],
    *,
    include_threshold: int,
    review_threshold: int,
) -> dict[str, Any]:
    """
    Score one row against all taxonomy categories and build explainability
    fields.
    """
    category_details: list[dict[str, Any]] = [
        category_signal_details(row=row, category_rule=rule)
        for rule in rule_library.values()
    ]

    positive_categories = [d for d in category_details if d["score"] > 0]
    primary_category = assign_baseline_primary_category(category_details)

    if primary_category is not None:
        primary_detail = next(
            d
            for d in category_details
            if d["category_name"] == primary_category
        )
    else:
        primary_detail = {
            "category_name": None,
            "score": 0,
            "signal_types": 0,
            "matched_keywords": [],
            "matched_psc_codes": [],
            "matched_naics_codes": [],
            "reason_codes": [],
            "ambiguity_notes": None,
        }

    rule_score = int(primary_detail["score"])

    # If a row strongly matches multiple categories, it may represent an
    # or bundled service profile.
    multi_category = len(positive_categories) >= 2
    if multi_category:
        rule_score += RULE_WEIGHTS["integrated_multi_category_bonus"]

    include = rule_score >= include_threshold
    review_flag = (not include) and (rule_score >= review_threshold)

    reason_codes: list[str] = list(primary_detail["reason_codes"])
    if multi_category:
        reason_codes.append("MULTI_CATEGORY_MATCH")
        if primary_category != "integrated_service_delivery":
            # Keep the dominant category, but explicitly mark that several
            # categories matched. This helps analysts detect blended contracts.
            reason_codes.append("POTENTIAL_INTEGRATED_SERVICE")

    if include:
        reason_codes.append("BASELINE_INCLUDE")
    elif review_flag:
        reason_codes.append("BASELINE_REVIEW")
    else:
        reason_codes.append("BASELINE_EXCLUDE")

    matched_keywords = sorted(
        {
            keyword
            for detail in positive_categories
            for keyword in detail["matched_keywords"]
        }
    )
    matched_psc_codes = sorted(
        {
            code
            for detail in positive_categories
            for code in detail["matched_psc_codes"]
        }
    )
    matched_naics_codes = sorted(
        {
            code
            for detail in positive_categories
            for code in detail["matched_naics_codes"]
        }
    )
    matched_categories = sorted(
        detail["category_name"] for detail in positive_categories
    )

    reason_text = build_reason_text(
        include=include,
        review_flag=review_flag,
        primary_category=primary_category,
        matched_psc_codes=matched_psc_codes,
        matched_naics_codes=matched_naics_codes,
        matched_keywords=matched_keywords,
        multi_category=multi_category,
    )

    return {
        "baseline_include": include,
        "baseline_rule_score": rule_score,
        "baseline_reason_codes": "|".join(dict.fromkeys(reason_codes)),
        "baseline_reason_text": reason_text,
        "matched_keywords": "|".join(matched_keywords),
        "matched_psc_codes": "|".join(matched_psc_codes),
        "matched_naics_codes": "|".join(matched_naics_codes),
        "baseline_primary_category": primary_category,
        "baseline_review_flag": review_flag,
        "baseline_matched_categories": "|".join(matched_categories),
        "baseline_signal_type_count": len(
            [
                signal
                for signal in [
                    matched_psc_codes,
                    matched_naics_codes,
                    matched_keywords,
                ]
                if signal
            ]
        ),
        "baseline_category_match_count": len(matched_categories),
    }


# ---------------------------------------------------------------------
# Public application functions
# ---------------------------------------------------------------------
def apply_baseline_filters(
    df: pd.DataFrame,
    taxonomy_rules: list[CategoryRule] | dict[str, CategoryRule],
    *,
    include_threshold: int = DEFAULT_INCLUDE_THRESHOLD,
    review_threshold: int = DEFAULT_REVIEW_THRESHOLD,
    keep_helper_columns: bool = False,
) -> pd.DataFrame:
    """
    Apply baseline taxonomy-driven rules to a cleaned USAspending dataframe.

    Parameters
    ----------
    df:
        Cleaned analytical dataframe from the transform stage.
    taxonomy_rules:
        Either a list of CategoryRule objects or a dict keyed by category name.
    include_threshold:
        Minimum score required for `baseline_include=True`.
    review_threshold:
        Minimum score required for `baseline_review_flag=True`
        when not included.
    keep_helper_columns:
        Whether to retain normalized helper columns used for scoring.

    Returns
    -------
    pd.DataFrame
        Copy of the input dataframe with explainability columns appended.
    """
    validate_input_dataframe(df)

    if isinstance(taxonomy_rules, list):
        rule_library = build_baseline_rule_library(taxonomy_rules)
    else:
        rule_library = taxonomy_rules

    if review_threshold > include_threshold:
        raise ValueError("review_threshold cannot exceed include_threshold.")

    working = ensure_baseline_text_columns(df)

    scored_rows = [
        score_row_against_taxonomy(
            row=row,
            rule_library=rule_library,
            include_threshold=include_threshold,
            review_threshold=review_threshold,
        )
        for _, row in working.iterrows()
    ]

    scored_df = pd.DataFrame(scored_rows, index=working.index)
    output = pd.concat([working, scored_df], axis=1)

    if not keep_helper_columns:
        helper_cols = [
            "baseline_text_all_norm",
            "baseline_description_norm",
            "baseline_description_clean_norm",
            "baseline_psc_code_norm",
            "baseline_naics_code_norm",
        ]
        existing_helper_cols = [
            column for column in helper_cols if column in output.columns
        ]
        output = output.drop(columns=existing_helper_cols)

    return output


def filter_to_baseline_comparables(
    df: pd.DataFrame,
    *,
    include_review: bool = False,
) -> pd.DataFrame:
    """
    Return the benchmark-derived baseline subset.

    By default, only included rows are retained.
    Set include_review=True to also keep borderline rows flagged for review.
    """
    if "baseline_include" not in df.columns:
        raise ValueError(
            "Dataframe does not contain baseline scoring columns."
        )

    if include_review:
        mask = df["baseline_include"] | df["baseline_review_flag"]
    else:
        mask = df["baseline_include"]

    filtered = df.loc[mask].copy()
    filtered = apply_max_award_amount_filter(filtered)
    return filtered


def summarize_baseline_filter_results(df: pd.DataFrame) -> dict[str, Any]:
    """
    Build a compact summary for evaluation logs or later methodology artifacts.
    """
    required = [
        "baseline_include",
        "baseline_review_flag",
        "baseline_rule_score",
        "baseline_primary_category",
    ]
    missing = [column for column in required if column not in df.columns]
    if missing:
        raise ValueError(
            "Dataframe missing required baseline result columns: "
            + ", ".join(missing)
        )

    total_rows = int(len(df))
    included_rows = int(df["baseline_include"].sum())
    review_rows = int(df["baseline_review_flag"].sum())
    excluded_rows = total_rows - included_rows - review_rows

    included_pct = (included_rows / total_rows * 100.0) if total_rows else 0.0
    review_pct = (review_rows / total_rows * 100.0) if total_rows else 0.0
    excluded_pct = (excluded_rows / total_rows * 100.0) if total_rows else 0.0

    category_counts = (
        df.loc[df["baseline_include"], "baseline_primary_category"]
        .fillna("unassigned")
        .value_counts(dropna=False)
        .to_dict()
    )

    score_distribution = (
        df["baseline_rule_score"].value_counts().sort_index().to_dict()
    )

    return {
        "total_rows": total_rows,
        "included_rows": included_rows,
        "review_rows": review_rows,
        "excluded_rows": excluded_rows,
        "included_pct": round(included_pct, 4),
        "review_pct": round(review_pct, 4),
        "excluded_pct": round(excluded_pct, 4),
        "included_category_counts": category_counts,
        "rule_score_distribution": score_distribution,
    }


# ---------------------------------------------------------------------
# File I/O helpers
# ---------------------------------------------------------------------
def _write_dataframe(df: pd.DataFrame, path: Path, output_format: str) -> Path:
    """Write dataframe in a simple, repo-friendly format."""
    output_format = output_format.lower().strip()

    if output_format == "parquet":
        df.to_parquet(path, index=False)
    elif output_format == "csv":
        df.to_csv(path, index=False)
    elif output_format == "json":
        df.to_json(path, orient="records", indent=2)
    else:
        raise ValueError(
            "Unsupported output_format. Expected one of: parquet, csv, json."
        )
    return path


def save_baseline_outputs(
    *,
    scored_df: pd.DataFrame,
    config: BaselineFilterConfig,
) -> dict[str, Path]:
    """
    Persist selected baseline outputs.

    This can write:
    - the full scored dataset
    - the filtered comparable subset
    """
    config.output_dir.mkdir(parents=True, exist_ok=True)

    suffix = config.output_format.lower()
    outputs: dict[str, Path] = {}

    if config.write_full_scored_dataset:
        full_path = config.output_dir / f"{config.output_stem}_scored.{suffix}"
        _write_dataframe(scored_df, full_path, config.output_format)
        outputs["scored_dataset"] = full_path

    if config.write_filtered_subset:
        filtered = filter_to_baseline_comparables(
            scored_df,
            include_review=config.include_review_rows_in_subset,
        )
        filtered_path = config.output_dir / f"{config.output_stem}.{suffix}"
        _write_dataframe(filtered, filtered_path, config.output_format)
        outputs["filtered_subset"] = filtered_path

    return outputs


def write_baseline_summary_json(
    summary: dict[str, Any],
    output_path: Path,
) -> Path:
    """Write a summary artifact for evaluation/debugging."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    return output_path


# ---------------------------------------------------------------------
# CLI helpers
# ---------------------------------------------------------------------
def parse_args() -> argparse.Namespace:
    """Parse CLI arguments for baseline filtering."""
    parser = argparse.ArgumentParser(
        description="Apply transparent baseline comparable-contract filters."
    )
    parser.add_argument(
        "--input-path",
        type=Path,
        required=True,
        help="Path to the cleaned processed dataset.",
    )
    parser.add_argument(
        "--taxonomy-path",
        type=Path,
        default=SERVICE_TAXONOMY_PATH,
        help="Path to the service taxonomy YAML.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=PROCESSED_DATA_DIR,
        help="Directory for baseline output artifacts.",
    )
    parser.add_argument(
        "--output-stem",
        type=str,
        default=DEFAULT_OUTPUT_STEM,
        help="Base filename stem for saved outputs.",
    )
    parser.add_argument(
        "--output-format",
        type=str,
        default="parquet",
        choices=["parquet", "csv", "json"],
        help="Output format for saved datasets.",
    )
    parser.add_argument(
        "--include-threshold",
        type=int,
        default=DEFAULT_INCLUDE_THRESHOLD,
        help="Score threshold for baseline inclusion.",
    )
    parser.add_argument(
        "--review-threshold",
        type=int,
        default=DEFAULT_REVIEW_THRESHOLD,
        help="Score threshold for borderline review.",
    )
    parser.add_argument(
        "--write-full-scored-dataset",
        action="store_true",
        help="Write the full scored dataset with baseline columns.",
    )
    parser.add_argument(
        "--write-filtered-subset",
        action="store_true",
        help="Write the filtered comparable subset.",
    )
    parser.add_argument(
        "--include-review-rows-in-subset",
        action="store_true",
        help="Include review-flagged rows in the saved subset.",
    )
    parser.add_argument(
        "--summary-json-path",
        type=Path,
        default=None,
        help="Optional path to save a JSON summary.",
    )
    parser.add_argument(
        "--log-level",
        type=str,
        default="INFO",
        help="Python logging level.",
    )
    return parser.parse_args()


def load_input_dataframe(input_path: Path) -> pd.DataFrame:
    """Load a dataframe based on file suffix."""
    suffix = input_path.suffix.lower()

    if suffix == ".parquet":
        return pd.read_parquet(input_path)
    if suffix == ".csv":
        return pd.read_csv(input_path)
    if suffix == ".json":
        return pd.read_json(input_path)

    raise ValueError(
        f"Unsupported input file type: {input_path.suffix}. "
        "Expected .parquet, .csv, or .json."
    )


def run_baseline_filter_pipeline(
    config: BaselineFilterConfig,
    input_path: Path,
) -> dict[str, Any]:
    """
    Run the end-to-end baseline filter workflow from a cleaned dataset.
    """
    validate_settings()
    ensure_directories()

    LOGGER.info("Loading cleaned dataset from %s", input_path)
    df = load_input_dataframe(input_path)

    LOGGER.info("Loading taxonomy from %s", config.taxonomy_path)
    taxonomy_rules = load_service_taxonomy(config.taxonomy_path)

    LOGGER.info("Applying baseline filters")
    scored_df = apply_baseline_filters(
        df,
        taxonomy_rules,
        include_threshold=config.include_threshold,
        review_threshold=config.review_threshold,
    )

    summary = summarize_baseline_filter_results(scored_df)
    output_paths = save_baseline_outputs(scored_df=scored_df, config=config)

    return {
        "scored_df": scored_df,
        "summary": summary,
        "output_paths": output_paths,
    }


def main() -> None:
    """CLI entry point."""
    args = parse_args()

    logging.basicConfig(
        level=getattr(logging, args.log_level.upper(), logging.INFO),
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )

    config = BaselineFilterConfig(
        taxonomy_path=args.taxonomy_path,
        output_dir=args.output_dir,
        output_stem=args.output_stem,
        include_threshold=args.include_threshold,
        review_threshold=args.review_threshold,
        write_filtered_subset=args.write_filtered_subset,
        write_full_scored_dataset=args.write_full_scored_dataset,
        include_review_rows_in_subset=args.include_review_rows_in_subset,
        output_format=args.output_format,
    )

    results = run_baseline_filter_pipeline(
        config=config,
        input_path=args.input_path,
    )

    summary = results["summary"]
    LOGGER.info(
        (
            "Baseline filtering complete | total=%s included=%s "
            "review=%s excluded=%s"
        ),
        summary["total_rows"],
        summary["included_rows"],
        summary["review_rows"],
        summary["excluded_rows"],
    )

    if args.summary_json_path is not None:
        write_baseline_summary_json(summary, args.summary_json_path)
        LOGGER.info(
            "Wrote baseline summary JSON to %s",
            args.summary_json_path,
        )


if __name__ == "__main__":
    main()
