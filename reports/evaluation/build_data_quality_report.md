from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

from src.config.settings import (
    PROCESSED_DATA_DIR,
    REPORTS_EVALUATION_DIR,
    ensure_directories,
    validate_settings,
)


DEFAULT_DATASET_PATH = PROCESSED_DATA_DIR / "usaspending_contracts_cleaned.parquet"
DEFAULT_MISSINGNESS_PATH = (
    PROCESSED_DATA_DIR / "usaspending_contracts_cleaned_missingness.csv"
)
DEFAULT_PROCESSING_SUMMARY_PATH = (
    PROCESSED_DATA_DIR / "usaspending_contracts_cleaned_processing_summary.json"
)

DEFAULT_REPORT_PATH = REPORTS_EVALUATION_DIR / "data_quality_report.md"
DEFAULT_SUMMARY_CSV_PATH = REPORTS_EVALUATION_DIR / "data_quality_summary.csv"


CRITICAL_FIELDS = {
    "award_amount",
    "description",
    "start_date",
    "end_date",
    "awarding_agency",
}

IMPORTANT_FIELDS = {
    "total_outlays",
    "recipient_name",
    "psc_code",
    "psc_description",
    "naics_code",
    "naics_description",
    "award_id",
    "generated_internal_id",
    "contract_award_type",
    "fiscal_year",
    "base_obligation_date",
    "awarding_agency_code",
    "awarding_sub_agency",
    "funding_agency",
    "funding_sub_agency",
    "recipient_uei",
}

ENRICHMENT_FIELDS = {
    "description_clean",
    "text_all",
    "award_duration_days",
    "record_hash",
    "is_duplicate_row",
    "processed_at",
    "source_file",
    "run_id",
    "query_name",
    "internal_id",
    "awarding_agency_id",
    "agency_slug",
}


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def classify_category(column_name: str) -> str:
    if column_name in CRITICAL_FIELDS:
        return "critical"
    if column_name in IMPORTANT_FIELDS:
        return "important"
    return "enrichment"


def classify_reliability(column_name: str, missing_pct: float) -> str:
    lineage_fields = {"run_id", "query_name"}

    if column_name in lineage_fields and missing_pct >= 100:
        return "low"
    if column_name == "total_outlays" and missing_pct >= 20:
        return "low"
    if missing_pct == 0:
        return "high"
    if missing_pct <= 0.5:
        return "high"
    if missing_pct <= 5:
        return "medium"
    if missing_pct <= 20:
        return "medium"
    return "low"


def classify_include_in_kpi(column_name: str, reliability: str) -> str:
    kpi_fields = {
        "award_amount",
        "description",
        "start_date",
        "end_date",
        "awarding_agency",
        "recipient_name",
        "psc_code",
        "psc_description",
        "naics_code",
        "naics_description",
        "award_duration_days",
        "base_obligation_date",
        "awarding_agency_code",
        "awarding_sub_agency",
        "funding_agency",
        "funding_sub_agency",
        "contract_award_type",
        "fiscal_year",
        "award_id",
        "generated_internal_id",
    }
    if column_name in kpi_fields and reliability != "low":
        return "yes"
    return "no"


def notes_for_field(column_name: str, missing_pct: float) -> str:
    if column_name in {"run_id", "query_name"}:
        return "Lineage field; should support auditability and run-level traceability."
    if column_name == "total_outlays":
        return "Use as secondary metric only; missingness is too high for headline KPI use."
    if column_name == "description":
        return "Core text field for filtering and future comparability logic."
    if column_name == "description_clean":
        return "Derived from description and inherits its missingness."
    if column_name == "text_all":
        return "Combined text feature for downstream filtering and ML."
    if column_name == "award_duration_days":
        return "Derived from start_date and end_date; useful for duration-based analysis."
    if column_name == "record_hash":
        return "Operational QA field."
    if column_name == "is_duplicate_row":
        return "Operational duplicate-monitoring field."
    if missing_pct == 0:
        return "Fully populated."
    return "Monitor for downstream analytical impact."


def build_summary_table(missingness_df: pd.DataFrame) -> pd.DataFrame:
    summary = missingness_df.copy()

    summary["category"] = summary["column_name"].apply(classify_category)
    summary["reliability"] = summary.apply(
        lambda row: classify_reliability(
            row["column_name"],
            float(row["missing_pct"]),
        ),
        axis=1,
    )
    summary["include_in_kpi"] = summary.apply(
        lambda row: classify_include_in_kpi(
            row["column_name"],
            row["reliability"],
        ),
        axis=1,
    )
    summary["notes"] = summary.apply(
        lambda row: notes_for_field(
            row["column_name"],
            float(row["missing_pct"]),
        ),
        axis=1,
    )

    summary = summary[
        [
            "column_name",
            "missing_pct",
            "reliability",
            "category",
            "include_in_kpi",
            "notes",
        ]
    ].sort_values(
        by=["missing_pct", "column_name"],
        ascending=[False, True],
    )

    return summary


def get_missing_row_count(
    missingness_df: pd.DataFrame,
    column_name: str,
) -> int:
    row = missingness_df.loc[missingness_df["column_name"] == column_name]
    if row.empty:
        return 0
    return int(row.iloc[0]["missing_count"])


def get_missing_pct(
    missingness_df: pd.DataFrame,
    column_name: str,
) -> float:
    row = missingness_df.loc[missingness_df["column_name"] == column_name]
    if row.empty:
        return 0.0
    return float(row.iloc[0]["missing_pct"])


def pct(value: float, digits: int = 4) -> str:
    return f"{value:.{digits}f}%"


def md_table(rows: list[list[str]], headers: list[str]) -> str:
    header_line = "| " + " | ".join(headers) + " |"
    divider_line = "| " + " | ".join(["---"] * len(headers)) + " |"
    body_lines = ["| " + " | ".join(row) + " |" for row in rows]
    return "\n".join([header_line, divider_line] + body_lines)


def build_report_markdown(
    df: pd.DataFrame,
    missingness_df: pd.DataFrame,
    processing_summary: dict[str, Any],
    summary_table: pd.DataFrame,
) -> str:
    raw_file_count = int(processing_summary["raw_file_count"])
    raw_row_count = int(processing_summary["raw_row_count"])
    cleaned_row_count = int(processing_summary["cleaned_row_count"])
    duplicates_flagged = int(processing_summary["duplicates_flagged"])
    duplicates_removed = int(processing_summary["duplicates_removed"])

    retained_pct = (cleaned_row_count / raw_row_count * 100) if raw_row_count else 0
    removed_pct = (duplicates_removed / raw_row_count * 100) if raw_row_count else 0

    usable_mask = (
        df["award_amount"].notna()
        & df["description"].notna()
        & df["start_date"].notna()
    )
    usable_count = int(usable_mask.sum())
    usable_rate = (usable_count / cleaned_row_count * 100) if cleaned_row_count else 0

    highest_missing = missingness_df.sort_values(
        by=["missing_pct", "column_name"],
        ascending=[False, True],
    ).head(10)

    highest_missing_lines = []
    for _, row in highest_missing.iterrows():
        highest_missing_lines.append(
            f"- `{row['column_name']}` → **{pct(float(row['missing_pct']))}** "
            f"({int(row['missing_count']):,} missing)"
        )

    fully_populated = missingness_df.loc[missingness_df["missing_pct"] == 0, "column_name"]
    fully_populated_list = sorted(fully_populated.tolist())

    critical_rows = []
    for field in ["award_amount", "description", "start_date", "end_date", "awarding_agency"]:
        mp = get_missing_pct(missingness_df, field)
        critical_rows.append(
            [f"`{field}`", pct(mp), "Excellent" if mp == 0 else "Strong"]
        )

    important_rows = []
    for field in [
        "total_outlays",
        "recipient_name",
        "psc_code",
        "psc_description",
        "naics_code",
        "naics_description",
    ]:
        mp = get_missing_pct(missingness_df, field)
        if field == "total_outlays":
            assessment = "Weak" if mp >= 20 else "Medium"
        else:
            assessment = "Strong" if mp < 1 else "Medium"
        important_rows.append([f"`{field}`", pct(mp), assessment])

    enrichment_rows = []
    for field in [
        "description_clean",
        "text_all",
        "award_duration_days",
        "record_hash",
        "is_duplicate_row",
        "processed_at",
        "query_name",
        "run_id",
    ]:
        mp = get_missing_pct(missingness_df, field)
        if field in {"query_name", "run_id"} and mp >= 100:
            assessment = "Failed lineage"
        elif mp == 0:
            assessment = "Strong"
        elif mp < 1:
            assessment = "Strong"
        else:
            assessment = "Medium"
        enrichment_rows.append([f"`{field}`", pct(mp), assessment])

    high_reliability = summary_table.loc[
        summary_table["reliability"] == "high", "column_name"
    ].tolist()
    medium_reliability = summary_table.loc[
        summary_table["reliability"] == "medium", "column_name"
    ].tolist()
    low_reliability = summary_table.loc[
        summary_table["reliability"] == "low", "column_name"
    ].tolist()

    lineage_problem = (
        get_missing_pct(missingness_df, "run_id") >= 100
        or get_missing_pct(missingness_df, "query_name") >= 100
    )

    lineage_risk_section = ""
    lineage_recommendation = ""
    lineage_weakness = ""

    if lineage_problem:
        lineage_risk_section = """
### 2. Missing lineage fields
`run_id` and `query_name` are completely missing in the cleaned dataset.

**Risk:**  
This weakens traceability for monitoring, auditability, and future run-to-run comparisons.
"""
        lineage_recommendation = """
1. **Fix lineage extraction first.**  
   Update filename parsing or fallback metadata extraction so `run_id` and `query_name` populate in the cleaned table.
"""
        lineage_weakness = "\n- `run_id` and `query_name` failed completely"
    else:
        lineage_risk_section = """
### 2. Lineage fields are available
`run_id` and `query_name` are present in the cleaned schema, which supports run-level traceability and benchmark-source transparency.

**Implication:**  
This improves auditability and supports future monitoring pages that distinguish raw source populations by benchmark layer.
"""
        lineage_recommendation = """
1. **Preserve lineage fields as monitored metadata.**  
   Keep `run_id` and `query_name` in the cleaned dataset and surface them in monitoring workflows where useful.
"""

    markdown = f"""# Data Quality Report
## Applied Government Analytics (AGA) External Cost Benchmarking & Value Estimation
## Task 7: Data Quality Evaluation

---

## 1. Purpose

This report evaluates the quality of the processed USAspending benchmark dataset after the clean/transform stage and before downstream filtering, ML classification, benchmarking, and dashboard use.

This project is an external benchmarking and value-estimation system, not an internal cost accounting system. The purpose of this report is to assess whether the transformed public procurement data is sufficiently reliable for external cost benchmarking, agency comparison, variability analysis, and scenario-based value estimation.

---

## 2. Dataset Overview

### Source
Processed USAspending contract data generated from the current full ingestion run and transform outputs.

### Processing Summary
- Raw file count: **{raw_file_count:,}**
- Raw row count: **{raw_row_count:,}**
- Cleaned row count: **{cleaned_row_count:,}**
- Duplicate rows flagged: **{duplicates_flagged:,}**
- Duplicate rows removed: **{duplicates_removed:,}**
- Output dataset: `{processing_summary['output_dataset_path']}`
- Missingness summary: `{processing_summary['missingness_summary_path']}`

### Interpretation
The transform stage reduced the dataset from {raw_row_count:,} raw rows to {cleaned_row_count:,} cleaned rows by removing {duplicates_removed:,} duplicates. That means roughly **{removed_pct:.1f}% of raw rows were removed as duplicates**, leaving about **{retained_pct:.1f}% retained** for the cleaned analytical dataset.

This is not automatically a problem, because overlapping benchmark populations can legitimately produce large duplicate overlap. But it is important enough to monitor in both evaluation and app reporting.

---

## 3. Schema Coverage Summary

The cleaned dataset contains **{len(df.columns)} columns**.

### Highest-missingness fields
{chr(10).join(highest_missing_lines)}

### Fully populated fields
The following fields have **0.0000% missingness**:
{chr(10).join([f"- `{col}`" for col in fully_populated_list])}

---

## 4. Missingness Analysis by Field Category

## 4.1 Critical Fields
These fields are essential for primary benchmark calculations and baseline analytical usability.

{md_table(critical_rows, ["Field", "Missing %", "Assessment"])}

### Interpretation
The dataset is strong on the core fields needed for benchmark distributions, time-based analysis, and agency segmentation. Small missingness in `description` only affects a limited subset of rows.

---

## 4.2 Important Fields
These materially improve interpretability, segmentation, or downstream analytical quality.

{md_table(important_rows, ["Field", "Missing %", "Assessment"])}

### Interpretation
Most important support fields are highly usable, especially PSC and NAICS fields, which are central to comparable-contract logic. The major weakness remains `total_outlays` when its missingness is high enough to reduce reliability for headline KPI use.

---

## 4.3 Enrichment / Operational Fields
These support lineage, app monitoring, or downstream engineering workflows.

{md_table(enrichment_rows, ["Field", "Missing %", "Assessment"])}

### Interpretation
Operationally, the transform is producing most of the convenience fields the app and pipeline will need. These fields are valuable for monitoring, traceability, and derived analytics.

---

## 5. Usable Record Rate

### Definition
A record is considered **usable for primary benchmarking** if all of the following are present:
- `award_amount`
- `description`
- `start_date`

### Result
**{usable_count:,} usable records out of {cleaned_row_count:,} cleaned records**

Usable-record rate:

**{usable_rate:.4f}%**

### Interpretation
This is a strong result. The dataset is highly usable for the project’s primary benchmark story because nearly all cleaned records have the cost, text, and timing fields needed for contract-level analysis.

---

## 6. Field Reliability Assessment

## 6.1 High Reliability
{chr(10).join([f"- `{c}`" for c in sorted(high_reliability)])}

## 6.2 Medium Reliability
{chr(10).join([f"- `{c}`" for c in sorted(medium_reliability)])}

## 6.3 Low Reliability
{chr(10).join([f"- `{c}`" for c in sorted(low_reliability)])}

### Interpretation
A field is treated as weak when its missingness materially limits its intended analytical use. This is why `total_outlays` may be low-reliability even when other slightly incomplete fields remain usable.

---

## 7. Known Data Issues and Risks

## 7.1 Structural Data Issues

### 1. High missingness in `total_outlays`
More than half of cleaned records may be missing outlays, depending on the current run.

**Risk:**  
Any KPI or chart based on outlays can rest on a much smaller and potentially biased subset of the data. Headline benchmarking should continue to center on `award_amount`, not `total_outlays`.

{lineage_risk_section}

### 3. Modest text incompleteness
Where present, small missingness in `description` slightly reduces coverage for future keyword filtering, category mapping, and ML text feature generation.

**Risk:**  
This is usually not severe for benchmark distributions overall, but it should still be tracked.

---

## 7.2 Pipeline-Induced Risks

### 1. Very large duplicate reduction
The transform can remove a substantial share of raw rows as duplicates.

**Risk:**  
This is often expected because the pipeline ingests overlapping benchmark populations, but it should be transparent in evaluation and app monitoring so users do not misinterpret the row reduction as corruption or unexplained loss.

### 2. Overlap is a feature, but it changes interpretation
The benchmark architecture intentionally combines overlapping benchmark layers.

**Risk:**  
Users must understand that raw row totals are not unique contract counts.

### 3. Cleaning success does not equal final benchmark validity
The transform stage normalizes and deduplicates data, but downstream relevance filtering is still required before final benchmark conclusions are made.

---

## 8. Impact on Business Questions

## Q1. What does comparable government work typically cost?
**Support level: Moderate at this stage**

The cleaned dataset is strong for basic award-level analysis because `award_amount` is complete and the usable-record rate is high. However, this is still a pre-filter dataset, so it includes records that are not yet validated as AGA-like comparables.

## Q2. How much variability exists in comparable contract cost?
**Support level: Moderate at this stage**

The data quality is sufficient for variability analysis, but not yet for comparable-only variability. The main blocker is not missingness; it is scope refinement and relevance filtering.

## Q3. How do costs differ across agencies?
**Support level: Strong for raw agency comparison**

Agency fields are complete enough to support raw agency segmentation well. But comparisons intended to support the AGA narrative should eventually be based on filtered comparable subsets.

## Q4. What is the estimated equivalent market value under selected scenarios?
**Support level: Moderate, contingent on downstream comparable filtering**

The cleaned dataset provides a strong cost backbone, but the value-estimation layer should be built on benchmark-derived comparable distributions, not this raw cleaned population alone.

---

## 9. Recommendations

## 9.1 Data Improvements
{lineage_recommendation}
2. **Treat `total_outlays` as secondary.**  
   Keep it available, but do not use it for headline KPIs unless the app displays reduced sample size clearly.

3. **Proceed to comparable filtering before executive interpretation.**  
   This cleaned table is good enough for monitoring and pipeline QA, but not yet for final benchmark claims.

## 9.2 Pipeline Improvements
1. Add a post-transform validation check that warns or fails when:
   - `run_id` missingness = 100%
   - `query_name` missingness = 100%
   - duplicate removal exceeds a threshold you define for monitoring.

2. Add a run-level QA artifact for:
   - retained row rate
   - usable-record rate
   - low-reliability field count
   - duplicate rate

## 9.3 Dashboard Safeguards
For `app/pages/6_Data_Quality_Monitoring.py`, show:
- raw rows
- cleaned rows
- retained-row %
- duplicate removal %
- usable-record rate
- highest-missingness fields
- warnings for weak outlay coverage
- lineage status

This page should clearly distinguish:
- data quality status
- benchmark readiness status
- comparability readiness status

---

## 10. Final Assessment

### Overall Data Quality Status: **Good for monitoring and upstream benchmark preparation**
The cleaned dataset is strong enough for:
- pipeline QA
- field coverage monitoring
- agency segmentation
- award-based exploratory distributions
- downstream comparable-contract modeling preparation

### Main Strengths
- strong usable-record rate for primary benchmarking fields
- complete or near-complete coverage for key benchmark fields
- operational fields available for monitoring and traceability where present

### Main Weaknesses
- `total_outlays` can be too incomplete for headline use{lineage_weakness}
- cleaned data still requires downstream relevance filtering before final executive benchmark claims

### Decision
Proceed to the next stage, but:
1. keep outlays secondary,
2. continue comparable filtering,
3. do not present this cleaned table as the final comparable benchmark population.
"""
    return markdown


def generate_data_quality_report(
    dataset_path: Path = DEFAULT_DATASET_PATH,
    missingness_path: Path = DEFAULT_MISSINGNESS_PATH,
    processing_summary_path: Path = DEFAULT_PROCESSING_SUMMARY_PATH,
    report_path: Path = DEFAULT_REPORT_PATH,
    summary_csv_path: Path = DEFAULT_SUMMARY_CSV_PATH,
) -> dict[str, Path]:
    validate_settings()
    ensure_directories()

    report_path.parent.mkdir(parents=True, exist_ok=True)
    summary_csv_path.parent.mkdir(parents=True, exist_ok=True)

    df = pd.read_parquet(dataset_path)
    missingness_df = pd.read_csv(missingness_path)
    processing_summary = load_json(processing_summary_path)

    summary_table = build_summary_table(missingness_df)
    markdown = build_report_markdown(
        df=df,
        missingness_df=missingness_df,
        processing_summary=processing_summary,
        summary_table=summary_table,
    )

    with report_path.open("w", encoding="utf-8") as f:
        f.write(markdown)

    summary_table.to_csv(summary_csv_path, index=False)

    return {
        "report_path": report_path,
        "summary_csv_path": summary_csv_path,
    }


def main() -> None:
    outputs = generate_data_quality_report()
    print("Data quality report generated.")
    print(f"Markdown report: {outputs['report_path']}")
    print(f"Summary CSV: {outputs['summary_csv_path']}")


if __name__ == "__main__":
    main()
