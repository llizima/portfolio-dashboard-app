import sys
from pathlib import Path

import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.components.layout_helpers import (
    render_methodology_info_box,
    render_page_header,
    render_scope_warning_box,
)

st.set_page_config(
    page_title="SOFWERX Value Dashboard",
    page_icon="🔶",
    layout="wide",
)

render_page_header(
    "Value Dashboard",
    "Benchmark-derived external cost context for SOFWERX procurement analysis.",
)

st.markdown(
    """
    This app provides a modular interface for exploring benchmark-derived value context,
    comparable contract data, service category analysis, model methodology, and data quality outputs.
    """
)

st.subheader("App Sections")
st.markdown(
    """
    Use the navigation sidebar to explore:

    - **Executive Overview** — high-level KPI and value story entry point
    - **Benchmark Explorer** — comparable contract inspection and benchmark context
    - **Service Category Analysis** — category-level patterns and summaries
    - **Value Calculator** — scenario-based benchmark-derived cost context
    - **Model Methodology** — relevance model summary and evaluation context
    - **Data Quality Monitoring** — processed-data checks and monitoring outputs
    - **Architecture & Deployment** — system structure and deployment-oriented notes
    """
)

render_methodology_info_box(
    "This is the initial app shell. Final charts, metric cards, and interactive analysis "
    "are populated from processed backend artifacts."
)

render_scope_warning_box(
    "This app presents benchmark-derived context and comparable-contract analysis. "
    "It should not be interpreted as a formal savings-claim engine without additional internal cost data."
)
