from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd

from src.ml.rule_layer import apply_rule_layer


@dataclass
class HybridContractClassifier:
    """
    Hybrid classifier that applies deterministic rules first,
    then falls back to an ML model only when needed.
    """

    vectorizer: Any
    model: Any
    positive_threshold: float = 0.80
    negative_threshold: float = 0.30

    def predict_one(self, description: str) -> dict[str, Any]:
        """
        Predict a label for a single description.

        Rule layer is applied first:
        - hard negative -> final_label = 0
        - strong positive -> final_label = 1
        - otherwise use ML probability

        Returns a dictionary with:
        - final_label: 0, 1, or None
        - decision_source: "rule" or "ml"
        - rule_bucket
        - matched_negative_patterns
        - matched_positive_patterns
        - ml_probability
        - review_recommended
        - normalized_description
        """
        rule_result = apply_rule_layer(description)

        rule_label = rule_result["rule_label"]
        rule_bucket = rule_result["rule_bucket"]
        matched_negative_patterns = rule_result["matched_negative_patterns"]
        matched_positive_patterns = rule_result["matched_positive_patterns"]
        normalized_description = rule_result["normalized_description"]

        if rule_label in (0, 1):
            return {
                "final_label": rule_label,
                "decision_source": "rule",
                "rule_bucket": rule_bucket,
                "matched_negative_patterns": matched_negative_patterns,
                "matched_positive_patterns": matched_positive_patterns,
                "ml_probability": None,
                "review_recommended": False,
                "normalized_description": normalized_description,
            }

        X_vec = self.vectorizer.transform([normalized_description])
        positive_probability = float(self.model.predict_proba(X_vec)[0][1])

        if positive_probability >= self.positive_threshold:
            final_label = 1
            review_recommended = False
        elif positive_probability <= self.negative_threshold:
            final_label = 0
            review_recommended = False
        else:
            final_label = None
            review_recommended = True

        return {
            "final_label": final_label,
            "decision_source": "ml",
            "rule_bucket": rule_bucket,
            "matched_negative_patterns": matched_negative_patterns,
            "matched_positive_patterns": matched_positive_patterns,
            "ml_probability": positive_probability,
            "review_recommended": review_recommended,
            "normalized_description": normalized_description,
        }

    def predict_many(self, descriptions: list[str]) -> pd.DataFrame:
        """
        Predict labels for many descriptions and return a DataFrame.
        """
        results = [self.predict_one(description) for description in descriptions]
        return pd.DataFrame(results)
