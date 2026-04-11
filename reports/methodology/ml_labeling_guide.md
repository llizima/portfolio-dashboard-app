# ML Labeling Guide
## Comparable Contract Relevance Review Guide for the SOFWERX Value Dashboard

---

## 1. Why This Guide Exists

This guide explains how to label comparable-contract records consistently for the future machine learning relevance model.

The model will only be as good as the training labels used to create it.

If reviewers label records inconsistently, the ML system will learn unstable patterns such as:

- treating vague language as strong evidence
- over-weighting broad keywords
- confusing category with relevance
- learning reviewer inconsistency instead of real benchmark comparability

The goal of this guide is to help reviewers make decisions that are:

- consistent
- explainable
- benchmark-focused
- aligned to project scope
- suitable for future QA and model evaluation

This guide supports the project’s benchmark methodology. It does **not** support internal savings analysis, ROI proof, or internal cost accounting.

---

## 2. What the Reviewer Is Deciding

The reviewer is making one primary decision:

> Is this record meaningfully relevant as a comparable external contract for SOFWERX-like services?

This is the **relevance decision**.

Only after that decision is made should the reviewer optionally assign a service category.

These are separate decisions:

- **Primary:** `relevance_label`
- **Secondary:** `category_label_optional`

Do not merge them.

---

## 3. Core Label Set

Use only these relevance labels:

- `relevant`
- `not_relevant`
- `ambiguous`

Use them exactly as written.

---

## 4. Step-by-Step Review Workflow

Use this workflow for each record.

### Step 1: Read the description carefully
Start with the contract description.

Ask:
- What is the contract mainly about?
- What appears to be the core deliverable?
- Does the text describe comparable service delivery, or something else?

Do not make a decision from one keyword alone.

---

### Step 2: Review PSC and NAICS context
Inspect the `psc_code` and `naics_code`.

Ask:
- Do these codes support the idea that the contract belongs in the benchmark universe?
- Are they specific and helpful, or broad and weak?

PSC/NAICS evidence is helpful but not decisive by itself.

---

### Step 3: Review baseline evidence fields
Inspect:
- `baseline_include_flag`
- `baseline_primary_category`
- `baseline_reason_codes`
- `matched_keywords`

Ask:
- Why did the baseline logic think this record might belong?
- Does that evidence still look convincing after reading the full row?

Important:
Baseline evidence is context, not final truth.

---

### Step 4: Decide relevance first
Before assigning any category, decide whether the record is:

- `relevant`
- `not_relevant`
- `ambiguous`

This is the most important step.

---

### Step 5: Assign optional category only if appropriate
If the record is clearly `relevant`, assign the best-fit dominant category when possible.

If the record is `not_relevant`, leave category blank.

If the record is `ambiguous`, category should usually remain blank unless later project policy explicitly allows tentative category tagging.

---

### Step 6: Mark ambiguity and confidence
Use:
- `ambiguity_flag`
- `confidence_level`
- `second_review_needed`

These fields help preserve uncertainty rather than hiding it.

---

### Step 7: Leave reviewer notes for difficult cases
Use `reviewer_notes` to explain:
- why a case was borderline
- why baseline evidence was overruled
- what made the decision uncertain
- why second review may be needed

Notes should stay factual and benchmark-focused.

Do not use notes to make unsupported claims about savings, ROI, or internal SOFWERX efficiency.

---

## 5. How to Decide `relevant`

Assign `relevant` when the record appears meaningfully comparable to SOFWERX-like externally contracted work.

A useful test is:

> Would a reasonable reviewer say this belongs in the benchmark comparison universe for SOFWERX-like services?

Examples of evidence that often support `relevant`:

- prototype fabrication, demonstrators, proof-of-concept builds
- systems engineering, technical design, modeling, or simulation
- workshops, challenge events, demo days, or conference/event execution
- collaborative environment or workspace provision
- startup scouting, innovation network access, curated vendor ecosystem access
- project/program support that is clearly tied to benchmark-relevant service delivery
- integrated contracts that combine multiple relevant services

Remember:
`relevant` does not mean “identical to SOFWERX.”

It means “close enough in type of externally contracted work to belong in the benchmark set.”

---

## 6. How to Decide `not_relevant`

Assign `not_relevant` when the contract is not meaningfully comparable to SOFWERX-like external work.

Examples that often support `not_relevant`:

- commodity procurement
- generic office support
- broad management consulting with no meaningful benchmark alignment
- unrelated sustainment or operational support
- unrelated construction or maintenance activity
- records where the only overlap is a broad word like “support,” “engineering,” or “development”

A record should be `not_relevant` when the overall contract meaning falls outside the benchmark scope, even if one or two signals look superficially related.

---

## 7. How to Decide `ambiguous`

Assign `ambiguous` when the evidence is too mixed or incomplete for a confident yes/no decision.

Use `ambiguous` when:

- the description is vague
- the work type is unclear
- the record contains mixed relevant and non-relevant signals
- PSC/NAICS evidence looks broad rather than targeted
- the record feels directionally relevant but not stable enough for confident inclusion
- the contract may be too broad, too mixed, or too program-scale for a clean decision

A useful test is:

> If another careful reviewer could reasonably go the other way using the same evidence, the row may be ambiguous.

Do not force binary labels just to make the dataset look cleaner.

A smaller, cleaner labeled set is better than a larger but noisier one.

---

## 8. Category Assignment Guidance

Category is secondary.

Only assign category after relevance is already clear.

Use the existing taxonomy-aligned values:

- `prototyping`
- `engineering_design_support`
- `project_program_support`
- `event_hosting`
- `workspace_collaboration`
- `innovation_ecosystem_access`
- `integrated_service_delivery`

Do not invent new category names.

---

## 9. Important Category Distinctions

These distinctions matter because they affect later benchmark segmentation and ML consistency.

### 9.1 Prototyping vs Engineering Design Support

Use `prototyping` when the core output is a built, fabricated, assembled, or demonstrable artifact.

Use `engineering_design_support` when the core output is design, modeling, simulation, systems engineering, technical analysis, architecture, or feasibility work rather than artifact creation.

Quick test:
- built thing → `prototyping`
- designed/analyzed thing → `engineering_design_support`

---

### 9.2 Event Hosting vs Innovation Ecosystem Access

Use `event_hosting` when the primary deliverable is the event itself.

Use `innovation_ecosystem_access` when the primary value is access to startups, vendors, non-traditional partners, scouting pipelines, or curated innovation relationships.

Quick test:
- event execution → `event_hosting`
- network access / discovery / partner pipeline → `innovation_ecosystem_access`

---

### 9.3 Workspace Collaboration vs Service Delivery

Use `workspace_collaboration` when the primary value is access to a space, environment, lab, or collaboration setting.

Do not use it just because relevant work happens inside a facility.

Quick test:
- environment itself is the deliverable → `workspace_collaboration`
- service performed in the environment → likely another category

---

### 9.4 Project Program Support vs Technical Work

Use `project_program_support` when the core value is coordination, scheduling, logistics, governance, reporting, or administrative support.

Do not use it as a fallback for vaguely technical work.

Quick test:
- coordination/oversight/reporting → `project_program_support`
- technical design/build/analysis/event/network work → likely another category

---

### 9.5 Integrated Service Delivery

Use `integrated_service_delivery` when a record is clearly relevant and genuinely combines multiple aligned service types such that forcing one dominant category would reduce accuracy.

Use this category sparingly.

It should not become a catch-all for uncertainty.

If the issue is uncertainty rather than genuine multi-service integration, use `ambiguous` instead of defaulting to this category.

---

## 10. How to Use Baseline Fields Correctly

Baseline fields provide useful context, but they are not the final answer.

### Helpful uses
Baseline fields can help a reviewer:
- see which taxonomy signals matched
- understand why a row was included or reviewed upstream
- identify possible candidate categories
- spot where rule-based logic may have over-included broad records

### Incorrect uses
Do not:
- auto-label `relevant` because `baseline_include_flag = true`
- auto-label by copying `baseline_primary_category`
- assume matched keywords are strong evidence without reading the row context
- treat rule outputs as superior to careful human review

The purpose of this labeling stage is to produce cleaner supervised labels than the baseline filter alone.

---

## 11. Confidence, Ambiguity, and Second Review

These fields should be used intentionally.

### `confidence_level`
Suggested values:
- `high`
- `medium`
- `low`

Use lower confidence when:
- the description is vague
- evidence conflicts
- the decision required judgment rather than direct evidence

### `ambiguity_flag`
Use this to preserve reviewer uncertainty.

At minimum, it should be marked for rows labeled `ambiguous`.

Depending on workflow, it may also be useful for low-confidence borderline rows that still received a final binary label.

### `second_review_needed`
Mark `true` when:
- the case is close
- evidence is conflicting
- the reviewer suspects another reasonable reviewer may disagree
- the decision could materially affect later dataset quality

---

## 12. Common Reviewer Mistakes

Avoid the following:

### Mistake 1: Confusing relevance with category
A record can be relevant even if the exact category is hard to determine.

### Mistake 2: Labeling from one keyword
One word like “support,” “engineering,” or “innovation” is not enough.

### Mistake 3: Treating baseline inclusion as final truth
Baseline logic is evidence, not final adjudication.

### Mistake 4: Forcing a binary answer when the case is borderline
Use `ambiguous` when the evidence is unstable.

### Mistake 5: Assigning category to non-relevant rows
Leave category blank for `not_relevant`.

### Mistake 6: Using `integrated_service_delivery` as a fallback for uncertainty
That category is for true multi-service relevance, not indecision.

### Mistake 7: Writing unsupported claims in notes
Do not use reviewer notes to claim:
- savings achieved
- ROI delivered
- proven efficiency gains
- verified cost avoidance

This project is benchmark-focused, not an internal financial audit.

---

## 13. Recommended Reviewer Mindset

A good reviewer should aim to be:

- careful, not aggressive
- consistent, not clever
- benchmark-focused, not speculative
- willing to use `ambiguous` when needed
- disciplined about separating evidence from assumptions

The goal is not to maximize the number of relevant rows.

The goal is to create a training set that is stable, defensible, and useful for future model evaluation.

---

## 14. Suggested QA Check

A simple quality check for this labeling framework is:

1. sample 10 to 20 records
2. have a second reviewer label them independently
3. compare:
   - relevance agreement
   - ambiguity usage
   - category agreement for relevant rows
4. review disagreements and refine instructions only if disagreement patterns are systematic

A useful labeling guide should reduce disagreement to a manageable set of understandable edge cases.

---

## 15. Final Reviewer Reminder

When in doubt:

- decide relevance first
- use the whole record, not isolated words
- use `ambiguous` when the evidence is not stable
- assign category only when relevance is already clear
- leave notes that help another reviewer understand your reasoning
