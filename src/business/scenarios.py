"""
Centralized scenario engine for the SOFWERX Value Dashboard business layer.

This module defines reusable scenario presets that can be applied to a base
calculator input payload before running benchmark/value estimation logic.

Design principles:
- Scenario definitions live in one place
- Scenario logic stays separate from service categories and UI code
- Outputs are comparison-ready for future Streamlit pages
- Scenario framing complements the calculator's low / central / high benchmark
  orientation instead of duplicating calculator internals

This module does NOT:
- render UI
- call Streamlit
- perform calculator math
- make financial savings or ROI claims
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any


SUPPORTED_BENCHMARK_POSITIONS: set[str] = {"low", "central", "high"}
DEFAULT_SCENARIO_NAMES: list[str] = ["conservative", "balanced", "upper_range"]

_ALLOWED_CUSTOM_OVERRIDE_KEYS: set[str] = {
    "benchmark_position",
    "duration_multiplier",
    "scale_multiplier",
    "complexity_multiplier",
    "description",
    "display_name",
    "notes",
}


SCENARIO_REGISTRY: dict[str, dict[str, Any]] = {
    "conservative": {
        "scenario_name": "conservative",
        "display_name": "Conservative",
        "description": (
            "Lower-bound benchmark framing with slightly restrained "
            "adjustment assumptions."
        ),
        "benchmark_position": "low",
        "duration_multiplier": 0.95,
        "scale_multiplier": 0.95,
        "complexity_multiplier": 0.98,
        "notes": (
            "Intended to represent a cautious lower-bound view of comparable "
            "external cost."
        ),
        "is_custom": False,
    },
    "balanced": {
        "scenario_name": "balanced",
        "display_name": "Balanced",
        "description": (
            "Central benchmark framing using default calculator-oriented "
            "assumptions."
        ),
        "benchmark_position": "central",
        "duration_multiplier": 1.0,
        "scale_multiplier": 1.0,
        "complexity_multiplier": 1.0,
        "notes": (
            "Intended to represent the default or neutral benchmark view."
        ),
        "is_custom": False,
    },
    "upper_range": {
        "scenario_name": "upper_range",
        "display_name": "Upper Range",
        "description": (
            "Upper-bound benchmark framing with moderately elevated "
            "adjustment assumptions."
        ),
        "benchmark_position": "high",
        "duration_multiplier": 1.05,
        "scale_multiplier": 1.05,
        "complexity_multiplier": 1.08,
        "notes": (
            "Intended to represent a more expansive upper-range benchmark "
            "view."
        ),
        "is_custom": False,
    },
    "custom": {
        "scenario_name": "custom",
        "display_name": "Custom",
        "description": (
            "User-defined benchmark framing and adjustment assumptions."
        ),
        "benchmark_position": "central",
        "duration_multiplier": 1.0,
        "scale_multiplier": 1.0,
        "complexity_multiplier": 1.0,
        "notes": (
            "Allows caller-supplied overrides for benchmark position and "
            "multipliers."
        ),
        "is_custom": True,
    },
}


def _copy_scenario_definition(definition: dict[str, Any]) -> dict[str, Any]:
    """
    Return a safe deep copy of a scenario definition.
    """
    return deepcopy(definition)


def _validate_scenario_name(scenario_name: str) -> None:
    """
    Validate that the supplied scenario name exists in the registry.
    """
    if not isinstance(scenario_name, str) or not scenario_name.strip():
        raise ValueError("scenario_name must be a non-empty string.")

    if scenario_name not in SCENARIO_REGISTRY:
        valid_names = ", ".join(sorted(SCENARIO_REGISTRY))
        raise ValueError(
            f"Unsupported scenario_name '{scenario_name}'. "
            f"Supported values are: {valid_names}."
        )


def _validate_benchmark_position(value: str) -> None:
    """
    Validate benchmark position against supported values.
    """
    if not isinstance(value, str):
        raise ValueError("benchmark_position must be a string.")

    if value not in SUPPORTED_BENCHMARK_POSITIONS:
        valid_values = ", ".join(sorted(SUPPORTED_BENCHMARK_POSITIONS))
        raise ValueError(
            f"benchmark_position must be one of: {valid_values}. "
            f"Received '{value}'."
        )


def _validate_positive_multiplier(name: str, value: Any) -> None:
    """
    Validate that a multiplier is numeric and strictly positive.
    """
    if not isinstance(value, (int, float)):
        raise ValueError(
            f"{name} must be numeric. Received {type(value).__name__}."
        )

    if value <= 0:
        raise ValueError(f"{name} must be greater than 0. Received {value}.")


def _validate_base_inputs(base_inputs: dict[str, Any]) -> None:
    """
    Validate that base_inputs is a dictionary.
    """
    if not isinstance(base_inputs, dict):
        raise ValueError("base_inputs must be a dictionary.")


def _normalize_custom_overrides(
    custom_overrides: dict[str, Any] | None,
) -> dict[str, Any]:
    """
    Validate and normalize custom overrides for the custom scenario.

    Allowed keys:
    - benchmark_position
    - duration_multiplier
    - scale_multiplier
    - complexity_multiplier
    - description
    - display_name
    - notes
    """
    if custom_overrides is None:
        return {}

    if not isinstance(custom_overrides, dict):
        raise ValueError(
            "custom_overrides must be a dictionary when provided."
        )

    unsupported_keys = set(custom_overrides) - _ALLOWED_CUSTOM_OVERRIDE_KEYS
    if unsupported_keys:
        unsupported_list = ", ".join(sorted(unsupported_keys))
        allowed = ", ".join(sorted(_ALLOWED_CUSTOM_OVERRIDE_KEYS))
        raise ValueError(
            f"Unsupported custom override keys: {unsupported_list}. "
            f"Allowed keys are: {allowed}."
        )

    cleaned: dict[str, Any] = dict(custom_overrides)

    if "benchmark_position" in cleaned:
        _validate_benchmark_position(cleaned["benchmark_position"])

    for multiplier_name in (
        "duration_multiplier",
        "scale_multiplier",
        "complexity_multiplier",
    ):
        if multiplier_name in cleaned:
            _validate_positive_multiplier(
                multiplier_name,
                cleaned[multiplier_name],
            )

    for text_field in ("description", "display_name", "notes"):
        if text_field in cleaned and not isinstance(cleaned[text_field], str):
            raise ValueError(f"{text_field} must be a string if provided.")

    return cleaned


def _validate_numeric_input_field(
    inputs: dict[str, Any],
    field_name: str,
) -> None:
    """
    Validate a numeric base input field if it exists.
    """
    if field_name in inputs and not isinstance(
        inputs[field_name],
        (int, float),
    ):
        raise ValueError(
            f"'{field_name}' must be numeric when provided. "
            f"Received {type(inputs[field_name]).__name__}."
        )


def get_default_scenario_names() -> list[str]:
    """
    Return the standard named scenarios used for side-by-side comparisons.
    """
    return list(DEFAULT_SCENARIO_NAMES)


def get_named_scenarios() -> dict[str, dict[str, Any]]:
    """
    Return all non-custom named scenarios as a safe copied structure.
    """
    named_scenarios: dict[str, dict[str, Any]] = {}

    for scenario_name in DEFAULT_SCENARIO_NAMES:
        named_scenarios[scenario_name] = get_scenario_definition(scenario_name)

    return named_scenarios


def get_scenario_definition(scenario_name: str) -> dict[str, Any]:
    """
    Return one validated scenario definition as a copied dictionary.

    Parameters
    ----------
    scenario_name : str
        Internal scenario name.

    Returns
    -------
    dict[str, Any]
        Copied and validated scenario definition.
    """
    _validate_scenario_name(scenario_name)

    definition = _copy_scenario_definition(SCENARIO_REGISTRY[scenario_name])

    _validate_benchmark_position(definition["benchmark_position"])
    _validate_positive_multiplier(
        "duration_multiplier",
        definition["duration_multiplier"],
    )
    _validate_positive_multiplier(
        "scale_multiplier",
        definition["scale_multiplier"],
    )
    _validate_positive_multiplier(
        "complexity_multiplier",
        definition["complexity_multiplier"],
    )

    return definition


def describe_scenario(scenario_name: str) -> str:
    """
    Return a nontechnical description of a scenario.
    """
    definition = get_scenario_definition(scenario_name)
    return str(definition["description"])


def apply_named_scenario(
    base_inputs: dict[str, Any],
    scenario_name: str,
    custom_overrides: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Apply a named scenario to a base input payload.

    This function does not mutate the caller's input dictionary.

    Parameters
    ----------
    base_inputs : dict[str, Any]
        Base calculator-style input payload.
    scenario_name : str
        Scenario name to apply.
    custom_overrides : dict[str, Any] | None
        Optional override values for the custom scenario only.

    Returns
    -------
    dict[str, Any]
        Comparison-ready scenario payload containing original and adjusted
        inputs.
    """
    _validate_base_inputs(base_inputs)
    _validate_scenario_name(scenario_name)

    scenario_definition = get_scenario_definition(scenario_name)

    if scenario_name == "custom":
        normalized_overrides = _normalize_custom_overrides(custom_overrides)
        scenario_definition.update(normalized_overrides)
        _validate_benchmark_position(scenario_definition["benchmark_position"])
        _validate_positive_multiplier(
            "duration_multiplier",
            scenario_definition["duration_multiplier"],
        )
        _validate_positive_multiplier(
            "scale_multiplier",
            scenario_definition["scale_multiplier"],
        )
        _validate_positive_multiplier(
            "complexity_multiplier",
            scenario_definition["complexity_multiplier"],
        )
    else:
        if custom_overrides not in (None, {}):
            raise ValueError(
                "custom_overrides may only be supplied when "
                "scenario_name='custom'."
            )

    original_inputs: dict[str, Any] = dict(base_inputs)
    adjusted_inputs: dict[str, Any] = dict(base_inputs)

    for field_name in ("duration_units", "scale_factor", "complexity_factor"):
        _validate_numeric_input_field(base_inputs, field_name)

    if "duration_units" in adjusted_inputs:
        adjusted_inputs["duration_units"] = (
            adjusted_inputs["duration_units"]
            * scenario_definition["duration_multiplier"]
        )

    if "scale_factor" in adjusted_inputs:
        adjusted_inputs["scale_factor"] = (
            adjusted_inputs["scale_factor"]
            * scenario_definition["scale_multiplier"]
        )

    if "complexity_factor" in adjusted_inputs:
        adjusted_inputs["complexity_factor"] = (
            adjusted_inputs["complexity_factor"]
            * scenario_definition["complexity_multiplier"]
        )

    adjusted_inputs["benchmark_position"] = scenario_definition[
        "benchmark_position"
    ]

    return {
        "scenario_name": scenario_definition["scenario_name"],
        "scenario_display_name": scenario_definition["display_name"],
        "scenario_description": scenario_definition["description"],
        "benchmark_position": scenario_definition["benchmark_position"],
        "scenario_notes": scenario_definition["notes"],
        "original_inputs": original_inputs,
        "adjusted_inputs": adjusted_inputs,
    }


def compare_scenarios(
    base_inputs: dict[str, Any],
    scenario_names: list[str],
    custom_overrides: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """
    Apply multiple scenarios to the same base input payload and return
    comparison-ready outputs.

    Parameters
    ----------
    base_inputs : dict[str, Any]
        Base calculator-style input payload.
    scenario_names : list[str]
        Ordered list of scenarios to apply.
    custom_overrides : dict[str, Any] | None
        Optional overrides used only when 'custom' appears in scenario_names.

    Returns
    -------
    list[dict[str, Any]]
        Ordered list of scenario payloads.
    """
    _validate_base_inputs(base_inputs)

    if not isinstance(scenario_names, list) or not scenario_names:
        raise ValueError("scenario_names must be a non-empty list of strings.")

    for scenario_name in scenario_names:
        if not isinstance(scenario_name, str):
            raise ValueError("Each scenario name must be a string.")
        _validate_scenario_name(scenario_name)

    results: list[dict[str, Any]] = []

    for scenario_name in scenario_names:
        if scenario_name == "custom":
            result = apply_named_scenario(
                base_inputs=base_inputs,
                scenario_name=scenario_name,
                custom_overrides=custom_overrides,
            )
        else:
            result = apply_named_scenario(
                base_inputs=base_inputs,
                scenario_name=scenario_name,
            )

        results.append(result)

    return results
