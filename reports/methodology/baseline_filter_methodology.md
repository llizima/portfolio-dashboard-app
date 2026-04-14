# Baseline Filter Methodology
## Applied Government Analytics (AGA) Value Dashboard

---

## 1. Purpose

The baseline filter is the project’s first transparent comparable-contract benchmark screen before machine learning classification.

Its purpose is to create a benchmark-derived subset of USAspending contract records that are plausibly relevant to AGA-like work using simple, reviewable rules. This gives the project an explainable non-ML benchmark layer that can be inspected directly, challenged by reviewers, and compared later against ML-based classification results.

This stage is designed to support external benchmarking, not internal cost accounting, audited savings claims, or ROI certification.

---

## 2. Inputs Used

The baseline filter uses the following inputs from the cleaned transformed dataset:

- `psc_code`
- `naics_code`
- `description`
- `description_clean`
- `text_all`
- taxonomy category keywords
- taxonomy PSC hints
- taxonomy NAICS hints

`text_all` is especially useful because it combines contract description text with PSC and NAICS descriptions, allowing one transparent text field to capture most of the baseline matching context.

---

## 3. Rule Logic Summary

The baseline filter uses a deterministic, taxonomy-driven rule library.

### 3.1 Code Signals
A row receives evidence when its:

- `psc_code` matches a category PSC hint
- `naics_code` matches a category NAICS hint

These signals are treated as structured evidence.

### 3.2 Keyword Signals
A row also receives evidence when taxonomy keywords appear in:

- `description_clean`
- `text_all`

The matching logic is intentionally simple and inspectable. It uses normalized phrase matching rather than opaque semantic inference.

### 3.3 Combined Evidence
Rows are scored based on the combination of:

- PSC evidence
- NAICS evidence
- keyword evidence

Rows with multiple signal types receive a modest bonus because combined evidence is generally more credible than a single isolated signal.

### 3.4 Conservative Handling of Broad Signals
Some signals are useful but broad. For example:

- broad PSC categories
- low-specificity keywords such as generic “support” language

These may contribute evidence, but they are not allowed to dominate the filter on their own.

### 3.5 Inclusion and Review Logic
The module produces three practical outcomes:

- **include** → sufficiently strong baseline evidence
- **review** → some relevance evidence, but weaker or more ambiguous
- **exclude** → no meaningful baseline evidence

This supports both strict benchmark construction and later analyst review of borderline records.

---

## 4. Reason Columns / Explainability

The baseline filter adds explainability columns so each row can be audited.

### `baseline_include`
Boolean flag indicating whether the row passed the baseline rule screen.

### `baseline_rule_score`
Numeric score summarizing the strength of transparent rule evidence.

### `baseline_reason_codes`
Pipe-delimited machine-friendly codes showing which rule types fired.

Examples:
- `PSC_MATCH`
- `NAICS_MATCH`
- `KEYWORD_MATCH`
- `MULTI_SIGNAL`
- `BASELINE_INCLUDE`
- `BASELINE_REVIEW`

### `baseline_reason_text`
Short human-readable explanation describing why the row was included, reviewed, or excluded.

### `matched_keywords`
Keywords matched from the taxonomy.

### `matched_psc_codes`
Matched PSC signals.

### `matched_naics_codes`
Matched NAICS signals.

### `baseline_primary_category`
The strongest matching taxonomy category for the row.

### `baseline_review_flag`
Boolean flag identifying borderline rows that may deserve analyst review.

### `baseline_matched_categories`
All taxonomy categories with positive evidence for the row.

These fields make the baseline filter easy to inspect in notebooks, evaluation reports, and later dashboard QA workflows.

---

## 5. Strengths

This baseline filter has several advantages:

- transparent
- reproducible
- easy to inspect
- easy to explain to leadership
- easy to compare against later ML outputs
- aligned to the project taxonomy
- grounded in both structured codes and contract text

Because every inclusion is traceable to explicit rule evidence, this stage provides a defensible benchmark baseline.

---

## 6. Limitations

This baseline filter is intentionally simple, so it has important limitations.

### 6.1 It may miss relevant contracts
Some truly comparable contracts may not contain the expected codes or keywords.

### 6.2 It may include some broad contracts
Some contracts may look relevant because of general engineering or support language even when they are not strong AGA-like comparables.

### 6.3 It is not the final comparable set
This baseline is an early benchmark screen, not the project’s final classification authority.

### 6.4 It does not prove savings
The filter supports benchmark construction and estimated equivalent market value workflows. It does not prove internal savings, audited ROI, or measured efficiency gains.

---

## 7. Relationship to the ML Stage

The baseline filter and the ML stage serve different purposes.

### Baseline Filter
- transparent benchmark screen
- deterministic
- easy to audit
- useful for benchmarking and evaluation baselines

### ML Stage
- later refinement / classification comparison
- may recover semantically relevant records missed by simple rules
- may improve precision / recall relative to baseline rules

The evaluation workflow should compare the baseline rule subset and the ML-based subset rather than treating them as interchangeable without testing.

---

## 8. Recommended Interpretation

Leadership-facing outputs should describe this stage using language such as:

- baseline comparable-contract screen
- transparent rule-based benchmark filter
- benchmark-derived subset
- comparable contract distribution

Avoid language that implies:

- audited savings
- proven cost reduction
- delivered ROI
- measured internal efficiency gains

---

## 9. Practical Use in the Pipeline

This stage should run after the clean/transform pipeline and before:

- final comparable-dataset construction
- KPI benchmarking
- value scenario calculations
- model evaluation comparisons

This keeps the project sequence defensible:

1. ingest raw benchmark data
2. clean and normalize it
3. apply transparent baseline rules
4. compare / refine with ML
5. benchmark costs and estimate external value under selected scenarios
