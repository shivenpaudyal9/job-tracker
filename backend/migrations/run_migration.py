"""Run the JMI migration against the configured database."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from app.database import engine, DATABASE_URL

if DATABASE_URL.startswith("sqlite"):
    print("SQLite detected — skipping pgvector migration (not supported).")
    print("Falling back to JSON-based embedding storage.")
    # Still create tables via SQLAlchemy ORM
    from app.models import Base
    from app.jmi_models import JMIBase
    Base.metadata.create_all(bind=engine)
    JMIBase.metadata.create_all(bind=engine)
    print("SQLite tables created via ORM.")
    sys.exit(0)

from sqlalchemy import text

for migration in ["001_jmi_tables.sql", "002_jmi_columns.sql"]:
    sql_file = os.path.join(os.path.dirname(__file__), migration)
    if not os.path.exists(sql_file):
        print(f"Skipping {migration} (not found)")
        continue
    with open(sql_file) as f:
        sql = f.read()
    with engine.connect() as conn:
        for statement in sql.split(";"):
            stmt = statement.strip()
            if stmt:
                try:
                    conn.execute(text(stmt))
                except Exception as e:
                    print(f"Warning ({migration}): {e}")
        conn.commit()
    print(f"Migration {migration} applied.")
