# Scoring Summary

## What was scored

- Input dataset: src\data\processed\comparable_contracts.parquet
- Output dataset: src\data\processed\comparable_contracts_scored.parquet
- Rows scored: 1764

## Model and scoring settings

- Model version: LogisticRegression_rows131_features2105_hybrid
- Model class: LogisticRegression
- Training mode: hybrid
- Threshold used: 0.50

## Score distribution

- Average relevance score: 0.5561
- Minimum relevance score: 0.0663
- Maximum relevance score: 0.9598
- Predicted relevant rows: 1477
- Predicted non-relevant rows: 287

## Output columns added

- model_version
- relevance_score
- predicted_relevance_label
- scoring_timestamp
- threshold_used

## Notes

- This module applies an existing trained model only.
- No retraining occurs during scoring.
- The scored dataset preserves original input columns and appends prediction metadata.
