# Scenario Logic

## 1. Purpose

The scenario engine provides a standardized way to view the same benchmark input under different estimate postures.

Its purpose is to support consistent, explainable scenario-based benchmark estimates across the calculator layer. Instead of requiring each page or analyst to manually adjust assumptions, the scenario engine defines named presets in one place and applies them consistently.

This supports reuse in both backend logic and future dashboard views.

---

## 2. Why Scenarios Are Needed

Comparable external contract costs can vary substantially depending on how a benchmark is framed and how input assumptions are interpreted.

Decision-makers often need more than a single default estimate. They may want to understand:

- a cautious lower-bound view
- a neutral default view
- a broader upper-range view

The scenario engine supports those views in a structured way.

This improves consistency because the same scenario definitions can be reused throughout the application rather than being re-created separately in different pages, scripts, or analyst workflows.

---

## 3. Difference Between Service Category and Scenario

A **service category** describes **what kind of work** is being benchmarked.

Examples include:

- `engineering_design_support`
- `prototyping`
- `event_hosting`

A **scenario** describes **which estimate posture** is being applied to that work.

Examples include:

- `conservative`
- `balanced`
- `upper_range`
- `custom`

For example:

- `engineering_design_support` tells the system the type of service being evaluated
- `conservative` tells the system to apply a lower-bound benchmark framing with slightly restrained adjustment assumptions

These are different concepts and should not be mixed together.

---

## 4. Scenario Definitions

### conservative

A lower-bound benchmark framing with slightly restrained adjustment assumptions.

This scenario is intended to represent a cautious view of comparable external cost. It maps to the calculator’s lower benchmark posture and applies slightly reduced multipliers to key adjustment inputs.

### balanced

A central or default benchmark framing.

This scenario is intended to represent the neutral benchmark view. It uses the default benchmark posture and leaves adjustment multipliers at their standard baseline values.

### upper_range

An upper-bound benchmark framing with moderately elevated adjustment assumptions.

This scenario is intended to represent a broader upper-range benchmark view. It maps to the calculator’s higher benchmark posture and applies modestly elevated multipliers to key adjustment inputs.

### custom

A caller-defined benchmark framing and adjustment profile.

This scenario allows a user or downstream system to explicitly define the benchmark position and selected multipliers rather than using one of the standard presets.

---

## 5. How Scenario Adjustments Are Applied

The scenario engine starts with the same base input payload and applies scenario metadata consistently.

Each scenario can influence:

- benchmark position
- duration multiplier
- scale multiplier
- complexity multiplier

In practical terms, the engine can take a base input such as:

- service category
- duration
- scale
- complexity

and return a scenario-adjusted version of that same input for downstream calculator use.

This keeps scenario logic centralized and prevents estimate posture rules from being scattered across dashboard pages or hidden inside calculator code.

---

## 6. Interpretation Guidance

Scenario outputs should be interpreted as:

- benchmark-derived estimate views
- structured external cost context
- scenario-based support for decision-making

They should **not** be interpreted as:

- audited savings
- ROI
- internal Applied Government Analytics (AGA) cost accounting
- proven cost avoidance
- accounting-grade financial conclusions

The purpose of the scenario engine is to standardize how benchmark views are applied, not to claim that one scenario represents a verified internal financial result.

---

## 7. Limitations

The scenario engine improves consistency, but it does not remove all uncertainty.

Important limitations include:

- scenario presets are simplified estimate postures
- the scenario engine is not a full economic model
- results still depend on the quality of the comparable benchmark dataset
- results also depend on the assumptions and logic used by the downstream calculator
- custom scenarios can improve flexibility, but they also require careful interpretation

For these reasons, scenario outputs should be treated as structured benchmark guidance rather than definitive financial truth.

---

## 8. Example Comparison Workflow

Assume the same base input is evaluated under three scenarios:

- `service_category`: `engineering_design_support`
- `duration_units`: `6`
- `scale_factor`: `1.0`
- `complexity_factor`: `1.0`

### Conservative view

The service type stays the same, but the estimate posture is cautious.

- benchmark position shifts toward the lower-bound framing
- duration, scale, and complexity adjustments are slightly restrained

### Balanced view

The service type stays the same, and the estimate posture remains neutral.

- benchmark position stays at the central/default framing
- duration, scale, and complexity remain at baseline assumptions

### Upper-range view

The service type stays the same, but the estimate posture becomes broader.

- benchmark position shifts toward the upper-bound framing
- duration, scale, and complexity adjustments are moderately elevated

This allows a leadership user to compare multiple benchmark-derived views of the same work without changing the underlying service category.

The result is a more interpretable, side-by-side scenario comparison that supports decision-making while remaining within the project’s methodology guardrails.
