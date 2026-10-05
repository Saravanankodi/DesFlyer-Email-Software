"""Dependency-free static/data integrity checks for the checked-in project.

Run with: python smoke_checks.py
Full Flask/SMTP integration tests require the project's requirements.txt
installed in the target Windows environment.
"""

import ast
import os
import sqlite3

ROOT = os.path.dirname(os.path.abspath(__file__))

for rel in ("app.py", "config.py", "desktop_launcher.py", "worker.py",
            "services/campaign_service.py", "services/email_service.py"):
    path = os.path.join(ROOT, rel)
    with open(path, encoding="utf-8") as handle:
        ast.parse(handle.read(), filename=rel)
    print(f"PASS syntax: {rel}")


db_path = os.path.join(ROOT, "database", "desflyer.db")
if os.path.exists(db_path):
    con = sqlite3.connect(db_path)
    queries = {
        "campaign recipient totals": """
            SELECT c.id FROM campaigns c
            LEFT JOIN campaign_recipients cr ON cr.campaign_id = c.id
            GROUP BY c.id HAVING c.total_recipients != COUNT(cr.id)
        """,
        "campaign sent totals": """
            SELECT c.id FROM campaigns c
            LEFT JOIN campaign_recipients cr ON cr.campaign_id = c.id
            GROUP BY c.id HAVING c.sent_count != COALESCE(SUM(cr.status='SENT'),0)
        """,
        "campaign failed totals": """
            SELECT c.id FROM campaigns c
            LEFT JOIN campaign_recipients cr ON cr.campaign_id = c.id
            GROUP BY c.id HAVING c.failed_count != COALESCE(SUM(cr.status='FAILED'),0)
        """,
        "orphan campaign email logs": """
            SELECT cr.id FROM campaign_recipients cr
            LEFT JOIN email_logs e ON e.id = cr.email_log_id
            WHERE e.id IS NULL
        """,
        "stuck sending recipients": "SELECT id FROM campaign_recipients WHERE status='SENDING'",
    }
    for name, query in queries.items():
        rows = con.execute(query).fetchall()
        if rows:
            raise SystemExit(f"FAIL {name}: {rows[:10]}")
        print(f"PASS data: {name}")
    con.close()
else:
    print("SKIP data: database/desflyer.db is not present")

print("All smoke checks passed.")
