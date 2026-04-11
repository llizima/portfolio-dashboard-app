# AWS Architecture Explainer

## Purpose

This diagram shows a practical AWS-oriented deployment shape for the SOFWERX Value Dashboard.

It is intended to make the cloud design concrete without overclaiming production maturity.

## Main Flow

1. **USAspending API**
   - Public procurement data is the source input.

2. **AWS Compute**
   - Ingestion and transformation jobs pull and normalize the source data.
   - This could be implemented with EC2, ECS, Lambda, or another AWS compute option depending on operational needs.

3. **Amazon S3**
   - S3 stores raw and processed benchmark artifacts.
   - This includes cleaned datasets, comparable contract datasets, KPI outputs, and summary files.

4. **Model Artifacts**
   - Trained model files, metadata, evaluation summaries, and scored outputs are stored as reusable artifacts.

5. **App Host**
   - The Streamlit app reads prepared artifacts and presents dashboard pages for review and analysis.

6. **Private / Controlled Access**
   - Although the source data is public, the deployed analytics environment should remain access-controlled for intended reviewers.

## Included AWS Concepts

The architecture intentionally includes the following concrete elements:

- **S3** for storage
- **compute/app host** for ingestion and UI hosting
- **model artifacts** as stored ML outputs
- **logs / monitoring** for MLOps-lite observability
- **access control** for private/internal usage

## Security / Deployment Notes

This is a conceptual architecture, not a full security engineering diagram.

Plain-English interpretation:

- public data comes in
- private processed analytics stay in controlled storage
- model artifacts are versioned and reused
- the app is intended for restricted/internal access rather than broad public publishing

## Important Limitation

This architecture diagram should be described as:

- a **proposed AWS deployment shape**
- a **practical cloud reference design**
- a **reviewable conceptual architecture**

It should not be described as:

- a formal ATO package
- a complete zero-trust design
- a finalized production security implementation
