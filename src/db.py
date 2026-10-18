import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv(Path(__file__).resolve().parents[1] / ".env")


def get_engine():
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_URL manquant : créer .env à partir de .env.example")
    return create_engine(url, pool_pre_ping=True)


def write_table(df, table: str, engine=None) -> None:
    if os.environ.get("SILVER_SKIP_DB") == "1":
        print(f"   → PostgreSQL ignoré pour '{table}' (SILVER_SKIP_DB=1)", flush=True)
        return
    if engine is None:
        engine = get_engine()
    df.to_sql(table, engine, if_exists="replace", index=False)
    table_sql = engine.dialect.identifier_preparer.quote(table)
    with engine.connect() as conn:
        n = conn.execute(text(f"SELECT COUNT(*) FROM {table_sql}")).scalar()
    print(f"   → PostgreSQL : {n:,} lignes dans '{table}'", flush=True)
