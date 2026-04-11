# SOFWERX Value Dashboard

End-to-End Data Pipeline and Benchmarking Platform for Government Contract Analysis

## Overview

The SOFWERX Value Dashboard is a full-stack data science application designed to benchmark internal prototype and event costs against federal contract data from USAspending.gov.

It provides a structured, data-driven framework to estimate:

- Market-equivalent contract costs
- Cost distributions across agencies and service categories
- Comparable contract benchmarks for decision support

This project demonstrates end-to-end ownership of a production-style data system, from raw API ingestion to a deployed analytics dashboard.

## Key Capabilities

### Data Ingestion (API Layer)

- Pulls contract data from the USAspending API
- Handles pagination, retries, and structured raw storage
- Maintains reproducible data pulls with manifest tracking

### Data Processing and Cleaning

- Transforms raw JSON into structured analytical datasets
- Standardizes fields, data types, and schema
- Handles duplicates and missing data
- Outputs clean Parquet datasets for downstream analysis

### Benchmarking and Classification

- Rule-based filtering identifies comparable federal contracts
- Custom service taxonomy maps contracts into categories such as:
  - Prototyping
  - Engineering Design Support
  - Program Support
- Produces a canonical comparable dataset used across the system

### KPI and Benchmark Insights

Generates structured benchmark metrics including:

- Cost distributions
- Agency comparisons
- Category-level summaries

### Value Estimation Logic

Scenario-based benchmarking approach:

- Conservative
- Balanced
- Upper-range

Translates raw contract data into decision-support insights

### Interactive Dashboard (Streamlit)

Multi-page dashboard designed for exploration and decision-making:

- Executive Overview
- Benchmark Explorer
- Service Category Analysis
- Value Calculator
- Model Methodology
- Data Quality Monitoring

## Architecture and Deployment

### Architecture

```text
USAspending API
→ Ingestion Pipeline
→ Raw JSON Storage
→ Data Cleaning and Transformation
→ Processed Dataset (Parquet)
→ Benchmark Filtering and Category Mapping
→ Comparable Contracts Dataset
→ KPI Generation and Scenario Logic
→ Streamlit Dashboard
```

## Project Structure

```text
SOFWERX_Value_Dashboard/
├── app/
│   ├── Home.py
│   ├── pages/
│   └── components/
├── src/
│   ├── config/
│   ├── data/
│   ├── benchmark/
│   └── ml/ (optional layer)
├── models/
├── reports/
└── tests/
```

## Setup and Installation

### Create Virtual Environment

**Windows (PowerShell):**

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

**Mac/Linux:**

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Running the Application

```bash
streamlit run app/Home.py
```

## Pipeline Workflow

Run commands from the repository root:

```bash
# Step 1: Ingest raw data
python -m src.data.ingest_pipeline

# Step 2: Clean and transform
python -m src.data.clean_transform

# Step 3: Generate comparable dataset
python -m src.benchmark.baseline_filters

# Step 4: Map service categories
python -m src.benchmark.category_mapper

# Step 5: Build canonical dataset
python -m src.benchmark.comparable_builder

# Step 6: Generate KPIs
python -m src.benchmark.kpis
```

## Key Outputs

- Comparable contracts dataset
- Category-mapped benchmark data
- KPI summary tables
- Evaluation and methodology reports

## Example Use Cases

- Benchmark internal prototype costs against federal contracts
- Identify cost outliers and inefficiencies
- Support acquisition and funding decisions
- Estimate fair market value for technical efforts

## Skills Demonstrated

- Data Engineering (ETL pipelines)
- API Integration (USAspending)
- Data Cleaning and Feature Engineering
- Rule-Based and ML Classification
- Business Analytics and Cost Modeling
- Dashboard Development (Streamlit)
- Modular System Design

## Notes

- Uses public federal procurement data
- Benchmarking is proxy-based (not exact contract matching)
- Designed for decision support, not exact valuation

## Deployment

This project is deployed as a Streamlit application for interactive use.

## Author

Louis Lizima  
Data Science and Engineering Intern — SOFWERX  
M.S. Data Science — New College of Florida

## Future Improvements

- Improve UI formatting and readability
- Add caching and pipeline-trigger controls
- Enhance classification accuracy
- Automate data refresh pipeline
- Optimize deployment performance
