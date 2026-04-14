# Deployment & Configuration Guide
## Applied Government Analytics (AGA) Value Dashboard

## 1. Purpose

This guide explains:

- how to run the project locally
- where key data and artifacts live
- how the Streamlit app is intended to be deployed in a private/internal environment

This document is designed to support:
- project handoff
- engineering resume review
- quick re-entry after a break in development

It is intentionally practical and repository-specific.

---

## 2. What This Project Is

The Applied Government Analytics (AGA) Value Dashboard is a benchmark-driven analytics application that:

- ingests public federal procurement data
- cleans and structures that data
- identifies comparable contracts
- scores relevance using a lightweight ML layer
- produces evaluation and scoring artifacts
- presents results in a Streamlit dashboard

The app is designed for:
- benchmark-derived external cost context
- decision support
- internal/private review

It is **not** positioned as:
- audited cost accounting
- ROI proof
- a public-facing open dashboard

---

## 3. Repository Structure (Important Paths)

The project is organized around a few core directories.

### App Layer

- `app/`
  - Streamlit entry point and app pages
- `app/pages/`
  - individual dashboard pages
- `app/components/`
  - shared loaders, filters, and layout helpers

### Source / Business Logic

- `src/`
  - backend Python modules
- `src/data/`
  - raw, interim, labels, and processed data
- `src/ml/`
  - feature engineering, training, evaluation, scoring, retrain checks
- `src/business/`
  - assumptions, calculator logic, scenario engine
- `src/config/`
  - centralized settings and path management

### Reports / Documentation

- `reports/evaluation/`
  - evaluation summaries, scoring summaries, KPI summary outputs
- `reports/architecture/`
  - architecture diagrams and deployment documentation

### Model Artifacts

- `src/models/`
  - saved model artifacts and metadata

---

## 4. Local Setup

### Python Environment

Use the project virtual environment rather than relying on a global Python install.

Typical workflow in PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
