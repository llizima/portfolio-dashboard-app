"""
Deterministic external procurement equivalent calculator for the
Applied Government Analytics (AGA) Value Dashboard.

Purpose
-------
This module converts benchmark anchors plus explicit assumptions into a
structured external benchmark estimate range that can be rendered by any
downstream consumer (Streamlit, API, reports, tests, etc.).

This module is intentionally limited to:
- input validation
- normalized calculator input handling
- benchmark range calculation
- scenario-aware multiplier application
- structured result building

It does NOT:
- render Streamlit widgets
- perform internal cost accounting
- claim audited savings or ROI
- read internal Applied Government Analytics (AGA) financial records
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from src.business.assumptions import (
    export_assumptions_reference,
    get_category_reference_values,
    get_default_assumptions,
    get_overall_benchmark_anchors,
    get_scenario_multipliers,
    list_supported_categories,
)
from src.config.settings import validate_settings


SUPPORTED_SCENARIOS: tuple[str, ...] = ("low", "central", "high")


@dataclass(frozen=True)
class CalculatorInputs:
    """
    Canonical normalized inputs used by calculator logic.

    Notes
    -----
    This dataclass defines the stable backend schema after validation and
    normalization. Optional convenience fields are allowed at the raw-input
    layer, but the calculator ultimately reduces them to these core inputs.
    """

    service_category: str
    scenario: str
    duration_units: float
    scale_factor: float
    complexity_factor: float
    number_of_stakeholders: int | None = None
    number_of_participants: int | None = None
    event_days: float | None = None
    workspace_duration: float | None = None
    number_of_prototypes: int | None = None
    engineering_labor_proxy: float | None = None


def _coerce_positive_float(
    value: Any,
    *,
    field_name: str,
    allow_none: bool = True,
) -> float | None:
    """Convert a value to a positive float or raise a clear ValueError."""
    if value is None:
        if allow_none:
            return None
        raise ValueError(f"{field_name} is required.")

    try:
        numeric = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field_name} must be numeric.") from exc

    if numeric <= 0:
        raise ValueError(f"{field_name} must be greater than 0.")

    return numeric


def _coerce_nonnegative_int(
    value: Any,
    *,
    field_name: str,
) -> int | None:
    """Convert a value to a nonnegative integer or return None."""
    if value is None:
        return None

    try:
        numeric = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field_name} must be an integer.") from exc

    if numeric < 0:
        raise ValueError(f"{field_name} cannot be negative.")

    return numeric


def format_currency(value: float) -> str:
    """Return a stable currency string for human-readable examples."""
    return f"${value:,.2f}"


def validate_calculator_inputs(inputs: dict[str, Any]) -> dict[str, Any]:
    """
    Validate raw calculator inputs.

    Returns
    -------
    dict[str, Any]
        Lightly normalized raw input dictionary.

    Raises
    ------
    ValueError
        If required fields are missing or invalid.
    """
    if not isinstance(inputs, dict):
        raise ValueError("Calculator inputs must be provided as a dictionary.")

    defaults = get_default_assumptions()

    raw_category = inputs.get("service_category", defaults["default_category"])
    service_category = str(raw_category).strip().lower()
    if not service_category:
        raise ValueError("service_category is required.")
    if service_category not in list_supported_categories():
        supported = ", ".join(list_supported_categories())
        raise ValueError(
            f"Unsupported service_category '{raw_category}'. "
            f"Supported categories: {supported}"
        )

    raw_scenario = inputs.get("scenario", defaults["default_scenario"])
    scenario = str(raw_scenario).strip().lower()
    if scenario not in SUPPORTED_SCENARIOS:
        raise ValueError(
            f"Unsupported scenario '{raw_scenario}'. "
            f"Supported scenarios: {', '.join(SUPPORTED_SCENARIOS)}"
        )

    validated = {
        "service_category": service_category,
        "scenario": scenario,
        "duration_units": _coerce_positive_float(
            inputs.get("duration_units"),
            field_name="duration_units",
        ),
        "scale_factor": _coerce_positive_float(
            inputs.get("scale_factor"),
            field_name="scale_factor",
        ),
        "complexity_factor": _coerce_positive_float(
            inputs.get("complexity_factor"),
            field_name="complexity_factor",
        ),
        "number_of_stakeholders": _coerce_nonnegative_int(
            inputs.get("number_of_stakeholders"),
            field_name="number_of_stakeholders",
        ),
        "number_of_participants": _coerce_nonnegative_int(
            inputs.get("number_of_participants"),
            field_name="number_of_participants",
        ),
        "event_days": _coerce_positive_float(
            inputs.get("event_days"),
            field_name="event_days",
        ),
        "workspace_duration": _coerce_positive_float(
            inputs.get("workspace_duration"),
            field_name="workspace_duration",
        ),
        "number_of_prototypes": _coerce_nonnegative_int(
            inputs.get("number_of_prototypes"),
            field_name="number_of_prototypes",
        ),
        "engineering_labor_proxy": _coerce_positive_float(
            inputs.get("engineering_labor_proxy"),
            field_name="engineering_labor_proxy",
        ),
    }

    return validated


def normalize_calculator_inputs(inputs: dict[str, Any]) -> CalculatorInputs:
    """
    Normalize validated inputs into the canonical calculator schema.

    Optional convenience fields may influence duration and scale in explicit,
    deterministic ways.
    """
    validated = validate_calculator_inputs(inputs)
    category_profile = get_category_reference_values(
        validated["service_category"]
    )

    duration_units = (
        validated["duration_units"]
        if validated["duration_units"] is not None
        else float(category_profile["default_duration_units"])
    )
    scale_factor = (
        validated["scale_factor"]
        if validated["scale_factor"] is not None
        else float(category_profile["default_scale_factor"])
    )
    complexity_factor = (
        validated["complexity_factor"]
        if validated["complexity_factor"] is not None
        else float(category_profile["default_complexity_factor"])
    )

    # Optional explicit mappings into core business inputs.
    if validated["event_days"] is not None:
        duration_units = float(validated["event_days"])
    if validated["workspace_duration"] is not None:
        duration_units = float(validated["workspace_duration"])

    if validated["number_of_participants"] is not None:
        participants = validated["number_of_participants"]
        if participants > 0:
            scale_factor *= 1.0 + (participants / 100.0)

    if validated["number_of_stakeholders"] is not None:
        stakeholders = validated["number_of_stakeholders"]
        if stakeholders > 0:
            scale_factor *= 1.0 + (stakeholders / 50.0)

    if validated["number_of_prototypes"] is not None:
        prototypes = validated["number_of_prototypes"]
        if prototypes > 0:
            scale_factor *= 1.0 + (prototypes - 1) * 0.25

    if validated["engineering_labor_proxy"] is not None:
        labor_proxy = float(validated["engineering_labor_proxy"])
        complexity_factor *= 1.0 + (labor_proxy / 1000.0)

    # Final hard guardrails after deterministic mappings.
    if duration_units <= 0:
        raise ValueError("Normalized duration_units must be greater than 0.")
    if scale_factor <= 0:
        raise ValueError("Normalized scale_factor must be greater than 0.")
    if complexity_factor <= 0:
        raise ValueError("Normalized complexity_factor must be greater than 0.")

    return CalculatorInputs(
        service_category=validated["service_category"],
        scenario=validated["scenario"],
        duration_units=round(float(duration_units), 4),
        scale_factor=round(float(scale_factor), 6),
        complexity_factor=round(float(complexity_factor), 6),
        number_of_stakeholders=validated["number_of_stakeholders"],
        number_of_participants=validated["number_of_participants"],
        event_days=validated["event_days"],
        workspace_duration=validated["workspace_duration"],
        number_of_prototypes=validated["number_of_prototypes"],
        engineering_labor_proxy=validated["engineering_labor_proxy"],
    )


def calculate_benchmark_range(
    *,
    category_profile: dict[str, Any],
    normalized_inputs: CalculatorInputs,
) -> dict[str, float]:
    """
    Calculate the baseline adjusted benchmark range before scenario emphasis.

    The baseline uses:
    - category reference profile values
    - duration scaling relative to default duration
    - explicit scale_factor
    - explicit complexity_factor
    """
    default_duration_units = float(category_profile["default_duration_units"])
    duration_ratio = normalized_inputs.duration_units / default_duration_units

    composite_multiplier = (
        duration_ratio
        * normalized_inputs.scale_factor
        * normalized_inputs.complexity_factor
    )

    low_estimate = round(
        float(category_profile["low_reference_value"]) * composite_multiplier,
        2,
    )
    central_estimate = round(
        float(category_profile["central_reference_value"])
        * composite_multiplier,
        2,
    )
    high_estimate = round(
        float(category_profile["high_reference_value"]) * composite_multiplier,
        2,
    )

    return {
        "duration_ratio": round(duration_ratio, 6),
        "composite_multiplier": round(composite_multiplier, 6),
        "low_estimate": low_estimate,
        "central_estimate": central_estimate,
        "high_estimate": high_estimate,
    }


def apply_scenario_adjustments(
    *,
    baseline_range: dict[str, float],
    normalized_inputs: CalculatorInputs,
    scenario_multipliers: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """
    Apply scenario-aware usability defaults while preserving a full range output.

    Design choice:
    - every run still returns low/central/high
    - selected scenario influences a scenario emphasis factor
    - monotonic ordering is explicitly preserved
    """
    selected = scenario_multipliers[normalized_inputs.scenario]

    scenario_factor = (
        float(selected["value_multiplier"])
        * float(selected["duration_multiplier"])
        * float(selected["scale_multiplier"])
        * float(selected["complexity_multiplier"])
    )

    adjusted_low = round(baseline_range["low_estimate"] * scenario_factor, 2)
    adjusted_central = round(
        baseline_range["central_estimate"] * scenario_factor,
        2,
    )
    adjusted_high = round(baseline_range["high_estimate"] * scenario_factor, 2)

    ordered = sorted([adjusted_low, adjusted_central, adjusted_high])

    return {
        "selected_scenario": normalized_inputs.scenario,
        "selected_scenario_multiplier": round(scenario_factor, 6),
        "selected_scenario_definition": selected,
        "low_estimate": ordered[0],
        "central_estimate": ordered[1],
        "high_estimate": ordered[2],
    }


def build_calculator_result(
    *,
    normalized_inputs: CalculatorInputs,
    category_profile: dict[str, Any],
    benchmark_reference: dict[str, Any],
    baseline_range: dict[str, float],
    scenario_adjusted_range: dict[str, Any],
    assumptions_reference: dict[str, Any],
) -> dict[str, Any]:
    """Build the final reusable structured calculator result."""
    notes: list[str] = []

    if baseline_range["duration_ratio"] != 1.0:
        notes.append(
            f"Duration scaled from the category default of "
            f"{category_profile['default_duration_units']} "
            f"{category_profile['duration_unit_label']} to "
            f"{normalized_inputs.duration_units} "
            f"{category_profile['duration_unit_label']}."
        )

    if normalized_inputs.scale_factor != float(
        category_profile["default_scale_factor"]
    ):
        notes.append(
            "Scale factor differed from the category default and adjusted "
            "the benchmark range proportionally."
        )

    if normalized_inputs.complexity_factor != float(
        category_profile["default_complexity_factor"]
    ):
        notes.append(
            "Complexity factor differed from the category default and "
            "adjusted the benchmark range proportionally."
        )

    reference_basis = category_profile.get(
        "reference_value_basis",
        "category-specific calculator reference logic",
    )
    notes.append(
        "Category reference values used in this calculation are based on: "
        f"{reference_basis}."
    )

    overall_reference_basis = benchmark_reference["reference_source"].get(
        "reference_basis",
        "overall benchmark context",
    )
    if reference_basis != overall_reference_basis:
        notes.append(
            "The category-specific benchmark basis used for calculation is "
            "different from the overall benchmark reference context included "
            "in the output."
        )
    notes.append(
        "Outputs should be described as scenario-based external benchmark "
        "estimates, not audited savings, proven ROI, or internal cost "
        "avoidance."
    )

    return {
        "service_category": normalized_inputs.service_category,
        "scenario": normalized_inputs.scenario,
        "low_estimate": scenario_adjusted_range["low_estimate"],
        "central_estimate": scenario_adjusted_range["central_estimate"],
        "high_estimate": scenario_adjusted_range["high_estimate"],
        "normalized_inputs": asdict(normalized_inputs),
        "assumptions_used": {
            "default_assumptions": get_default_assumptions(),
            "category_reference_profile": category_profile,
            "scenario_multipliers_used": scenario_adjusted_range[
                "selected_scenario_definition"
            ],
            "selected_scenario_multiplier": scenario_adjusted_range[
                "selected_scenario_multiplier"
            ],
            "baseline_composite_multiplier": baseline_range[
                "composite_multiplier"
            ],
            "baseline_duration_ratio": baseline_range["duration_ratio"],
        },
        "benchmark_reference": benchmark_reference,
        "category_reference_profile": category_profile,
        "scenario_multipliers_used": scenario_adjusted_range[
            "selected_scenario_definition"
        ],
        "notes": notes,
        "defensibility_notes": assumptions_reference["defensibility_summary"],
        "calculation_metadata": {
            "calculation_version": "0.1.0",
            "selected_scenario": scenario_adjusted_range["selected_scenario"],
            "baseline_range_before_scenario": {
                "low_estimate": baseline_range["low_estimate"],
                "central_estimate": baseline_range["central_estimate"],
                "high_estimate": baseline_range["high_estimate"],
            },
            "range_ordering_valid": (
                scenario_adjusted_range["low_estimate"]
                <= scenario_adjusted_range["central_estimate"]
                <= scenario_adjusted_range["high_estimate"]
            ),
            "category_reference_basis": category_profile.get(
                "reference_value_basis",
                "category-specific calculator reference logic",
            ),
            "overall_benchmark_reference_basis": benchmark_reference[
                "reference_source"
            ].get(
                "reference_basis",
                "overall benchmark context",
            ),
            "interpretation_guardrail": get_default_assumptions()[
                "interpretation_guardrail"
            ],
        },
        "scaled_breakdown": {
            "per_duration_unit_central_estimate": round(
                scenario_adjusted_range["central_estimate"]
                / normalized_inputs.duration_units,
                2,
            ),
            "per_duration_unit_label": category_profile["duration_unit_label"],
        },
    }


def calculate_external_procurement_equivalent(
    inputs: dict[str, Any],
) -> dict[str, Any]:
    """
    Primary public calculator entrypoint.

    Parameters
    ----------
    inputs : dict[str, Any]
        Raw user or app input payload.

    Returns
    -------
    dict[str, Any]
        Structured benchmark estimate result.
    """
    validate_settings()

    normalized_inputs = normalize_calculator_inputs(inputs)
    category_profile = get_category_reference_values(
        normalized_inputs.service_category
    )
    benchmark_reference = get_overall_benchmark_anchors()
    scenario_multipliers = get_scenario_multipliers()
    assumptions_reference = export_assumptions_reference()

    baseline_range = calculate_benchmark_range(
        category_profile=category_profile,
        normalized_inputs=normalized_inputs,
    )
    scenario_adjusted_range = apply_scenario_adjustments(
        baseline_range=baseline_range,
        normalized_inputs=normalized_inputs,
        scenario_multipliers=scenario_multipliers,
    )

    return build_calculator_result(
        normalized_inputs=normalized_inputs,
        category_profile=category_profile,
        benchmark_reference=benchmark_reference,
        baseline_range=baseline_range,
        scenario_adjusted_range=scenario_adjusted_range,
        assumptions_reference=assumptions_reference,
    )

