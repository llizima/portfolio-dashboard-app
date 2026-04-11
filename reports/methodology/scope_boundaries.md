# SOFWERX External Cost Benchmarking & Value Estimation  
## Scope Boundaries & Methodology Guardrails

---

## 1. What the Project DOES (Claims)

This project provides a **data-driven external benchmark** of what comparable government work costs under traditional contracting structures.

Specifically, the application:

- Uses publicly available federal procurement data (USAspending)
- Identifies contracts comparable to SOFWERX-like services using:
  - PSC codes
  - NAICS codes
  - keyword filtering
  - machine learning classification
- Produces cost distributions for comparable contracts, including:
  - median values
  - interquartile ranges (IQR)
  - variability metrics
- Enables **scenario-based estimation** of equivalent market value using:
  - user-controlled inputs (sliders)
  - filtered benchmark data
- Provides **decision-support insights** for leadership, including:
  - expected cost ranges
  - variability and risk
  - agency-level comparisons

---

## 2. What the Project DOES NOT DO (Non-Claims)

This project explicitly does NOT:

- Calculate or verify **internal SOFWERX cost savings**
- Access or analyze **non-public financial data**
- Evaluate **internal budget structures**
- Measure **operational efficiency of SOFWERX**
- Compare **quality, outcomes, or mission effectiveness**
- Provide **audited or accounting-grade financial conclusions**

---

## 3. Definition of “Value”

In this project, **value** is defined as:

> The estimated external market cost of performing comparable work under traditional contracting structures, derived from benchmark distributions and scenario-based inputs.

Key characteristics:

- It is **benchmark-derived**, not observed internally  
- It is **scenario-dependent**, based on user-selected parameters  
- It represents a **range**, not a single definitive number  
- It is intended for **decision support**, not financial reporting  

---

## 4. Definition of “Comparable Contracts”

Comparable contracts are defined through a structured, multi-stage filtering process:

---

### Step 1: Context Filtering

Contracts are prioritized by mission alignment:

- Primary: USSOCOM  
- Secondary: Department of Defense (DoD)  
- Optional comparison: broader federal contracts  

---

### Step 2: Keyword + Code Matching

Contracts are identified using:

- PSC (Product Service Codes)
- NAICS (Industry Codes)
- Keyword matching in:
  - contract descriptions
  - PSC descriptions
  - NAICS descriptions  

Examples include:
  - "rapid prototyping"  
  - "engineering support"  
  - "proof of concept"  
  - "additive manufacturing"  

---

### Step 3: PSC Narrowing

- PSC codes are selected based on coverage of keyword-matched contracts  
- Retain codes covering ~90% of relevant observations  
- Exclude overly broad or non-specific categories (e.g., R499)  

---

### Step 4: Machine Learning Classification

A supervised model (TF-IDF + linear classifier) assigns contracts into:

- **include** → considered comparable  
- **manual_review** → borderline  
- **exclude** → not comparable  

Final benchmark dataset includes only:
→ **“include” classified contracts**

---

## 5. In Scope vs Out of Scope

### In Scope

- External contract benchmarking  
- Cost distribution analysis  
- Agency comparisons  
- Scenario-based value estimation  
- ML-assisted contract filtering  
- Interactive dashboard exploration  

### Out of Scope

- Internal SOFWERX financial analysis  
- Cost accounting or auditing  
- ROI calculations using internal data  
- Performance or mission success comparisons  
- Real-time procurement forecasting  

---

## 6. Language Guidance (CRITICAL FOR EXECUTIVE USE)

### ✅ Approved Language

- “Estimated equivalent market value”  
- “Benchmark-derived cost range”  
- “Scenario-based estimate”  
- “External cost context”  
- “Comparable contract distribution”  

### ❌ Avoid These Terms

- “Savings achieved”  
- “Proven cost reduction”  
- “ROI delivered”  
- “Efficiency gains measured”  
- “Cost avoided (without full internal cost data)”  

---

## 7. Key Distinction (NON-NEGOTIABLE)

This project maintains strict separation between:

| Concept | Meaning |
|--------|--------|
| Benchmark | What similar work costs externally |
| Value Estimate | What that implies under selected scenarios |
| Savings | Requires internal cost data (NOT included) |

---

## 8. Validation Principle

All outputs must pass this test:

> “Can a leadership user understand the estimate, its assumptions, and its limitations without misinterpreting it as audited financial savings?”

If not, the output must be revised.    

