from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

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

# ---------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------
MODEL_METADATA_PATH = PROJECT_ROOT / "src" / "models" / "baseline_logreg_metadata.json"

# Prefer repo-root docs if present, then fall back to project docs folders if you later move them
BASELINE_METHODOLOGY_CANDIDATES = [
    PROJECT_ROOT / "baseline_filter_methodology.md",
    PROJECT_ROOT / "reports" / "methodology" / "baseline_filter_methodology.md",
    PROJECT_ROOT / "docs" / "baseline_filter_methodology.md",
]

LABELING_GUIDE_CANDIDATES = [
    PROJECT_ROOT / "ml_labeling_guide.md",
    PROJECT_ROOT / "reports" / "methodology" / "ml_labeling_guide.md",
    PROJECT_ROOT / "docs" / "ml_labeling_guide.md",
]

SCOPE_BOUNDARIES_CANDIDATES = [
    PROJECT_ROOT / "scope_boundaries.md",
    PROJECT_ROOT / "reports" / "methodology" / "scope_boundaries.md",
    PROJECT_ROOT / "docs" / "scope_boundaries.md",
]


# ---------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------
def _first_existing_path(candidates: list[Path]) -> Path | None:
    for path in candidates:
        if path.exists():
            return path
    return None


def _read_text_if_exists(candidates: list[Path]) -> tuple[str, Path | None]:
    path = _first_existing_path(candidates)
    if path is None:
        return "", None

    try:
        return path.read_text(encoding="utf-8"), path
    except Exception:
        return "", path


def _load_model_metadata() -> dict[str, Any]:
    if not MODEL_METADATA_PATH.exists():
        return {}

    try:
        with open(MODEL_METADATA_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _safe_metric(report: dict[str, Any], label: str, metric_name: str) -> float | None:
    try:
        return float(report[label][metric_name])
    except Exception:
        return None


def _safe_accuracy(report: dict[str, Any]) -> float | None:
    try:
        return float(report["accuracy"])
    except Exception:
        return None


def _fmt_metric(value: float | None) -> str:
    if value is None:
        return "N/A"
    return f"{value:.2f}"


def _render_metric_cards(metadata: dict[str, Any]) -> None:
    report = metadata.get("classification_report", {})
    class_balance = metadata.get("class_balance", {})

    precision_pos = _safe_metric(report, "1", "precision")
    recall_pos = _safe_metric(report, "1", "recall")
    f1_pos = _safe_metric(report, "1", "f1-score")
    accuracy = _safe_accuracy(report)

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        render_metric_card("Precision", _fmt_metric(precision_pos))
    with col2:
        render_metric_card("Recall", _fmt_metric(recall_pos))
    with col3:
        render_metric_card("F1 Score", _fmt_metric(f1_pos))
    with col4:
        render_metric_card("Accuracy", _fmt_metric(accuracy))

    st.caption(
        "These metrics evaluate the Logistic Regression model (ML layer). "
        "They measure how well the model distinguishes relevant vs non-relevant contracts after baseline filtering."
    )

    st.caption(
        "These metrics are shown for the positive class ('relevant') where available. "
        "The saved model metadata shows 98 training rows, 33 test rows, 2,105 features, "
        "and a class balance of 86 positive vs 45 negative labeled records."
    )


def _render_training_summary(metadata: dict[str, Any]) -> None:
    train_rows = metadata.get("train_rows", "N/A")
    test_rows = metadata.get("test_rows", "N/A")
    feature_count = metadata.get("feature_count", "N/A")
    model_class = metadata.get("model_class", "N/A")
    mode = metadata.get("mode", "N/A")

    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        render_metric_card("Train Rows", str(train_rows))
    with col2:
        render_metric_card("Test Rows", str(test_rows))
    with col3:
        render_metric_card("Features", str(feature_count))
    with col4:
        render_metric_card("ML Model", str(model_class))
    with col5:
        render_metric_card("Mode", str(mode))

    class_balance = metadata.get("class_balance", {})
    if class_balance:
        st.markdown("### Class Balance")
        st.json(class_balance)


# ---------------------------------------------------------------------
# Page
# ---------------------------------------------------------------------
def main() -> None:
    render_page_header(
        "Model Methodology",
        (
            "Explain how comparable contracts are identified using transparent baseline rules "
            "and a machine learning refinement layer, without cluttering leadership-facing pages."
        ),
    )

    render_methodology_info_box(
        "This page is for credibility and interpretability. It explains how the benchmark dataset "
        "is constructed and how the relevance model supports defensible analysis."
    )

    # -----------------------------------------------------------------
    # Executive Summary (NEW)
    # -----------------------------------------------------------------
    st.subheader("Methodology Overview")

    col1, col2, col3 = st.columns(3)

    col1.markdown(
        """
        **1. Baseline Rules**

        Transparent filters (PSC, NAICS, keywords)  
        create an initial pool of potentially comparable contracts.
        """
    )

    col2.markdown(
        """
        **2. ML Refinement**

        Logistic regression model improves precision  
        and reduces false positives from broad rule matches.
        """
    )

    col3.markdown(
        """
        **3. Benchmark Dataset**

        Final comparable set supports  
        defensible external cost benchmarking.
        """
    )

    st.markdown(
        """
This system is designed to prioritize **credibility and defensibility** over raw volume.

- Rules provide transparency  
- ML provides consistency  
- Metrics provide validation  
"""
    )

    # -----------------------------------------------------------------
    # 3. Performance metrics
    # -----------------------------------------------------------------

    st.markdown(
        """
### How to read this section

This system uses a **hybrid approach**:

- **Baseline Rules** → initial filtering using PSC, NAICS, and keywords  
- **Machine Learning (Logistic Regression)** → refines results and assigns relevance scores  
- **Hybrid Output** → final dataset used in the dashboard combines both  

**Important:**  
The performance metrics shown below (precision, recall, F1) apply to the **machine learning model only**,  
not the full hybrid system.
"""
    )

    st.subheader("3. Model Performance")

    metadata = _load_model_metadata()
    if not metadata:
        st.warning("Model metadata file was not found or could not be read.")
    else:
        _render_training_summary(metadata)
        st.markdown("### Key Metrics")
        _render_metric_cards(metadata)

        st.markdown(
            """
### Interpretation

- **High precision (~0.95)** indicates most contracts classified as relevant are truly comparable  
- **Strong recall (~0.86)** indicates the model captures most relevant contracts  
- **F1 score (~0.90)** shows a balanced and reliable classification performance  

For this use case, **precision is the priority**, because including non-comparable contracts
can distort benchmark distributions and weaken downstream analysis.
"""
        )

        report = metadata.get("classification_report", {})
        if report:
            with st.expander("View full classification report", expanded=False):
                st.json(report)

    st.markdown(
        """
### Why these metrics matter

- **Precision** tells us how many contracts predicted as relevant are actually relevant.
- **Recall** tells us how many truly relevant contracts are successfully captured.
- **F1 Score** balances precision and recall.
- **Accuracy** summarizes overall prediction correctness.

For this use case, **precision is especially important**, because including non-comparable contracts
can distort benchmark distributions and downstream value interpretation.
"""
    )

    # -----------------------------------------------------------------
    # 1. Baseline filtering logic
    # -----------------------------------------------------------------
    st.subheader("1. Baseline Filtering Logic")

    st.markdown(
        """
The first stage of the system is a **transparent, rule-based benchmark screen**.

It uses:
- **PSC codes**
- **NAICS codes**
- **keyword / phrase matching**
- combined contract text fields

Its role is to create an explainable candidate pool of potentially comparable contracts
before any machine learning is applied.
"""
    )

    baseline_text, baseline_path = _read_text_if_exists(BASELINE_METHODOLOGY_CANDIDATES)

    if baseline_text:
        st.caption(f"Loaded from: {baseline_path}")
        with st.expander("View baseline methodology details", expanded=False):
            st.markdown(baseline_text)
    else:
        st.warning(
            "Baseline methodology document was not found in the expected repo locations."
        )

    st.markdown(
        """
**Interpretation:** baseline rules are intentionally transparent and reviewable.  
They are useful because they can be challenged, inspected, and compared against later ML outputs.
They are not the final authority on relevance.
"""
    )

    # -----------------------------------------------------------------
    # 2. ML role
    # -----------------------------------------------------------------
    st.subheader("2. Machine Learning Role")

    st.markdown(
        """
The ML model acts as a **refinement layer** on top of the baseline rules.

Its purpose is to:
- improve precision
- reduce false positives from broad rule matches
- provide probabilistic relevance scoring
- support more consistent contract inclusion decisions at scale

The project’s business framework explicitly positions ML comparability validity as a credibility question,
with precision, recall, and F1 among the key model-review metrics.
"""
    )

    st.caption(
        "The final dashboard dataset is produced using a hybrid approach: "
        "baseline rules first filter candidates, and the ML model then refines and scores them."
    )

    # -----------------------------------------------------------------
    # 4. Threshold notes
    # -----------------------------------------------------------------
    st.subheader("4. Threshold Notes")

    st.markdown(
        """
The ML model produces a relevance probability score.

That score can be turned into a final classification using a threshold:

- higher threshold → stricter inclusion, usually higher precision
- lower threshold → broader inclusion, usually higher recall

This matters because the project is designed for **benchmark stability and defensibility**, not for
maximizing raw inclusion volume.
"""
    )

    render_methodology_info_box(
        "Thresholds are a governance choice, not just a technical setting. "
        "They should be chosen to support benchmark quality and defensible interpretation."
    )

    # -----------------------------------------------------------------
    # 5. Labeling and review discipline
    # -----------------------------------------------------------------
    st.subheader("5. Labeling and Review Discipline")

    st.markdown(
        """
The supervised model is only as good as the labeled examples used to train it.

The labeling framework emphasizes:
- relevance first, category second
- consistent reviewer judgment
- explicit handling of ambiguous cases
- benchmark-focused reasoning rather than speculative claims
"""
    )

    labeling_text, labeling_path = _read_text_if_exists(LABELING_GUIDE_CANDIDATES)

    if labeling_text:
        st.caption(f"Loaded from: {labeling_path}")
        with st.expander("View labeling guide details", expanded=False):
            st.markdown(labeling_text)
    else:
        st.info("Labeling guide file was not found in the expected repo locations.")

    # -----------------------------------------------------------------
    # 6. Scope boundaries
    # -----------------------------------------------------------------
    st.subheader("6. Scope Boundaries")

    scope_text, scope_path = _read_text_if_exists(SCOPE_BOUNDARIES_CANDIDATES)

    if scope_text:
        st.caption(f"Loaded from: {scope_path}")
        with st.expander("View scope boundaries and guardrails", expanded=False):
            st.markdown(scope_text)
    else:
        st.info("Scope boundaries file was not found in the expected repo locations.")

    render_scope_warning_box(
        "This methodology supports benchmark-derived external cost context. "
        "It does not prove internal savings, audited ROI, or measured AGA efficiency gains."
    )


if __name__ == "__main__":
    main()

