# OpenTradeJudge

**An open-source test bench for AI veto decisions.** Check whether a model allows,
vetoes, or abstains on synthetic scenarios under explicit, published rules.

Python 3.10+, standard library only, MIT licensed. Version **0.2.0** is an early
release, with an offline scorer, an opt-in OpenAI Responses API runner, 60 generated
cases across 10 scenario families, and 38 automated tests. No live-model benchmark
has been run for this release. There are no adoption or profitability claims.

## What problem does it solve?

An AI reviewer can return perfectly valid JSON while allowing something it should
reject, refusing a permitted action, or guessing when evidence is missing.
OpenTradeJudge separates those errors and makes repeated experiments comparable.
The market-inspired setting is a toy instruction-following task, not a strategy.
The public tool can be evaluated independently of any private application.

## Try it without a key

```sh
python demo.py
python -m unittest discover -v
```

The demo compares a deterministic rule implementation against an intentionally
faulty always-allow baseline. Neither is an LLM. The correct baseline matches all
60 labels; always-allow matches 12/60 and falsely allows every veto/abstain case.
These are checks of the scoring logic, **not model evaluation results**.
See [the reproducible simulation report](examples/simulation-report.json).

Generate the suite and evaluate the deterministic baseline:

```sh
mkdir runs
python veto_cases.py --output runs/cases.jsonl --baseline runs/baseline.jsonl
python opentradejudge.py --cases runs/cases.jsonl --responses runs/baseline.jsonl
```

The generator refuses to overwrite existing files. The suite covers within-limit
inputs, risk over the toy limit, stale inputs, missing fields, conflicting inputs,
exact boundaries, invalid types, negative values, and misleading notes. The 60
cases are variations of ten templates, not 60 independent problem families.

## OpenAI adapter: dry run first

```sh
python openai_runner.py --cases runs/cases.jsonl --model gpt-6-astra --max-requests 60 --input-price 10 --output-price 50 --budget-usd 5
```

This only prints a plan; no key, file output, or network call is needed. The model
is always explicit. Prices above are standard short-context text prices checked
on September 14, 2026, in the [Astra model documentation](https://developers.openai.com/api/docs/models/gpt-6-astra).
Check current prices and account access before any live run.

For actual calls, set `OPENAI_API_KEY` locally and append `--live`. The default
output is `runs/responses.jsonl`; existing results are never overwritten. Then:

```sh
python opentradejudge.py --cases runs/cases.jsonl --responses runs/responses.jsonl
```

Live mode sends only each reviewed case prompt, fixed instructions, and the
response schema to OpenAI. It never sends expected labels or arbitrary case
metadata. It uses `store: false`, no tools, no redirects, no automatic retries,
an explicit request limit, and `max_output_tokens` (512 by default).
On a transport error it records a failed trial and stops. Refusals, incomplete
outputs, and malformed decisions remain failures rather than becoming abstentions.

**Budget meaning:** preflight reserves a conservative estimate for every planned
call using UTF-8 request size plus a 2,048-token allowance and the output cap.
It is not an exact token count or a provider-enforced dollar limit. Prices are
user-supplied; incorrect prices or billing rules can invalidate the estimate.
Request count and output-token settings are hard application/request limits.
Returned token usage is converted to a separately labeled cost estimate, without
cache discounts. Confirm actual billed cost in your provider account.

## Metrics

| Metric | Meaning |
| --- | --- |
| Case coverage | Unique evaluated cases / all cases |
| Schema valid rate | Completed, valid decision rows / all trials |
| Rule match rate | Valid rows matching the published label / all trials |
| False allow rate | Valid allow answers on veto/abstain cases / all such trials |
| False veto rate | Valid veto answers on allow cases / all such trials |
| Abstention rate | Valid abstain answers / all trials |
| Repeat agreement | Matching valid pairs / all within-case repeat pairs |
| Category results | Trial counts and correct counts per scenario family |
| Latency and cost | Supplied timing and actual/estimated cost, separately counted |

Read schema failures alongside false-allow rates: a broken model that never returns
a valid answer can have zero false allows. Missing cases reduce coverage. Missing
telemetry stays unknown. No repeated pairs means agreement is `null`. Confidence
is range-checked, not calibrated. Metrics do not certify deployment safety.

Input/output details and limitations are in [the methodology](docs/methodology.md).
The original four buy/sell/hold/abstain fixtures remain supported for compatibility.

## Privacy and scope

This repository was written independently from scratch. It contains no private
application code, credentials, trading histories, or proprietary decision rules.
It has no broker integration or trade execution. `runs/` is ignored by Git.
Synthetic flags are declarations, not automatic secret detectors. Review inputs
before live use, and review outputs before publishing: model justifications can
echo prompts. Aggregate reports omit prompt/justification text but retain IDs
and model/config labels. `store: false` is not a promise of zero provider retention.

## Next milestones

Run a small real-model pilot after API access is configured, publish failures and
actual costs, add independently reviewed held-out cases, and gather external
feedback. Multimodal charts, confidence calibration, and production integrations
are future work. See [the roadmap](docs/roadmap.md).

Contributions are welcome; see [CONTRIBUTING.md](CONTRIBUTING.md). The initial
implementation was developed with Codex assistance. No automatic merge/release
pipeline or autonomous trading capability is included.
