from __future__ import annotations

import sys
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.components.layout_helpers import (
    render_methodology_info_box,
    render_metric_card,
    render_page_header,
    render_scope_warning_box,
)
from src.business.assumptions import (
    get_category_reference_values,
    get_default_assumptions,
    list_supported_categories,
)
from src.business.calculator import calculate_external_procurement_equivalent
from src.business.scenarios import compare_scenarios, get_default_scenario_names


def _currency(value: float) -> str:
    return f"${float(value):,.0f}"


def _safe_float(value: object, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _render_result_cards(result: dict) -> None:
    col1, col2, col3 = st.columns(3)

    with col1:
        render_metric_card("Low Estimate", _currency(result["low_estimate"]))
    with col2:
        render_metric_card("Central Estimate", _currency(result["central_estimate"]))
    with col3:
        render_metric_card("High Estimate", _currency(result["high_estimate"]))


def _render_assumptions_section(
    *,
    category: str,
    benchmark_position: str,
    duration_units: float,
    scale_factor: float,
    complexity_factor: float,
) -> None:
    reference_values = get_category_reference_values(category)

    with st.expander("View assumptions, reference values, and calculation context", expanded=False):
        st.markdown("### Current user-selected assumptions")

        assumptions_df = pd.DataFrame(
            [
                {"assumption": "Type of work", "value": str(category)},
                {"assumption": "Benchmark view", "value": str(benchmark_position)},
                {"assumption": "Estimated duration (months)", "value": str(duration_units)},
                {"assumption": "Scope multiplier", "value": str(scale_factor)},
                {"assumption": "Complexity multiplier", "value": str(complexity_factor)},
            ]
        )
        assumptions_df["value"] = assumptions_df["value"].astype(str)

        st.dataframe(
            assumptions_df,
            width="stretch",
            hide_index=True,
        )

        st.markdown("### Category reference values")

        ref_df = pd.DataFrame(
            [
                {
                    "reference_level": "Low",
                    "value": _currency(
                        _safe_float(reference_values.get("low_reference_value"))
                    ),
                },
                {
                    "reference_level": "Central",
                    "value": _currency(
                        _safe_float(reference_values.get("central_reference_value"))
                    ),
                },
                {
                    "reference_level": "High",
                    "value": _currency(
                        _safe_float(reference_values.get("high_reference_value"))
                    ),
                },
            ]
        )
        ref_df["value"] = ref_df["value"].astype(str)

        st.dataframe(
            ref_df,
            width="stretch",
            hide_index=True,
        )


def _render_scenario_comparison(base_inputs: dict) -> None:
    st.subheader("Scenario Comparison")

    st.markdown(
        """
        Scenarios are designed to show different estimate postures for the **same type of work**.

        - **Conservative** = lower-bound benchmark posture  
        - **Balanced** = typical benchmark posture  
        - **Upper Range** = broader upper-range benchmark posture  

        These scenarios help compare how the estimate changes when the benchmark view shifts,
        while keeping the work definition itself constant.
        """
    )

    scenario_names = get_default_scenario_names()
    scenario_payloads = compare_scenarios(
        base_inputs=base_inputs,
        scenario_names=scenario_names,
    )

    rows: list[dict[str, object]] = []

    for payload in scenario_payloads:
        adjusted_inputs = payload["adjusted_inputs"]

        # Scenario engine adds benchmark_position, but calculator expects scenario.
        benchmark_position = adjusted_inputs.get("benchmark_position", "central")
        scenario_for_calculator = (
            "low"
            if benchmark_position == "low"
            else "high"
            if benchmark_position == "high"
            else "central"
        )

        calculator_inputs = {
            "service_category": adjusted_inputs["service_category"],
            "scenario": scenario_for_calculator,
            "duration_units": adjusted_inputs["duration_units"],
            "scale_factor": adjusted_inputs["scale_factor"],
            "complexity_factor": adjusted_inputs["complexity_factor"],
        }

        calc_result = calculate_external_procurement_equivalent(calculator_inputs)

        rows.append(
            {
                "Scenario": str(payload["scenario_display_name"]),
                "Benchmark Position": str(benchmark_position),
                "Low": _safe_float(calc_result["low_estimate"]),
                "Central": _safe_float(calc_result["central_estimate"]),
                "High": _safe_float(calc_result["high_estimate"]),
            }
        )

    scenario_df = pd.DataFrame(rows)
    scenario_df = scenario_df.astype(
        {
            "Scenario": "string",
            "Benchmark Position": "string",
            "Low": "float64",
            "Central": "float64",
            "High": "float64",
        }
    )

    display_df = scenario_df.copy()
    for col in ["Low", "Central", "High"]:
        display_df[col] = display_df[col].map(_currency)

    st.dataframe(display_df, width="stretch", hide_index=True)

    chart_df = scenario_df[["Scenario", "Central"]].copy()
    chart_df = chart_df.rename(columns={"Central": "estimate"})
    chart = (
        alt.Chart(chart_df)
        .mark_bar(color="#ed6622", cornerRadiusTopLeft=4, cornerRadiusTopRight=4)
        .encode(
            x=alt.X("Scenario:N", axis=alt.Axis(labelColor="#8a8fa8", titleColor="#8a8fa8", labelAngle=0), title=None),
            y=alt.Y("estimate:Q", axis=alt.Axis(labelColor="#8a8fa8", titleColor="#8a8fa8", gridColor="#2a2d3a"), title="Central Estimate ($)"),
            tooltip=["Scenario:N", "estimate:Q"],
        )
        .properties(background="#1a1d27", padding={"left": 10, "right": 10, "top": 10, "bottom": 10})
        .configure_view(strokeWidth=0)
        .configure_axis(domainColor="#3a3d4a")
    )
    st.altair_chart(chart, width="stretch")


def main() -> None:
    render_page_header(
        "Value Calculator",
        (
            "Interactively estimate benchmark-derived external procurement context "
            "using transparent assumptions and scenario comparison."
        ),
    )

    defaults = get_default_assumptions()
    categories = list_supported_categories()

    st.subheader("Define the Work Being Estimated")

    st.markdown(
        """
        Configure the work type and assumptions below to estimate what a similar
        effort might cost if procured externally using benchmark-derived reference values.
        """
    )

    st.markdown(
        """
        **What these inputs mean**

        - **Type of Work** = the service category being estimated  
        - **Estimated Duration** = how long the engagement lasts  
        - **Scope Size** = how large the effort is overall  
        - **Technical Complexity** = how difficult or customized the work is  
        - **Benchmark View** = whether you want a lower-bound, typical, or upper-range benchmark posture
        """
    )

    col1, col2 = st.columns(2)

    SCALE_MAP = {
        "Small": 0.75,
        "Standard": 1.00,
        "Large": 1.35,
    }

    COMPLEXITY_MAP = {
        "Low": 0.85,
        "Moderate": 1.00,
        "High": 1.30,
    }

    with col1:
        default_category = str(
            defaults.get(
                "default_category",
                categories[0] if categories else "engineering_design_support",
            )
        )
        default_category_index = (
            categories.index(default_category)
            if default_category in categories
            else 0
        )

        category = st.selectbox(
            "Type of Work",
            options=categories,
            index=default_category_index,
            help="Select the service category that best matches the work being estimated.",
        )

        duration_units = st.number_input(
            "Estimated Duration (Months)",
            min_value=1.0,
            value=float(defaults.get("default_duration_units", 6)),
            step=1.0,
            help="Represents the duration of the engagement in months.",
        )

        scope_label = st.selectbox(
            "Scope Size",
            options=list(SCALE_MAP.keys()),
            index=1,
            help="Represents the overall size or breadth of the engagement.",
        )
        scale_factor = SCALE_MAP[scope_label]

    with col2:
        benchmark_position = st.selectbox(
            "Benchmark View",
            options=["low", "central", "high"],
            index=["low", "central", "high"].index(
                str(defaults.get("default_scenario", "central"))
            ),
            help="Controls whether the estimate reflects a lower-bound, typical, or upper-range benchmark posture.",
        )

        complexity_label = st.selectbox(
            "Technical Complexity",
            options=list(COMPLEXITY_MAP.keys()),
            index=1,
            help="Represents how technically difficult or customized the work is.",
        )
        complexity_factor = COMPLEXITY_MAP[complexity_label]

    st.markdown(
        f"""
        **Current assumption summary:**  
        - {duration_units:.0f}-month engagement  
        - {scope_label} scope  
        - {complexity_label} complexity  
        - {benchmark_position} benchmark view
        """
    )

    calculator_inputs = {
        "service_category": category,
        "scenario": benchmark_position,
        "duration_units": duration_units,
        "scale_factor": scale_factor,
        "complexity_factor": complexity_factor,
    }

    result = calculate_external_procurement_equivalent(calculator_inputs)

    st.markdown("---")
    st.subheader("Estimated External Benchmark Range")
    _render_result_cards(result)

    selected_estimate = {
        "low": result["low_estimate"],
        "central": result["central_estimate"],
        "high": result["high_estimate"],
    }[benchmark_position]

    st.markdown(
        f"""
        **Selected estimate:** {_currency(selected_estimate)}  
        This reflects the **{benchmark_position} benchmark view** for a
        **{category}** effort with:

        - **{duration_units:.0f} months** of estimated duration
        - **{scope_label}** scope
        - **{complexity_label}** technical complexity
        """
    )

    st.markdown(
        """
        The full low / central / high range is shown above so the estimate can be
        interpreted as a benchmark-derived range rather than a single exact price.
        """
    )

    st.markdown("---")
    _render_assumptions_section(
        category=category,
        benchmark_position=benchmark_position,
        duration_units=duration_units,
        scale_factor=scale_factor,
        complexity_factor=complexity_factor,
    )

    st.markdown("---")
    _render_scenario_comparison(calculator_inputs)

    render_methodology_info_box(
        "This page estimates what similar work might cost if procured externally, using "
        "benchmark-derived reference values plus transparent assumptions about duration, "
        "scope, complexity, and benchmark posture."
    )

    render_scope_warning_box(
        "All estimates shown here are scenario-based external benchmark estimates. "
        "They support interpretation and comparison, not audited savings claims, "
        "proven ROI, or contractual price commitments."
    )


if __name__ == "__main__":
    main()

