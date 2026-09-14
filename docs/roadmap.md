# Development milestones

These are proposed deliverables, not completed experiments.

## Baseline

Shipped: dependency-free offline scorer, four synthetic cases, handwritten demo
outputs, input fingerprints, unit tests, and documented metric definitions.

## First development cycle

- Grow to at least 50 independently reviewed synthetic cases across arithmetic
  boundaries, missing data, contradictory context, and explicit abstention.
- Add a mock-tested opt-in OpenAI adapter with bounded requests and output tokens.
- Preserve failed trials and distinguish transport failures from malformed output.
- Use Codex for test development, maintenance, documentation, and code review;
  keep human review of changes and benchmark labels.

## First public experiment

Proposed pilot: 50 cases x 2 model configurations x 3 repeats = 300 calls.
Measure actual cost and failure patterns before expanding. Publish methodology,
configuration metadata, aggregate results, and limitations. Model selection and
token budgets will be set before execution; no fixed dollar estimate is claimed.

## Later work

Only after the pilot, consider more cases, synthetic chart inputs, uncertainty
estimation, and confidence calibration. Prioritize reproducibility and external
feedback over a large unvalidated benchmark.
