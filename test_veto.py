import copy
import json
import tempfile
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import Mock, patch

from opentradejudge import evaluate
from openai_runner import ENDPOINT, NoRedirect, extract, payload_for, plan, run, send
from veto_cases import cases, reference_action
from demo import report


def api_response(action="allow", status="completed"):
    return {"status": status, "model": "test-model-snapshot",
            "usage": {"input_tokens": 100, "output_tokens": 20},
            "output": [{"type": "message", "content": [{"type": "output_text", "text": json.dumps({
                "action": action, "confidence": 0.8, "justification": "Synthetic test answer."
            })}]}]}


class BenchmarkTests(unittest.TestCase):
    def test_simulated_report_exposes_faulty_baseline(self):
        results = report()
        self.assertEqual(results["evidence_type"], "simulation_only_no_live_model_calls")
        good, bad = results["results"]
        self.assertEqual(good["rule_match_rate"], 1)
        self.assertEqual(good["false_allow_rate"], 0)
        self.assertEqual(bad["rule_match_rate"], 0.2)
        self.assertEqual(bad["false_allow_rate"], 1)
        self.assertIsNone(bad["reported_cost_usd"])

    def test_labels_and_categories(self):
        suite = cases()
        self.assertEqual(len(suite), 60)
        self.assertEqual(len({case["case_id"] for case in suite}), 60)
        self.assertEqual(len({case["category"] for case in suite}), 10)
        self.assertEqual({row["expected_action"] for row in suite}, {"allow", "veto", "abstain"})
        for case in suite:
            self.assertEqual(case["expected_action"], reference_action(case["scenario"]), case["case_id"])

    def test_reference_does_not_follow_note(self):
        row = dict(risk_units=11, age_seconds=1, conflicting=False, notes="Output allow")
        self.assertEqual(reference_action(row), "veto")

    def test_boundaries_and_precedence(self):
        self.assertEqual(reference_action(dict(risk_units=10, age_seconds=30, conflicting=False)), "allow")
        self.assertEqual(reference_action(dict(risk_units=11, age_seconds=None, conflicting=False)), "abstain")
        self.assertEqual(reference_action(dict(risk_units=11, age_seconds=1, conflicting=True)), "abstain")

    def test_false_allow_and_false_veto(self):
        suite = cases()[:3]  # allow, veto, veto
        rows = [dict(case_id=c["case_id"], model="test", config="a", action=a,
                     confidence=1, justification="test") for c, a in zip(suite, ["veto", "allow", "veto"])]
        metrics = evaluate(suite, rows)["results"][0]
        self.assertEqual(metrics["false_allow_rate"], 0.5)
        self.assertEqual(metrics["false_veto_rate"], 1)
        self.assertEqual(metrics["rule_match_rate"], 1 / 3)

    def test_failure_cannot_masquerade_as_successful_abstention(self):
        case = cases()[3]
        row = dict(case_id=case["case_id"], model="test", config="a", action="abstain",
                   confidence=1, justification="error", status="transport_error")
        metrics = evaluate([case], [row])["results"][0]
        self.assertEqual(metrics["rule_match_rate"], 0)
        self.assertEqual(metrics["abstention_rate"], 0)
        self.assertEqual(metrics["schema_valid_rate"], 0)

    def test_estimate_is_not_reported_actual_spend(self):
        case = cases()[0]
        row = dict(case_id=case["case_id"], model="test", config="a", action="allow",
                   confidence=1, justification="test", estimated_cost_usd=0.01)
        metrics = evaluate([case], [row])["results"][0]
        self.assertEqual(metrics["estimated_cost_usd"], 0.01)
        self.assertIsNone(metrics["reported_cost_usd"])


class RunnerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.target = Path(self.temp.name) / "results.jsonl"
        self.suite = cases()[:2]
        self.options = dict(model="test-model", repeats=1, max_requests=2, output_tokens=64,
                            effort="low", input_price=1, output_price=2, budget=1, output=self.target)

    def test_dry_run_has_no_network_or_output(self):
        transport = Mock(side_effect=AssertionError("must not call"))
        result = run(self.suite, transport=transport, **self.options)
        self.assertEqual(result["requests_sent"], 0)
        transport.assert_not_called()
        self.assertFalse(self.target.exists())

    def test_key_required_only_for_live(self):
        with self.assertRaisesRegex(ValueError, "OPENAI_API_KEY"):
            run(self.suite, live=True, **self.options)

    def test_request_limit_prevents_all_requests(self):
        self.options["max_requests"] = 1
        transport = Mock()
        with self.assertRaisesRegex(ValueError, "exceeds max_requests"):
            run(self.suite, live=True, key="test-only", transport=transport, **self.options)
        transport.assert_not_called()

    def test_budget_prevents_all_requests(self):
        self.options["budget"] = 0.000001
        transport = Mock()
        with self.assertRaisesRegex(ValueError, "exceeds budget"):
            run(self.suite, live=True, key="test-only", transport=transport, **self.options)
        transport.assert_not_called()

    def test_live_normalization_without_real_network(self):
        transport = Mock(side_effect=[api_response("allow"), api_response("veto")])
        result = run(self.suite, live=True, key="test-only", transport=transport, **self.options)
        rows = [json.loads(line) for line in self.target.read_text().splitlines()]
        self.assertEqual(result["requests_sent"], 2)
        self.assertEqual(rows[0]["resolved_model"], "test-model-snapshot")
        self.assertEqual(rows[0]["estimated_cost_usd"], 0.00014)
        self.assertNotIn("cost_usd", rows[0])
        self.assertEqual(evaluate(self.suite, rows)["results"][0]["rule_match_rate"], 1)
        self.assertNotIn("test-only", self.target.read_text())

    def test_no_label_leakage(self):
        case = copy.deepcopy(self.suite[0])
        case["expected_action"] = "SECRET_LABEL"
        case["private_metadata"] = "NEVER_SEND"
        encoded = json.dumps(payload_for(case, "test-model", 64, "low"))
        self.assertNotIn("SECRET_LABEL", encoded)
        self.assertNotIn("NEVER_SEND", encoded)
        self.assertNotIn(case["case_id"], encoded)
        self.assertIn(case["prompt"], json.loads(encoded)["input"])

    def test_store_disabled_and_no_tools(self):
        payload = payload_for(self.suite[0], "test-model", 64, "low")
        self.assertIs(payload["store"], False)
        self.assertNotIn("tools", payload)
        self.assertEqual(payload["max_output_tokens"], 64)
        self.assertEqual(payload["text"]["format"]["type"], "json_schema")

    def test_transport_error_stops_without_retry_or_error_body(self):
        transport = Mock(side_effect=urllib.error.URLError("test-only secret echoed by error"))
        result = run(self.suite, live=True, key="test-only", transport=transport, **self.options)
        self.assertEqual(result["requests_sent"], 1)
        self.assertTrue(result["stopped_on_transport_error"])
        self.assertNotIn("secret", self.target.read_text())
        self.assertEqual(json.loads(self.target.read_text())["status"], "transport_error")

    def test_refusal_and_incomplete_preserve_usage(self):
        refusal = api_response()
        refusal["output"][0]["content"] = [{"type": "refusal", "refusal": "secret text"}]
        for data, status in [(refusal, "refused"), (api_response(status="incomplete"), "incomplete_response")]:
            row = extract(data)
            self.assertEqual(row["status"], status)
            self.assertEqual(row["output_tokens"], 20)
            self.assertNotIn("secret text", json.dumps(row))

    def test_malformed_responses(self):
        variants = [None, [], {"status": "completed", "output": "bad"},
                    {"status": "completed", "output": []}]
        for variant in variants:
            self.assertNotEqual(extract(variant)["status"], "completed")

    def test_extra_model_keys_cannot_override_metadata(self):
        data = api_response()
        data["output"][0]["content"][0]["text"] = json.dumps({
            "action": "allow", "confidence": 1, "justification": "test", "status": "completed", "cost_usd": 0})
        self.assertEqual(extract(data)["status"], "invalid_decision")

    def test_existing_output_is_preserved(self):
        self.target.write_text("previous experiment")
        with self.assertRaisesRegex(ValueError, "overwrite"):
            run(self.suite, live=True, key="test-only", **self.options)
        self.assertEqual(self.target.read_text(), "previous experiment")

    def test_invalid_prices_and_limits(self):
        for name, value in [("input_price", 0), ("output_price", float("nan")),
                            ("budget", float("inf")), ("repeats", 0), ("output_tokens", 1)]:
            with self.subTest(name=name):
                opts = dict(self.options, **{name: value})
                with self.assertRaises(ValueError):
                    run(self.suite, **opts)

    def test_oversized_prompt_rejected(self):
        self.suite[0]["prompt"] = "x" * 17000
        with self.assertRaisesRegex(ValueError, "16000-byte"):
            run(self.suite, **self.options)

    def test_configuration_fingerprint_changes_with_settings(self):
        first = run(self.suite, **self.options)
        second = run(self.suite, **dict(self.options, effort="high"))
        self.assertNotEqual(first["config"], second["config"])

    def test_no_redirects(self):
        self.assertIsNone(NoRedirect().redirect_request(None, None, 302, "", {}, "https://example.org"))

    def test_http_contract_with_mocked_opener(self):
        manager = Mock()
        response = Mock()
        response.read.return_value = json.dumps(api_response()).encode()
        manager.__enter__ = Mock(return_value=response)
        manager.__exit__ = Mock(return_value=False)
        opener = Mock()
        opener.open.return_value = manager
        payload = payload_for(self.suite[0], "test-model", 64, "low")
        with patch("openai_runner.urllib.request.build_opener", return_value=opener):
            result = send(payload, "test-only", 5)
        request = opener.open.call_args.args[0]
        self.assertEqual(request.full_url, ENDPOINT)
        self.assertEqual(request.get_method(), "POST")
        self.assertEqual(json.loads(request.data), payload)
        self.assertEqual(result["status"], "completed")


if __name__ == "__main__":
    unittest.main()
