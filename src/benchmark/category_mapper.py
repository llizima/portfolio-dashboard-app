#mapper


"""
Transparent service-category mapper for filtered comparable contracts.

Purpose
-------
This module assigns SOFWERX-aligned service categories to already-filtered
comparable contract records. It sits downstream of the baseline comparable
screen and converts each included contract into one final category or
"unmapped" using deterministic, inspectable rules derived from the
service taxonomy.

This stage is intentionally limited to:
- loading the service taxonomy
- building a category rule library
- scoring category evidence using PSC, NAICS, and keyword signals
- assigning a final mapped service category
- generating explainability columns
- producing category summary artifacts

It does NOT:
- train ML models
- perform TF-IDF / semantic classification
- calculate business value estimates
- render charts or Streamlit pages
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
    REPORTS_EVALUATION_DIR,
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

DEFAULT_OUTPUT_STEM = "usaspending_contracts_category_mapped"
DEFAULT_CATEGORY_SUMMARY_NAME = "category_counts_report.csv"
DEFAULT_MAPPING_SUMMARY_NAME = "category_mapping_summary.json"
DEFAULT_OUTPUT_FORMAT = "parquet"

INTEGRATED_CATEGORY_NAME = "integrated_service_delivery"
UNMAPPED_CATEGORY_NAME = "unmapped"

# ---------------------------------------------------------------------
# Scoring / threshold controls
# ---------------------------------------------------------------------
DEFAULT_MIN_ASSIGNMENT_SCORE = 2
DEFAULT_MIN_PROGRAM_SUPPORT_SCORE = 3
DEFAULT_AMBIGUITY_SCORE_GAP = 1
DEFAULT_MIN_DOMINANCE_GAP = 1
DEFAULT_INTEGRATED_MIN_POSITIVE_CATEGORIES = 3
DEFAULT_INTEGRATED_MIN_TOTAL_SCORE = 6

# Weighted rule strengths.
RULE_WEIGHTS: dict[str, int] = {
    "psc_match": 2,
    "naics_match": 2,
    "strong_keyword_match": 2,
    "keyword_match": 1,
    "multi_signal_bonus": 1,
    "multiple_keyword_bonus": 1,
    "strong_keyword_bonus": 1,
    "engineering_text_recovery_bonus": 2,
    "technical_text_penalty": 2,
    "seta_override_bonus": 4,
}

# Broad codes are weak evidence only; they should not drive assignment.
BROAD_PSC_CODES: set[str] = {
    "R499",
    "R425",
    "R706",
    "U099",
}

BROAD_NAICS_CODES: set[str] = {
    "541330",
    "541715",
}

LOW_SPECIFICITY_KEYWORDS: set[str] = {
    "analysis",
    "support",
    "coordination",
    "management",
    "event",
    "meeting",
    "development",
    "testing",
    "research",
    "r d",
    "innovation",
    "network",
    "engagement",
    "outreach",
    "collaboration",
}

PROTOTYPE_BUILD_TERMS: set[str] = {
    "prototype build",
    "build prototype",
    "hardware prototype",
    "test article",
    "demonstrator",
    "fabrication",
    "fabricate",
    "fabricated",
    "additive manufacturing",
    "3d printing",
    "assemble prototype",
    "prototype integration",
    "prototype unit",
    "mockup",
    "breadboard",
    "benchtop prototype",
}

PROGRAM_SUPPORT_OPERATIONAL_TERMS: set[str] = {
    "program management",
    "project management",
    "pmo",
    "acquisition support",
    "acquisition planning",
    "milestone tracking",
    "compliance support",
    "documentation support",
    "logistics coordination",
    "logistics support",
    "governance support",
    "administrative support",
    "oversight support",
    "program coordination",
    "project coordination",
}

ENGINEERING_STRONG_TERMS: set[str] = {
    "engineering",
    "engineering support",
    "engineering support services",
    "systems engineering",
    "technical assistance",
    "seta",
    "c4i",
    "architecture",
    "design",
    "integration",
    "analysis",
    "modeling",
    "simulation",
    "test",
    "evaluation",
}

PROGRAM_SUPPORT_TRUE_ADMIN_TERMS: set[str] = {
    "program management",
    "project management",
    "pmo",
    "acquisition support",
    "milestone tracking",
    "compliance",
    "documentation",
    "logistics coordination",
    "logistics support",
    "governance",
    "administrative support",
    "financial management",
    "contract management",
    "earned value management",
}

SETA_OVERRIDE_TERMS: set[str] = {
    "seta",
    "systems engineering technical assistance",
}

STRONG_PROTOTYPING_TERMS: set[str] = {
    "prototype development",
    "prototype deliverable",
    "prototype fabrication",
    "rapid prototyping",
    "sbir",
    "phase ii",
    "phase iii",
    "proof of concept",
}

WEAK_PROTOTYPING_TERMS: set[str] = {
    "prototype",
    "fabrication",
    "build",
    "assembly",
    "testbed",
}

NOISE_PHRASES: tuple[str, ...] = (
    "all other professional scientific and technical services",
    "support professional other",
    "other professional",
    "professional scientific and technical services",
    "scientific technical services",
)

TEXT_REQUIRED_CATEGORIES: set[str] = {
    "innovation_ecosystem_access",
    "event_hosting",
    "workspace_collaboration",
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
    strong_signals: tuple[str, ...]
    weak_signals: tuple[str, ...]
    negative_signals: tuple[str, ...]
    psc_hints: tuple[str, ...]
    naics_hints: tuple[str, ...]
    ambiguity_notes: str | None = None


@dataclass(frozen=True)
class CategoryMapperConfig:
    """Configuration for the category mapping stage."""

    taxonomy_path: Path = SERVICE_TAXONOMY_PATH
    output_dir: Path = PROCESSED_DATA_DIR
    report_dir: Path = REPORTS_EVALUATION_DIR
    output_stem: str = DEFAULT_OUTPUT_STEM
    output_format: str = DEFAULT_OUTPUT_FORMAT
    write_mapped_dataset: bool = False
    write_summary_csv: bool = False
    write_summary_json: bool = False
    keep_helper_columns: bool = False
    ambiguity_score_gap: int = DEFAULT_AMBIGUITY_SCORE_GAP
    min_assignment_score: int = DEFAULT_MIN_ASSIGNMENT_SCORE
    min_program_support_score: int = DEFAULT_MIN_PROGRAM_SUPPORT_SCORE
    min_dominance_gap: int = DEFAULT_MIN_DOMINANCE_GAP
    integrated_min_positive_categories: int = DEFAULT_INTEGRATED_MIN_POSITIVE_CATEGORIES
    integrated_min_total_score: int = DEFAULT_INTEGRATED_MIN_TOTAL_SCORE


# ---------------------------------------------------------------------
# Text normalization helpers
# ---------------------------------------------------------------------
_WHITESPACE_RE = re.compile(r"\s+")
_NON_ALNUM_RE = re.compile(r"[^a-z0-9]+")


def normalize_text(value: Any) -> str:
    """Normalize a text-like value for deterministic matching."""
    if value is None or pd.isna(value):
        return ""
    text = str(value).strip().lower()
    if not text:
        return ""
    text = _NON_ALNUM_RE.sub(" ", text)
    text = _WHITESPACE_RE.sub(" ", text).strip()
    return text


def normalize_code(value: Any) -> str:
    """Normalize PSC/NAICS code strings."""
    if value is None or pd.isna(value):
        return ""
    return str(value).strip().upper()


def phrase_in_text(phrase: str, text: str) -> bool:
    """Phrase matcher using normalized strings and padded containment."""
    normalized_phrase = normalize_text(phrase)
    if not normalized_phrase or not text:
        return False
    return f" {normalized_phrase} " in f" {text} "


def remove_noise_phrases(text: str) -> str:
    """Remove known generic boilerplate phrases from normalized text."""
    if not text:
        return ""
    cleaned = text
    for phrase in NOISE_PHRASES:
        cleaned = cleaned.replace(phrase, " ")
    cleaned = _WHITESPACE_RE.sub(" ", cleaned).strip()
    return cleaned


# ---------------------------------------------------------------------
# Taxonomy loading / rule library
# ---------------------------------------------------------------------
def load_service_taxonomy(
    taxonomy_path: Path | str = SERVICE_TAXONOMY_PATH,
) -> list[CategoryRule]:
    """Load service taxonomy YAML and convert it into category rules."""
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
            strong_signals=tuple(
                normalize_text(k)
                for k in (raw.get("strong_signals", []) or [])
                if normalize_text(k)
            ),
            weak_signals=tuple(
                normalize_text(k)
                for k in (raw.get("weak_signals", []) or [])
                if normalize_text(k)
            ),
            negative_signals=tuple(
                normalize_text(k)
                for k in (raw.get("negative_signals", []) or [])
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
            ambiguity_notes=(str(raw.get("ambiguity_notes", "")).strip() or None),
        )
        rules.append(rule)

    if not rules:
        raise ValueError("No valid taxonomy categories were parsed.")

    return rules


def build_category_rule_library(
    category_rules: list[CategoryRule],
) -> dict[str, CategoryRule]:
    """Build a simple category-name keyed rule library."""
    return {rule.name: rule for rule in category_rules}


# ---------------------------------------------------------------------
# Schema / preprocessing helpers
# ---------------------------------------------------------------------
def validate_input_dataframe(df: pd.DataFrame) -> None:
    """Validate required input schema."""
    missing = [column for column in REQUIRED_INPUT_COLUMNS if column not in df.columns]
    if missing:
        raise ValueError(
            "Input dataframe is missing required category mapper columns: "
            + ", ".join(missing)
        )


def ensure_category_text_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Create normalized helper columns for deterministic mapping."""
    output = df.copy()

    for column in OPTIONAL_TEXT_COLUMNS:
        if column not in output.columns:
            output[column] = ""

    output["category_text_all_norm"] = output["text_all"].map(normalize_text)
    output["category_description_norm"] = output["description"].map(normalize_text)
    output["category_description_clean_norm"] = output["description_clean"].map(
        normalize_text
    )
    output["category_psc_description_norm"] = output["psc_description"].map(
        normalize_text
    )
    output["category_naics_description_norm"] = output["naics_description"].map(
        normalize_text
    )
    output["category_psc_code_norm"] = output["psc_code"].map(normalize_code)
    output["category_naics_code_norm"] = output["naics_code"].map(normalize_code)

    return output


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

    A keyword is only counted once even if it appears in both fields.
    """
    matches: list[str] = []

    for keyword in category_rule.keywords:
        if (
            description_clean_norm and phrase_in_text(keyword, description_clean_norm)
        ) or (text_all_norm and phrase_in_text(keyword, text_all_norm)):
            matches.append(keyword)

    return sorted(set(matches))


def get_strong_signal_matches_for_category(
    *,
    text_all_norm: str,
    description_clean_norm: str,
    category_rule: CategoryRule,
) -> list[str]:
    """Return matched strong signals for one category."""
    matches: list[str] = []

    for signal in category_rule.strong_signals:
        if (
            description_clean_norm and phrase_in_text(signal, description_clean_norm)
        ) or (text_all_norm and phrase_in_text(signal, text_all_norm)):
            matches.append(signal)

    return sorted(set(matches))


def get_weak_signal_matches_for_category(
    *,
    text_all_norm: str,
    description_clean_norm: str,
    category_rule: CategoryRule,
) -> list[str]:
    """Return matched weak signals for one category."""
    matches: list[str] = []

    for signal in category_rule.weak_signals:
        if (
            description_clean_norm and phrase_in_text(signal, description_clean_norm)
        ) or (text_all_norm and phrase_in_text(signal, text_all_norm)):
            matches.append(signal)

    return sorted(set(matches))


def _keyword_specificity_score(
    matched_keywords: list[str],
    matched_strong_signals: list[str],
) -> int:
    """Score keyword evidence conservatively."""
    score = 0

    specific_keywords = [
        keyword
        for keyword in matched_keywords
        if keyword not in LOW_SPECIFICITY_KEYWORDS
    ]

    if matched_strong_signals:
        score += RULE_WEIGHTS["strong_keyword_match"]
        if len(matched_strong_signals) >= 2:
            score += RULE_WEIGHTS["strong_keyword_bonus"]

    if specific_keywords:
        score += RULE_WEIGHTS["keyword_match"]
        if len(specific_keywords) >= 2:
            score += RULE_WEIGHTS["multiple_keyword_bonus"]

    return score


def _has_text_evidence(
    matched_keywords: list[str],
    matched_strong_signals: list[str],
) -> bool:
    """Return True when text produced non-trivial evidence."""
    return bool(matched_keywords or matched_strong_signals)


def _apply_row_level_signal_boosts(
    *,
    row: pd.Series,
    category_name: str,
    score: int,
    matched_keywords: list[str],
    matched_strong_signals: list[str],
    reason_codes: list[str],
) -> tuple[int, list[str]]:
    def any_phrase_in_text(phrases: set[str], text: str) -> bool:
        return any(phrase_in_text(phrase, text) for phrase in phrases)

    full_text_parts: list[str] = []
    for key in (
        "category_text_all_norm",
        "category_psc_description_norm",
        "category_naics_description_norm",
    ):
        val = row[key]
        if val is not None and not pd.isna(val):
            full_text_parts.append(str(val))
    full_text = " ".join(full_text_parts)
    full_text = remove_noise_phrases(full_text)

    if category_name == "engineering_design_support":
        if any_phrase_in_text(ENGINEERING_STRONG_TERMS, full_text):
            score += RULE_WEIGHTS["engineering_text_recovery_bonus"]
            reason_codes.append("ENGINEERING_TEXT_RECOVERY")
        if any_phrase_in_text(SETA_OVERRIDE_TERMS, full_text):
            score += RULE_WEIGHTS["seta_override_bonus"]
            reason_codes.append("SETA_ENGINEERING_OVERRIDE")

    if category_name == "project_program_support":
        has_engineering_text = any_phrase_in_text(ENGINEERING_STRONG_TERMS, full_text)
        has_true_admin_text = any_phrase_in_text(
            PROGRAM_SUPPORT_TRUE_ADMIN_TERMS, full_text
        )
        if has_engineering_text and not has_true_admin_text:
            score -= RULE_WEIGHTS["technical_text_penalty"]
            score = max(0, score)
            reason_codes.append("PROGRAM_SUPPORT_DOWNWEIGHTED_FOR_TECHNICAL_TEXT")

    return score, reason_codes


def _count_phrase_hits(phrases: set[str], text: str) -> int:
    return sum(1 for phrase in phrases if phrase_in_text(phrase, text))


def category_signal_details(
    *,
    row: pd.Series,
    category_rule: CategoryRule,
) -> dict[str, Any]:
    """Compute all category signals for one row against one taxonomy category."""
    psc_code = row["category_psc_code_norm"]
    naics_code = row["category_naics_code_norm"]
    text_all_norm = row["category_text_all_norm"]
    description_clean_norm = row["category_description_clean_norm"]

    text_all_norm = remove_noise_phrases(text_all_norm)
    description_clean_norm = remove_noise_phrases(description_clean_norm)

    matched_psc_codes = [code for code in category_rule.psc_hints if code == psc_code]
    matched_naics_codes = [
        code for code in category_rule.naics_hints if code == naics_code
    ]
    matched_keywords = get_keyword_matches_for_category(
        text_all_norm=text_all_norm,
        description_clean_norm=description_clean_norm,
        category_rule=category_rule,
    )
    matched_strong_signals = get_strong_signal_matches_for_category(
        text_all_norm=text_all_norm,
        description_clean_norm=description_clean_norm,
        category_rule=category_rule,
    )
    matched_weak_signals = get_weak_signal_matches_for_category(
        text_all_norm=text_all_norm,
        description_clean_norm=description_clean_norm,
        category_rule=category_rule,
    )

    specific_keywords = [
        keyword
        for keyword in matched_keywords
        if keyword not in LOW_SPECIFICITY_KEYWORDS
    ]

    signal_types = 0
    text_evidence = _has_text_evidence(matched_keywords, matched_strong_signals)

    if matched_psc_codes:
        signal_types += 1
    if matched_naics_codes:
        signal_types += 1
    if text_evidence:
        signal_types += 1

    score = 0
    reason_codes: list[str] = []

    # Specific PSC / NAICS help. Broad codes are recorded but do not score.
    if matched_psc_codes:
        if any(code in BROAD_PSC_CODES for code in matched_psc_codes):
            reason_codes.append("PSC_BROAD_MATCH")
        else:
            score += RULE_WEIGHTS["psc_match"]
            reason_codes.append("PSC_MATCH")

    if matched_naics_codes:
        if any(code in BROAD_NAICS_CODES for code in matched_naics_codes):
            reason_codes.append("NAICS_BROAD_MATCH")
        else:
            score += RULE_WEIGHTS["naics_match"]
            reason_codes.append("NAICS_MATCH")

    keyword_score = _keyword_specificity_score(
        matched_keywords=matched_keywords,
        matched_strong_signals=matched_strong_signals,
    )
    if matched_keywords or matched_strong_signals:
        if keyword_score > 0:
            score += keyword_score
            if matched_keywords:
                reason_codes.append("KEYWORD_MATCH")
            if len(specific_keywords) >= 2:
                reason_codes.append("MULTI_KEYWORD_MATCH")
            if matched_strong_signals:
                reason_codes.append("STRONG_SIGNAL_MATCH")
        else:
            reason_codes.append("LOW_SPECIFICITY_KEYWORD_ONLY")

    if (
        category_rule.name in {"professional_services_support", "technical_advisory_services"}
        and len(matched_strong_signals) >= 1
    ):
        score += 1
        reason_codes.append("ALT_CATEGORY_STRONG_SIGNAL_BOOST")

    score, reason_codes = _apply_row_level_signal_boosts(
        row=row,
        category_name=category_rule.name,
        score=score,
        matched_keywords=matched_keywords,
        matched_strong_signals=matched_strong_signals,
        reason_codes=reason_codes,
    )

    if signal_types >= 2 and score >= 2:
        score += RULE_WEIGHTS["multi_signal_bonus"]
        reason_codes.append("MULTI_SIGNAL")

    # Category-specific gating
    hard_reject = False

    if category_rule.name == "prototyping":
        has_prototype_build_evidence = bool(
            set(matched_strong_signals) & PROTOTYPE_BUILD_TERMS
        )
        if not has_prototype_build_evidence:
            # Broad R&D / development / "prototype" alone is not enough.
            hard_reject = True
            reason_codes.append("PROTOTYPE_BUILD_REQUIRED")

    if category_rule.name == "innovation_ecosystem_access":
        # Never allow broad codes alone to drive this bucket.
        if not matched_strong_signals:
            hard_reject = True
            reason_codes.append("ECOSYSTEM_TEXT_SIGNAL_REQUIRED")

    if category_rule.name == "event_hosting":
        if not matched_strong_signals and "event hosting" not in matched_keywords:
            # Event must be more explicit than a generic mention.
            if not (
                {"workshop", "conference", "symposium", "hackathon", "challenge event"}
                & set(matched_keywords)
            ):
                hard_reject = True
                reason_codes.append("EVENT_TEXT_SIGNAL_REQUIRED")

    if category_rule.name == "workspace_collaboration":
        if not matched_strong_signals:
            hard_reject = True
            reason_codes.append("WORKSPACE_TEXT_SIGNAL_REQUIRED")

    if category_rule.name == "project_program_support":
        has_program_ops_text = bool(
            set(matched_strong_signals) & PROGRAM_SUPPORT_OPERATIONAL_TERMS
        ) or bool(set(specific_keywords) & PROGRAM_SUPPORT_OPERATIONAL_TERMS)

        # Avoid making this the fallback for broad "other support" rows.
        if not has_program_ops_text and score < DEFAULT_MIN_PROGRAM_SUPPORT_SCORE:
            hard_reject = True
            reason_codes.append("PROGRAM_SUPPORT_OPERATIONAL_SIGNAL_REQUIRED")

    if hard_reject:
        score = 0

    return {
        "category_name": category_rule.name,
        "score": int(score),
        "signal_types": signal_types if score > 0 else 0,
        "matched_keywords": matched_keywords,
        "matched_strong_signals": matched_strong_signals,
        "matched_weak_signals": matched_weak_signals,
        "matched_psc_codes": matched_psc_codes,
        "matched_naics_codes": matched_naics_codes,
        "reason_codes": reason_codes,
        "ambiguity_notes": category_rule.ambiguity_notes,
    }


def _category_specificity_value(
    category_detail: dict[str, Any],
    *,
    rule_library: dict[str, CategoryRule],
) -> int:
    """
    Deterministic specificity ranking for tie-breaking.

    Higher means more specific / preferred when evidence is otherwise similar.
    """
    category_name = str(category_detail["category_name"])
    matched_keywords = set(category_detail["matched_keywords"])
    matched_strong_signals = set(category_detail["matched_strong_signals"])
    matched_psc = set(category_detail["matched_psc_codes"])
    matched_naics = set(category_detail["matched_naics_codes"])

    value = 0

    if matched_psc and not any(code in BROAD_PSC_CODES for code in matched_psc):
        value += 1
    if matched_naics and not any(code in BROAD_NAICS_CODES for code in matched_naics):
        value += 1

    value += len(matched_strong_signals)

    if category_name == "prototyping":
        if matched_strong_signals & PROTOTYPE_BUILD_TERMS:
            value += 3

    if category_name == "engineering_design_support":
        if {
            "systems engineering",
            "system design",
            "architecture design",
            "cad",
            "modeling",
            "simulation",
            "engineering analysis",
            "technical analysis",
        } & matched_strong_signals:
            value += 2

    if category_name == "project_program_support":
        if matched_strong_signals & PROGRAM_SUPPORT_OPERATIONAL_TERMS:
            value += 1

    if category_name == INTEGRATED_CATEGORY_NAME:
        value -= 1

    return value


def _build_reason_text(
    *,
    final_category: str,
    primary_detail: dict[str, Any] | None,
    matched_categories: list[str],
    ambiguity_flag: bool,
    ambiguity_reason: str,
) -> str:
    """Build concise human-readable reason text."""
    if final_category == UNMAPPED_CATEGORY_NAME or primary_detail is None:
        return "No sufficiently specific or dominant category evidence; row mapped as unmapped."

    parts: list[str] = [f"Mapped to {final_category}"]

    if primary_detail.get("matched_psc_codes"):
        parts.append("PSC signals: " + ", ".join(primary_detail["matched_psc_codes"]))

    if primary_detail.get("matched_naics_codes"):
        parts.append(
            "NAICS signals: " + ", ".join(primary_detail["matched_naics_codes"])
        )

    preview_terms = (
        primary_detail.get("matched_strong_signals", [])
        or primary_detail.get("matched_keywords", [])
    )
    if preview_terms:
        preview = ", ".join(preview_terms[:6])
        if len(preview_terms) > 6:
            preview += ", ..."
        parts.append(f"text signals: {preview}")

    if len(matched_categories) >= 2:
        parts.append("multiple categories had positive evidence")

    if ambiguity_flag and ambiguity_reason:
        parts.append(f"ambiguity: {ambiguity_reason}")

    return " | ".join(parts)


def _empty_unmapped_result(reason_code: str = "UNMAPPED") -> dict[str, Any]:
    """Return a standard unmapped result payload."""
    return {
        "mapped_service_category": UNMAPPED_CATEGORY_NAME,
        "category_mapper_score": 0,
        "category_mapper_reason_codes": reason_code,
        "category_mapper_reason_text": (
            "No sufficiently specific or dominant category evidence; row mapped as unmapped."
        ),
        "category_mapper_matched_categories": "",
        "category_mapper_matched_keywords": "",
        "category_mapper_matched_psc_codes": "",
        "category_mapper_matched_naics_codes": "",
        "category_mapper_is_ambiguous": False,
        "category_mapper_ambiguity_notes": "",
        "category_mapper_runner_up_categories": "",
        "category_mapper_signal_type_count": 0,
        "category_mapper_category_match_count": 0,
    }


def assign_final_category(
    category_details: list[dict[str, Any]],
    *,
    rule_library: dict[str, CategoryRule],
    row: pd.Series,
    ambiguity_score_gap: int = DEFAULT_AMBIGUITY_SCORE_GAP,
    min_assignment_score: int = DEFAULT_MIN_ASSIGNMENT_SCORE,
    min_program_support_score: int = DEFAULT_MIN_PROGRAM_SUPPORT_SCORE,
    min_dominance_gap: int = DEFAULT_MIN_DOMINANCE_GAP,
    integrated_min_positive_categories: int = DEFAULT_INTEGRATED_MIN_POSITIVE_CATEGORIES,
    integrated_min_total_score: int = DEFAULT_INTEGRATED_MIN_TOTAL_SCORE,
) -> dict[str, Any]:
    """
    Select the strongest final category for a row.

    Tie-break order:
    1. highest score
    2. most signal types
    3. most matched strong signals
    4. most matched specific keywords
    5. strongest structured evidence / specificity value
    6. lexical category name (deterministic)
    """
    positive_categories = [d for d in category_details if d["score"] > 0]
    matched_categories = sorted(detail["category_name"] for detail in positive_categories)

    if not positive_categories:
        return _empty_unmapped_result()

    ranked = sorted(
        positive_categories,
        key=lambda item: (
            item["score"],
            item["signal_types"],
            len(item["matched_strong_signals"]),
            len(
                [
                    keyword
                    for keyword in item["matched_keywords"]
                    if keyword not in LOW_SPECIFICITY_KEYWORDS
                ]
            ),
            _category_specificity_value(item, rule_library=rule_library),
            item["category_name"],
        ),
        reverse=True,
    )

    best = ranked[0]
    runner_ups = ranked[1:]
    best_score = int(best["score"])

    full_text_cell = row["category_text_all_norm"]
    full_text = (
        ""
        if full_text_cell is None or pd.isna(full_text_cell)
        else str(full_text_cell)
    )

    def should_engineering_fallback(full_text: str) -> bool:
        engineering_fallback_terms = [
            "engineering",
            "systems",
            "integration",
            "design",
            "analysis",
            "fabrication",
            "testing",
            "evaluation",
            "technical",
        ]
        engineering_signal_count = sum(
            term in full_text for term in engineering_fallback_terms
        )
        return engineering_signal_count >= 3 and "prototype" not in full_text

    # Minimum score threshold
    if best_score < min_assignment_score:
        if should_engineering_fallback(full_text):
            return {
                "mapped_service_category": "engineering_design_support",
                "category_mapper_score": best_score,
                "category_mapper_reason_codes": "ENGINEERING_FALLBACK_OVERRIDE",
                "category_mapper_reason_text": "Mapped to engineering_design_support via fallback override after weak initial assignment evidence.",
                "category_mapper_matched_categories": "|".join(matched_categories),
                "category_mapper_matched_keywords": "",
                "category_mapper_matched_psc_codes": "",
                "category_mapper_matched_naics_codes": "",
                "category_mapper_is_ambiguous": False,
                "category_mapper_ambiguity_notes": "",
                "category_mapper_runner_up_categories": "",
                "category_mapper_signal_type_count": 0,
                "category_mapper_category_match_count": len(matched_categories),
            }
        return _empty_unmapped_result("BELOW_MIN_ASSIGNMENT_SCORE")

    # Make program support harder to win on weak evidence.
    if (
        best["category_name"] == "project_program_support"
        and best_score < min_program_support_score
    ):
        return _empty_unmapped_result("PROGRAM_SUPPORT_BELOW_MIN_SCORE")

    ambiguity_flag = False
    ambiguity_notes: list[str] = []
    runner_up_categories: list[str] = []

    second_score = int(runner_ups[0]["score"]) if runner_ups else -999

    if runner_ups:
        close_competitors = [
            item
            for item in runner_ups
            if (best_score - int(item["score"])) <= ambiguity_score_gap
        ]
        if close_competitors:
            ambiguity_flag = True
            runner_up_categories = [item["category_name"] for item in close_competitors]
            ambiguity_notes.append(
                "Top categories had similar scores and were preserved as an explicit ambiguity."
            )

    # Dominance rule: do not force a label when the winner is too weakly separated.
    if runner_ups and (best_score - second_score) < min_dominance_gap and best_score <= (
        min_assignment_score + 1
    ):
        if should_engineering_fallback(full_text):
            return {
                "mapped_service_category": "engineering_design_support",
                "category_mapper_score": best_score,
                "category_mapper_reason_codes": "ENGINEERING_FALLBACK_OVERRIDE",
                "category_mapper_reason_text": "Mapped to engineering_design_support via fallback override after insufficient dominance.",
                "category_mapper_matched_categories": "|".join(matched_categories),
                "category_mapper_matched_keywords": "",
                "category_mapper_matched_psc_codes": "",
                "category_mapper_matched_naics_codes": "",
                "category_mapper_is_ambiguous": False,
                "category_mapper_ambiguity_notes": "",
                "category_mapper_runner_up_categories": "",
                "category_mapper_signal_type_count": 0,
                "category_mapper_category_match_count": len(matched_categories),
            }
        return _empty_unmapped_result("INSUFFICIENT_DOMINANCE")

    # Integrated-service handling: only plausible if multiple categories are strong.
    if (
        len(positive_categories) >= integrated_min_positive_categories
        and sum(int(item["score"]) for item in positive_categories)
        >= integrated_min_total_score
    ):
        integrated_present = any(
            item["category_name"] == INTEGRATED_CATEGORY_NAME
            for item in positive_categories
        )
        if integrated_present:
            integrated_detail = next(
                item
                for item in positive_categories
                if item["category_name"] == INTEGRATED_CATEGORY_NAME
            )
            if int(integrated_detail["score"]) >= int(best["score"]) - ambiguity_score_gap:
                if best["category_name"] != INTEGRATED_CATEGORY_NAME:
                    ambiguity_flag = True
                    ambiguity_notes.append(
                        "Integrated delivery was also plausible due to bundled multi-category evidence."
                    )

    final_category = str(best["category_name"])
    reason_codes = list(best["reason_codes"])

    if ambiguity_flag:
        reason_codes.append("CATEGORY_AMBIGUOUS")
    if len(positive_categories) >= 2:
        reason_codes.append("MULTI_CATEGORY_MATCH")
    if (
        len(positive_categories) >= integrated_min_positive_categories
        and sum(int(item["score"]) for item in positive_categories)
        >= integrated_min_total_score
    ):
        reason_codes.append("POTENTIAL_INTEGRATED_SERVICE")

    strong_proto_hits = _count_phrase_hits(STRONG_PROTOTYPING_TERMS, full_text)
    weak_proto_hits = _count_phrase_hits(WEAK_PROTOTYPING_TERMS, full_text)
    engineering_text_detected = any(
        k in full_text
        for k in [
            "engineering",
            "engineering support",
            "systems engineering",
            "technical assistance",
            "integration",
            "design",
            "analysis",
            "c4i",
            "test",
            "evaluation",
        ]
    )
    if (
        final_category == "project_program_support"
        and "engineering_design_support" in str(runner_up_categories)
        and engineering_text_detected
    ):
        final_category = "engineering_design_support"
        reason_codes.append("FINAL_ENGINEERING_OVERRIDE")

    if (
        final_category != "prototyping"
        and (
            strong_proto_hits >= 1
            or weak_proto_hits >= 3
        )
    ):
        final_category = "prototyping"
        reason_codes.append("PROTO_DOMINANT_OVERRIDE")

    all_keywords = sorted(
        {
            keyword
            for detail in positive_categories
            for keyword in detail["matched_keywords"]
        }
    )
    all_psc_codes = sorted(
        {
            code
            for detail in positive_categories
            for code in detail["matched_psc_codes"]
        }
    )
    all_naics_codes = sorted(
        {
            code
            for detail in positive_categories
            for code in detail["matched_naics_codes"]
        }
    )

    reason_text = _build_reason_text(
        final_category=final_category,
        primary_detail=best,
        matched_categories=matched_categories,
        ambiguity_flag=ambiguity_flag,
        ambiguity_reason=" | ".join(ambiguity_notes),
    )

    return {
        "mapped_service_category": final_category,
        "category_mapper_score": best_score,
        "category_mapper_reason_codes": "|".join(dict.fromkeys(reason_codes)),
        "category_mapper_reason_text": reason_text,
        "category_mapper_matched_categories": "|".join(matched_categories),
        "category_mapper_matched_keywords": "|".join(all_keywords),
        "category_mapper_matched_psc_codes": "|".join(all_psc_codes),
        "category_mapper_matched_naics_codes": "|".join(all_naics_codes),
        "category_mapper_is_ambiguous": ambiguity_flag,
        "category_mapper_ambiguity_notes": " | ".join(
            note for note in ambiguity_notes if note
        ),
        "category_mapper_runner_up_categories": "|".join(runner_up_categories),
        "category_mapper_signal_type_count": len(
            [signal for signal in [all_psc_codes, all_naics_codes, all_keywords] if signal]
        ),
        "category_mapper_category_match_count": len(matched_categories),
    }


# ---------------------------------------------------------------------
# Public application functions
# ---------------------------------------------------------------------
def score_row_categories(
    row: pd.Series,
    rule_library: dict[str, CategoryRule],
) -> list[dict[str, Any]]:
    """Score one row against all taxonomy categories."""
    return [
        category_signal_details(row=row, category_rule=rule)
        for rule in rule_library.values()
    ]


def map_contract_categories(
    df: pd.DataFrame,
    taxonomy_rules: list[CategoryRule] | dict[str, CategoryRule],
    *,
    keep_helper_columns: bool = False,
    ambiguity_score_gap: int = DEFAULT_AMBIGUITY_SCORE_GAP,
    min_assignment_score: int = DEFAULT_MIN_ASSIGNMENT_SCORE,
    min_program_support_score: int = DEFAULT_MIN_PROGRAM_SUPPORT_SCORE,
    min_dominance_gap: int = DEFAULT_MIN_DOMINANCE_GAP,
    integrated_min_positive_categories: int = DEFAULT_INTEGRATED_MIN_POSITIVE_CATEGORIES,
    integrated_min_total_score: int = DEFAULT_INTEGRATED_MIN_TOTAL_SCORE,
) -> pd.DataFrame:
    """Apply service-category mapping to a comparable-contract dataframe."""
    validate_input_dataframe(df)

    if isinstance(taxonomy_rules, list):
        rule_library = build_category_rule_library(taxonomy_rules)
    else:
        rule_library = taxonomy_rules

    working = ensure_category_text_columns(df)

    mapped_rows = [
        assign_final_category(
            score_row_categories(row=row, rule_library=rule_library),
            rule_library=rule_library,
            row=row,
            ambiguity_score_gap=ambiguity_score_gap,
            min_assignment_score=min_assignment_score,
            min_program_support_score=min_program_support_score,
            min_dominance_gap=min_dominance_gap,
            integrated_min_positive_categories=integrated_min_positive_categories,
            integrated_min_total_score=integrated_min_total_score,
        )
        for _, row in working.iterrows()
    ]

    mapped_df = pd.DataFrame(mapped_rows, index=working.index)
    output = pd.concat([working, mapped_df], axis=1)

    if not keep_helper_columns:
        helper_cols = [
            "category_text_all_norm",
            "category_description_norm",
            "category_description_clean_norm",
            "category_psc_description_norm",
            "category_naics_description_norm",
            "category_psc_code_norm",
            "category_naics_code_norm",
        ]
        existing_helper_cols = [column for column in helper_cols if column in output.columns]
        output = output.drop(columns=existing_helper_cols)

    return output


def build_category_counts_report(df: pd.DataFrame) -> pd.DataFrame:
    """
    Build a category counts summary dataframe.

    Output columns:
    - mapped_service_category
    - row_count
    - percent_of_rows
    - ambiguous_count
    - ambiguous_pct_within_category
    - average_mapper_score
    """
    required = [
        "mapped_service_category",
        "category_mapper_score",
        "category_mapper_is_ambiguous",
    ]
    missing = [column for column in required if column not in df.columns]
    if missing:
        raise ValueError(
            "Dataframe missing required category mapping result columns: "
            + ", ".join(missing)
        )

    total_rows = int(len(df))
    if total_rows == 0:
        return pd.DataFrame(
            columns=[
                "mapped_service_category",
                "row_count",
                "percent_of_rows",
                "ambiguous_count",
                "ambiguous_pct_within_category",
                "average_mapper_score",
            ]
        )

    grouped = (
        df.groupby("mapped_service_category", dropna=False)
        .agg(
            row_count=("mapped_service_category", "size"),
            ambiguous_count=("category_mapper_is_ambiguous", "sum"),
            average_mapper_score=("category_mapper_score", "mean"),
        )
        .reset_index()
    )

    grouped["percent_of_rows"] = (grouped["row_count"] / total_rows * 100.0).round(4)
    grouped["ambiguous_pct_within_category"] = grouped.apply(
        lambda row: round(
            (float(row["ambiguous_count"]) / float(row["row_count"]) * 100.0)
            if float(row["row_count"]) > 0
            else 0.0,
            4,
        ),
        axis=1,
    )
    grouped["average_mapper_score"] = grouped["average_mapper_score"].round(4)

    grouped = grouped.sort_values(
        by=["row_count", "mapped_service_category"],
        ascending=[False, True],
    ).reset_index(drop=True)

    return grouped


def summarize_category_mapping_results(df: pd.DataFrame) -> dict[str, Any]:
    """Build a compact JSON-friendly mapping summary."""
    required = [
        "mapped_service_category",
        "category_mapper_score",
        "category_mapper_is_ambiguous",
    ]
    missing = [column for column in required if column not in df.columns]
    if missing:
        raise ValueError(
            "Dataframe missing required category mapping result columns: "
            + ", ".join(missing)
        )

    total_rows = int(len(df))
    ambiguous_rows = int(df["category_mapper_is_ambiguous"].sum())
    unmapped_rows = int((df["mapped_service_category"] == UNMAPPED_CATEGORY_NAME).sum())
    mapped_rows = total_rows - unmapped_rows

    category_counts = (
        df["mapped_service_category"]
        .fillna(UNMAPPED_CATEGORY_NAME)
        .value_counts(dropna=False)
        .to_dict()
    )

    score_distribution = df["category_mapper_score"].value_counts().sort_index().to_dict()

    return {
        "total_rows": total_rows,
        "mapped_rows": mapped_rows,
        "unmapped_rows": unmapped_rows,
        "ambiguous_rows": ambiguous_rows,
        "mapped_pct": round((mapped_rows / total_rows * 100.0) if total_rows else 0.0, 4),
        "unmapped_pct": round((unmapped_rows / total_rows * 100.0) if total_rows else 0.0, 4),
        "ambiguous_pct": round((ambiguous_rows / total_rows * 100.0) if total_rows else 0.0, 4),
        "category_counts": category_counts,
        "score_distribution": score_distribution,
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


def write_mapping_summary_json(
    summary: dict[str, Any],
    output_path: Path,
) -> Path:
    """Write JSON summary artifact."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    return output_path


def save_category_mapping_outputs(
    *,
    mapped_df: pd.DataFrame,
    config: CategoryMapperConfig,
) -> dict[str, Path]:
    """Persist selected category mapping outputs."""
    config.output_dir.mkdir(parents=True, exist_ok=True)
    config.report_dir.mkdir(parents=True, exist_ok=True)

    outputs: dict[str, Path] = {}
    suffix = config.output_format.lower().strip()

    if config.write_mapped_dataset:
        mapped_path = config.output_dir / f"{config.output_stem}.{suffix}"
        _write_dataframe(mapped_df, mapped_path, config.output_format)
        outputs["mapped_dataset"] = mapped_path

    category_counts = build_category_counts_report(mapped_df)

    if config.write_summary_csv:
        summary_csv_path = config.report_dir / DEFAULT_CATEGORY_SUMMARY_NAME
        category_counts.to_csv(summary_csv_path, index=False)
        outputs["category_counts_report"] = summary_csv_path

    if config.write_summary_json:
        summary = summarize_category_mapping_results(mapped_df)
        summary_json_path = config.report_dir / DEFAULT_MAPPING_SUMMARY_NAME
        write_mapping_summary_json(summary, summary_json_path)
        outputs["mapping_summary_json"] = summary_json_path

    return outputs


# ---------------------------------------------------------------------
# CLI helpers
# ---------------------------------------------------------------------
def _load_input_dataframe(input_path: Path) -> pd.DataFrame:
    """Load supported input dataset formats."""
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


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments for category mapping."""
    parser = argparse.ArgumentParser(
        description="Map filtered comparable contracts to service categories."
    )
    parser.add_argument(
        "--input-path",
        type=Path,
        required=True,
        help="Path to the filtered comparable dataset.",
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
        help="Directory for mapped dataset output.",
    )
    parser.add_argument(
        "--report-dir",
        type=Path,
        default=REPORTS_EVALUATION_DIR,
        help="Directory for summary report outputs.",
    )
    parser.add_argument(
        "--output-stem",
        type=str,
        default=DEFAULT_OUTPUT_STEM,
        help="Base filename stem for mapped dataset output.",
    )
    parser.add_argument(
        "--output-format",
        type=str,
        default=DEFAULT_OUTPUT_FORMAT,
        choices=["parquet", "csv", "json"],
        help="File format for mapped dataset output.",
    )
    parser.add_argument(
        "--keep-helper-columns",
        action="store_true",
        help="Retain normalized helper columns used during mapping.",
    )
    parser.add_argument(
        "--write-mapped-dataset",
        action="store_true",
        help="Write the mapped dataset to disk.",
    )
    parser.add_argument(
        "--write-summary-csv",
        action="store_true",
        help="Write category counts summary CSV.",
    )
    parser.add_argument(
        "--write-summary-json",
        action="store_true",
        help="Write mapping summary JSON.",
    )
    parser.add_argument(
        "--ambiguity-score-gap",
        type=int,
        default=DEFAULT_AMBIGUITY_SCORE_GAP,
        help="Maximum score gap to preserve explicit ambiguity.",
    )
    parser.add_argument(
        "--min-assignment-score",
        type=int,
        default=DEFAULT_MIN_ASSIGNMENT_SCORE,
        help="Minimum score required before a category can be assigned.",
    )
    parser.add_argument(
        "--min-program-support-score",
        type=int,
        default=DEFAULT_MIN_PROGRAM_SUPPORT_SCORE,
        help="Minimum score required before project_program_support can be assigned.",
    )
    parser.add_argument(
        "--min-dominance-gap",
        type=int,
        default=DEFAULT_MIN_DOMINANCE_GAP,
        help="Minimum score gap needed to separate the winner from the runner-up when evidence is weak.",
    )
    return parser.parse_args()


def main() -> None:
    """CLI entry point."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )

    validate_settings()
    ensure_directories()

    args = parse_args()

    config = CategoryMapperConfig(
        taxonomy_path=args.taxonomy_path,
        output_dir=args.output_dir,
        report_dir=args.report_dir,
        output_stem=args.output_stem,
        output_format=args.output_format,
        write_mapped_dataset=args.write_mapped_dataset,
        write_summary_csv=args.write_summary_csv,
        write_summary_json=args.write_summary_json,
        keep_helper_columns=args.keep_helper_columns,
        ambiguity_score_gap=args.ambiguity_score_gap,
        min_assignment_score=args.min_assignment_score,
        min_program_support_score=args.min_program_support_score,
        min_dominance_gap=args.min_dominance_gap,
    )

    LOGGER.info("Loading input dataset from %s", args.input_path)
    df = _load_input_dataframe(args.input_path)

    LOGGER.info("Loading service taxonomy from %s", config.taxonomy_path)
    taxonomy_rules = load_service_taxonomy(config.taxonomy_path)

    LOGGER.info("Running category mapping on %s rows", len(df))
    mapped_df = map_contract_categories(
        df,
        taxonomy_rules,
        keep_helper_columns=config.keep_helper_columns,
        ambiguity_score_gap=config.ambiguity_score_gap,
        min_assignment_score=config.min_assignment_score,
        min_program_support_score=config.min_program_support_score,
        min_dominance_gap=config.min_dominance_gap,
        integrated_min_positive_categories=config.integrated_min_positive_categories,
        integrated_min_total_score=config.integrated_min_total_score,
    )

    summary = summarize_category_mapping_results(mapped_df)
    LOGGER.info(
        "Category mapping complete | total_rows=%s | mapped_rows=%s | "
        "unmapped_rows=%s | ambiguous_rows=%s",
        summary["total_rows"],
        summary["mapped_rows"],
        summary["unmapped_rows"],
        summary["ambiguous_rows"],
    )

    if (
        config.write_mapped_dataset
        or config.write_summary_csv
        or config.write_summary_json
    ):
        outputs = save_category_mapping_outputs(mapped_df=mapped_df, config=config)
        for name, path in outputs.items():
            LOGGER.info("Wrote %s -> %s", name, path)


if __name__ == "__main__":
    main()