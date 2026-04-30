"""
scripts/verify_backend.py
==========================
STEP 1 — Backend verification script.
Checks: MODEL_PATH exists | DB connected | /health responds.
Run: python scripts/verify_backend.py
"""

import os
import sys
from pathlib import Path

# ── Setup path ────────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

PASS = "\033[92m[PASS]\033[0m"
FAIL = "\033[91m[FAIL]\033[0m"
INFO = "\033[94m[INFO]\033[0m"

results = []


def check(name: str, ok: bool, detail: str = ""):
    status = PASS if ok else FAIL
    print(f"  {status} {name}" + (f" — {detail}" if detail else ""))
    results.append(ok)


print("\n" + "=" * 55)
print("  AI Green Budget Optimizer — Backend Verification")
print("=" * 55)

# ── Check 1: MODEL_PATH ───────────────────────────────────────────────────────
print("\n[1] Model file")
model_path_str = os.getenv("MODEL_PATH", "")
model_path = PROJECT_ROOT / model_path_str
check("MODEL_PATH env var set", bool(model_path_str), model_path_str)
check("Model .pkl exists on disk", model_path.exists(), str(model_path))

# ── Check 2: DATABASE_URL ─────────────────────────────────────────────────────
print("\n[2] Database")
db_url = os.getenv("DATABASE_URL", "")
check("DATABASE_URL set", bool(db_url), db_url[:40] + "..." if db_url else "")

try:
    from sqlalchemy import create_engine, text
    safe_url = db_url.replace("%", "%%")  # for SQLAlchemy
    engine = create_engine(db_url, connect_args={} if "postgresql" in db_url else {})
    with engine.connect() as conn:
        version = conn.execute(text("SELECT version()")).scalar()
    check("DB connection", True, version[:50])
except Exception as e:
    check("DB connection", False, str(e))

# ── Check 3: Tables ───────────────────────────────────────────────────────────
print("\n[3] DB Tables")
try:
    from sqlalchemy import inspect as sa_inspect
    inspector = sa_inspect(engine)
    tables = inspector.get_table_names()
    expected = ["users", "predictions", "optimizations", "datasets", "budgets"]
    for t in expected:
        check(f"Table '{t}'", t in tables)
except Exception as e:
    check("Table inspection", False, str(e))

# ── Check 4: /health endpoint ─────────────────────────────────────────────────
print("\n[4] API Health")
try:
    import requests
    r = requests.get("http://localhost:8000/health", timeout=5)
    data = r.json()
    check("/health HTTP 200", r.status_code == 200, f"status={data.get('status')}")
    check("DB reported connected", data.get("database") == "connected")
    check("Model loaded in API", data.get("model_loaded", False))
except Exception as e:
    check("/health reachable", False, f"Is uvicorn running? {e}")

# ── Check 5: JWT config ───────────────────────────────────────────────────────
print("\n[5] Auth Config")
jwt_key = os.getenv("JWT_SECRET_KEY", "")
check("JWT_SECRET_KEY set", bool(jwt_key) and jwt_key != "changeme", "***")
check("JWT length >= 32 chars", len(jwt_key) >= 32)

# ── Summary ───────────────────────────────────────────────────────────────────
print("\n" + "=" * 55)
passed = sum(results)
total  = len(results)
color  = "\033[92m" if passed == total else "\033[91m"
print(f"  {color}Result: {passed}/{total} checks passed\033[0m")
print("=" * 55 + "\n")

sys.exit(0 if passed == total else 1)
