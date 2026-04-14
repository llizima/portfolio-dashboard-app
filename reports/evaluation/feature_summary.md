# Feature Engineering Summary
## Applied Government Analytics (AGA) Comparable-Contract Relevance Model

---

## 1. Purpose

This document summarizes the feature engineering module built for the Applied Government Analytics (AGA) Comparable-Contract relevance model.

The purpose of the module is to convert labeled contract records into reproducible model-ready inputs for later supervised learning experiments.

At this stage, the system is focused on **feature construction only**.

It does **not**:
- train a model
- report model performance
- claim benchmark superiority
- produce final classification decisions

The feature module is intended to support clean baseline experimentation for relevance classification.

---

## 2. Input Data Assumptions

The module expects labeled comparable-contract records stored in the labels layer, with key fields such as:

- `record_id`
- `description`
- `psc_code`
- `naics_code`
- `relevance_label`

The primary supervised target is the contract-level relevance label:

- `relevant`
- `not_relevant`
- `ambiguous`

For baseline binary experiments, ambiguous rows are excluded by default unless explicitly requested.

---

## 3. Feature Families Implemented

The initial feature pipeline supports both text and structured feature families.

### 3.1 Text Features

Text features are built from the contract description field using TF-IDF vectorization.

Current baseline implementation:
- source field: `description`
- vectorization method: `TfidfVectorizer`
- default support for unigram and bigram features
- deterministic vocabulary construction based on the provided training data

This supports baseline text-only relevance experiments.

---

### 3.2 Structured Features

Structured features are built using explicit, inspectable feature logic.

Current baseline structured features include:

- PSC code indicators
- NAICS code indicators
- description character length
- description word count
- missingness indicators for PSC/NAICS
- keyword-hit indicators for benchmark-relevant concept groups

Keyword groups currently cover:
- prototyping-related language
- engineering/design language
- event-related language
- workspace/collaboration language
- innovation ecosystem language
- project/program support language

These features are intentionally simple, transparent, and easy to audit.

---

## 4. Experiment Modes Supported

The feature module supports three experiment modes.

### 4.1 Text-Only Mode

Uses only TF-IDF text features from the description field.

Intended use:
- baseline NLP experiments
- comparison against structured-only models

---

### 4.2 Structured-Only Mode

Uses only structured metadata and explicit keyword/length features.

Intended use:
- transparent baseline models
- comparison against text-only models
- interpretability-oriented experiments

---

### 4.3 Hybrid Mode

Combines text and structured features into one sparse modeling matrix.

Intended use:
- stronger baseline experiments
- comparison of combined evidence vs single-family evidence
- future supervised training workflows

---

## 5. Leakage Controls

The feature module deliberately excludes obvious human-review and downstream label fields from predictive inputs.

Examples of excluded fields:
- `relevance_label`
- `category_label_optional`
- `reviewer_notes`
- `confidence_level`
- `second_review_needed`
- `ambiguity_flag`
- reviewer tracking fields

These fields are excluded because they either contain the target directly or encode downstream review outcomes that would contaminate baseline model training.

This is an important design choice for keeping the feature pipeline defensible.

---

## 6. Ambiguous Label Handling

The current baseline relevance setup is binary:

- `relevant -> 1`
- `not_relevant -> 0`

Rows labeled `ambiguous` are excluded by default for baseline experiments.

This design keeps the first feature/training workflow simple and reduces noise in early model development.

If future experiments require three-class classification or separate ambiguous-handling logic, that should be added intentionally in a later task rather than being mixed into the first baseline pipeline implicitly.

---

## 7. Reproducibility and Modularity

The feature engineering module was designed to be:

- reusable
- deterministic
- testable
- compatible with later training code

The code is organized around explicit function boundaries:

- `load_labeled_data(...)`
- `build_text_features(...)`
- `build_structured_features(...)`
- `combine_features(...)`
- `get_feature_matrix_and_target(...)`

This makes it easier to:
- compare feature families cleanly
- run controlled experiments
- reuse fitted transformers later
- avoid notebook-specific feature drift

---

## 8. Why This Design Is Appropriate for the Current Project Stage

This project is still in the baseline supervised ML setup stage.

At this point, the most important design goals are:

- stable labeled input handling
- leakage-safe target extraction
- simple but useful feature families
- support for text-only and hybrid comparisons
- reproducibility for later training/evaluation tasks

For that reason, the current feature design intentionally favors:
- clarity over complexity
- modularity over ad hoc experimentation
- transparency over cleverness

This makes the feature layer a strong foundation for the later training and evaluation modules.

---

## 9. Next Expected Use

The next downstream use of this module is likely to be:

- training a baseline relevance classifier
- comparing text-only vs structured-only vs hybrid performance
- inspecting class balance and basic model behavior
- supporting methodology reporting for the model layer

Those tasks should happen in later modules.

This feature engineering task only prepares the modeling inputs.
