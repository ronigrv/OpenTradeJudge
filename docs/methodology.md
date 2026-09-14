# Evaluation methodology, v0.2

## Task and labels

The veto suite asks a model to apply a published toy rule to synthetic numeric
inputs. Missing, invalid, negative, or conflicting evidence requires abstention;
otherwise, exceeding explicit toy limits requires veto; remaining cases allow.
These labels describe instruction following, not future returns or investment
quality. A deterministic generator produces 60 variations across ten families.
Manually assigned family labels are checked against a separate executable rule.
This is an internal consistency check, not external validation.

## Records

Cases are JSONL objects with a unique `case_id`, `synthetic: true`, `prompt`, and
`expected_action`. Optional `category` is used for breakdowns. The original action
set (buy/sell/hold/abstain) and the veto set (allow/veto/abstain) are supported.
Responses require case/model/config labels, action, confidence in [0,1], and a
nonempty justification. Optional `status` defaults to completed for older files.
Non-completed statuses count as failures even if the action resembles a valid one.

The API runner requests strict JSON with only action/confidence/justification.
It reads completed message output and handles refusals, incomplete responses,
malformed JSON, and transport errors separately. Unknown or extra decision keys
are rejected. It preserves available input/output token counts, requested and
resolved model names, trial number, timing, prompt fingerprint, and run settings.
`estimated_cost_usd` uses supplied uncached input/output prices; `cost_usd` is
reserved for externally supplied actual cost, so estimates cannot masquerade as bills.

## Experiment design

1. Freeze case definitions before evaluating. Do not tune against held-out labels.
2. Record exact model/config settings. The runner hashes its instructions, schema,
   version, requested model, reasoning effort, and output cap into the config ID.
3. Use the same case set and repeat count across comparisons. Do not send expected
   labels to models. Each request receives only the case prompt and fixed instructions.
4. Keep malformed/incomplete/refused trials in the denominator. Transport failures
   stop the current run; coverage reveals cases that were never attempted.
5. Read coverage, schema validity, and false allowances together. An invalid output
   does not count as a false allow, but is still a failed response and rule mismatch.
6. Review all exported files. Aggregate reports omit prompt and justification text,
   but labels/IDs are caller supplied. Raw response records may echo prompt content.
7. Publish source versions, settings, input fingerprints, sample counts, failures,
   and limitations alongside any real-model comparison.

Repeat agreement pools all within-case pairs; pairs are not independent. Case
templates are also related. Rates are descriptive, with no significance or
confidence interval claims. Future work should use independently reviewed cases
and case/family-level uncertainty estimates. Results currently group by requested
model/config; inspect `resolved_model` records and avoid pooling changing aliases.

## Evidence for this release

Only deterministic baselines and simulated API responses were run. The published
simulation report demonstrates that the scorer distinguishes the known-correct
toy rule from a deliberately broken always-allow implementation. It says nothing
about Astra or any other model. Mocked HTTP tests cover payload format, privacy
boundaries, transport failure behavior, refusal handling, budgets, and output
preservation. Live account access, real response behavior, latency, and costs
have not been validated.

## API references

- [Responses API](https://developers.openai.com/api/reference/python/resources/responses/methods/create)
- [Structured outputs](https://developers.openai.com/api/docs/guides/structured-outputs)

The optional runner sends `store: false`, uses no tools, and does not follow HTTP
redirects. This does not override provider retention policies or guarantee that
user-provided synthetic prompts contain no sensitive information.
