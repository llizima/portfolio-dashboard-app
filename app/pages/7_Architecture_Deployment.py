from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.components.layout_helpers import (
    render_methodology_info_box,
    render_page_header,
    render_scope_warning_box,
)

DIAGRAM_PATH = PROJECT_ROOT / "app" / "assets" / "architecture_diagram.svg"


def main() -> None:
    render_page_header(
        "Architecture & Deployment",
        (
            "Show how public procurement data moves through ingestion, processed storage, "
            "model/scoring artifacts, and the private Streamlit application."
        ),
    )

    render_methodology_info_box(
        "This page explains the real system shape in plain English so reviewers can "
        "understand how data, artifacts, and app components fit together."
    )

    st.subheader("Architecture Diagram")

    '''if DIAGRAM_PATH.exists():
        svg_content = DIAGRAM_PATH.read_text(encoding="utf-8")
        st.markdown(
            f'<div style="width:100%;max-width:1400px;background:#13151e;padding:12px;border-radius:8px;box-sizing:border-box;">{svg_content}</div>',
            unsafe_allow_html=True,
        )
        st.markdown(f"*Loaded diagram: `{DIAGRAM_PATH.relative_to(PROJECT_ROOT)}`*")'''
    if DIAGRAM_PATH.exists():
        st.image(str(DIAGRAM_PATH), use_container_width=True)
        st.markdown(f"*Loaded diagram: `{DIAGRAM_PATH.relative_to(PROJECT_ROOT)}`*")
    else:
        st.warning("Architecture diagram image was not found.")
        st.code("Expected path: app/assets/architecture_diagram.svg")

    st.markdown("---")
    st.subheader("System Flow")

    st.markdown(
        """
### 1. Public Source Data
The project begins with the **USAspending API**, which provides public federal procurement data.

### 2. Ingestion & Transformation
Raw records are pulled, cleaned, normalized, and enriched into a more analysis-ready structure.

### 3. Processed Storage
Processed outputs are written into stable datasets that can be reused across:
- benchmarking
- category analysis
- scoring
- app pages

### 4. Model & Scoring Artifacts
The ML layer adds:
- trained relevance-model artifacts
- evaluation summaries
- scored benchmark datasets
- metadata such as model version and scoring timestamps

### 5. Streamlit App Layer
The Streamlit app sits on top of those prepared artifacts and exposes:
- executive summaries
- benchmark exploration
- category analysis
- value calculator outputs
- methodology
- monitoring

### 6. Private Access Posture
While the source procurement data is public, the processed outputs, model artifacts,
and app deployment are intended to be consumed in a more controlled internal context.
"""
    )

    st.markdown("---")
    st.subheader("Deployment Notes")

    st.markdown(
        """
This project is structured so the analytics app can be deployed as a private internal dashboard.

A practical deployment shape looks like this:

- data ingestion and processing run as controlled backend jobs
- processed datasets and model artifacts are stored in private project storage
- the Streamlit app reads those prepared artifacts
- end users access the app through an internal or restricted environment

This keeps the system easier to maintain because:
- expensive processing does not need to happen inside the app itself
- the UI stays responsive
- model and benchmark artifacts can be versioned separately from page code
"""
    )

    st.markdown("---")
    st.subheader("Plain-English Security Notes")

    st.markdown(
        """
This is **not** presented as a hardened enterprise security architecture diagram.

Instead, the practical security posture is:

- the project starts from **public procurement data**
- the **processed benchmark datasets**, **model artifacts**, and **dashboard** should remain in controlled storage/access environments
- user access to the app should be restricted to intended reviewers or internal stakeholders
- the app is meant for **private analytical use**, not broad anonymous public exposure

The main security distinction is simple:

> **public source data in** → **private processed analytics environment out**
"""
    )

    render_scope_warning_box(
        "This diagram is a conceptual architecture view for app explanation and review. "
        "It should not be interpreted as a full network engineering diagram, zero-trust design, "
        "or formal Authority to Operate security package."
    )


if __name__ == "__main__":
    main()  

