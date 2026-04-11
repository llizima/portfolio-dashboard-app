from __future__ import annotations

import re
from typing import Any


HARD_NEGATIVE_PATTERNS: dict[str, str] = {
    "nsn": r"\bnsn\b",
    "qty": r"\bqty\b",
    "option_exercised": r"\boption exercised\b",
    "procurement": r"\bprocurement\b",
    "supply": r"\bsupply\b",
    "assembly_building": r"\bassembly building\b",
    "facility": r"\bfacility\b|\bfacilities\b",
    "renovation": r"\brenovation\b",
    "upgrade": r"\bupgrade\b|\bupgrades\b",
    "reman": r"\breman\b|\bremanufacture\b|\bremanufacturing\b",
    "spare": r"\bspare\b|\bspares\b",
    "technician_support": r"\btechnician support\b",
    "feasibility_study": r"\bfeasibility study\b",
    "sbir_phase_i": r"\bsbir phase i\b|\bsbir ph i\b|\bsbir phase 1\b",
    "sttr_phase_i": r"\bsttr phase i\b|\bsttr ph i\b|\bsttr phase 1\b",
    "concept_study": r"\bconcept study\b|\bconcept studies\b",
    "phase_a_study": r"\bphase a study\b|\bphase a concept study\b|\bphase a concept studies\b",
}

STRONG_POSITIVE_PATTERNS: dict[str, str] = {
    "prototype": r"\bprototype\b|\bprototypes\b",
    "prototyping": r"\bprototyping\b",
    "fabrication": r"\bfabrication\b",
    "fabricate": r"\bfabricate\b|\bfabricated\b|\bfabricating\b",
    "integrate": r"\bintegrate\b|\bintegrated\b|\bintegration\b",
    "integration_and_test": r"\bintegration and test\b|\bintegrate, test\b",
    "build_and_test": r"\bbuild and test\b|\bdesign, build,? test\b",
    "deliver": r"\bdeliver\b|\bdelivers\b|\bdelivered\b|\bdelivering\b",
    "delivery": r"\bdelivery\b|\bdeliverable\b|\bdeliverables\b",
    "engineering_and_manufacturing_development": r"\bengineering and manufacturing development\b",
    "emd": r"\bemd\b",
    "assembly": r"\bassembly\b|\bassemble\b|\bassembled\b|\bassembling\b",
    "manufacturing_development": r"\bmanufacturing development\b",
}


def normalize_description(text: str) -> str:
    """
    Normalize a contract description for rule-based matching.

    This function lowercases the text, strips leading/trailing whitespace,
    and collapses repeated internal whitespace to a single space.
    """
    if text is None:
        return ""
    normalized = str(text).lower().strip()
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized


def _collect_matches(text: str, pattern_map: dict[str, str]) -> list[str]:
    """
    Return the pattern-map keys whose regex patterns match the normalized text.
    """
    matches: list[str] = []
    for name, pattern in pattern_map.items():
        if re.search(pattern, text, flags=re.IGNORECASE):
            matches.append(name)
    return matches


def get_rule_signals(description: str) -> dict[str, Any]:
    """
    Collect rule-based positive and negative signals from a description.

    Returns a dictionary containing:
    - normalized_description
    - matched_negative_patterns
    - matched_positive_patterns
    """
    normalized = normalize_description(description)
    matched_negative = _collect_matches(normalized, HARD_NEGATIVE_PATTERNS)
    matched_positive = _collect_matches(normalized, STRONG_POSITIVE_PATTERNS)

    return {
        "normalized_description": normalized,
        "matched_negative_patterns": matched_negative,
        "matched_positive_patterns": matched_positive,
    }


def apply_rule_layer(description: str) -> dict[str, Any]:
    """
    Apply the rule layer to a single contract description.

    Decision logic:
    - If any hard negative pattern matches, return rule_label=0
    - Else if any strong positive pattern matches, return rule_label=1
    - Else return rule_label=None

    Returns a dictionary with:
    - rule_label: 0, 1, or None
    - rule_bucket: "hard_negative", "strong_positive", or "needs_ml"
    - matched_negative_patterns: list[str]
    - matched_positive_patterns: list[str]
    - normalized_description: str
    """
    signals = get_rule_signals(description)

    matched_negative = signals["matched_negative_patterns"]
    matched_positive = signals["matched_positive_patterns"]
    normalized = signals["normalized_description"]

    if matched_negative:
        return {
            "rule_label": 0,
            "rule_bucket": "hard_negative",
            "matched_negative_patterns": matched_negative,
            "matched_positive_patterns": matched_positive,
            "normalized_description": normalized,
        }

    if matched_positive:
        return {
            "rule_label": 1,
            "rule_bucket": "strong_positive",
            "matched_negative_patterns": matched_negative,
            "matched_positive_patterns": matched_positive,
            "normalized_description": normalized,
        }

    return {
        "rule_label": None,
        "rule_bucket": "needs_ml",
        "matched_negative_patterns": matched_negative,
        "matched_positive_patterns": matched_positive,
        "normalized_description": normalized,
    }
