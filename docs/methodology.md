# Evaluation methodology

## What is measured

The current task asks a model to follow an explicit synthetic rule and return a
structured action. Expected actions come from that stated exercise rule, not
future prices or a trading strategy. This isolates format compliance, rule
matching, abstention, and repeatability from market prediction.

## Reproducible experiment procedure

1. Version the synthetic cases and prompt template before evaluating.
2. Keep expected labels out of the model input; send only the case prompt.
3. Choose and record the exact model/version and prompt configuration.
4. Run each case the same number of times per configuration. Record failures
   instead of discarding them. Represent malformed action outputs with an invalid
   action and retain required grouping labels so they count as failures.
5. Measure latency per request and use actual usage/billing information for costs.
   Do not fill unknown telemetry with zero. Capture transport errors separately;
   v0.1 does not have a request runner or an automatic transport-error schema.
6. Evaluate all configurations using the same case set. Compare coverage alongside
   rule match rate; high accuracy on a small subset is not full benchmark success.
7. Publish aggregate results with input fingerprints and configuration metadata.
   Review every artifact before publication. Keep credentials out of inputs.

## Limitations

Four demo cases are a smoke test, not a statistically meaningful benchmark.
Handwritten answers demonstrate the evaluator only. Confidence is range-checked
but is not calibrated or scored. Repeat agreement measures consistency, not
correctness. Pairwise observations are not independent. Invalid responses are
penalized in both schema validity and repeat agreement. No model performance
claim should be drawn from fixtures. No historical or live trading performance
is evaluated. A larger suite should separate development cases from held-out
cases and report uncertainty at the case level.
