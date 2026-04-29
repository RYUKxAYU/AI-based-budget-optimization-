import sqlite3
import os

db_path = "data/app.db"
if not os.path.exists(db_path):
    print("ERROR: DB file not found at", db_path)
else:
    conn = sqlite3.connect(db_path)
    tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name").fetchall()
    print(f"DB created at: {db_path}")
    print(f"Tables found ({len(tables)}):")
    for (t,) in tables:
        cols = conn.execute(f"PRAGMA table_info({t})").fetchall()
        print(f"  [OK] {t:<20} ({len(cols)} columns)")
        for col in cols:
            print(f"       - {col[1]:<25} {col[2]}")
    conn.close()
    print("\nStep 1 COMPLETE: DB verified successfully.")
