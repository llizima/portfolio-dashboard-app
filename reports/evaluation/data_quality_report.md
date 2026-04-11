# Data Quality Report
## SOFWERX External Cost Benchmarking & Value Estimation
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
- Raw file count: **12**
- Raw row count: **95,553**
- Cleaned row count: **29,311**
- Duplicate rows flagged: **66,242**
- Duplicate rows removed: **66,242**
- Output dataset: `C:\Users\laliz\Desktop\Internship\SOFWERX\Sofwerx_Value_Dashboard\src\data\processed\usaspending_contracts_cleaned.parquet`
- Missingness summary: `C:\Users\laliz\Desktop\Internship\SOFWERX\Sofwerx_Value_Dashboard\src\data\processed\usaspending_contracts_cleaned_missingness.csv`

### Interpretation
The transform stage reduced the dataset from 95,553 raw rows to 29,311 cleaned rows by removing 66,242 duplicates. That means roughly **69.3% of raw rows were removed as duplicates**, leaving about **30.7% retained** for the cleaned analytical dataset.

This is not automatically a problem, because overlapping benchmark populations can legitimately produce large duplicate overlap. But it is important enough to monitor in both evaluation and app reporting.

---

## 3. Schema Coverage Summary

The cleaned dataset contains **33 columns**.

### Highest-missingness fields
- `total_outlays` → **53.4441%** (15,665 missing)
- `description` → **0.5936%** (174 missing)
- `description_clean` → **0.5936%** (174 missing)
- `naics_code` → **0.2456%** (72 missing)
- `naics_description` → **0.2456%** (72 missing)
- `agency_slug` → **0.0205%** (6 missing)
- `awarding_agency_id` → **0.0205%** (6 missing)
- `award_amount` → **0.0000%** (0 missing)
- `award_duration_days` → **0.0000%** (0 missing)
- `award_id` → **0.0000%** (0 missing)

### Fully populated fields
The following fields have **0.0000% missingness**:
- `award_amount`
- `award_duration_days`
- `award_id`
- `awarding_agency`
- `awarding_agency_code`
- `awarding_sub_agency`
- `base_obligation_date`
- `contract_award_type`
- `end_date`
- `fiscal_year`
- `funding_agency`
- `funding_sub_agency`
- `generated_internal_id`
- `internal_id`
- `is_duplicate_row`
- `processed_at`
- `psc_code`
- `psc_description`
- `query_name`
- `recipient_name`
- `recipient_uei`
- `record_hash`
- `run_id`
- `source_file`
- `start_date`
- `text_all`

---

## 4. Missingness Analysis by Field Category

## 4.1 Critical Fields
These fields are essential for primary benchmark calculations and baseline analytical usability.

| Field | Missing % | Assessment |
| --- | --- | --- |
| `award_amount` | 0.0000% | Excellent |
| `description` | 0.5936% | Strong |
| `start_date` | 0.0000% | Excellent |
| `end_date` | 0.0000% | Excellent |
| `awarding_agency` | 0.0000% | Excellent |

### Interpretation
The dataset is strong on the core fields needed for benchmark distributions, time-based analysis, and agency segmentation. Small missingness in `description` only affects a limited subset of rows.

---

## 4.2 Important Fields
These materially improve interpretability, segmentation, or downstream analytical quality.

| Field | Missing % | Assessment |
| --- | --- | --- |
| `total_outlays` | 53.4441% | Weak |
| `recipient_name` | 0.0000% | Strong |
| `psc_code` | 0.0000% | Strong |
| `psc_description` | 0.0000% | Strong |
| `naics_code` | 0.2456% | Strong |
| `naics_description` | 0.2456% | Strong |

### Interpretation
Most important support fields are highly usable, especially PSC and NAICS fields, which are central to comparable-contract logic. The major weakness remains `total_outlays` when its missingness is high enough to reduce reliability for headline KPI use.

---

## 4.3 Enrichment / Operational Fields
These support lineage, app monitoring, or downstream engineering workflows.

| Field | Missing % | Assessment |
| --- | --- | --- |
| `description_clean` | 0.5936% | Strong |
| `text_all` | 0.0000% | Strong |
| `award_duration_days` | 0.0000% | Strong |
| `record_hash` | 0.0000% | Strong |
| `is_duplicate_row` | 0.0000% | Strong |
| `processed_at` | 0.0000% | Strong |
| `query_name` | 0.0000% | Strong |
| `run_id` | 0.0000% | Strong |

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
**29,137 usable records out of 29,311 cleaned records**

Usable-record rate:

**99.4064%**

### Interpretation
This is a strong result. The dataset is highly usable for the project’s primary benchmark story because nearly all cleaned records have the cost, text, and timing fields needed for contract-level analysis.

---

## 6. Field Reliability Assessment

## 6.1 High Reliability
- `agency_slug`
- `award_amount`
- `award_duration_days`
- `award_id`
- `awarding_agency`
- `awarding_agency_code`
- `awarding_agency_id`
- `awarding_sub_agency`
- `base_obligation_date`
- `contract_award_type`
- `end_date`
- `fiscal_year`
- `funding_agency`
- `funding_sub_agency`
- `generated_internal_id`
- `internal_id`
- `is_duplicate_row`
- `naics_code`
- `naics_description`
- `processed_at`
- `psc_code`
- `psc_description`
- `query_name`
- `recipient_name`
- `recipient_uei`
- `record_hash`
- `run_id`
- `source_file`
- `start_date`
- `text_all`

## 6.2 Medium Reliability
- `description`
- `description_clean`

## 6.3 Low Reliability
- `total_outlays`

### Interpretation
A field is treated as weak when its missingness materially limits its intended analytical use. This is why `total_outlays` may be low-reliability even when other slightly incomplete fields remain usable.

---

## 7. Known Data Issues and Risks

## 7.1 Structural Data Issues

### 1. High missingness in `total_outlays`
More than half of cleaned records may be missing outlays, depending on the current run.

**Risk:**  
Any KPI or chart based on outlays can rest on a much smaller and potentially biased subset of the data. Headline benchmarking should continue to center on `award_amount`, not `total_outlays`.


### 2. Lineage fields are available
`run_id` and `query_name` are present in the cleaned schema, which supports run-level traceability and benchmark-source transparency.

**Implication:**  
This improves auditability and supports future monitoring pages that distinguish raw source populations by benchmark layer.


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

The cleaned dataset is strong for basic award-level analysis because `award_amount` is complete and the usable-record rate is high. However, this is still a pre-filter dataset, so it includes records that are not yet validated as SOFWERX-like comparables.

## Q2. How much variability exists in comparable contract cost?
**Support level: Moderate at this stage**

The data quality is sufficient for variability analysis, but not yet for comparable-only variability. The main blocker is not missingness; it is scope refinement and relevance filtering.

## Q3. How do costs differ across agencies?
**Support level: Strong for raw agency comparison**

Agency fields are complete enough to support raw agency segmentation well. But comparisons intended to support the SOFWERX narrative should eventually be based on filtered comparable subsets.

## Q4. What is the estimated equivalent market value under selected scenarios?
**Support level: Moderate, contingent on downstream comparable filtering**

The cleaned dataset provides a strong cost backbone, but the value-estimation layer should be built on benchmark-derived comparable distributions, not this raw cleaned population alone.

---

## 9. Recommendations

## 9.1 Data Improvements

1. **Preserve lineage fields as monitored metadata.**  
   Keep `run_id` and `query_name` in the cleaned dataset and surface them in monitoring workflows where useful.

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
- `total_outlays` can be too incomplete for headline use
- cleaned data still requires downstream relevance filtering before final executive benchmark claims

### Decision
Proceed to the next stage, but:
1. keep outlays secondary,
2. continue comparable filtering,
3. do not present this cleaned table as the final comparable benchmark population.
