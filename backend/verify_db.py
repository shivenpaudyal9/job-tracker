"""
Verify Database Setup

Checks that all tables exist and can be queried.
"""

from app.database import engine, SessionLocal
from app.models import (
    RawEmail, Application, ApplicationEvent, Link,
    Company, ManualReview, ExportLog
)
from sqlalchemy import inspect

print("=" * 80)
print("VERIFYING DATABASE SETUP")
print("=" * 80)

try:
    # Check tables exist
    inspector = inspect(engine)
    tables = inspector.get_table_names()

    print(f"\nFound {len(tables)} tables:")
    for table in tables:
        columns = inspector.get_columns(table)
        print(f"  - {table} ({len(columns)} columns)")

    # Try to query each table
    db = SessionLocal()

    print("\nTesting queries...")
    print(f"  RawEmails: {db.query(RawEmail).count()} records")
    print(f"  Applications: {db.query(Application).count()} records")
    print(f"  ApplicationEvents: {db.query(ApplicationEvent).count()} records")
    print(f"  Links: {db.query(Link).count()} records")
    print(f"  Companies: {db.query(Company).count()} records")
    print(f"  ManualReviews: {db.query(ManualReview).count()} records")
    print(f"  ExportLogs: {db.query(ExportLog).count()} records")

    db.close()

    print("\n" + "=" * 80)
    print("[SUCCESS] Database is working correctly!")
    print("=" * 80)

except Exception as e:
    print(f"\n[ERROR] Database verification failed: {e}")
    import traceback
    traceback.print_exc()
