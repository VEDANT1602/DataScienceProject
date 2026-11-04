"""Transactional workflow with transaction-specific approvals.

Principal construction is a TRUSTED application boundary, not authentication.
Never construct a Principal from model output or unverified request JSON.
"""

from contextlib import closing, contextmanager
from dataclasses import dataclass
from pathlib import Path
import base64
import hashlib
import hmac
import json
import secrets
import sqlite3
import time


class WorkflowError(Exception):
    def __init__(self, code, message=None):
        self.code = code
        super().__init__(message or code)


@dataclass(frozen=True)
class Principal:
    tenant: str
    actor: str
    roles: frozenset

    def __post_init__(self):
        object.__setattr__(self, "roles", frozenset(self.roles))
        if not self.actor or len(self.actor) > 80:
            raise ValueError("actor must be nonempty and at most 80 characters")


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def digest(value):
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def snapshot_payload(payload):
    """Detach caller-owned JSON before validation, signing, or lock waits.

    Every later check and write uses this single snapshot. A concurrent change
    during serialization can fail closed; it must never change an already
    checked action while the database transaction waits for its lock.
    """
    if type(payload) is not dict:
        raise WorkflowError("invalid_payload")
    try:
        return json.loads(canonical(payload))
    except (TypeError, ValueError, RuntimeError, RecursionError):
        raise WorkflowError("invalid_payload") from None


SCHEMA = """
CREATE TABLE accounts(id TEXT PRIMARY KEY, name TEXT NOT NULL, plan TEXT NOT NULL,
                      active INTEGER NOT NULL, version INTEGER NOT NULL);
CREATE TABLE cases(id TEXT PRIMARY KEY, account_id TEXT NOT NULL REFERENCES accounts(id),
                   status TEXT NOT NULL, priority INTEGER NOT NULL, version INTEGER NOT NULL);
CREATE TABLE requests(id TEXT PRIMARY KEY, actor TEXT NOT NULL, operation TEXT NOT NULL,
 payload TEXT NOT NULL, payload_digest TEXT NOT NULL, expected_version INTEGER NOT NULL,
 expires_at INTEGER NOT NULL, state TEXT NOT NULL CHECK(state IN ('pending','approved','executed')),
 reviewer TEXT, receipt TEXT, idempotency_key TEXT NOT NULL, fingerprint TEXT NOT NULL,
 UNIQUE(actor,idempotency_key));
CREATE TABLE audit(seq INTEGER PRIMARY KEY AUTOINCREMENT, at INTEGER NOT NULL,
 actor TEXT NOT NULL, action TEXT NOT NULL, request_id TEXT, detail TEXT NOT NULL);
"""


class Engine:
    def __init__(self, tenant_paths, signing_key, clock=time.time, failpoint=None):
        if not isinstance(signing_key, bytes) or len(signing_key) < 32:
            raise ValueError("signing key must contain at least 32 bytes")
        self.paths = {k: Path(v).resolve() for k, v in tenant_paths.items()}
        if len(set(self.paths.values())) != len(self.paths):
            raise ValueError("tenants must use distinct physical database files")
        self.key, self.clock, self.failpoint = signing_key, clock, failpoint

    @classmethod
    def seed(cls, directory, signing_key=None, clock=time.time, failpoint=None, empty=False):
        """Create new fictional tenant fixtures. Refuses to overwrite existing DBs."""
        directory = Path(directory)
        directory.mkdir(parents=True, exist_ok=True)
        paths = {tenant: directory / (tenant + ".sqlite3") for tenant in ("north", "south")}
        if any(p.exists() for p in paths.values()):
            raise ValueError("fixture destination already contains a database")
        for tenant, path in paths.items():
            with closing(sqlite3.connect(path)) as db:
                db.executescript(SCHEMA)
                if not empty:
                    rows = [(f"A{i:02}", f"{tenant}-account-{i:02}", "pro" if i % 3 == 0 else "standard", 1, 0)
                            for i in range(1, 13)]
                    db.executemany("INSERT INTO accounts VALUES (?,?,?,?,?)", rows)
                    db.executemany("INSERT INTO cases VALUES (?,?,?,?,?)", [
                        (f"C{i:02}", f"A{i:02}", "resolved" if i % 4 == 0 else "open", i % 3, 0)
                        for i in range(1, 13)])
                db.commit()
        return cls(paths, signing_key or secrets.token_bytes(32), clock, failpoint)

    def path(self, principal):
        if not isinstance(principal, Principal) or principal.tenant not in self.paths:
            raise WorkflowError("unknown_tenant")
        return self.paths[principal.tenant]

    def require(self, principal, *roles):
        self.path(principal)
        if not principal.roles.intersection(roles):
            raise WorkflowError("forbidden")

    def _connect(self, principal):
        db = sqlite3.connect(self.path(principal), timeout=10, isolation_level=None)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys=ON")
        return db

    def _audit(self, db, principal, action, request_id, detail):
        db.execute("INSERT INTO audit(at,actor,action,request_id,detail) VALUES (?,?,?,?,?)",
                   (int(self.clock()), principal.actor, action, request_id, canonical(detail)))

    @contextmanager
    def _transaction(self, principal):
        db = self._connect(principal)
        try:
            db.execute("BEGIN IMMEDIATE")
            yield db
            db.execute("COMMIT")
        except BaseException:
            if db.in_transaction:
                db.execute("ROLLBACK")
            raise
        finally:
            db.close()

    @staticmethod
    def _validate(operation, payload, expected_version):
        if type(expected_version) is not int or expected_version < 0:
            raise WorkflowError("invalid_version")
        specs = {
            "set_plan": ({"account_id", "plan"}, "account_id", "plan", {"standard", "pro", "enterprise"}),
            "set_case_status": ({"case_id", "status"}, "case_id", "status", {"open", "investigating", "resolved"}),
        }
        if operation not in specs:
            raise WorkflowError("unsupported_operation")
        keys, target, field, allowed = specs[operation]
        if not isinstance(payload, dict) or set(payload) != keys:
            raise WorkflowError("invalid_payload")
        if not isinstance(payload[target], str) or not 1 <= len(payload[target]) <= 40:
            raise WorkflowError("invalid_payload")
        if not isinstance(payload[field], str) or payload[field] not in allowed:
            raise WorkflowError("invalid_payload")
        return ("accounts", "id", "plan", target) if operation == "set_plan" else ("cases", "id", "status", target)

    def request_change(self, principal, operation, payload, expected_version, idempotency_key, ttl=120):
        self.require(principal, "requester")
        payload = snapshot_payload(payload)
        table, _, _, target = self._validate(operation, payload, expected_version)
        if not isinstance(idempotency_key, str) or not 1 <= len(idempotency_key) <= 100:
            raise WorkflowError("invalid_idempotency_key")
        if type(ttl) is not int or not 1 <= ttl <= 600:
            raise WorkflowError("invalid_ttl")
        fingerprint = digest([operation, payload, expected_version, ttl])
        with self._transaction(principal) as db:
            old = db.execute("SELECT * FROM requests WHERE actor=? AND idempotency_key=?",
                             (principal.actor, idempotency_key)).fetchone()
            if old:
                if old["fingerprint"] != fingerprint:
                    raise WorkflowError("idempotency_conflict")
                return {"request_id": old["id"], "state": old["state"], "replayed": True}
            resource = db.execute(f"SELECT version FROM {table} WHERE id=?", (payload[target],)).fetchone()
            if resource is None:
                raise WorkflowError("resource_not_found")
            if resource["version"] != expected_version:
                raise WorkflowError("stale_version")
            request_id = secrets.token_hex(16)
            db.execute("INSERT INTO requests VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", (
                request_id, principal.actor, operation, canonical(payload), digest(payload), expected_version,
                int(self.clock()) + ttl, "pending", None, None, idempotency_key, fingerprint))
            self._audit(db, principal, "requested", request_id, {"operation": operation, "payload_digest": digest(payload)})
            return {"request_id": request_id, "state": "pending", "replayed": False}

    def _request(self, db, request_id):
        row = db.execute("SELECT * FROM requests WHERE id=?", (request_id,)).fetchone()
        if row is None:
            raise WorkflowError("request_not_found")
        return row

    def review(self, principal, request_id):
        self.require(principal, "reviewer")
        db = self._connect(principal)
        try:
            row = self._request(db, request_id)
            return {"request_id": row["id"], "requester": row["actor"], "operation": row["operation"],
                    "payload": json.loads(row["payload"]), "payload_digest": row["payload_digest"],
                    "expected_version": row["expected_version"], "expires_at": row["expires_at"], "state": row["state"]}
        finally:
            db.close()

    @staticmethod
    def _claims(tenant, row):
        return {"request_id": row["id"], "tenant": tenant, "actor": row["actor"], "reviewer": row["reviewer"],
                "operation": row["operation"], "payload_digest": row["payload_digest"],
                "expected_version": row["expected_version"], "expires_at": row["expires_at"]}

    def _sign(self, claims):
        body = canonical(claims).encode("utf-8")
        signature = hmac.new(self.key, body, hashlib.sha256).digest()
        return ".".join(base64.urlsafe_b64encode(x).decode("ascii").rstrip("=") for x in (body, signature))

    def _verify(self, token):
        try:
            if not isinstance(token, str) or len(token) > 4096:
                raise ValueError()
            chunks = token.split(".")
            if len(chunks) != 2:
                raise ValueError()
            body, signature = [base64.b64decode(x + "=" * (-len(x) % 4), altchars=b"-_", validate=True) for x in chunks]
            expected = hmac.new(self.key, body, hashlib.sha256).digest()
            if not hmac.compare_digest(expected, signature):
                raise ValueError()
            claims = json.loads(body)
            if not isinstance(claims, dict) or body.decode("utf-8") != canonical(claims):
                raise ValueError()
            return claims
        except (ValueError, TypeError, UnicodeError):
            raise WorkflowError("invalid_approval") from None

    def approve(self, principal, request_id, acknowledged_digest):
        self.require(principal, "reviewer")
        with self._transaction(principal) as db:
            row = self._request(db, request_id)
            if row["actor"] == principal.actor:
                raise WorkflowError("self_approval")
            if int(self.clock()) >= row["expires_at"]:
                raise WorkflowError("expired")
            if acknowledged_digest != row["payload_digest"]:
                raise WorkflowError("review_mismatch")
            if row["state"] == "executed" or (row["state"] == "approved" and row["reviewer"] != principal.actor):
                raise WorkflowError("invalid_transition")
            if row["state"] == "pending":
                db.execute("UPDATE requests SET state='approved', reviewer=? WHERE id=?", (principal.actor, request_id))
                self._audit(db, principal, "approved", request_id, {"payload_digest": row["payload_digest"]})
            row = self._request(db, request_id)
            return self._sign(self._claims(principal.tenant, row))

    def execute(self, principal, request_id, operation, payload, expected_version, approval):
        self.require(principal, "requester")
        payload = snapshot_payload(payload)
        table, _, field, target = self._validate(operation, payload, expected_version)
        claims = self._verify(approval)
        supplied = {"request_id": request_id, "tenant": principal.tenant, "actor": principal.actor,
                    "operation": operation, "payload_digest": digest(payload), "expected_version": expected_version}
        if any(claims.get(key) != value for key, value in supplied.items()):
            raise WorkflowError("approval_binding_mismatch")
        if type(claims.get("expires_at")) is not int or int(self.clock()) >= claims["expires_at"]:
            raise WorkflowError("expired")
        with self._transaction(principal) as db:
            row = self._request(db, request_id)
            if claims != self._claims(principal.tenant, row):
                raise WorkflowError("approval_binding_mismatch")
            # The lock may have waited. Re-check expiry at the mutation boundary.
            if int(self.clock()) >= row["expires_at"]:
                raise WorkflowError("expired")
            if row["state"] == "executed":
                return {**json.loads(row["receipt"]), "replayed": True}
            if row["state"] != "approved" or row["reviewer"] is None or row["reviewer"] == principal.actor:
                raise WorkflowError("not_approved")
            changed = db.execute(f"UPDATE {table} SET {field}=?, version=version+1 WHERE id=? AND version=?",
                                 (payload[field], payload[target], expected_version)).rowcount
            if changed != 1:
                raise WorkflowError("stale_version")
            if self.failpoint:
                self.failpoint("after_mutation")
            receipt = {"request_id": request_id, "operation": operation, "target_id": payload[target],
                       "version": expected_version + 1, "state": "executed"}
            db.execute("UPDATE requests SET state='executed', receipt=? WHERE id=?", (canonical(receipt), request_id))
            self._audit(db, principal, "executed", request_id, {"operation": operation, "version": expected_version + 1})
            return {**receipt, "replayed": False}

    def audit(self, principal):
        """Trusted reviewer inspection, not exposed through the SQL tool."""
        self.require(principal, "reviewer")
        db = self._connect(principal)
        try:
            return [dict(row) for row in db.execute("SELECT * FROM audit ORDER BY seq")]
        finally:
            db.close()
