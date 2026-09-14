# OpenTradeJudge

A small, model-independent evaluation toolkit for structured AI decisions on
synthetic market scenarios. Python 3.10+; no dependencies or API key required.

**Status: early prototype, v0.1.0.** The offline evaluator works. Live model
adapters, multimodal evaluations, and larger benchmark suites are planned.
There are no published live-model benchmark results or adoption claims.

## Why this exists

A model can produce valid-looking JSON while violating a stated rule, failing to
abstain when inputs are missing, or changing its answer across repeated trials.
OpenTradeJudge makes those failures measurable in an inspectable, reproducible
format. The toy market setting is a controlled instruction-following task; it
does not measure investment skill or predict profitable trades.

## Try it

```sh
python opentradejudge.py --cases examples/cases.jsonl --responses examples/responses.jsonl
python -m unittest discover -v
```

The included responses are **handwritten fixtures, not OpenAI/model outputs**.
The demo has five trials over four synthetic cases, full schema validity and
rule matching, and one agreeing repeat pair. No latency or cost is invented.

To save a report:

```sh
python opentradejudge.py --cases examples/cases.jsonl --responses examples/responses.jsonl --output report.json
```

## Input format

Each file contains one JSON object per line. Cases require `case_id`,
`synthetic: true`, `prompt`, and `expected_action` (buy/sell/hold/abstain).
Responses require `case_id`, `model`, `config`, `action`, `confidence` (0 to 1),
and a nonempty `justification`. Optional `latency_ms` and `cost_usd` must be
finite nonnegative numbers. `model` and `config` identify an exact model version
and prompt configuration when used with real model outputs.

Repeated response case IDs are separate trials. Duplicate case definitions,
unknown case references, empty datasets, and missing grouping labels fail
explicitly. The evaluator records schema failures rather than dropping them.

## Metrics and interpretation

| Metric | Definition |
| --- | --- |
| Case coverage | Unique evaluated cases / all defined cases |
| Schema valid rate | Fully valid response rows / trials |
| Rule match rate | Valid rows matching the exercise label / trials |
| Abstention rate | Valid abstain rows / trials |
| Repeat agreement | Matching valid-action pairs / all within-case repeat pairs |
| Mean latency | Mean of supplied valid timing values, with sample count |
| Reported cost | Sum of supplied valid costs, with sample count |

Invalid outputs count against rule matching and repeat agreement. No repeat
pairs means agreement is `null`, not 100%. Missing telemetry remains unknown.
Reports group by model/config and include input SHA-256 fingerprints. Reports
exclude prompt and justification text, but do include caller-provided case IDs
and model/config labels; use non-sensitive labels.

## Scope and data boundaries

- This repository was authored independently from scratch. It contains synthetic
  exercises only, with no broker integration, order execution, or live data feed.
- The tool makes no network requests. It cannot upload inputs or spend credits.
- The `synthetic` flag is a declaration, not a detector for confidential data.
  Only use datasets you have reviewed and are allowed to process.
- Scores describe these exercise rules, not profitability, safety certification,
  or suitability for use with real funds. Larger datasets need independent review.

## Roadmap

1. Expand synthetic cases covering missing, contradictory, and boundary inputs.
2. Add an opt-in OpenAI adapter with request/token limits, explicit cost reporting,
   fixed model/config metadata, and mock tests before live runs.
3. Publish reproducible comparison reports, including errors and limitations.
4. Explore synthetic chart inputs and confidence calibration after the text-only
   baseline is established.

See [evaluation methodology](docs/methodology.md) and
[development milestones](docs/roadmap.md). Contributions are welcome; see
[CONTRIBUTING.md](CONTRIBUTING.md). Licensed under MIT.
