from __future__ import annotations

import streamlit as st


def inject_custom_css() -> None:
    """
    Inject Applied Government Analytics (AGA)-branded CSS into the current Streamlit page.
    Idempotent — safe to call multiple times per page load.
    """
    st.markdown(
        """
        <style>
        /* ============================================================
           FONTS: Rajdhani (labels/UI) + IBM Plex Mono (data values)
                  + Barlow (body text)
           Avoiding generic choices — these have a tactical/technical
           character appropriate for a defense-adjacent ops dashboard.
        ============================================================ */
        @import url('https://fonts.googleapis.com/css2?family=Rajdhani:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;600&family=Barlow:ital,wght@0,300;0,400;0,500;1,300&display=swap');

        html, body, [class*="css"] {
            font-family: 'Barlow', -apple-system, sans-serif !important;
        }

        /* ============================================================
           PAGE BACKGROUND — near-black with tactical grid overlay
        ============================================================ */
        .stApp {
            background-color: #080a0f !important;
            background-image:
                linear-gradient(rgba(237, 102, 34, 0.022) 1px, transparent 1px),
                linear-gradient(90deg, rgba(237, 102, 34, 0.022) 1px, transparent 1px);
            background-size: 44px 44px;
        }

        section[data-testid="stMain"] {
            background-color: transparent !important;
        }

        /* Aggressively override Streamlit's internal container width cap.
           Streamlit hard-codes max-width on .block-container regardless of
           wide mode. Target every selector variant across versions. */
        .main .block-container,
        .block-container,
        div[data-testid="stAppViewBlockContainer"],
        div[data-testid="stMainBlockContainer"],
        section[data-testid="stMain"] .block-container,
        section[data-testid="stMain"] > div > div > div {
            max-width: 1900px !important;
            width: 100% !important;
            padding-top: 0.5rem !important;
            padding-bottom: 3rem !important;
            padding-left: 2.5rem !important;
            padding-right: 2.5rem !important;
        }

        /* Subtle page fade-in */
        @keyframes swx-in {
            from { opacity: 0; transform: translateY(5px); }
            to   { opacity: 1; transform: translateY(0); }
        }
        .main .block-container > div {
            animation: swx-in 0.22s ease forwards;
        }

        /* ============================================================
           HEADINGS
        ============================================================ */
        h1 {
            font-family: 'Rajdhani', sans-serif !important;
            font-weight: 700 !important;
            font-size: 2.8rem !important;
            color: #edf0f5 !important;
            letter-spacing: 0.07em !important;
            text-transform: uppercase !important;
            line-height: 1 !important;
            border: none !important;
            padding: 0 !important;
            margin: 0 !important;
        }

        h2 {
            font-family: 'Rajdhani', sans-serif !important;
            font-weight: 600 !important;
            font-size: 1.45rem !important;
            color: #c8d0de !important;
            letter-spacing: 0.06em !important;
            text-transform: uppercase !important;
        }

        /* h3 — st.subheader() and ### markdown — orange left-bar accent */
        h3 {
            font-family: 'Rajdhani', sans-serif !important;
            font-weight: 600 !important;
            font-size: 0.72rem !important;
            color: #8fa0bc !important;
            letter-spacing: 0.22em !important;
            text-transform: uppercase !important;
            position: relative !important;
            padding-left: 0.85rem !important;
            margin: 1.75rem 0 0.65rem !important;
        }

        h3::before {
            content: '' !important;
            position: absolute !important;
            left: 0 !important;
            top: 50% !important;
            transform: translateY(-50%) !important;
            width: 3px !important;
            height: 0.85em !important;
            background: #ed6622 !important;
            box-shadow: 0 0 8px rgba(237, 102, 34, 0.55) !important;
            border-radius: 1px !important;
        }

        /* Body text */
        p {
            font-family: 'Barlow', sans-serif !important;
            font-size: 0.93rem !important;
            font-weight: 400 !important;
            color: #a8b4cc !important;
            line-height: 1.7 !important;
        }

        strong {
            color: #d8e0f0 !important;
            font-weight: 600 !important;
        }

        li {
            font-family: 'Barlow', sans-serif !important;
            font-size: 0.93rem !important;
            color: #a8b4cc !important;
            line-height: 1.7 !important;
        }

        /* ============================================================
           SIDEBAR
        ============================================================ */
        section[data-testid="stSidebar"] {
            background-color: #060810 !important;
            border-right: 1px solid #131828 !important;
        }

        section[data-testid="stSidebar"] .stMarkdown p,
        section[data-testid="stSidebar"] label,
        section[data-testid="stSidebar"] li {
            color: #a8b4cc !important;
            font-family: 'Barlow', sans-serif !important;
            font-size: 0.88rem !important;
        }

        section[data-testid="stSidebar"] h3 {
            font-size: 0.58rem !important;
            color: #5a6480 !important;
            letter-spacing: 0.28em !important;
            margin-top: 0.25rem !important;
        }

        section[data-testid="stSidebarNav"] a,
        section[data-testid="stSidebarNav"] span {
            font-family: 'Barlow', sans-serif !important;
            font-size: 0.9rem !important;
            color: #a8b4cc !important;
            font-weight: 400 !important;
            text-transform: none !important;
            letter-spacing: 0 !important;
        }

        section[data-testid="stSidebarNav"] li[aria-selected="true"] a,
        section[data-testid="stSidebarNav"] li[aria-selected="true"] span {
            color: #ed6622 !important;
            font-weight: 600 !important;
        }

        section[data-testid="stSidebarNav"] a:hover,
        section[data-testid="stSidebarNav"] span:hover {
            color: #ed6622 !important;
        }

        /* ============================================================
           BUTTONS — ghost style with orange, fills on hover
        ============================================================ */
        .stButton > button,
        .stDownloadButton > button {
            font-family: 'Rajdhani', sans-serif !important;
            font-weight: 700 !important;
            font-size: 0.72rem !important;
            letter-spacing: 0.15em !important;
            text-transform: uppercase !important;
            background: transparent !important;
            color: #ed6622 !important;
            border: 1px solid rgba(237, 102, 34, 0.5) !important;
            border-radius: 2px !important;
            padding: 0.45rem 1.4rem !important;
            transition: all 0.15s ease !important;
        }

        .stButton > button:hover,
        .stDownloadButton > button:hover {
            background: #ed6622 !important;
            color: #080a0f !important;
            border-color: #ed6622 !important;
            box-shadow: 0 0 18px rgba(237, 102, 34, 0.3) !important;
        }

        /* ============================================================
           DATAFRAME
        ============================================================ */
        div[data-testid="stDataFrame"] {
            border: 1px solid #131828 !important;
            border-radius: 3px !important;
            overflow: hidden !important;
        }

        /* ============================================================
           ALTAIR CHART CONTAINER
        ============================================================ */
        div[data-testid="stArrowVegaLiteChart"] {
            border-radius: 3px !important;
            overflow: hidden !important;
            border: 1px solid #131828 !important;
            background-color: #0a0d15 !important;
            padding: 0.5rem !important;
        }

        /* ============================================================
           EXPANDERS
        ============================================================ */
        div[data-testid="stExpander"] {
            border: 1px solid #131828 !important;
            border-radius: 3px !important;
            background: #0a0d15 !important;
        }

        div[data-testid="stExpander"] summary {
            font-family: 'Rajdhani', sans-serif !important;
            font-size: 0.7rem !important;
            font-weight: 600 !important;
            letter-spacing: 0.18em !important;
            text-transform: uppercase !important;
            color: #5a6280 !important;
            background: #0a0d15 !important;
            padding: 0.75rem 1rem !important;
        }

        div[data-testid="stExpander"] summary:hover {
            color: #ed6622 !important;
        }

        /* ============================================================
           INPUTS & SELECTS
        ============================================================ */
        div[data-baseweb="select"] > div,
        div[data-baseweb="input"] > div {
            background-color: #0a0d15 !important;
            border-color: #1e2335 !important;
            color: #c0c8d8 !important;
            border-radius: 2px !important;
            font-family: 'Barlow', sans-serif !important;
        }

        div[data-baseweb="select"] > div:focus-within,
        div[data-baseweb="input"] > div:focus-within {
            border-color: #ed6622 !important;
            box-shadow: 0 0 0 1px rgba(237, 102, 34, 0.25) !important;
        }

        ul[data-baseweb="menu"] {
            background-color: #0d1020 !important;
            border: 1px solid #1e2335 !important;
        }

        li[role="option"]:hover {
            background-color: rgba(237, 102, 34, 0.08) !important;
            color: #ed6622 !important;
        }

        div[data-testid="stMultiSelect"] span[data-baseweb="tag"] {
            background-color: rgba(237, 102, 34, 0.12) !important;
            border: 1px solid rgba(237, 102, 34, 0.35) !important;
            color: #ed6622 !important;
            border-radius: 2px !important;
            font-family: 'Rajdhani', sans-serif !important;
            font-size: 0.65rem !important;
            font-weight: 600 !important;
            letter-spacing: 0.1em !important;
            text-transform: uppercase !important;
        }

        div[data-testid="stWidgetLabel"] label,
        .stSelectbox label,
        .stNumberInput label,
        .stMultiSelect label {
            font-family: 'Rajdhani', sans-serif !important;
            font-size: 0.65rem !important;
            font-weight: 600 !important;
            letter-spacing: 0.18em !important;
            text-transform: uppercase !important;
            color: #7a8aaa !important;
        }

        /* ============================================================
           CAPTIONS
        ============================================================ */
        div[data-testid="stCaptionContainer"] p,
        .stCaption p {
            font-family: 'IBM Plex Mono', monospace !important;
            font-size: 0.65rem !important;
            color: #6070a0 !important;
            letter-spacing: 0.04em !important;
        }

        /* ============================================================
           HORIZONTAL RULES — gradient fade from orange
        ============================================================ */
        hr {
            border: none !important;
            height: 1px !important;
            background: linear-gradient(90deg, rgba(237,102,34,0.6) 0%, #1e2335 25%, transparent 100%) !important;
            margin: 2rem 0 !important;
            opacity: 0.7 !important;
        }

        /* ============================================================
           NATIVE ALERT FALLBACKS (when custom HTML is not used)
        ============================================================ */
        div[data-testid="stInfo"] {
            background-color: #06111e !important;
            border-left: 3px solid #467886 !important;
            border-radius: 3px !important;
        }

        div[data-testid="stWarning"] {
            background-color: #100c00 !important;
            border-left: 3px solid #ed6622 !important;
            border-radius: 3px !important;
        }

        div[data-testid="stError"] {
            background-color: #120606 !important;
            border-left: 3px solid #c0392b !important;
            border-radius: 3px !important;
        }

        /* ============================================================
           TOP HEADER BAR
        ============================================================ */
        header[data-testid="stHeader"] {
            background-color: #080a0f !important;
            border-bottom: 1px solid #131828 !important;
        }

        /* ============================================================
           SCROLLBARS
        ============================================================ */
        ::-webkit-scrollbar { width: 4px; height: 4px; }
        ::-webkit-scrollbar-track { background: #080a0f; }
        ::-webkit-scrollbar-thumb { background: #1e2335; border-radius: 2px; }
        ::-webkit-scrollbar-thumb:hover { background: #ed6622; }

        /* ============================================================
           CUSTOM HTML COMPONENT STYLES
           All classes prefixed swx- to avoid collisions
        ============================================================ */

        /* ----- Page Header ----- */
        .swx-page-header {
            position: relative;
            padding: 1.6rem 2rem 1.6rem 1.75rem;
            border-left: 4px solid #ed6622;
            background: linear-gradient(
                100deg,
                rgba(237,102,34,0.08) 0%,
                rgba(237,102,34,0.02) 45%,
                transparent 100%
            );
            margin-bottom: 2.25rem;
            overflow: hidden;
        }

        /* Tactical grid texture in header right area */
        .swx-page-header::after {
            content: '';
            position: absolute;
            top: 0; right: 0;
            width: 45%;
            height: 100%;
            background-image:
                linear-gradient(rgba(237,102,34,0.05) 1px, transparent 1px),
                linear-gradient(90deg, rgba(237,102,34,0.05) 1px, transparent 1px);
            background-size: 18px 18px;
            pointer-events: none;
            opacity: 0.6;
        }

        .swx-header-eyebrow {
            font-family: 'IBM Plex Mono', monospace;
            font-size: 0.58rem;
            font-weight: 400;
            letter-spacing: 0.3em;
            color: #ed6622;
            opacity: 0.85;
            margin-bottom: 0.55rem;
        }

        .swx-page-title {
            font-family: 'Rajdhani', sans-serif;
            font-size: 3.2rem;
            font-weight: 700;
            color: #edf0f5;
            letter-spacing: 0.07em;
            text-transform: uppercase;
            line-height: 1;
            margin: 0 0 0.7rem;
        }

        .swx-title-line {
            width: 44px;
            height: 2px;
            background: #ed6622;
            box-shadow: 0 0 10px rgba(237,102,34,0.55);
            margin-bottom: 0.75rem;
        }

        .swx-page-subtitle {
            font-family: 'Barlow', sans-serif;
            font-size: 0.88rem;
            font-weight: 300;
            font-style: italic;
            color: #8090aa;
            line-height: 1.55;
            max-width: 620px;
            margin: 0;
        }

        /* ----- Metric Card ----- */
        .swx-metric {
            position: relative;
            background: #0a0d15;
            border: 1px solid #131828;
            border-radius: 3px;
            padding: 1.2rem 1.1rem 1rem;
            overflow: hidden;
            min-height: 100px;
        }

        /* Glowing orange top bar */
        .swx-metric::before {
            content: '';
            position: absolute;
            top: 0; left: 0; right: 0;
            height: 2px;
            background: linear-gradient(90deg, #ed6622 0%, rgba(237,102,34,0.25) 100%);
            box-shadow: 0 1px 12px rgba(237,102,34,0.4);
        }

        /* Grid dot pattern background */
        .swx-metric::after {
            content: '';
            position: absolute;
            inset: 0;
            background-image:
                radial-gradient(circle, rgba(237,102,34,0.07) 1px, transparent 1px);
            background-size: 14px 14px;
            background-position: 7px 7px;
            pointer-events: none;
        }

        .swx-metric-label {
            font-family: 'Rajdhani', sans-serif;
            font-size: 0.6rem;
            font-weight: 600;
            letter-spacing: 0.2em;
            text-transform: uppercase;
            color: #ed6622;
            margin-bottom: 0.55rem;
            position: relative;
            z-index: 1;
        }

        .swx-metric-value {
            font-family: 'IBM Plex Mono', monospace;
            font-size: 2rem;
            font-weight: 600;
            color: #edf0f5;
            line-height: 1;
            letter-spacing: -0.02em;
            position: relative;
            z-index: 1;
        }

        .swx-metric-delta {
            font-family: 'IBM Plex Mono', monospace;
            font-size: 0.68rem;
            margin-top: 0.3rem;
            position: relative;
            z-index: 1;
        }
        .swx-metric-delta.pos { color: #22c55e; }
        .swx-metric-delta.neg { color: #ef4444; }

        /* ----- Info Box (Methodology) ----- */
        .swx-info {
            background: #050f1a;
            border: 1px solid #0e2030;
            border-top: 2px solid #467886;
            border-radius: 3px;
            padding: 0.9rem 1.1rem;
            margin: 0.65rem 0;
        }

        .swx-info-tag {
            font-family: 'IBM Plex Mono', monospace;
            font-size: 0.55rem;
            font-weight: 600;
            letter-spacing: 0.22em;
            text-transform: uppercase;
            color: #467886;
            margin-bottom: 0.35rem;
        }

        .swx-info-body {
            font-family: 'Barlow', sans-serif;
            font-size: 0.87rem;
            font-weight: 400;
            color: #90b0be;
            line-height: 1.65;
        }

        .swx-info-body strong {
            color: #aac8d8 !important;
        }

        /* ----- Warning Box (Scope Boundary) ----- */
        .swx-warn {
            background: #0c0800;
            border: 1px solid #201500;
            border-left: 3px solid #ed6622;
            border-radius: 3px;
            padding: 0.9rem 1.1rem;
            margin: 0.65rem 0;
        }

        .swx-warn-tag {
            font-family: 'IBM Plex Mono', monospace;
            font-size: 0.55rem;
            font-weight: 600;
            letter-spacing: 0.22em;
            text-transform: uppercase;
            color: rgba(237, 102, 34, 0.7);
            margin-bottom: 0.35rem;
        }

        .swx-warn-body {
            font-family: 'Barlow', sans-serif;
            font-size: 0.87rem;
            font-weight: 400;
            color: #c09858;
            line-height: 1.65;
        }

        .swx-warn-body strong {
            color: #d8b878 !important;
        }

        /* ----- Data disclaimer (portfolio / demo notice) ----- */
        .swx-disclaimer {
            background: #0a0d14;
            border: 1px solid #1a2430;
            border-left: 3px solid #5a7a8c;
            border-radius: 3px;
            padding: 0.95rem 1.15rem;
            margin: 0.85rem 0 1.25rem;
        }

        .swx-disclaimer-tag {
            font-family: 'IBM Plex Mono', monospace;
            font-size: 0.55rem;
            font-weight: 600;
            letter-spacing: 0.22em;
            text-transform: uppercase;
            color: #6d8fa3;
            margin-bottom: 0.45rem;
        }

        .swx-disclaimer-body {
            font-family: 'Barlow', sans-serif;
            font-size: 0.87rem;
            font-weight: 400;
            color: #9aa8bc;
            line-height: 1.65;
        }

        .swx-disclaimer-body p {
            margin: 0 0 0.65rem;
            color: #9aa8bc !important;
        }

        .swx-disclaimer-body p:last-child {
            margin-bottom: 0;
        }

        /* ----- Empty State ----- */
        .swx-empty {
            background: #0a0d15;
            border: 1px dashed #1e2335;
            border-radius: 3px;
            padding: 2.5rem 1.5rem;
            text-align: center;
            margin: 1rem 0;
        }

        .swx-empty-glyph {
            font-family: 'IBM Plex Mono', monospace;
            font-size: 1.4rem;
            color: #1e2335;
            letter-spacing: 0.1em;
            margin-bottom: 0.7rem;
        }

        .swx-empty-label {
            font-family: 'Rajdhani', sans-serif;
            font-size: 0.7rem;
            font-weight: 600;
            letter-spacing: 0.22em;
            text-transform: uppercase;
            color: #5a6888;
            margin-bottom: 0.4rem;
        }

        .swx-empty-desc {
            font-family: 'Barlow', sans-serif;
            font-size: 0.82rem;
            color: #5a6888;
            line-height: 1.5;
        }

        /* ----- Sidebar Brand ----- */
        .swx-brand {
            display: flex;
            align-items: center;
            gap: 0.65rem;
            padding: 0.85rem 1rem;
            border-bottom: 1px solid #131828;
            margin-bottom: 0.5rem;
        }

        .swx-brand-badge {
            font-family: 'Rajdhani', sans-serif;
            font-size: 0.95rem;
            font-weight: 700;
            color: #080a0f;
            background: #ed6622;
            width: 32px;
            height: 32px;
            display: flex;
            align-items: center;
            justify-content: center;
            border-radius: 2px;
            letter-spacing: 0.03em;
            flex-shrink: 0;
        }

        .swx-brand-name {
            font-family: 'Rajdhani', sans-serif;
            font-size: 0.78rem;
            font-weight: 700;
            letter-spacing: 0.22em;
            color: #b0b8c8;
            line-height: 1;
        }

        .swx-brand-sub {
            font-family: 'IBM Plex Mono', monospace;
            font-size: 0.5rem;
            letter-spacing: 0.14em;
            color: #4a5878;
            margin-top: 2px;
        }

        .swx-brand-dot {
            margin-left: auto;
            width: 5px;
            height: 5px;
            border-radius: 50%;
            background: #22c55e;
            box-shadow: 0 0 6px rgba(34, 197, 94, 0.55);
            flex-shrink: 0;
        }

        </style>
        """,
        unsafe_allow_html=True,
    )
