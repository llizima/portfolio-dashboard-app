# Service Taxonomy Notes
## Applied Government Analytics (AGA) Value Dashboard

---

## 1. Purpose of the Taxonomy

This taxonomy defines the **core service categories** used across the entire system:

- ML classification (feature targets)
- Contract filtering
- Benchmark segmentation
- Dashboard grouping
- Scenario-based value estimation

It ensures that all analysis is **consistent, explainable, and defensible**.

---

## 2. Design Principles

The taxonomy was built using the following principles:

### 1. Mutually Exclusive Categories
Each contract should map to ONE dominant category wherever possible.

### 2. Operational Use
Categories are not conceptual — they must:
- map to keywords
- map to PSC/NAICS signals
- support filtering logic
- support ML classification

### 3. Alignment with Value Definition
All categories support:

> “Estimated equivalent market value based on comparable external contracts”

NOT:
- savings
- ROI
- internal efficiency claims :contentReference[oaicite:4]{index=4}  

---

## 3. Category Breakdown Logic

---

### Prototyping vs Engineering Support

**Key distinction:**

| Category | Core Output |
|----------|------------|
| Prototyping | Physical or functional artifact |
| Engineering Support | Design, analysis, planning |

This distinction is critical for:
- cost benchmarking (prototyping is often higher cost)
- scenario modeling

---

### Event Hosting vs Ecosystem Access

**Key distinction:**

| Category | Core Value |
|----------|-----------|
| Event Hosting | The event itself |
| Ecosystem Access | The network and relationships |

This prevents:
- double counting
- inflated value interpretation

---

### Workspace vs Services

Workspace/Collaboration is:

- infrastructure (space, environment)

NOT:
- engineering work
- program support

---

### Program Support vs Technical Work

Program support includes:

- coordination
- logistics
- reporting

NOT:
- engineering
- prototyping

---

## 4. Integrated Service Category

Some contracts span multiple categories.

Instead of forcing incorrect classification:

→ `integrated_service_delivery` is used

This preserves:
- classification integrity
- benchmark accuracy

---

## 5. How This Supports ML

The taxonomy enables:

### Feature Engineering
- keyword matching
- TF-IDF signals
- label generation

### Model Training
- supervised classification (include/exclude + category tagging)

### Explainability
- each classification can be traced to:
  - keywords
  - definitions
  - examples

---

## 6. How This Supports the Dashboard

The taxonomy directly powers:

- filter controls (by service type)
- benchmark segmentation
- scenario inputs (e.g., “type of service”)
- KPI breakdowns by category

---

## 7. How This Supports Business Questions

This taxonomy directly enables:

- Q1 → cost by service type  
- Q2 → variability by service type  
- Q3 → agency differences within service types  
- Q4 → scenario-based value by service type :contentReference[oaicite:5]{index=5}  

---

## 8. Final Validation Rule

Each category must pass:

> “Can a leadership user understand what this represents, how it maps to real contracts, and how it impacts cost interpretation?”

If not → revise.

