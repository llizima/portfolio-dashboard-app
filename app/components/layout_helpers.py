from __future__ import annotations

import html as _html

import streamlit as st

from app.components.theme import inject_custom_css

DATA_DISCLAIMER_PRIMARY = (
    "Disclaimer: This dashboard is a demonstration prototype built using publicly available datasets "
    "and synthetic data for illustrative purposes. Benchmark estimates are derived from publicly "
    "accessible federal contract data, while internal cost values are simulated for comparison only "
    "and do not represent real proprietary figures. This project was originally developed as part of "
    "an internship submission and is presented here for educational and portfolio purposes only."
)

DATA_DISCLAIMER_CLOSING = (
    "This dashboard should not be interpreted as an official valuation or procurement decision tool."
)


def _md(text: str) -> str:
    """
    Escape HTML special chars then convert **bold** markers to <strong> tags.
    Keeps inline bold formatting when embedding user-facing messages in HTML.
    """
    parts = text.split("**")
    result = []
    for i, part in enumerate(parts):
        escaped = _html.escape(part)
        if i % 2 == 1:
            result.append(f'<strong>{escaped}</strong>')
        else:
            result.append(escaped)
    return "".join(result)


def render_page_header(title: str, purpose: str) -> None:
    """
    Render the Applied Government Analytics (AGA)-branded page hero header.
    Also injects global CSS and sidebar brand on every page.
    """
    inject_custom_css()
    _render_sidebar_brand()
    st.markdown(
        f"""
        <div class="swx-page-header">
            <div class="swx-header-eyebrow">// Applied Government Analytics (AGA) &nbsp;·&nbsp; VALUE DASHBOARD</div>
            <div class="swx-page-title">{_html.escape(title)}</div>
            <div class="swx-title-line"></div>
            <p class="swx-page-subtitle">{_html.escape(purpose)}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_sidebar_brand() -> None:
    st.sidebar.markdown(
        """
        <div class="swx-brand">
            <div class="swx-brand-badge">AGA</div>
            <div>
                <div class="swx-brand-name">Applied Government Analytics (AGA)</div>
                <div class="swx-brand-sub">VALUE DASHBOARD</div>
            </div>
            <div class="swx-brand-dot"></div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_methodology_info_box(message: str) -> None:
    st.markdown(
        f"""
        <div class="swx-info">
            <div class="swx-info-tag">◈ &nbsp;METHODOLOGY NOTE</div>
            <div class="swx-info-body">{_md(message)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_scope_warning_box(message: str) -> None:
    st.markdown(
        f"""
        <div class="swx-warn">
            <div class="swx-warn-tag">⚠ &nbsp;SCOPE BOUNDARY</div>
            <div class="swx-warn-body">{_md(message)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_data_disclaimer_box() -> None:
    """
    Portfolio/demo notice: public benchmark data, synthetic internal comparisons, non-operational use.
    Call after render_page_header() so themed CSS is already injected.
    """
    p1 = _html.escape(DATA_DISCLAIMER_PRIMARY)
    p2 = _html.escape(DATA_DISCLAIMER_CLOSING)
    st.markdown(
        f"""
        <div class="swx-disclaimer">
            <div class="swx-disclaimer-tag">◆ &nbsp;DATA DISCLAIMER</div>
            <div class="swx-disclaimer-body">
                <p>{p1}</p>
                <p>{p2}</p>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_empty_data_message(label: str) -> None:
    st.markdown(
        f"""
        <div class="swx-empty">
            <div class="swx-empty-glyph">[ &nbsp;_ &nbsp;]</div>
            <div class="swx-empty-label">No Data Available</div>
            <div class="swx-empty-desc">
                {_html.escape(label)} is not available yet.<br>
                Generate the required backend artifact or complete the upstream task.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_metric_card(
    label: str,
    value: str,
    delta: str | None = None,
    delta_positive: bool = True,
) -> None:
    """
    Render a custom Applied Government Analytics (AGA)-branded metric card.
    Call this inside a st.columns() context to match the standard column layout.
    """
    delta_html = ""
    if delta is not None:
        css_class = "pos" if delta_positive else "neg"
        arrow = "▲" if delta_positive else "▼"
        delta_html = (
            f'<div class="swx-metric-delta {css_class}">'
            f'{arrow} {_html.escape(str(delta))}'
            f'</div>'
        )

    st.markdown(
        f"""
        <div class="swx-metric">
            <div class="swx-metric-label">{_html.escape(label)}</div>
            <div class="swx-metric-value">{_html.escape(str(value))}</div>
            {delta_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_placeholder_section(heading: str, body: str) -> None:
    st.subheader(heading)
    st.markdown(body)
