"""
Centralized project configuration and path management for the
SOFWERX Value Dashboard repository.

This module defines repo-relative paths, environment-driven runtime
settings, and lightweight helper utilities so that all other modules
can import configuration from one place.

This file is intentionally limited to configuration and path logic.
It should not contain business logic, ML logic, ingestion logic,
or dashboard-specific behavior.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Callable


# ---------------------------------------------------------------------
# Optional .env loading
# ---------------------------------------------------------------------
# This allows local environment configuration without making python-dotenv
# a hard requirement for the project to run.
try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    # Safe fallback: environment variables can still be provided by the shell,
    # deployment platform, or IDE run configuration.
    pass


# ---------------------------------------------------------------------
# Project root detection
# ---------------------------------------------------------------------
# settings.py lives at:
#   <repo_root>/src/config/settings.py
# Therefore:
#   Path(__file__).resolve().parents[2] == <repo_root>
PROJECT_ROOT: Path = Path(__file__).resolve().parents[2]


# ---------------------------------------------------------------------
# Core repository directories
# ---------------------------------------------------------------------
SRC_DIR: Path = PROJECT_ROOT / "src"
CONFIG_DIR: Path = SRC_DIR / "config"

APP_DIR: Path = PROJECT_ROOT / "app"
APP_PAGES_DIR: Path = APP_DIR / "pages"
APP_COMPONENTS_DIR: Path = APP_DIR / "components"

DATA_DIR: Path = SRC_DIR / "data"
RAW_DATA_DIR: Path = DATA_DIR / "raw"
INTERIM_DATA_DIR: Path = DATA_DIR / "interim"
PROCESSED_DATA_DIR: Path = DATA_DIR / "processed"
LABELS_DIR: Path = DATA_DIR / "labels"

MODELS_DIR: Path = PROJECT_ROOT / "models"
MODELS_CURRENT_DIR: Path = MODELS_DIR / "current"
MODELS_ARCHIVE_DIR: Path = MODELS_DIR / "archive"

REPORTS_DIR: Path = PROJECT_ROOT / "reports"
REPORTS_ARCHITECTURE_DIR: Path = REPORTS_DIR / "architecture"
REPORTS_EVALUATION_DIR: Path = REPORTS_DIR / "evaluation"
REPORTS_METHODOLOGY_DIR: Path = REPORTS_DIR / "methodology"

TESTS_DIR: Path = PROJECT_ROOT / "tests"
NOTEBOOKS_DIR: Path = PROJECT_ROOT / "notebooks"

DOCS_DIR: Path = PROJECT_ROOT / "docs"
# optional support for current repo state


# ---------------------------------------------------------------------
# Important file-level paths
# ---------------------------------------------------------------------
SERVICE_TAXONOMY_PATH: Path = CONFIG_DIR / "service_taxonomy.yaml"


# ---------------------------------------------------------------------
# Environment helper
# ---------------------------------------------------------------------
def _get_env(
    name: str,
    default: Any,
    cast: Callable[[str], Any] | None = None,
) -> Any:
    """
    Read an environment variable with optional type casting.

    Parameters
    ----------
    name : str
        Environment variable name.
    default : Any
        Default value if the variable is not set or is invalid.
    cast : Callable[[str], Any] | None
        Optional function used to cast the string value.

    Returns
    -------
    Any
        The cast value if available and valid, otherwise the default.
    """
    raw_value = os.getenv(name)
    if raw_value is None or raw_value == "":
        return default

    if cast is None:
        return raw_value

    try:
        return cast(raw_value)
    except (TypeError, ValueError):
        return default


def _cast_bool(value: str) -> bool:
    """
    Convert common string values into booleans.
    """
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


# ---------------------------------------------------------------------
# Runtime environment settings
# ---------------------------------------------------------------------
APP_ENV: str = _get_env("APP_ENV", "dev", str)
LOG_LEVEL: str = _get_env("LOG_LEVEL", "INFO", str).upper()

DEFAULT_FISCAL_YEAR_START: int = _get_env(
    "DEFAULT_FISCAL_YEAR_START",
    2021,
    int,
)
DEFAULT_FISCAL_YEAR_END: int = _get_env(
    "DEFAULT_FISCAL_YEAR_END",
    2024,
    int,
)

DATA_FRESHNESS_THRESHOLD_DAYS: int = _get_env(
    "DATA_FRESHNESS_THRESHOLD_DAYS",
    30,
    int,
)

DEFAULT_OUTPUT_FORMAT: str = _get_env(
    "DEFAULT_OUTPUT_FORMAT",
    "parquet",
    str,
).lower()
SUPPORTED_OUTPUT_FORMATS: tuple[str, ...] = ("csv", "parquet", "json")

DEFAULT_MODEL_ARTIFACT_NAME: str = _get_env(
    "MODEL_ARTIFACT_NAME",
    "foundry_classifier.pkl",
    str,
)

STREAMLIT_SERVER_HOST: str = _get_env("STREAMLIT_SERVER_HOST", "0.0.0.0", str)
STREAMLIT_SERVER_PORT: int = _get_env("STREAMLIT_SERVER_PORT", 8501, int)

AUTO_CREATE_DIRECTORIES: bool = _get_env(
    "AUTO_CREATE_DIRECTORIES",
    False,
    _cast_bool,
)


# ---------------------------------------------------------------------
# Derived file paths
# ---------------------------------------------------------------------
DEFAULT_MODEL_ARTIFACT_PATH: Path = (
    MODELS_CURRENT_DIR / DEFAULT_MODEL_ARTIFACT_NAME
)


# ---------------------------------------------------------------------
# Directory groups
# ---------------------------------------------------------------------
REQUIRED_DIRS: tuple[Path, ...] = (
    APP_DIR,
    APP_PAGES_DIR,
    APP_COMPONENTS_DIR,
    DATA_DIR,
    RAW_DATA_DIR,
    INTERIM_DATA_DIR,
    PROCESSED_DATA_DIR,
    LABELS_DIR,
    MODELS_DIR,
    MODELS_CURRENT_DIR,
    MODELS_ARCHIVE_DIR,
    REPORTS_DIR,
    REPORTS_ARCHITECTURE_DIR,
    REPORTS_EVALUATION_DIR,
    REPORTS_METHODOLOGY_DIR,
    TESTS_DIR,
    NOTEBOOKS_DIR,
    SRC_DIR,
    CONFIG_DIR,
)


# ---------------------------------------------------------------------
# Lightweight helpers
# ---------------------------------------------------------------------
def ensure_directories(paths: tuple[Path, ...] = REQUIRED_DIRS) -> None:
    """
    Create project directories if they do not already exist.

    This is useful for setup scripts, local development, and first-run
    initialization, but it is intentionally optional.
    """
    for path in paths:
        path.mkdir(parents=True, exist_ok=True)


def get_path_summary() -> dict[str, Path]:
    """
    Return a dictionary of commonly used project paths.
    """
    return {
        "PROJECT_ROOT": PROJECT_ROOT,
        "SRC_DIR": SRC_DIR,
        "CONFIG_DIR": CONFIG_DIR,
        "APP_DIR": APP_DIR,
        "APP_PAGES_DIR": APP_PAGES_DIR,
        "APP_COMPONENTS_DIR": APP_COMPONENTS_DIR,
        "DATA_DIR": DATA_DIR,
        "RAW_DATA_DIR": RAW_DATA_DIR,
        "INTERIM_DATA_DIR": INTERIM_DATA_DIR,
        "PROCESSED_DATA_DIR": PROCESSED_DATA_DIR,
        "LABELS_DIR": LABELS_DIR,
        "MODELS_DIR": MODELS_DIR,
        "MODELS_CURRENT_DIR": MODELS_CURRENT_DIR,
        "MODELS_ARCHIVE_DIR": MODELS_ARCHIVE_DIR,
        "REPORTS_DIR": REPORTS_DIR,
        "REPORTS_ARCHITECTURE_DIR": REPORTS_ARCHITECTURE_DIR,
        "REPORTS_EVALUATION_DIR": REPORTS_EVALUATION_DIR,
        "REPORTS_METHODOLOGY_DIR": REPORTS_METHODOLOGY_DIR,
        "TESTS_DIR": TESTS_DIR,
        "NOTEBOOKS_DIR": NOTEBOOKS_DIR,
        "SERVICE_TAXONOMY_PATH": SERVICE_TAXONOMY_PATH,
        "DEFAULT_MODEL_ARTIFACT_PATH": DEFAULT_MODEL_ARTIFACT_PATH,
    }


def validate_settings() -> None:
    """
    Validate a small set of configuration assumptions.

    Raises
    ------
    ValueError
        If a core runtime setting is invalid.
    """
    if DEFAULT_FISCAL_YEAR_START > DEFAULT_FISCAL_YEAR_END:
        raise ValueError(
            "DEFAULT_FISCAL_YEAR_START cannot be greater than "
            "DEFAULT_FISCAL_YEAR_END."
        )

    if DEFAULT_OUTPUT_FORMAT not in SUPPORTED_OUTPUT_FORMATS:
        raise ValueError(
            f"DEFAULT_OUTPUT_FORMAT must be one of "
            f"{SUPPORTED_OUTPUT_FORMATS}, got '{DEFAULT_OUTPUT_FORMAT}'."
        )

    if STREAMLIT_SERVER_PORT <= 0:
        raise ValueError("STREAMLIT_SERVER_PORT must be a positive integer.")


# ---------------------------------------------------------------------
# Optional startup behavior
# ---------------------------------------------------------------------
if AUTO_CREATE_DIRECTORIES:
    ensure_directories()

validate_settings()
