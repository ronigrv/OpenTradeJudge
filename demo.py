"""Compare executable and deliberately faulty baselines. No API calls."""

import argparse
import json
from pathlib import Path

from opentradejudge import evaluate
from veto_cases import cases, reference_action


def report():
    suite = cases()
    rows = []
    for case in suite:
        for name, action in [
            ("deterministic-reference-not-an-llm", reference_action(case["scenario"])),
            ("intentionally-faulty-always-allow-not-an-llm", "allow"),
        ]:
            rows.append(dict(case_id=case["case_id"], model=name, config="simulation-v1",
                             action=action, confidence=1.0, justification="Synthetic demonstration baseline."))
    result = evaluate(suite, rows)
    result["evidence_type"] = "simulation_only_no_live_model_calls"
    result["interpretation"] = "This verifies scoring behavior. It is not evidence of OpenAI model performance."
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    rendered = json.dumps(report(), indent=2, allow_nan=False) + "\n"
    if args.output:
        with args.output.open("x", encoding="utf-8") as target:
            target.write(rendered)
    else:
        print(rendered, end="")


if __name__ == "__main__":
    main()
