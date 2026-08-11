"""
Step 5: Load Gold → PostgreSQL

Reads Gold Delta tables and writes them to PostgreSQL
so the Streamlit dashboard can query them.

Usage:
    python spark_jobs/gold_to_postgres.py
    make load-postgres
"""

import os
import pandas as pd
from sqlalchemy import create_engine, text


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GOLD_DIR = os.path.join(PROJECT_ROOT, "data", "gold")

# PostgreSQL connection
DB_URL = "postgresql://grid_admin:ontario_grid_2026@localhost:5432/ontario_grid"


def get_engine():
    """Create SQLAlchemy engine for PostgreSQL."""
    return create_engine(DB_URL)


def load_table(engine, table_name: str, delta_path: str):
    """Read a Gold Delta table (as Parquet) and load into PostgreSQL."""
    if not os.path.exists(delta_path):
        print(f"  ⚠️  {table_name}: no data found at {delta_path}")
        return

    # Read Delta table as Parquet (pandas can read Parquet directly)
    df = pd.read_parquet(delta_path)

    # Write to PostgreSQL (replace existing table)
    df.to_sql(table_name, engine, if_exists="replace", index=False)

    print(f"  ✅ {table_name}: {len(df)} rows, {len(df.columns)} columns")


if __name__ == "__main__":
    print("=" * 60)
    print("Step 5: Load Gold → PostgreSQL")
    print("=" * 60)

    engine = get_engine()

    # Test connection
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        print("  Connected to PostgreSQL\n")
    except Exception as e:
        print(f"  ❌ Cannot connect to PostgreSQL: {e}")
        print("  Make sure Docker is running: make up")
        exit(1)

    # Load all Gold tables
    gold_tables = {
        "dim_date": os.path.join(GOLD_DIR, "dim_date"),
        "dim_fuel_type": os.path.join(GOLD_DIR, "dim_fuel_type"),
        "fct_hourly_grid_snapshot": os.path.join(GOLD_DIR, "fct_hourly_grid_snapshot"),
        "mart_daily_summary": os.path.join(GOLD_DIR, "mart_daily_summary"),
        "mart_carbon_intensity": os.path.join(GOLD_DIR, "mart_carbon_intensity"),
    }

    for table_name, delta_path in gold_tables.items():
        load_table(engine, table_name, delta_path)

    engine.dispose()
    print("\n✅ All Gold tables loaded into PostgreSQL")
