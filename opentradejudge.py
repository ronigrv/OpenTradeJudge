"""Offline evaluation of structured decisions on synthetic market scenarios.

Python 3.10+, standard library only. No network calls or order execution.
"""

import argparse
import hashlib
import json
import math
from collections import Counter, defaultdict
from pathlib import Path

VERSION = "0.1.0"
ACTIONS = {"buy", "sell", "hold", "abstain"}


def read_jsonl(path):
    rows = []
    for line_number, line in enumerate(Path(path).read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except ValueError as exc:
            raise ValueError(f"{Path(path).name}:{line_number}: invalid JSON") from exc
        if not isinstance(row, dict):
            raise ValueError(f"{Path(path).name}:{line_number}: expected an object")
        rows.append(row)
    return rows


def nonnegative_number(value):
    return type(value) in (int, float) and math.isfinite(value) and value >= 0


def validate_cases(cases):
    indexed = {}
    for case in cases:
        case_id = case.get("case_id")
        if not isinstance(case_id, str) or not case_id.strip() or case_id in indexed:
            raise ValueError("Case IDs must be nonempty unique strings")
        expected = case.get("expected_action")
        if not isinstance(expected, str) or expected not in ACTIONS:
            raise ValueError(f"{case_id}: unsupported expected_action")
        if case.get("synthetic") is not True:
            raise ValueError(f"{case_id}: this release accepts explicitly synthetic cases only")
        if not isinstance(case.get("prompt"), str) or not case["prompt"].strip():
            raise ValueError(f"{case_id}: prompt is required")
        indexed[case_id] = case
    if not indexed:
        raise ValueError("At least one case is required")
    return indexed


def validate_response(row):
    errors = []
    action = row.get("action")
    if not isinstance(action, str) or action not in ACTIONS:
        errors.append("invalid_action")
    confidence = row.get("confidence")
    if not nonnegative_number(confidence) or confidence > 1:
        errors.append("invalid_confidence")
    if not isinstance(row.get("justification"), str) or not row["justification"].strip():
        errors.append("missing_justification")
    for field in ("latency_ms", "cost_usd"):
        if field in row and not nonnegative_number(row[field]):
            errors.append(f"invalid_{field}")
    return errors


def evaluate(cases, responses):
    """Return aggregate metrics; never include prompts or response text in reports.

    A response is one independent trial. Repeated case IDs are allowed. Every row
    needs model and config labels, allowing comparisons without mixing prompts.
    Missing cases reduce coverage; malformed predictions remain in denominators.
    """
    indexed = validate_cases(cases)
    groups = defaultdict(list)
    for row in responses:
        for key in ("case_id", "model", "config"):
            if not isinstance(row.get(key), str) or not row[key].strip():
                raise ValueError(f"Each response requires a nonempty {key}")
        if row["case_id"] not in indexed:
            raise ValueError(f"Unknown case_id: {row['case_id']}")
        groups[(row["model"], row["config"])].append(row)
    if not groups:
        raise ValueError("At least one response is required")
    results = []
    for (model, config), rows in sorted(groups.items()):
        valid = correct = abstained = 0
        violations = Counter()
        repeated = defaultdict(list)
        latencies, costs = [], []
        for row in rows:
            errors = validate_response(row)
            violations.update(errors)
            valid += not errors
            correct += not errors and row.get("action") == indexed[row["case_id"]]["expected_action"]
            abstained += not errors and row.get("action") == "abstain"
            repeated[row["case_id"]].append(None if errors else row["action"])
            # Timing and spend include malformed outputs when telemetry is valid.
            if "latency_ms" in row and nonnegative_number(row["latency_ms"]):
                latencies.append(row["latency_ms"])
            if "cost_usd" in row and nonnegative_number(row["cost_usd"]):
                costs.append(row["cost_usd"])
        pairs = agreements = 0
        for actions in repeated.values():
            pairs += len(actions) * (len(actions) - 1) // 2
            for count in Counter(a for a in actions if a is not None).values():
                agreements += count * (count - 1) // 2
        n = len(rows)
        results.append({
            "model": model, "config": config, "trials": n,
            "case_coverage": len(repeated) / len(indexed),
            "missing_case_ids": sorted(set(indexed) - set(repeated)),
            "schema_valid_rate": valid / n,
            "rule_match_rate": correct / n,
            "abstention_rate": abstained / n,
            "repeat_agreement": agreements / pairs if pairs else None,
            "repeat_pairs": pairs,
            "latency_samples": len(latencies),
            "mean_latency_ms": sum(latencies) / len(latencies) if latencies else None,
            "cost_samples": len(costs),
            "reported_cost_usd": sum(costs) if costs else None,
            "violations": dict(sorted(violations.items())),
        })
    return {"version": VERSION, "synthetic_only": True, "case_count": len(indexed), "results": results}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cases", required=True, type=Path)
    parser.add_argument("--responses", required=True, type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        report = evaluate(read_jsonl(args.cases), read_jsonl(args.responses))
        report["inputs_sha256"] = {
            "cases": hashlib.sha256(args.cases.read_bytes()).hexdigest(),
            "responses": hashlib.sha256(args.responses.read_bytes()).hexdigest(),
        }
        rendered = json.dumps(report, indent=2, allow_nan=False) + "\n"
        if args.output:
            args.output.write_text(rendered, encoding="utf-8")
        else:
            print(rendered, end="")
    except (ValueError, OSError) as exc:
        parser.exit(2, f"Error: {exc}\n")


if __name__ == "__main__":
    main()
