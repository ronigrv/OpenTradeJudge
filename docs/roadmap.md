# Development milestones

## Completed in v0.2

- Dependency-free offline scorer and CLI, maintaining v0.1 fixture compatibility.
- False-allow/false-veto metrics and per-family counts for veto evaluations.
- A deterministic 60-case generator across ten synthetic scenario families.
- Opt-in Responses API adapter, preflight planning, request/output caps, no retries,
  failure recording, local result persistence, and separately labeled cost estimates.
- Executable and intentionally faulty baselines with a reproducible simulation report.
- Tests and CI, including mocked HTTP tests. No API key is required for CI.

## Next: first live pilot

No live model experiment has run. Proposed pilot: 60 cases x 2 configurations x
3 repeats = 360 calls, split into separately budgeted runs. Begin with a much
smaller smoke test to verify access and usage accounting before running the full
pilot. The model, current prices, and request/token limits must be chosen explicitly.
Publish failures, coverage, actual billed cost where available, and limitations.

## Strengthen public usefulness

- Seek independent feedback on case coverage, labels, and usability.
- Add new families and held-out cases rather than merely increasing repetitions.
- Add case-level uncertainty estimates and clearer comparison artifacts.
- Explore synthetic charts and confidence calibration only after the baseline.

## Proposed credit use

Credits would support public toolkit development, tests, code review, documentation,
and reproducible evaluations. A private application may use the toolkit without
publishing its internals, but that does not establish eligibility to spend grant
credits on private work. Any grant-funded use must follow the award's approved scope.
