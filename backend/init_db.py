"""
Initialize Database

Creates all tables in the database.
Run: python init_db.py
"""

from app.database import engine, Base
from app.models import (
    RawEmail,
    Application,
    ApplicationEvent,
    Link,
    Company,
    ManualReview,
    ExportLog,
)

print("=" * 80)
print("INITIALIZING DATABASE")
print("=" * 80)

try:
    print("\nDebug info:")
    print(f"  Base.metadata.tables: {list(Base.metadata.tables.keys())}")
    print(f"  Engine: {engine}")
    print(f"  Database URL: {engine.url}")

    print("\nCreating all tables...")

    # Create tables
    Base.metadata.create_all(bind=engine)

    # Verify tables were created
    from sqlalchemy import inspect
    inspector = inspect(engine)
    tables = inspector.get_table_names()

    if len(tables) == 0:
        print("[ERROR] No tables were created!")
        print("Trying to diagnose the issue...")
        print(f"  Base has {len(Base.metadata.tables)} table definitions")
        print(f"  Tables defined: {list(Base.metadata.tables.keys())}")
    else:
        print(f"[SUCCESS] {len(tables)} tables created successfully!")
        print("\nTables created:")
        for table in tables:
            columns = inspector.get_columns(table)
            print(f"  - {table} ({len(columns)} columns)")

    print("\n" + "=" * 80)
    print("DATABASE READY")
    print("=" * 80)
    print("\nNext steps:")
    print("1. Start API: python -m uvicorn app.main:app --reload")
    print("2. Visit docs: http://localhost:8000/docs")
    print("3. Test endpoints or sync Outlook emails")

except Exception as e:
    print(f"[ERROR] Failed to create tables: {e}")
    import traceback
    traceback.print_exc()
