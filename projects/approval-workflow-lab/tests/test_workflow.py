from contextlib import closing
from concurrent.futures import ThreadPoolExecutor
import json
import sqlite3
import tempfile
import threading
import unittest

from approval_workflow import Engine, Principal, WorkflowError
from approval_workflow.core import digest
from approval_workflow.scenarios import Sandbox, load_cases, run_case


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(prefix="approval-test-")
        self.addCleanup(self.directory.cleanup)
        self.s = Sandbox(self.directory.name)

    def assertCode(self, code, operation):
        with self.assertRaises(WorkflowError) as error:
            operation()
        self.assertEqual(error.exception.code, code)

    def call_behind_writer_lock(self, operation, mutate_caller_input):
        """Observe preflight completion, mutate input, then release a real DB lock."""
        connected = threading.Event()
        original_connect = self.s.engine._connect
        blocker = sqlite3.connect(self.s.engine.paths["north"], isolation_level=None)
        blocker.execute("BEGIN IMMEDIATE")

        def observed_connect(principal):
            db = original_connect(principal)
            connected.set()
            return db

        self.s.engine._connect = observed_connect
        try:
            with ThreadPoolExecutor(max_workers=1) as pool:
                future = pool.submit(operation)
                try:
                    self.assertTrue(connected.wait(3), "worker did not complete preflight")
                    mutate_caller_input()
                finally:
                    blocker.execute("COMMIT")
                    blocker.close()
                return future.result(timeout=5)
        finally:
            self.s.engine._connect = original_connect

    def test_execute_does_not_reuse_mutable_payload_after_approval_check(self):
        rid = self.s.request()
        token = self.s.approval(rid)
        caller_payload = dict(self.s.payload)
        receipt = self.call_behind_writer_lock(
            lambda: self.s.execute(rid, token, payload=caller_payload),
            lambda: caller_payload.update(plan="pro"),
        )
        self.assertEqual(caller_payload["plan"], "pro")
        self.assertEqual(self.s.state()["account_A01"], ["enterprise", 1])
        self.assertEqual(receipt["target_id"], "A01")
        self.assertEqual(self.s.state()["execution_audit_events"], 1)

    def test_request_payload_and_retry_fingerprint_share_one_detached_snapshot(self):
        caller_payload = dict(self.s.payload)
        rid = self.call_behind_writer_lock(
            lambda: self.s.request(payload=caller_payload),
            lambda: caller_payload.update(plan="pro"),
        )
        preview = self.s.engine.review(self.s.reviewer, rid)
        self.assertEqual(preview["payload"], self.s.payload)
        self.assertEqual(preview["payload_digest"], digest(self.s.payload))
        self.assertEqual(self.s.request(), rid)
        self.assertCode("idempotency_conflict", lambda: self.s.request(payload=caller_payload))

    def test_review_shows_exact_transaction_before_signing(self):
        rid = self.s.request(ttl=30)
        preview = self.s.engine.review(self.s.reviewer, rid)
        self.assertEqual(preview["payload"], self.s.payload)
        self.assertEqual(preview["payload_digest"], digest(self.s.payload))
        self.assertEqual(preview["expected_version"], 0)
        self.assertEqual(preview["expires_at"], 1030)
        self.assertEqual(preview["requester"], "alex")

    def test_valid_signature_cannot_skip_persisted_approval(self):
        rid = self.s.request()
        with closing(self.s.engine._connect(self.s.requester)) as db:
            row = self.s.engine._request(db, rid)
            token = self.s.engine._sign(self.s.engine._claims("north", row))
        self.assertCode("not_approved", lambda: self.s.execute(rid, token))
        self.assertEqual(self.s.state()["mutations"], 0)

    def test_transaction_rollback_survives_a_fresh_engine_connection(self):
        rid = self.s.request()
        token = self.s.approval(rid)
        def fail(_):
            raise RuntimeError("simulated interruption")
        self.s.engine.failpoint = fail
        with self.assertRaises(RuntimeError):
            self.s.execute(rid, token)
        fresh = Engine(self.s.engine.paths, self.s.engine.key, self.s.clock)
        self.assertEqual(fresh.review(self.s.reviewer, rid)["state"], "approved")
        self.assertEqual([r["action"] for r in fresh.audit(self.s.reviewer)], ["requested", "approved"])
        self.assertEqual(self.s.state()["mutations"], 0)
        receipt = fresh.execute(self.s.requester, rid, "set_plan", self.s.payload, 0, token)
        self.assertFalse(receipt["replayed"])
        self.assertEqual(self.s.state()["execution_audit_events"], 1)

    def test_approval_is_bound_to_request_id_not_just_equal_payload(self):
        first, second = self.s.request("one"), self.s.request("two")
        token = self.s.approval(first)
        self.assertCode("approval_binding_mismatch", lambda: self.s.execute(second, token))

    def test_cross_tenant_review_cannot_find_other_tenant_request(self):
        rid = self.s.request()
        other = Principal("south", "riley", {"reviewer"})
        self.assertCode("request_not_found", lambda: self.s.engine.review(other, rid))

    def test_idempotency_keys_are_scoped_to_actor(self):
        first = self.s.request("same-key")
        other = Principal("north", "second-operator", {"requester"})
        second = self.s.request("same-key", principal=other)
        self.assertNotEqual(first, second)

    def test_retry_never_extends_original_expiry(self):
        rid = self.s.request(ttl=10)
        self.s.clock.now += 5
        self.assertEqual(rid, self.s.request(ttl=10))
        self.assertEqual(self.s.engine.review(self.s.reviewer, rid)["expires_at"], 1010)

    def test_other_reviewer_cannot_replace_an_approved_transaction(self):
        rid = self.s.request()
        self.s.approval(rid)
        other = Principal("north", "another-reviewer", {"reviewer"})
        self.assertCode("invalid_transition", lambda: self.s.engine.approve(other, rid, digest(self.s.payload)))

    def test_executed_transaction_cannot_be_approved_again(self):
        rid = self.s.request()
        self.s.execute(rid, self.s.approval(rid))
        self.assertCode("invalid_transition", lambda: self.s.approval(rid))

    def test_expired_receipt_retry_is_also_rejected(self):
        rid = self.s.request(ttl=1)
        token = self.s.approval(rid)
        self.s.execute(rid, token)
        self.s.clock.now += 1
        self.assertCode("expired", lambda: self.s.execute(rid, token))
        self.assertEqual(self.s.state()["mutations"], 1)

    def test_expiry_is_rechecked_after_transaction_lock_acquisition(self):
        rid = self.s.request(ttl=10)
        token = self.s.approval(rid)
        readings = iter([1000, 1010])
        self.s.engine.clock = lambda: next(readings)
        self.assertCode("expired", lambda: self.s.execute(rid, token))
        self.assertEqual(self.s.state()["mutations"], 0)

    def test_audit_is_durable_and_does_not_store_bearer_token(self):
        rid = self.s.request()
        token = self.s.approval(rid)
        self.s.execute(rid, token)
        fresh = Engine(self.s.engine.paths, self.s.engine.key, self.s.clock)
        events = fresh.audit(self.s.reviewer)
        self.assertEqual([event["action"] for event in events], ["requested", "approved", "executed"])
        self.assertNotIn(token, json.dumps(events))
        self.assertEqual([event["actor"] for event in events], ["alex", "riley", "alex"])

    def test_reader_cannot_inspect_approval_audit(self):
        self.assertCode("forbidden", lambda: self.s.engine.audit(self.s.reader))

    def test_target_id_sql_injection_is_bound_as_data(self):
        self.assertCode("resource_not_found", lambda: self.s.request(payload={"account_id": "A01' OR 1=1 --", "plan": "pro"}))
        self.assertEqual(self.s.state()["mutations"], 0)

    def test_boolean_versions_and_unbounded_ttl_are_invalid(self):
        self.assertCode("invalid_version", lambda: self.s.request(expected_version=True))
        self.assertCode("invalid_ttl", lambda: self.s.request(ttl=601))
        self.assertCode("invalid_ttl", lambda: self.s.request(ttl=0))

    def test_mutable_role_input_is_copied_at_principal_boundary(self):
        roles = {"reader"}
        principal = Principal("north", "sam", roles)
        roles.add("requester")
        self.assertEqual(principal.roles, frozenset({"reader"}))

    def test_short_signing_key_and_shared_tenant_database_rejected(self):
        with self.assertRaises(ValueError):
            Engine(self.s.engine.paths, b"short")
        with self.assertRaises(ValueError):
            Engine({"north": self.s.engine.paths["north"], "south": self.s.engine.paths["north"]}, b"x" * 32)

    def test_seed_refuses_to_overwrite_existing_state(self):
        with self.assertRaises(ValueError):
            Engine.seed(self.directory.name)


class FixedContractTests(unittest.TestCase):
    """Independent expected results and final mutation/audit counts live in the fixture."""


def make_contract(case):
    def test(self):
        result = run_case(case)
        self.assertTrue(result["passed"], json.dumps(result, indent=2))
    return test


for fixture_case in load_cases():
    setattr(FixedContractTests, "test_" + fixture_case["id"].replace("-", "_") + "_" + fixture_case["action"], make_contract(fixture_case))


if __name__ == "__main__":
    unittest.main()
