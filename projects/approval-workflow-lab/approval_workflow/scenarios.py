"""Original, deterministic protocol scenarios. No natural-language model scoring."""

from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from pathlib import Path
import json
import sqlite3
import tempfile

from .core import Engine, Principal, WorkflowError
from .tools import ReadOnlySQL, Tools


class Clock:
    def __init__(self):
        self.now = 1000

    def __call__(self):
        return self.now


class Sandbox:
    def __init__(self, directory, empty=False):
        self.clock = Clock()
        self.engine = Engine.seed(directory, clock=self.clock, empty=empty)
        self.requester = Principal("north", "alex", {"reader", "requester"})
        self.reviewer = Principal("north", "riley", {"reader", "reviewer"})
        self.reader = Principal("north", "sam", {"reader"})
        self.payload = {"account_id": "A01", "plan": "enterprise"}
        self.tools = Tools(self.engine)

    def request(self, key="req", **overrides):
        args = dict(principal=self.requester, operation="set_plan", payload=self.payload,
                    expected_version=0, idempotency_key=key)
        args.update(overrides)
        return self.engine.request_change(**args)["request_id"]

    def approval(self, request_id):
        preview = self.engine.review(self.reviewer, request_id)
        return self.engine.approve(self.reviewer, request_id, preview["payload_digest"])

    def execute(self, request_id, token, **overrides):
        args = dict(principal=self.requester, request_id=request_id, operation="set_plan",
                    payload=self.payload, expected_version=0, approval=token)
        args.update(overrides)
        return self.engine.execute(**args)

    def state(self):
        with closing(sqlite3.connect(self.engine.paths["north"])) as db:
            mutations = db.execute("SELECT coalesce(sum(version),0) FROM accounts").fetchone()[0]
            mutations += db.execute("SELECT coalesce(sum(version),0) FROM cases").fetchone()[0]
            executions = db.execute("SELECT count(*) FROM audit WHERE action='executed'").fetchone()[0]
            accounts = db.execute("SELECT plan,version FROM accounts WHERE id='A01'").fetchone()
        return {"mutations": mutations, "execution_audit_events": executions,
                "account_A01": list(accounts) if accounts else None}


def perform(s, action):
    """Return a small, non-secret observed outcome; assertions are real contracts."""
    e, p, t = s.engine, s.requester, s.tools
    if action == "workflow_plan":
        rid = s.request()
        receipt = s.execute(rid, s.approval(rid))
        assert receipt["version"] == 1 and receipt["state"] == "executed"
        return "executed", {"version": receipt["version"]}
    if action == "workflow_case":
        payload = {"case_id": "C01", "status": "investigating"}
        rid = s.request(operation="set_case_status", payload=payload)
        receipt = s.execute(rid, s.approval(rid), operation="set_case_status", payload=payload)
        rows = t.sql.query(p, "SELECT status,version FROM cases WHERE id=?", ["C01"])["rows"]
        assert rows == [{"status": "investigating", "version": 1}]
        return "executed", {"version": receipt["version"]}
    if action == "request_retry":
        rid = s.request()
        repeated = e.request_change(p, "set_plan", s.payload, 0, "req")
        assert repeated["request_id"] == rid and repeated["replayed"]
        assert len(e.audit(s.reviewer)) == 1
        return "idempotent", {"request_audit_events": 1}
    if action == "approve_retry":
        rid = s.request()
        assert s.approval(rid) == s.approval(rid)
        assert len(e.audit(s.reviewer)) == 2
        return "idempotent", {"approval_audit_events": 1}
    if action in {"execute_retry", "threaded_replay"}:
        rid = s.request()
        token = s.approval(rid)
        n = 8 if action == "threaded_replay" else 2
        if n == 8:
            with ThreadPoolExecutor(max_workers=8) as pool:
                receipts = list(pool.map(lambda _: s.execute(rid, token), range(n)))
        else:
            receipts = [s.execute(rid, token) for _ in range(n)]
        assert sum(not item["replayed"] for item in receipts) == 1
        assert {item["version"] for item in receipts} == {1}
        return "idempotent", {"calls": n, "new_executions": 1, "replayed_receipts": n - 1}
    if action == "rollback":
        rid = s.request()
        token = s.approval(rid)
        def fail(_):
            raise RuntimeError("injected failure after SQL mutation")
        e.failpoint = fail
        try:
            s.execute(rid, token)
            raise AssertionError("failpoint did not fire")
        except RuntimeError:
            pass
        assert s.state()["account_A01"] == ["standard", 0]
        assert e.review(s.reviewer, rid)["state"] == "approved"
        assert [row["action"] for row in e.audit(s.reviewer)] == ["requested", "approved"]
        return "rolled_back", {"state_after_failure": "approved", "mutation_persisted": False}
    if action in {"stale_request", "stale_execution"}:
        original = s.request("original") if action == "stale_execution" else None
        token = s.approval(original) if original else None
        other = s.request("competing", payload={"account_id": "A01", "plan": "pro"})
        s.execute(other, s.approval(other), payload={"account_id": "A01", "plan": "pro"})
        if original:
            s.execute(original, token)
        else:
            s.request("late")
    if action == "wrong_role_request":
        s.request(principal=s.reader)
    if action == "wrong_role_review":
        e.review(s.reader, s.request())
    if action == "wrong_role_execute":
        rid = s.request()
        s.execute(rid, s.approval(rid), principal=s.reader)
    if action == "self_approval":
        rid = s.request()
        principal = Principal("north", "alex", {"requester", "reviewer"})
        e.approve(principal, rid, e.review(principal, rid)["payload_digest"])
    if action == "no_approval":
        s.execute(s.request(), "")
    if action in {"expired_approval", "expired_review"}:
        rid = s.request(ttl=10)
        token = s.approval(rid) if action == "expired_approval" else None
        s.clock.now += 10  # Expiry is exclusive, including its exact boundary.
        s.execute(rid, token) if token else s.approval(rid)
    if action in {"changed_payload", "changed_operation", "changed_version", "cross_tenant_execute", "other_actor_execute", "altered_signature", "wrong_key"}:
        rid = s.request()
        token = s.approval(rid)
        args = {}
        if action == "changed_payload":
            args["payload"] = {"account_id": "A01", "plan": "pro"}
        elif action == "changed_operation":
            args.update(operation="set_case_status", payload={"case_id": "C01", "status": "resolved"})
        elif action == "changed_version":
            args["expected_version"] = 1
        elif action == "cross_tenant_execute":
            args["principal"] = Principal("south", "alex", {"requester"})
        elif action == "other_actor_execute":
            args["principal"] = Principal("north", "other", {"requester"})
        elif action == "altered_signature":
            body, signature = token.split(".")
            token = body + "." + ("A" if signature[0] != "A" else "B") + signature[1:]
        elif action == "wrong_key":
            e.key = bytes([7]) * 32
        s.execute(rid, token, **args)
    if action == "review_digest":
        e.approve(s.reviewer, s.request(), "0" * 64)
    if action == "idempotency_collision":
        s.request()
        s.request(payload={"account_id": "A01", "plan": "pro"})
    if action == "unknown_target":
        s.request(payload={"account_id": "missing", "plan": "pro"})
    if action == "unknown_operation":
        s.request(operation="run_python")
    if action == "extra_payload":
        s.request(payload={**s.payload, "approved": True})
    if action == "unknown_tenant":
        s.request(principal=Principal("../../south", "alex", {"requester"}))
    if action in {"sql_select", "sql_count", "sql_limit", "sql_parameter", "tenant_isolation"}:
        sql, params = "SELECT name FROM accounts ORDER BY id", []
        if action == "sql_count":
            sql = "SELECT count(*) AS n FROM accounts"
        elif action == "sql_limit":
            result = ReadOnlySQL(e, row_limit=3).query(p, sql)
            assert len(result["rows"]) == 3 and result["truncated"]
            return "read", {"rows": 3, "truncated": True}
        elif action == "sql_parameter":
            sql, params = "SELECT name FROM accounts WHERE id=?", ["A01' OR 1=1 --"]
        result = t.sql.query(p, sql, params)
        if action == "sql_count":
            assert result["rows"] == [{"n": 12}]
        elif action == "sql_parameter":
            assert result["rows"] == []
        else:
            assert len(result["rows"]) == 12
            assert all(row["name"].startswith("north-") for row in result["rows"])
            if action == "tenant_isolation":
                south = t.sql.query(Principal("south", "sam", {"reader"}), sql)["rows"]
                assert all(row["name"].startswith("south-") for row in south)
                assert {x["name"] for x in south}.isdisjoint(x["name"] for x in result["rows"])
        return "read", {"rows": len(result["rows"]), "tenant": "north"}
    denied_sql = {
        "sql_write": "UPDATE accounts SET plan='enterprise'",
        "sql_attach": "ATTACH DATABASE ':memory:' AS other",
        "sql_pragma": "PRAGMA table_info(accounts)",
        "sql_metadata": "SELECT sql FROM sqlite_master",
        "sql_extension": "SELECT load_extension('not-a-library')",
        "sql_heavy": "SELECT count(*) FROM accounts a, accounts b, accounts c, accounts d, accounts e, accounts f",
    }
    if action in denied_sql:
        t.sql.query(p, denied_sql[action])
    if action in {"kpi_share", "kpi_empty", "registered_kpi"}:
        result = t.kpi(p, "resolved_case_share")
        expected = None if action == "kpi_empty" else 0.25
        assert result["value"] == expected
        assert result["status"] == ("not_applicable" if expected is None else "ok")
        return "metric", result
    if action.startswith("router_"):
        intent = action.removeprefix("router_")
        result = t.plan(intent)
        assert result == {"lookup": "read_sql", "metric": "registered_kpi", "change": "request_change"}[intent]
        return "routed", {"tool": result}
    raise AssertionError("scenario action did not produce an outcome: " + action)


def load_cases():
    return json.loads((Path(__file__).resolve().parents[1] / "data" / "scenarios.json").read_text(encoding="utf-8"))


def run_case(case):
    with tempfile.TemporaryDirectory(prefix="approval-lab-") as directory:
        sandbox = Sandbox(directory, empty=case["action"] == "kpi_empty")
        details = {}
        try:
            actual, details = perform(sandbox, case["action"])
        except WorkflowError as error:
            actual = error.code
        except Exception as error:
            actual = "unexpected_error"
            details = {"error_type": type(error).__name__, "message": str(error)}
        state = sandbox.state()
        correct_outcome = actual == case["expected"]
        correct_state = state["mutations"] == case["mutations"]
        correct_audit = state["execution_audit_events"] == case["mutations"]
        return {"case_id": case["id"], "split": case["split"], "category": case["category"],
                "action": case["action"], "expected": case["expected"], "actual": actual,
                "passed": correct_outcome and correct_state and correct_audit,
                "checks": {"outcome": correct_outcome, "mutation_count": correct_state, "atomic_execution_audit": correct_audit},
                "state": state, "details": details}
