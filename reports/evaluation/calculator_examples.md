# Calculator Example Outputs

## Purpose

These examples show how the external procurement equivalent calculator returns structured benchmark-derived ranges using the centralized assumptions layer.

These outputs are intended to support **external benchmark context** and **scenario-based estimate framing**. They are **not** audited savings, proven ROI, or verified internal cost avoidance.

---

## Example 1 — Engineering Design Support, Central Scenario, Default-Like Case

### Input

```json
{
  "service_category": "engineering_design_support",
  "scenario": "central",
  "duration_units": 6,
  "scale_factor": 1.0,
  "complexity_factor": 1.0
}            Example output summary: {
  "service_category": "engineering_design_support",
  "scenario": "central",
  "low_estimate": 316885.87,
  "central_estimate": 30470594.47,
  "high_estimate": 66770481.57
}     {
  "service_category": "engineering_design_support",
  "scenario": "central",
  "low_estimate": 316885.87,
  "central_estimate": 30470594.47,
  "high_estimate": 66770481.57
}   Interpretation

This is a benchmark-oriented default case. Because the duration, scale, and complexity align with the category defaults, the resulting range stays close to the category’s current reference anchors.

Example 2 — Prototyping, Central Scenario, Calculator-Grade Subset Logic
Input {
  "service_category": "prototyping",
  "scenario": "central",
  "duration_units": 6,
  "scale_factor": 1.0,
  "complexity_factor": 1.05
}    Example Output Summary  {
  "service_category": "prototyping",
  "scenario": "central",
  "low_estimate": 2095136.53,
  "central_estimate": 3186086.96,
  "high_estimate": 5229244.84
}  {
  "service_category": "prototyping",
  "scenario": "central",
  "low_estimate": 2095136.53,
  "central_estimate": 3186086.96,
  "high_estimate": 5229244.84
}  Interpretation

This example uses the current prototyping-specific calculator path. The resulting range reflects narrowed prototyping subset anchors and policy-informed scaling for calculator comparability, rather than the raw full prototyping category. {
  "service_category": "event_hosting",
  "scenario": "low",
  "event_days": 2,
  "number_of_participants": 40
}  Example Output Summary  {
  "service_category": "event_hosting",
  "scenario": "low",
  "low_estimate": 67979.45,
  "central_estimate": 6530829.48,
  "high_estimate": 14308315.22
}  {
  "service_category": "event_hosting",
  "scenario": "low",
  "low_estimate": 67979.45,
  "central_estimate": 6530829.48,
  "high_estimate": 14308315.22
}  Interpretation

This scenario shows how event-duration and participant count inputs map into the calculator’s duration and scale adjustments. It should be interpreted as benchmark-derived external cost context, not a quoted event price.
