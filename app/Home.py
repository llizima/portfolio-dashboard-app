import sys
from pathlib import Path

import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.components.layout_helpers import (
    render_data_disclaimer_box,
    render_methodology_info_box,
    render_page_header,
    render_scope_warning_box,
)

_OVERVIEW_CHALLENGE = (
    "Applied Government Analytics (AGA) delivers a diverse set of "
    "services—including rapid prototyping, event facilitation, and project "
    "support—within a complex government contracting environment where cost, "
    "value, and impact are not always directly visible. While internal data "
    "captures operational activity such as event participation, marketing "
    "engagement, and service utilization, it lacks connection to the broader "
    "federal marketplace. As a result, leadership faces a critical challenge: "
    "understanding how these services compare to similar efforts across "
    "government in terms of cost, scale, and strategic value. Without this "
    "context, it becomes difficult to assess efficiency, justify resource "
    "allocation, or identify which service areas present the strongest "
    "opportunities for growth and expansion."
)

_OVERVIEW_SOLUTION = (
    "To address this gap, the Applied Government Analytics (AGA) Value "
    "Dashboard integrates internal service data with external contract data "
    "from USAspending to create a unified benchmarking and analysis platform. "
    "The dashboard enables users to explore comparable government projects, "
    "evaluate cost distributions across service categories, and estimate the "
    "relative value of Applied Government Analytics (AGA) activities against "
    "real-world federal spending patterns. This transforms internal reporting "
    "from descriptive metrics into actionable insight—allowing leadership to "
    "identify high-impact service areas, uncover underexplored opportunities, "
    "and make data-driven decisions about where to focus future investment. "
    "By reframing internal operations through the lens of external benchmarks, "
    "the tool provides a clearer understanding of both performance and "
    "potential, supporting more strategic and defensible decision-making."
)

st.set_page_config(
    page_title="Applied Government Analytics (AGA) Value Dashboard",
    page_icon="🔶",
    layout="wide",
)

render_page_header(
    "Value Dashboard",
    (
        "Benchmark-derived external cost context for Applied Government "
        "Analytics (AGA) procurement analysis."
    ),
)

st.subheader("The Challenge")
st.markdown(_OVERVIEW_CHALLENGE)

st.subheader("The Solution & Impact")
st.markdown(_OVERVIEW_SOLUTION)

st.markdown(
    """
    This app provides a modular interface for exploring benchmark-derived
    value context, comparable contract data, service category analysis, model
    methodology, and data quality outputs.
    """
)

render_data_disclaimer_box()

st.subheader("App Sections")
st.markdown(
    """
    Use the navigation sidebar to explore:

    - **Executive Overview** — high-level KPI and value story entry point
    - **Benchmark Explorer** — comparable contract inspection and benchmark
      context
    - **Service Category Analysis** — category-level patterns and summaries
    - **Value Calculator** — scenario-based benchmark-derived cost context
    - **Model Methodology** — relevance model summary and evaluation context
    - **Data Quality Monitoring** — processed-data checks and monitoring
      outputs
    - **Architecture & Deployment** — system structure and deployment-oriented
      notes
    """
)

render_methodology_info_box(
    "This is the initial app shell. Final charts, metric cards, and "
    "interactive analysis are populated from processed backend artifacts."
)

render_scope_warning_box(
    "This app presents benchmark-derived context and comparable-contract "
    "analysis. It should not be interpreted as a formal savings-claim engine "
    "without additional internal cost data."
)
