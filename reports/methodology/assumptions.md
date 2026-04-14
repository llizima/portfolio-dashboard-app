# Assumptions & Methodology

## Purpose

This document defines the assumptions used in the Applied Government Analytics (AGA) external benchmark value calculator.

The goal of the calculator is to provide:
- scenario-based external benchmark estimates
- comparable contract context
- structured, transparent modeling assumptions

The calculator does NOT:
- produce audited pricing
- prove internal cost savings
- calculate ROI
- represent exact government-wide costs

All outputs should be interpreted as:
**scenario-based external benchmark estimates**

---

## Overall Benchmark Anchors

The system uses benchmark anchors derived from the comparable-contract dataset:

- Low (Q1): 25th percentile of award_amount  
- Central (Median): 50th percentile of award_amount  
- High (Q3): 75th percentile of award_amount  

These anchors are:
- descriptive statistics from the dataset
- not prescriptive prices
- not guarantees of cost

---

## Category Assumptions

Most service categories currently use:

- overall benchmark anchors (Q1 / median / Q3)
- plus category-specific modifiers
- plus default duration, scale, and complexity assumptions

These are treated as:
- calculator defaults
- not empirically validated category-specific distributions

---

## Prototyping Assumptions

### Why Prototyping Is Handled Differently

The raw prototyping category in the dataset includes:
- small prototype efforts
- large program-scale contracts
- multi-phase engineering work

This makes the raw distribution too broad for direct calculator use.

To improve comparability, prototyping uses a **special benchmark path**.

---

## Prototyping Benchmark Construction

For `service_category = prototyping`, the calculator uses the following process:

### Step 1 — Source Dataset

Start from:

- `src/data/processed/comparable_contracts.parquet`

---

### Step 2 — Category Filter

Keep only rows where:

- `mapped_service_category == "prototyping"`

---

### Step 3 — Numeric Requirement

Keep only rows where:

- `award_amount` is numeric and non-null

---

### Step 4 — Upper Cap

Apply:

- `award_amount <= 50,000,000`

Purpose:
- remove large program-scale contracts
- keep prototype-scale efforts

---

### Step 5 — Description Filtering

Apply lightweight intent filtering.

A row is kept only if:
- it contains at least one include keyword
- AND contains none of the exclude keywords

#### Include Keywords

- prototype  
- prototyping  
- fabrication  
- fabricate  
- sbir  
- build  
- demonstrator  

#### Exclude Keywords

- program management  
- management support  
- support program  
- upgrade program  
- sustainment  

---

### Step 6 — Anchor Construction

Compute:

- Low = Q1 of award_amount  
- Central = Median of award_amount  
- High = Q3 of award_amount  

on the narrowed subset.

---

### Step 7 — Scaling for Prototyping

Apply policy-informed scaling to convert full contract values into prototype-phase comparable values.

#### RDT&E Share Assumptions

- Low: 10%  
- Central: 12.5%  
- High: 15%  

#### Government Share Assumptions

- Low: 60%  
- Central: 67%  
- High: 75%  

#### Final Multipliers

- Low: 0.10 × 0.60 = 0.06  
- Central: 0.125 × 0.67 = 0.08375  
- High: 0.15 × 0.75 = 0.1125  

These multipliers are applied to the narrowed subset anchors.

---

## Interpretation of Prototyping Outputs

The resulting prototyping values represent:

- prototype-phase comparable estimates
- scaled benchmark values
- scenario-based external cost context

They do NOT represent:

- audited contract pricing  
- universal prototype costs  
- validated market rates  
- internal Applied Government Analytics (AGA) costs  

---

## Why Scaling Is Required

The dataset contains full contract values, which often include:

- multi-year program costs  
- integration and sustainment  
- non-prototype activities  

Scaling adjusts those values to better approximate:

- the portion of work attributable to prototyping

---

## Important Distinction

> The prototyping calculator anchors are NOT the same as:
> - raw benchmark anchors
> - raw prototyping category values

They are:

- narrowed
- filtered
- scaled

This distinction must be preserved in:
- documentation
- UI labels
- presentations

---

## Limitations

This approach is:

- transparent  
- structured  
- defensible  

But it is still:

- modeled logic  
- not a validated economic model  
- not a complete representation of all contracting variability  

Future improvements may include:

- better prototype classification
- refined filtering logic
- category-specific empirical validation

---

## Summary Table

| Component | Value |
|----------|------|
| Dataset | comparable_contracts.parquet |
| Category filter | prototyping |
| Cap | ≤ 50,000,000 |
| Anchor method | Q1 / Median / Q3 |
| Scaling | RDT&E × Government share |
| Output type | Scenario-based benchmark estimate |

---
