# Task 18 — Baseline Rules vs Model Evaluation

Purpose: determine whether ML adds value beyond deterministic rules.

## Rules-Only Baseline

- Precision: 0.8904
- Recall: 0.7558
- F1: 0.8176
- ROC AUC: N/A
- Confusion Matrix: [[37, 8], [21, 65]]

## ML-Only Baseline

- Precision: 0.9765
- Recall: 0.9651
- F1: 0.9708
- ROC AUC: 0.9778
- Confusion Matrix: [[43, 2], [3, 83]]

## Hybrid Rules + ML

- Precision: 0.9012
- Recall: 0.8488
- F1: 0.8743
- ROC AUC: 0.8121
- Confusion Matrix: [[37, 8], [13, 73]]

## Threshold Tradeoff Summary (ML-Only)

|   threshold |   precision |   recall |       f1 |
|------------:|------------:|---------:|---------:|
|         0.1 |    0.794393 | 0.988372 | 0.880829 |
|         0.2 |    0.833333 | 0.988372 | 0.904255 |
|         0.3 |    0.867347 | 0.988372 | 0.923913 |
|         0.4 |    0.913978 | 0.988372 | 0.949721 |
|         0.5 |    0.976471 | 0.965116 | 0.97076  |
|         0.6 |    0.987013 | 0.883721 | 0.932515 |
|         0.7 |    0.986111 | 0.825581 | 0.898734 |
|         0.8 |    0.982759 | 0.662791 | 0.791667 |
|         0.9 |    1        | 0.27907  | 0.436364 |

## Interpretation Notes

- Rules-only is expected to be stricter and less flexible because non-matching rows default to negative.
- ML-only shows how much signal the trained classifier can recover from text and structured features.
- Hybrid shows the practical production-style path: deterministic rules first, ML fallback when rules are inconclusive.
- The threshold table helps show the precision/recall tradeoff when adjusting the ML decision boundary.
