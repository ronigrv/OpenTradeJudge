import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from opentradejudge import evaluate, read_jsonl

ROOT = Path(__file__).parent


class EvaluationTests(unittest.TestCase):
    def setUp(self):
        self.cases = read_jsonl(ROOT / "examples/cases.jsonl")
        self.rows = read_jsonl(ROOT / "examples/responses.jsonl")

    def result(self, rows=None):
        return evaluate(self.cases, self.rows if rows is None else rows)["results"][0]

    def test_demo(self):
        result = self.result()
        self.assertEqual(result["trials"], 5)
        self.assertEqual(result["rule_match_rate"], 1)
        self.assertEqual(result["case_coverage"], 1)
        self.assertEqual(result["repeat_agreement"], 1)
        self.assertEqual(result["abstention_rate"], 0.2)
        self.assertIsNone(result["reported_cost_usd"])

    def test_invalid_outputs_count_against_score_and_agreement(self):
        self.rows[0]["action"] = ["buy"]
        result = self.result()
        self.assertEqual(result["rule_match_rate"], 0.8)
        self.assertEqual(result["repeat_agreement"], 0)
        self.assertEqual(result["violations"], {"invalid_action": 1})

    def test_disagreement(self):
        self.rows[0]["action"] = "sell"
        self.assertEqual(self.result()["repeat_agreement"], 0)

    def test_missing_cases_not_silently_covered(self):
        result = self.result(self.rows[:1])
        self.assertEqual(result["case_coverage"], 0.25)
        self.assertEqual(len(result["missing_case_ids"]), 3)
        self.assertIsNone(result["repeat_agreement"])

    def test_groups_do_not_mix_configurations(self):
        other = copy.deepcopy(self.rows[0])
        other["config"] = "another-prompt"
        report = evaluate(self.cases, self.rows + [other])
        self.assertEqual(len(report["results"]), 2)

    def test_nonfinite_and_boolean_confidence(self):
        for value in (True, float("nan"), float("inf"), -0.1, 1.1, "1"):
            with self.subTest(value=value):
                self.rows[0]["confidence"] = value
                self.assertEqual(self.result()["schema_valid_rate"], 0.8)

    def test_costs_count_for_invalid_predictions(self):
        self.rows[0].update(action="invalid", cost_usd=0.01, latency_ms=100)
        result = self.result()
        self.assertEqual(result["reported_cost_usd"], 0.01)
        self.assertEqual(result["cost_samples"], 1)
        self.assertEqual(result["mean_latency_ms"], 100)

    def test_reject_unknown_case(self):
        self.rows[0]["case_id"] = "unknown"
        with self.assertRaisesRegex(ValueError, "Unknown case_id"):
            self.result()

    def test_reject_duplicate_case(self):
        with self.assertRaisesRegex(ValueError, "unique"):
            evaluate(self.cases + self.cases[:1], self.rows)

    def test_reject_real_data_marker(self):
        self.cases[0]["synthetic"] = False
        with self.assertRaisesRegex(ValueError, "synthetic"):
            self.result()

    def test_empty_inputs(self):
        for cases, responses in (([], self.rows), (self.cases, [])):
            with self.assertRaises(ValueError):
                evaluate(cases, responses)

    def test_report_does_not_echo_prompts_or_justifications(self):
        self.rows[0]["justification"] = "unique-response-text"
        encoded = json.dumps(evaluate(self.cases, self.rows))
        self.assertNotIn("unique-response-text", encoded)
        self.assertNotIn(self.cases[0]["prompt"], encoded)

    def test_cli_and_input_fingerprints(self):
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / "report.json"
            completed = subprocess.run([
                sys.executable, str(ROOT / "opentradejudge.py"),
                "--cases", str(ROOT / "examples/cases.jsonl"),
                "--responses", str(ROOT / "examples/responses.jsonl"),
                "--output", str(output),
            ], capture_output=True, text=True)
            self.assertEqual(completed.returncode, 0, completed.stderr)
            report = json.loads(output.read_text())
            self.assertEqual(len(report["inputs_sha256"]["cases"]), 64)

    def test_jsonl_error_has_line_number(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "bad.jsonl"
            source.write_text('{}\nnot-json\n')
            with self.assertRaisesRegex(ValueError, "bad.jsonl:2"):
                read_jsonl(source)


if __name__ == "__main__":
    unittest.main()
