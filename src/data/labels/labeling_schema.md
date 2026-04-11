# Comparable Contract Labeling Schema
## SOFWERX Value Dashboard

---

## 1. Purpose

This document defines the labeling schema for the future machine learning relevance model used in the SOFWERX Value Dashboard project.

The purpose of this schema is to support **consistent human labeling** of USAspending contract records so that future supervised ML work is trained on clear, reviewable, and defensible labels.

This labeling system is designed to answer one primary question:

> Is this contract record meaningfully relevant as a comparable external contract for SOFWERX-like services?

This schema is part of the project’s **external benchmark comparability** workflow. It does **not** support internal cost accounting, audited savings claims, ROI calculation, or internal efficiency measurement.

---

## 2. Core Labeling Principle

The core ML target is **relevance**, not service category.

Reviewers must answer relevance first.

Only after relevance is determined should the reviewer optionally assign a service category.

These are two separate decisions:

1. **Relevance label** = whether the record belongs in the comparable-contract benchmark problem
2. **Category label (optional)** = what type of SOFWERX-like service the relevant record most closely represents

These must not be merged into one label.

---

## 3. Primary Target Label

### Field Name
`relevance_label`

### Allowed Values
- `relevant`
- `not_relevant`
- `ambiguous`

These values should be used exactly as written.

---

## 4. Relevance Label Definitions

### 4.1 `relevant`

Assign `relevant` when the contract record appears meaningfully comparable to SOFWERX-like external work for benchmarking purposes.

A record should be labeled `relevant` when the available evidence suggests that the contract is primarily about one or more service types aligned with the project taxonomy, such as:

- prototyping
- engineering/design support
- event hosting
- workspace/collaboration support
- innovation ecosystem access
- project/program support that is genuinely aligned to the benchmark scope
- integrated service delivery spanning multiple aligned categories

A record does **not** need to be a perfect SOFWERX match to be `relevant`.

It should be labeled `relevant` when a reasonable reviewer would say:

> “Yes, this looks like the kind of externally contracted work that belongs in the benchmark comparison universe.”

---

### 4.2 `not_relevant`

Assign `not_relevant` when the contract record is not meaningfully comparable to SOFWERX-like external work for benchmark purposes.

A record should be labeled `not_relevant` when:

- the work is clearly outside the benchmark scope
- the text reflects unrelated procurement activity
- the record reflects commodity purchasing rather than comparable service delivery
- the language is broad but not actually aligned to the project taxonomy
- the apparent work is dominated by unrelated sustainment, operations, or administrative activity
- the evidence is sufficient to say it does not belong in the comparable-contract benchmark set

Use `not_relevant` even if the record contains one or two overlapping keywords, as long as the record as a whole is not meaningfully comparable.

---

### 4.3 `ambiguous`

Assign `ambiguous` when the available evidence is too mixed, weak, incomplete, or conflicting to support a confident `relevant` or `not_relevant` decision.

A record should be labeled `ambiguous` when:

- the description is too vague to determine the actual work
- the record contains mixed signals pointing in different directions
- broad PSC/NAICS or keyword evidence exists but the description is weak
- the contract may be relevant at a high level but appears too broad, too large-scale, or too mixed for a confident benchmark inclusion decision
- the reviewer would need more context to make a stable call

`ambiguous` is a valid and expected label.

Reviewers should **not** force borderline records into binary labels when the evidence does not justify it.

---

## 5. Positive Example Patterns (`relevant`)

The following are examples of patterns that often support a `relevant` label.

These are examples, not automatic rules.

### 5.1 Prototyping
Examples:
- rapid prototyping of defense-related systems
- fabrication of demonstrators or test articles
- build and integration of prototype units
- proof-of-concept hardware or software prototype work

### 5.2 Engineering / Design Support
Examples:
- systems engineering support
- modeling and simulation
- CAD-based design work
- engineering trade studies
- architecture design
- technical feasibility analysis
- requirements development tied to technical solution design

### 5.3 Event Hosting
Examples:
- execution of innovation challenge events
- workshop or hackathon operations
- conference or symposium logistics where the event itself is the core deliverable
- demo day or industry day support

### 5.4 Workspace / Collaboration
Examples:
- collaborative lab environment access
- innovation facility access
- makerspace or experimentation environment support
- provision of secure or shared collaboration environments

### 5.5 Innovation Ecosystem Access
Examples:
- startup scouting
- curated vendor access
- technology scouting pipelines
- non-traditional partner network access
- accelerator or innovation-network access

### 5.6 Project / Program Support
Examples:
- project coordination, reporting, or scheduling support that is clearly tied to benchmark-relevant technical/service delivery
- program support contracts that are genuinely aligned with SOFWERX-like external service structures rather than generic admin support

### 5.7 Integrated Service Delivery
Examples:
- records that combine clearly relevant services across more than one category
- contracts that bundle prototyping, engineering, and event-related delivery in a way that still fits the benchmark scope

---

## 6. Negative Example Patterns (`not_relevant`)

The following are examples of patterns that often support a `not_relevant` label.

These are examples, not automatic rules.

Examples:
- commodity equipment purchasing with no comparable service delivery
- generic office support
- broad administrative staffing with no meaningful benchmark relevance
- unrelated sustainment-heavy work
- generic management consulting not aligned to SOFWERX-like services
- custodial, routine facilities maintenance, or unrelated operational support
- unrelated construction or procurement activity
- records whose only relevance comes from a single broad keyword such as “support,” “engineering,” or “development” without meaningful contextual alignment

A record should not be labeled `relevant` just because one term overlaps with the taxonomy.

---

## 7. Ambiguous / Review-Needed Example Patterns

The following are common `ambiguous` situations:

- “technical support” with no clear deliverable
- “engineering services” with no indication whether the work is design, program support, sustainment, or prototype-related
- records that match broad PSC/NAICS hints but provide weak description evidence
- mixed contracts combining technical, administrative, and operational work with no clear dominant benchmark-relevant function
- records that seem directionally relevant but may be too program-scale or too broad for fair comparability
- contracts whose description appears truncated or incomplete

Use `ambiguous` when the reviewer’s honest conclusion is:

> “I can see why this might belong, but the evidence is not stable enough for a confident yes/no decision.”

---

## 8. Optional Secondary Label: Service Category

### Field Name
`category_label_optional`

This field is **secondary** and should only be assigned **after** relevance is determined.

This field is optional because the primary ML task is relevance classification.

### Rule
- If `relevance_label = not_relevant`, leave `category_label_optional` blank.
- If `relevance_label = ambiguous`, category may be left blank unless the reviewer has a strong tentative view and project policy later allows that.
- If `relevance_label = relevant`, assign the best-fit dominant category when possible.

### Allowed Category Values

Use existing taxonomy-aligned values only:

- `prototyping`
- `engineering_design_support`
- `project_program_support`
- `event_hosting`
- `workspace_collaboration`
- `innovation_ecosystem_access`
- `integrated_service_delivery`

Do not invent new category names in the labeling file.

---

## 9. Required Human Review Columns

The labeling template should support the following fields.

### Core record context
- `record_id`
- `award_id`
- `description`
- `psc_code`
- `naics_code`

### Baseline-rule context
- `baseline_include_flag`
- `baseline_primary_category`
- `baseline_reason_codes`
- `matched_keywords`

### Human labeling outputs
- `relevance_label`
- `category_label_optional`
- `ambiguity_flag`
- `confidence_level`
- `second_review_needed`

### Review tracking / QA
- `reviewer_id`
- `review_date`
- `reviewer_notes`

---

## 10. Field-Level Meaning

### `record_id`
Stable internal record identifier used for row-level traceability.

### `award_id`
Award identifier from the source procurement record.

### `description`
Contract description or other main review text used by the reviewer.

### `psc_code`
Product Service Code supplied with the record.

### `naics_code`
NAICS code supplied with the record.

### `baseline_include_flag`
Indicates whether the rule-based baseline filter included the record.

This field is context only. It does **not** determine the final human label automatically.

### `baseline_primary_category`
Best taxonomy category assigned by the baseline filter.

This is supporting evidence only.

### `baseline_reason_codes`
Machine-friendly reason codes showing which baseline rules fired.

### `matched_keywords`
Keywords matched by the baseline logic.

### `relevance_label`
Primary supervised learning target label.

### `category_label_optional`
Optional secondary category label for relevant records.

### `ambiguity_flag`
Boolean-style indicator showing whether the record had meaningful ambiguity during review.

This can be useful even when the final label is `relevant` or `not_relevant`, if local policy wants to preserve reviewer uncertainty. At minimum, it should be set for `ambiguous` rows.

### `confidence_level`
Reviewer confidence in the assigned relevance decision.

Suggested values:
- `high`
- `medium`
- `low`

### `second_review_needed`
Flag indicating whether the record should be reviewed by another person.

Suggested values:
- `true`
- `false`

### `reviewer_id`
Identifier for the reviewer.

### `review_date`
Date the record was reviewed.

### `reviewer_notes`
Free-text notes explaining borderline decisions, uncertainty, or reasoning.

Notes should remain benchmark-focused and must avoid unsupported savings or ROI language.

---

## 11. Labeling Decision Rules

Reviewers should follow these rules in order.

### Rule 1: Decide relevance first
Always assign `relevance_label` before thinking about category.

### Rule 2: Do not force a category onto non-relevant rows
If `relevance_label = not_relevant`, leave `category_label_optional` blank.

### Rule 3: Use `ambiguous` when evidence is unstable
If the record cannot be confidently assigned to `relevant` or `not_relevant`, use `ambiguous`.

### Rule 4: One vague keyword is not enough
Do not assign `relevant` just because one broad term appears in the record.

### Rule 5: Baseline fields are evidence, not truth
The baseline filter is useful context, but the human label is the final adjudication for the training set.

### Rule 6: Judge the record as a whole
Use the overall contract meaning, not isolated fragments.

### Rule 7: Category is optional and secondary
Only assign category when the relevance judgment is already stable.

---

## 12. Common Labeling Failure Modes

The following errors should be actively avoided:

- mixing relevance labeling with category labeling
- labeling based on one keyword alone
- assuming baseline inclusion means automatic relevance
- forcing binary labels when the record is truly borderline
- assigning categories to clearly non-relevant records
- creating new ad hoc category names during review
- using reviewer notes to make unsupported project claims about savings, ROI, or internal efficiency

---

## 13. Quality Standard

This labeling schema is successful only if it supports **consistent reviewer behavior**.

A practical validation test is:

> If two reviewers independently label a sample of 10 to 20 records using this schema, they should usually reach the same relevance decision or be able to explain disagreements in a narrow, structured way.

That is the standard this schema is intended to support.
