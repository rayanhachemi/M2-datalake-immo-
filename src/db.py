from sqlalchemy import create_engine, text

PG_URL = (
    "postgresql+psycopg2://22409796:rayanrayan"
    "@10.172.44.23:32951/M2ProjectDataLake"
)


def get_engine():
    return create_engine(PG_URL, pool_pre_ping=True)


def write_table(df, table: str, engine=None) -> None:
    if engine is None:
        engine = get_engine()
    df.to_sql(table, engine, if_exists="replace", index=False)
    with engine.connect() as conn:
        n = conn.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar()
    print(f"   → PostgreSQL : {n:,} lignes dans '{table}'", flush=True)
