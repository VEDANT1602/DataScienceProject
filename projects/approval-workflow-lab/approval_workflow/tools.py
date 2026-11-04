"""Small typed tool surface: no arbitrary Python, dynamic imports, or shell."""

import sqlite3
from .core import WorkflowError


FUNCTIONS = frozenset({"count", "sum", "avg", "min", "max", "coalesce", "round", "abs", "lower", "upper", "length"})
TABLES = frozenset({"accounts", "cases"})


class ReadOnlySQL:
    def __init__(self, engine, row_limit=20, instruction_budget=50000):
        if type(row_limit) is not int or not 1 <= row_limit <= 100:
            raise ValueError("row_limit must be between 1 and 100")
        if type(instruction_budget) is not int or instruction_budget < 100:
            raise ValueError("instruction_budget must be at least 100")
        self.engine, self.row_limit, self.budget = engine, row_limit, instruction_budget

    @staticmethod
    def authorize(action, arg1, arg2, database, source):
        if action == sqlite3.SQLITE_SELECT:
            return sqlite3.SQLITE_OK
        # SQLite reports no database/column for count(*)'s table-only read.
        table_count = database is None and arg2 == ""
        if action == sqlite3.SQLITE_READ and (database == "main" or table_count) and arg1 in TABLES:
            return sqlite3.SQLITE_OK
        if action == sqlite3.SQLITE_FUNCTION and (arg2 or "").lower() in FUNCTIONS:
            return sqlite3.SQLITE_OK
        return sqlite3.SQLITE_DENY

    def query(self, principal, sql, parameters=()):
        self.engine.require(principal, "reader", "requester", "reviewer")
        if not isinstance(sql, str) or not sql.strip() or len(sql) > 4096:
            raise WorkflowError("invalid_sql")
        if not isinstance(parameters, (tuple, list)) or len(parameters) > 50:
            raise WorkflowError("invalid_parameters")
        db = sqlite3.connect(self.engine.path(principal).as_uri() + "?mode=ro", uri=True)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA query_only=ON")
        db.setlimit(sqlite3.SQLITE_LIMIT_LENGTH, 65536)
        db.setlimit(sqlite3.SQLITE_LIMIT_SQL_LENGTH, 4096)
        db.setlimit(sqlite3.SQLITE_LIMIT_COLUMN, 64)
        db.setlimit(sqlite3.SQLITE_LIMIT_EXPR_DEPTH, 50)
        db.setlimit(sqlite3.SQLITE_LIMIT_ATTACHED, 0)
        db.set_authorizer(self.authorize)
        consumed = 0

        def progress():
            nonlocal consumed
            consumed += 100
            return int(consumed >= self.budget)

        db.set_progress_handler(progress, 100)
        try:
            cursor = db.execute(sql, parameters)
            if cursor.description is None:
                raise WorkflowError("sql_denied")
            rows = cursor.fetchmany(self.row_limit + 1)
            return {"rows": [dict(row) for row in rows[:self.row_limit]],
                    "truncated": len(rows) > self.row_limit, "row_limit": self.row_limit}
        except sqlite3.Error as error:
            code = "query_budget_exceeded" if "interrupt" in str(error).lower() else "sql_denied"
            raise WorkflowError(code) from None
        finally:
            db.close()


class Tools:
    """Exact registered intents are a contract router, not an LLM planner."""
    INTENTS = {"lookup": "read_sql", "metric": "registered_kpi", "change": "request_change"}
    KPIS = {
        "open_case_count": ("SELECT count(*) AS n FROM cases WHERE status!='resolved'", False),
        "resolved_case_share": ("SELECT coalesce(sum(status='resolved'),0) AS n, count(*) AS d FROM cases", True),
        "active_accounts": ("SELECT count(*) AS n FROM accounts WHERE active=1", False),
        "pro_plan_share": ("SELECT coalesce(sum(plan='pro'),0) AS n, count(*) AS d FROM accounts", True),
    }

    def __init__(self, engine):
        self.engine = engine
        self.sql = ReadOnlySQL(engine)

    def plan(self, intent):
        if not isinstance(intent, str) or intent not in self.INTENTS:
            raise WorkflowError("unsupported_intent")
        return self.INTENTS[intent]

    def kpi(self, principal, name):
        if not isinstance(name, str) or name not in self.KPIS:
            raise WorkflowError("unsupported_kpi")
        query, is_share = self.KPIS[name]
        row = self.sql.query(principal, query)["rows"][0]
        numerator, denominator = row["n"], row.get("d")
        return {"name": name, "numerator": numerator, "denominator": denominator,
                "value": (numerator / denominator if denominator else None) if is_share else numerator,
                "unit": "share" if is_share else "count",
                "status": "not_applicable" if is_share and denominator == 0 else "ok"}
