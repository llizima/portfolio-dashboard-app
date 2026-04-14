"""
Centralized assumptions layer for the Applied Government Analytics (AGA) external benchmark/value
calculator.

Purpose
-------
This module defines the reusable assumptions that later calculator logic can
import without duplicating constants inside Streamlit pages, business logic,
or scenario code.

This module is intentionally limited to:
- benchmark reference anchors
- scenario definitions and multipliers
- category-level assumption profiles
- default calculator inputs
- exportable assumption references

It does NOT:
- render Streamlit widgets
- calculate final value estimates
- claim savings, ROI, or internal cost avoidance
- read internal Applied Government Analytics (AGA) financial data
- perform category-specific empirical benchmarking unless such values are
  explicitly available and validated

Design philosophy
-----------------
The calculator is intended to support conservative, benchmark-based external
cost context. Current uploaded KPI outputs provide overall benchmark quartiles
for the comparable-contract dataset, which are used here as the primary
benchmark-derived anchors. Category-level profiles are supported, but unless
validated category-specific benchmark distributions are available, they should
be treated as structured calculator defaults rather than empirical facts.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import pandas as pd

from src.config.settings import (
    PROCESSED_DATA_DIR,
    ensure_directories,
    validate_settings,
)

# ---------------------------------------------------------------------
# Version / metadata
# ---------------------------------------------------------------------
ASSUMPTIONS_VERSION = "1.0"
ASSUMPTIONS_OUTPUT_NAME = "calculator_reference_values.json"
DEFAULT_EXPORT_PATH = PROCESSED_DATA_DIR / ASSUMPTIONS_OUTPUT_NAME


# ---------------------------------------------------------------------
# Benchmark-derived overall anchors
# ---------------------------------------------------------------------
# These values come from the current overall benchmark KPI summary and are
# treated as descriptive anchors for later scenario-based estimation.
# They are not audited savings values and should not be interpreted as proof
# of internal cost avoidance.
OVERALL_BENCHMARK_LOW_Q1 = 316_885.8675
OVERALL_BENCHMARK_MEDIAN = 30_470_594.47
OVERALL_BENCHMARK_HIGH_Q3 = 66_770_481.5675

BENCHMARK_REFERENCE_SOURCE = {
    "source_type": "overall_comparable_contract_kpis",
    "reference_dataset": "comparable_contracts",
    "reference_metric_field": "award_amount",
    "reference_basis": "overall comparable-contract distribution",
    "benchmark_low_definition": "25th percentile (Q1)",
    "benchmark_central_definition": "50th percentile (median)",
    "benchmark_high_definition": "75th percentile (Q3)",
    "notes": (
        "These anchors are descriptive benchmark values derived from the "
        "current overall comparable-contract dataset. They support "
        "scenario-based external cost context and do not represent audited "
        "savings, internal cost data, or verified equivalent pricing for "
        "any single Applied Government Analytics (AGA) effort."
    ),
}


# ---------------------------------------------------------------------
# Scenario definitions
# ---------------------------------------------------------------------
# Multipliers are kept explicit and conservative.
# In this first version, low / central / high are anchored primarily to the
# benchmark distribution itself rather than aggressive scenario inflation.
SCENARIO_NOTES = {
    "low": (
        "Represents a lower-bound benchmark-oriented estimate anchored to "
        "the lower quartile of the current comparable-contract "
        "distribution."
    ),
    "central": (
        "Represents the default scenario anchored to the median of the "
        "current comparable-contract distribution."
    ),
    "high": (
        "Represents an upper-bound benchmark-oriented estimate anchored to "
        "the upper quartile of the current comparable-contract "
        "distribution."
    ),
}


@dataclass(frozen=True)
class ScenarioMultiplier:
    """
    Multipliers applied to a category reference profile.

    These are calculator usability defaults, not empirical claims of actual
    pricing behavior in all contracting contexts.
    """

    value_multiplier: float
    duration_multiplier: float = 1.0
    scale_multiplier: float = 1.0
    complexity_multiplier: float = 1.0
    notes: str = ""


SCENARIO_MULTIPLIERS: dict[str, ScenarioMultiplier] = {
    "low": ScenarioMultiplier(
        value_multiplier=1.0,
        duration_multiplier=0.90,
        scale_multiplier=0.95,
        complexity_multiplier=0.95,
        notes=(
            "Low scenario keeps the benchmark anchor at the low reference "
            "value and applies modestly conservative duration, scale, and "
            "complexity defaults."
        ),
    ),
    "central": ScenarioMultiplier(
        value_multiplier=1.0,
        duration_multiplier=1.0,
        scale_multiplier=1.0,
        complexity_multiplier=1.0,
        notes=(
            "Central scenario is the default benchmark-oriented calculator "
            "view."
        ),
    ),
    "high": ScenarioMultiplier(
        value_multiplier=1.0,
        duration_multiplier=1.10,
        scale_multiplier=1.05,
        complexity_multiplier=1.10,
        notes=(
            "High scenario keeps the benchmark anchor at the high reference "
            "value and applies modest upward defaults to duration, scale, "
            "and complexity."
        ),
    ),
}


# ---------------------------------------------------------------------
# Category assumption structures
# ---------------------------------------------------------------------
@dataclass(frozen=True)
class CategoryReferenceProfile:
    """
    Central reference profile for one service category.

    IMPORTANT:
    - low_reference_value / central_reference_value / high_reference_value
      are the current calculator anchors for the category.
    - reference_value_basis must explicitly state whether these values are
      benchmark-derived or provisional defaults that inherit overall
      anchors.
    - category_modifier is a business-rule default only. It is not an
      empirical claim unless separately validated by category-specific
      benchmark analysis.
    """

    category_name: str
    category_group: str
    reference_value_basis: str
    low_reference_value: float
    central_reference_value: float
    high_reference_value: float
    category_modifier: float
    default_duration_units: int
    default_scale_factor: float
    default_complexity_factor: float
    duration_unit_label: str = "months"
    adjustable_inputs: tuple[str, ...] = field(default_factory=tuple)
    notes: str = ""
    defensibility_notes: str = ""


DEFAULT_ADJUSTABLE_INPUTS: tuple[str, ...] = (
    "scenario",
    "duration_units",
    "scale_factor",
    "complexity_factor",
)

PROTOTYPING_CALCULATOR_MAX_AWARD_AMOUNT = 50_000_000

PROTOTYPING_CALCULATOR_INCLUDE_KEYWORDS: tuple[str, ...] = (
    "prototype",
    "prototyping",
    "fabrication",
    "fabricate",
    "sbir",
    "build",
    "demonstrator",
)

PROTOTYPING_CALCULATOR_EXCLUDE_KEYWORDS: tuple[str, ...] = (
    "program management",
    "management support",
    "support program",
    "upgrade program",
    "sustainment",
)

PROTOTYPING_SCALING_LOW_RDT_E_SHARE = 0.10
PROTOTYPING_SCALING_CENTRAL_RDT_E_SHARE = 0.125
PROTOTYPING_SCALING_HIGH_RDT_E_SHARE = 0.15

PROTOTYPING_SCALING_LOW_GOV_SHARE = 0.60
PROTOTYPING_SCALING_CENTRAL_GOV_SHARE = 0.67
PROTOTYPING_SCALING_HIGH_GOV_SHARE = 0.75

PROTOTYPING_SCALING_LOW_MULTIPLIER = (
    PROTOTYPING_SCALING_LOW_RDT_E_SHARE
    * PROTOTYPING_SCALING_LOW_GOV_SHARE
)
PROTOTYPING_SCALING_CENTRAL_MULTIPLIER = (
    PROTOTYPING_SCALING_CENTRAL_RDT_E_SHARE
    * PROTOTYPING_SCALING_CENTRAL_GOV_SHARE
)
PROTOTYPING_SCALING_HIGH_MULTIPLIER = (
    PROTOTYPING_SCALING_HIGH_RDT_E_SHARE
    * PROTOTYPING_SCALING_HIGH_GOV_SHARE
)

# Conservative business-rule modifiers.
# These are intentionally modest and should be described as calculator
# defaults, not empirical conclusions.
CATEGORY_MODIFIERS: dict[str, float] = {
    "prototyping": 1.10,
    "engineering_design_support": 1.00,
    "project_program_support": 0.90,
    "event_hosting": 0.85,
    "workspace_collaboration": 0.80,
    "innovation_ecosystem_access": 0.95,
    "integrated_service_delivery": 1.15,
    "technical_advisory_services": 0.95,
    "development_program_services": 1.00,
    "professional_services_support": 0.90,
}

CATEGORY_DEFAULT_DURATIONS: dict[str, int] = {
    "prototyping": 6,
    "engineering_design_support": 6,
    "project_program_support": 12,
    "event_hosting": 1,
    "workspace_collaboration": 3,
    "innovation_ecosystem_access": 6,
    "integrated_service_delivery": 12,
    "technical_advisory_services": 6,
    "development_program_services": 12,
    "professional_services_support": 6,
}

CATEGORY_DEFAULT_SCALE: dict[str, float] = {
    "prototyping": 1.00,
    "engineering_design_support": 1.00,
    "project_program_support": 1.00,
    "event_hosting": 1.00,
    "workspace_collaboration": 1.00,
    "innovation_ecosystem_access": 1.00,
    "integrated_service_delivery": 1.00,
    "technical_advisory_services": 1.00,
    "development_program_services": 1.00,
    "professional_services_support": 1.00,
}

CATEGORY_DEFAULT_COMPLEXITY: dict[str, float] = {
    "prototyping": 1.0,
    "engineering_design_support": 1.00,
    "project_program_support": 0.95,
    "event_hosting": 0.90,
    "workspace_collaboration": 0.90,
    "innovation_ecosystem_access": 0.95,
    "integrated_service_delivery": 1.10,
    "technical_advisory_services": 0.95,
    "development_program_services": 1.00,
    "professional_services_support": 0.95,
}


def _apply_modifier(value: float, modifier: float) -> float:
    """Return a rounded category-adjusted reference value."""
    return round(value * modifier, 2)


def _build_category_profile(
    category_name: str,
    *,
    category_group: str,
    category_modifier: float,
    default_duration_units: int,
    default_scale_factor: float,
    default_complexity_factor: float,
    notes: str,
) -> CategoryReferenceProfile:
    """
    Build one category profile using current overall benchmark anchors.

    At this stage, category-level reference values inherit the overall
    benchmark anchors and apply only a modest, explicit business-rule
    modifier. This makes the assumption structure usable for later
    calculator logic without pretending category-specific benchmark
    distributions are already validated.
    """
    return CategoryReferenceProfile(
        category_name=category_name,
        category_group=category_group,
        reference_value_basis=(
            "provisional category profile using overall benchmark anchors "
            "plus explicit business-rule category modifier"
        ),
        low_reference_value=_apply_modifier(
            OVERALL_BENCHMARK_LOW_Q1,
            category_modifier,
        ),
        central_reference_value=_apply_modifier(
            OVERALL_BENCHMARK_MEDIAN,
            category_modifier,
        ),
        high_reference_value=_apply_modifier(
            OVERALL_BENCHMARK_HIGH_Q3,
            category_modifier,
        ),
        category_modifier=category_modifier,
        default_duration_units=default_duration_units,
        default_scale_factor=default_scale_factor,
        default_complexity_factor=default_complexity_factor,
        adjustable_inputs=DEFAULT_ADJUSTABLE_INPUTS,
        notes=notes,
        defensibility_notes=(
            "These category values are calculator defaults built from overall "
            "benchmark anchors. They should not be described as empirically "
            "validated category-specific distributions unless replaced later "
            "by category-level benchmark summaries."
        ),
    )


# IMPORTANT:
# CATEGORY_REFERENCE_VALUES stores baseline/default category profiles.
# Public callers should use get_category_reference_values(...) instead of
# reading CATEGORY_REFERENCE_VALUES directly, because some categories
# (currently prototyping) may apply live override logic before returning
# calculator-facing reference values.

CATEGORY_REFERENCE_VALUES: dict[str, CategoryReferenceProfile] = {
    "prototyping": _build_category_profile(
        "prototyping",
        category_group="technical_delivery",
        category_modifier=CATEGORY_MODIFIERS["prototyping"],
        default_duration_units=CATEGORY_DEFAULT_DURATIONS["prototyping"],
        default_scale_factor=CATEGORY_DEFAULT_SCALE["prototyping"],
        default_complexity_factor=CATEGORY_DEFAULT_COMPLEXITY["prototyping"],
        notes=(
            "Prototyping often involves build/fabrication/integration "
            "activity, so a modest upward modifier is provided as a "
            "business-rule default."
        ),
    ),
    "engineering_design_support": _build_category_profile(
        "engineering_design_support",
        category_group="technical_delivery",
        category_modifier=CATEGORY_MODIFIERS["engineering_design_support"],
        default_duration_units=CATEGORY_DEFAULT_DURATIONS[
            "engineering_design_support"
        ],
        default_scale_factor=CATEGORY_DEFAULT_SCALE[
            "engineering_design_support"
        ],
        default_complexity_factor=CATEGORY_DEFAULT_COMPLEXITY[
            "engineering_design_support"
        ],
        notes=(
            "Engineering/design support is treated as the neutral reference "
            "category for technical analytical work."
        ),
    ),
    "project_program_support": _build_category_profile(
        "project_program_support",
        category_group="program_support",
        category_modifier=CATEGORY_MODIFIERS["project_program_support"],
        default_duration_units=CATEGORY_DEFAULT_DURATIONS[
            "project_program_support"
        ],
        default_scale_factor=CATEGORY_DEFAULT_SCALE["project_program_support"],
        default_complexity_factor=CATEGORY_DEFAULT_COMPLEXITY[
            "project_program_support"
        ],
        notes=(
            "Project/program support is assigned a modest downward modifier "
            "as a calculator default because it is typically less "
            "artifact-centric than prototyping or integrated technical "
            "delivery."
        ),
    ),
    "event_hosting": _build_category_profile(
        "event_hosting",
        category_group="event_and_collaboration",
        category_modifier=CATEGORY_MODIFIERS["event_hosting"],
        default_duration_units=CATEGORY_DEFAULT_DURATIONS["event_hosting"],
        default_scale_factor=CATEGORY_DEFAULT_SCALE["event_hosting"],
        default_complexity_factor=CATEGORY_DEFAULT_COMPLEXITY["event_hosting"],
        notes=(
            "Event hosting is treated as a shorter-duration, "
            "lower-complexity calculator profile by default."
        ),
    ),
    "workspace_collaboration": _build_category_profile(
        "workspace_collaboration",
        category_group="event_and_collaboration",
        category_modifier=CATEGORY_MODIFIERS["workspace_collaboration"],
        default_duration_units=CATEGORY_DEFAULT_DURATIONS[
            "workspace_collaboration"
        ],
        default_scale_factor=CATEGORY_DEFAULT_SCALE[
            "workspace_collaboration"
        ],
        default_complexity_factor=CATEGORY_DEFAULT_COMPLEXITY[
            "workspace_collaboration"
        ],
        notes=(
            "Workspace/collaboration is treated as an environment-access "
            "profile with relatively modest default complexity."
        ),
    ),
    "innovation_ecosystem_access": _build_category_profile(
        "innovation_ecosystem_access",
        category_group="network_access",
        category_modifier=CATEGORY_MODIFIERS["innovation_ecosystem_access"],
        default_duration_units=CATEGORY_DEFAULT_DURATIONS[
            "innovation_ecosystem_access"
        ],
        default_scale_factor=CATEGORY_DEFAULT_SCALE[
            "innovation_ecosystem_access"
        ],
        default_complexity_factor=CATEGORY_DEFAULT_COMPLEXITY[
            "innovation_ecosystem_access"
        ],
        notes=(
            "Innovation ecosystem access is treated as a network/scouting "
            "access profile with a slight downward default modifier relative "
            "to neutral."
        ),
    ),
    "integrated_service_delivery": _build_category_profile(
        "integrated_service_delivery",
        category_group="bundled_delivery",
        category_modifier=CATEGORY_MODIFIERS["integrated_service_delivery"],
        default_duration_units=CATEGORY_DEFAULT_DURATIONS[
            "integrated_service_delivery"
        ],
        default_scale_factor=CATEGORY_DEFAULT_SCALE[
            "integrated_service_delivery"
        ],
        default_complexity_factor=CATEGORY_DEFAULT_COMPLEXITY[
            "integrated_service_delivery"
        ],
        notes=(
            "Integrated service delivery bundles multiple service types, so "
            "it uses the largest conservative modifier among the current "
            "defaults."
        ),
    ),
    "technical_advisory_services": _build_category_profile(
        "technical_advisory_services",
        category_group="advisory_support",
        category_modifier=CATEGORY_MODIFIERS["technical_advisory_services"],
        default_duration_units=CATEGORY_DEFAULT_DURATIONS[
            "technical_advisory_services"
        ],
        default_scale_factor=CATEGORY_DEFAULT_SCALE[
            "technical_advisory_services"
        ],
        default_complexity_factor=CATEGORY_DEFAULT_COMPLEXITY[
            "technical_advisory_services"
        ],
        notes=(
            "Technical advisory services are treated as guidance-oriented "
            "work with modest complexity and a slightly conservative downward "
            "modifier."
        ),
    ),
    "development_program_services": _build_category_profile(
        "development_program_services",
        category_group="program_delivery",
        category_modifier=CATEGORY_MODIFIERS["development_program_services"],
        default_duration_units=CATEGORY_DEFAULT_DURATIONS[
            "development_program_services"
        ],
        default_scale_factor=CATEGORY_DEFAULT_SCALE[
            "development_program_services"
        ],
        default_complexity_factor=CATEGORY_DEFAULT_COMPLEXITY[
            "development_program_services"
        ],
        notes=(
            "Development program services are currently treated as a neutral "
            "calculator profile until category-specific benchmark values "
            "are validated."
        ),
    ),
    "professional_services_support": _build_category_profile(
        "professional_services_support",
        category_group="general_support",
        category_modifier=CATEGORY_MODIFIERS["professional_services_support"],
        default_duration_units=CATEGORY_DEFAULT_DURATIONS[
            "professional_services_support"
        ],
        default_scale_factor=CATEGORY_DEFAULT_SCALE[
            "professional_services_support"
        ],
        default_complexity_factor=CATEGORY_DEFAULT_COMPLEXITY[
            "professional_services_support"
        ],
        notes=(
            "Professional services support is treated as a modestly lower-cost "
            "support-oriented calculator profile by default."
        ),
    ),
}


# ---------------------------------------------------------------------
# Default calculator assumptions
# ---------------------------------------------------------------------
DEFAULT_ASSUMPTIONS: dict[str, Any] = {
    "default_category": "engineering_design_support",
    "default_scenario": "central",
    "default_duration_units": 6,
    "default_duration_unit_label": "months",
    "default_scale_factor": 1.0,
    "default_complexity_factor": 1.0,
    "allow_user_adjustment": True,
    "user_adjustable_fields": [
        "category_name",
        "scenario",
        "duration_units",
        "scale_factor",
        "complexity_factor",
    ],
    "benchmark_value_field": "award_amount",
    "benchmark_reference_priority": [
        "category-specific benchmark distributions when validated",
        "otherwise current overall benchmark anchors",
    ],
    "interpretation_guardrail": (
        "Outputs generated from these assumptions should be described as "
        "scenario-based external benchmark estimates, not audited savings, "
        "internal cost avoidance, or proven ROI."
    ),
}


# ---------------------------------------------------------------------
# Public helper functions
# ---------------------------------------------------------------------
def _prototyping_description_matches_calculator_intent(description: Any) -> bool:
    """
    Return True if normalized description matches prototyping calculator
    intent: at least one include keyword and no exclude keyword.
    """
    if description is None or pd.isna(description):
        return False

    text = str(description).strip().lower()
    if not text:
        return False

    include_match = any(
        keyword in text for keyword in PROTOTYPING_CALCULATOR_INCLUDE_KEYWORDS
    )
    exclude_match = any(
        keyword in text for keyword in PROTOTYPING_CALCULATOR_EXCLUDE_KEYWORDS
    )
    return include_match and not exclude_match


def load_prototyping_calculator_subset() -> pd.DataFrame:
    """
    Load comparable benchmark rows for prototyping calculator anchors.

    Reads PROCESSED_DATA_DIR / "comparable_contracts.parquet". If that file
    is missing, returns an empty DataFrame. Keeps rows where
    mapped_service_category is "prototyping", award_amount is non-null
    after numeric coercion, award_amount is at or below
    PROTOTYPING_CALCULATOR_MAX_AWARD_AMOUNT, and description matches
    calculator intent. Returns a copy.
    """
    path = PROCESSED_DATA_DIR / "comparable_contracts.parquet"
    if not path.is_file():
        return pd.DataFrame()

    df = pd.read_parquet(path)
    working = df.copy()
    award_numeric = pd.to_numeric(working["award_amount"], errors="coerce")
    mask = (
        (working["mapped_service_category"] == "prototyping")
        & award_numeric.notna()
        & (award_numeric <= PROTOTYPING_CALCULATOR_MAX_AWARD_AMOUNT)
    )
    subset = working.loc[mask].copy()
    if "description" not in subset.columns:
        return pd.DataFrame(columns=subset.columns)

    intent_mask = subset["description"].map(
        _prototyping_description_matches_calculator_intent
    )
    return subset.loc[intent_mask].copy()


def build_prototyping_calculator_anchors() -> dict[str, Any] | None:
    """
    Derive low / central / high calculator anchors from the prototyping subset.

    Calls :func:`load_prototyping_calculator_subset`. If that frame is empty,
    returns ``None``. Otherwise returns quartiles of ``award_amount`` (Q1,
    median, Q3) rounded like other reference values in this module, plus
    metadata fields.
    """
    subset = load_prototyping_calculator_subset()
    if subset.empty:
        return None

    awards = pd.to_numeric(subset["award_amount"], errors="coerce")
    low_reference_value = round(float(awards.quantile(0.25)), 2)
    central_reference_value = round(float(awards.quantile(0.50)), 2)
    high_reference_value = round(float(awards.quantile(0.75)), 2)

    return {
        "low_reference_value": low_reference_value,
        "central_reference_value": central_reference_value,
        "high_reference_value": high_reference_value,
        "contract_count": int(len(subset)),
        "max_award_amount_cap_used": float(
            PROTOTYPING_CALCULATOR_MAX_AWARD_AMOUNT
        ),
        "reference_value_basis": (
            "calculator-grade prototyping subset using mapped prototyping rows "
            "with an explicit upper award cap and prototype-intent description "
            "filtering for comparability"
        ),
        "notes": (
            "Anchors are Q1 / median / Q3 of award_amount on the narrowed "
            "prototyping slice after applying an upper award cap and "
            "lightweight prototype-intent description filtering. Describe "
            "outputs as external benchmark context, not audited pricing."
        ),
    }


def build_scaled_prototyping_calculator_anchors() -> dict[str, Any] | None:
    """
    Derive scaled low / central / high calculator anchors for prototyping.

    Starts from the narrowed prototyping calculator anchors and applies
    policy-informed scaling multipliers for low / central / high scenarios.
    Returns None if the narrowed prototyping anchors are unavailable.
    """
    base_anchors = build_prototyping_calculator_anchors()
    if base_anchors is None:
        return None

    scaled_low = round(
        float(base_anchors["low_reference_value"])
        * PROTOTYPING_SCALING_LOW_MULTIPLIER,
        2,
    )
    scaled_central = round(
        float(base_anchors["central_reference_value"])
        * PROTOTYPING_SCALING_CENTRAL_MULTIPLIER,
        2,
    )
    scaled_high = round(
        float(base_anchors["high_reference_value"])
        * PROTOTYPING_SCALING_HIGH_MULTIPLIER,
        2,
    )

    return {
        "low_reference_value": scaled_low,
        "central_reference_value": scaled_central,
        "high_reference_value": scaled_high,
        "contract_count": int(base_anchors["contract_count"]),
        "max_award_amount_cap_used": float(
            base_anchors["max_award_amount_cap_used"]
        ),
        "scaling_low_multiplier": float(PROTOTYPING_SCALING_LOW_MULTIPLIER),
        "scaling_central_multiplier": float(
            PROTOTYPING_SCALING_CENTRAL_MULTIPLIER
        ),
        "scaling_high_multiplier": float(PROTOTYPING_SCALING_HIGH_MULTIPLIER),
        "reference_value_basis": (
            "scaled calculator-grade prototyping subset using mapped "
            "prototyping rows, explicit upper award cap, lightweight "
            "prototype-intent description filtering, and policy-informed "
            "RDT&E/government-share scaling"
        ),
        "notes": (
            "Anchors start from narrowed prototyping benchmark quartiles and "
            "apply low / central / high policy-informed scaling multipliers "
            "for calculator comparability. Describe outputs as scenario-based "
            "external benchmark context, not audited pricing."
        ),
    }


def list_supported_categories() -> list[str]:
    """Return all supported calculator categories."""
    return sorted(CATEGORY_REFERENCE_VALUES.keys())


def get_category_reference_values(category_name: str) -> dict[str, Any]:
    """
    Return the centralized reference profile for one category.

    Parameters
    ----------
    category_name : str
        Service category name.

    Returns
    -------
    dict[str, Any]
        Machine-friendly dictionary representation of the category profile.

    Raises
    ------
    KeyError
        If the category is not supported.
    """
    normalized = str(category_name).strip().lower()
    if normalized not in CATEGORY_REFERENCE_VALUES:
        supported = ", ".join(list_supported_categories())
        raise KeyError(
            f"Unsupported category '{category_name}'. "
            f"Supported categories: {supported}"
        )
    if normalized == "prototyping":
        scaled_proto = build_scaled_prototyping_calculator_anchors()
        if scaled_proto is not None:
            return {
                "category_name": "prototyping",
                "category_group": "technical_delivery",
                "reference_value_basis": scaled_proto["reference_value_basis"],
                "low_reference_value": scaled_proto["low_reference_value"],
                "central_reference_value": scaled_proto[
                    "central_reference_value"
                ],
                "high_reference_value": scaled_proto["high_reference_value"],
                "category_modifier": CATEGORY_MODIFIERS["prototyping"],
                "default_duration_units": CATEGORY_DEFAULT_DURATIONS[
                    "prototyping"
                ],
                "default_scale_factor": CATEGORY_DEFAULT_SCALE["prototyping"],
                "default_complexity_factor": CATEGORY_DEFAULT_COMPLEXITY[
                    "prototyping"
                ],
                "duration_unit_label": "months",
                "adjustable_inputs": DEFAULT_ADJUSTABLE_INPUTS,
                "notes": scaled_proto["notes"],
                "defensibility_notes": (
                    "These prototyping values use a narrowed calculator-grade "
                    "subset with explicit cap, description filtering, and "
                    "policy-informed scaling for calculator comparability. They "
                    "should not be described as audited prices or universal "
                    "market rates."
                ),
            }
    return asdict(CATEGORY_REFERENCE_VALUES[normalized])


def get_scenario_multipliers() -> dict[str, dict[str, Any]]:
    """
    Return all scenario multiplier definitions.

    Returns
    -------
    dict[str, dict[str, Any]]
        Dictionary keyed by scenario name.
    """
    return {
        scenario_name: asdict(multiplier)
        for scenario_name, multiplier in SCENARIO_MULTIPLIERS.items()
    }


def get_default_assumptions() -> dict[str, Any]:
    """
    Return centralized default calculator assumptions.
    """
    return DEFAULT_ASSUMPTIONS.copy()


def get_overall_benchmark_anchors() -> dict[str, Any]:
    """
    Return the benchmark-derived overall anchors currently used by the
    assumptions layer.
    """
    return {
        "reference_source": BENCHMARK_REFERENCE_SOURCE,
        "low_reference_value": OVERALL_BENCHMARK_LOW_Q1,
        "central_reference_value": OVERALL_BENCHMARK_MEDIAN,
        "high_reference_value": OVERALL_BENCHMARK_HIGH_Q3,
    }


def export_assumptions_reference() -> dict[str, Any]:
    """
    Return a fully exportable assumptions reference payload.

    This is suitable for JSON serialization and later inspection by calculator
    logic, QA scripts, or app-level data loading.
    """
    return {
        "version": ASSUMPTIONS_VERSION,
        "module_name": "src.business.assumptions",
        "purpose": (
            "Centralized assumptions layer for scenario-based external "
            "benchmark value estimation."
        ),
        "benchmark_anchors": get_overall_benchmark_anchors(),
        "scenario_notes": SCENARIO_NOTES.copy(),
        "scenario_multipliers": get_scenario_multipliers(),
        "default_assumptions": get_default_assumptions(),
        "category_reference_values": {
            category_name: get_category_reference_values(category_name)
            for category_name in CATEGORY_REFERENCE_VALUES.keys()
        },
        "defensibility_summary": {
            "benchmark_derived_components": [
                "overall benchmark low reference (Q1)",
                "overall benchmark central reference (median)",
                "overall benchmark high reference (Q3)",
            ],
            "business_rule_components": [
                "category modifiers",
                "default duration assumptions",
                "default scale assumptions",
                "default complexity assumptions",
                "scenario usability defaults",
                (
                    "prototyping may use scaled calculator-grade subset anchors "
                    "with explicit upper award cap, lightweight prototype-intent "
                    "description filtering, and policy-informed RDT&E/"
                    "government-share scaling when available rather than the "
                    "full prototyping category"
                ),
            ],
            "non_claims": [
                "This assumptions layer does not prove internal cost savings.",
                "This assumptions layer does not produce audited ROI.",
                (
                    "These category profiles are not category-specific "
                    "empirical benchmark distributions unless replaced later "
                    "by validated data."
                ),
            ],
        },
    }


def write_assumptions_reference_json(
    output_path: Path | str = DEFAULT_EXPORT_PATH,
) -> Path:
    """
    Write the assumptions reference payload to JSON.

    Parameters
    ----------
    output_path : Path | str, default DEFAULT_EXPORT_PATH
        Destination JSON path.

    Returns
    -------
    Path
        Resolved output path.
    """
    validate_settings()
    ensure_directories()

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)

    payload = export_assumptions_reference()
    with output.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)

    return output


def main() -> None:
    """
    CLI entrypoint for writing the assumptions reference JSON artifact.
    """
    output_path = write_assumptions_reference_json()
    print(f"Wrote assumptions reference JSON to: {output_path}")


if __name__ == "__main__":
    main()
