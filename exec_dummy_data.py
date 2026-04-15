"""Executive dummy dataset: loads `df` from sibling `exec_dummy_data.csv`.

The CSV has 48 rows (2025-01 through 2025-12 × four service categories) and
15 columns: internal vs benchmark cost metrics, estimated avoidance, efficiency,
event funnel fields (non-zero only for Events & Engagement), and benchmark
totals (spend and contract count).

Specs and a reference Streamlit page live in `executive_dummy_dashboard/`.
"""

from pathlib import Path

import pandas as pd

_ROOT = Path(__file__).resolve().parent
_CSV = _ROOT / "exec_dummy_data.csv"

df = pd.read_csv(_CSV)
