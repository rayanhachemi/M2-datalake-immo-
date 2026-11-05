"""Resynchronise les trois tables Silver SQL depuis leurs Parquets existants.

Usage : python src/charger_silver_postgres.py
La quatrième table S_communes est créée par src/communes/silver.py.
"""

import io
from pathlib import Path

import pandas as pd
from sqlalchemy import text

from db import get_engine

ROOT = Path(__file__).resolve().parents[1]
SOURCES = {
    "S_dvf_ventes": ROOT / "silver" / "dvf_ventes.parquet",
    "S_osm_poi": ROOT / "silver" / "osm_poi.parquet",
    "S_insee_communes": ROOT / "silver" / "insee_communes.parquet",
}


def charger(nom: str, path: Path) -> None:
    frame = pd.read_parquet(path)
    engine = get_engine()
    try:
        with engine.begin() as conn:
            frame.head(0).to_sql(nom, conn, if_exists="replace", index=False)
            colonnes = ", ".join(f'"{c}"' for c in frame.columns)
            commande = f'COPY "{nom}" ({colonnes}) FROM STDIN WITH (FORMAT CSV, NULL E\'\\\\N\')'
            raw = conn.connection.driver_connection
            for debut in range(0, len(frame), 50_000):
                tampon = io.StringIO()
                frame.iloc[debut:debut + 50_000].to_csv(
                    tampon, index=False, header=False, na_rep="\\N", date_format="%Y-%m-%d")
                tampon.seek(0)
                with raw.cursor() as curseur:
                    curseur.copy_expert(commande, tampon)
            nombre = conn.execute(text(f'SELECT COUNT(*) FROM "{nom}"')).scalar_one()
            if nombre != len(frame):
                raise ValueError(f"{nom} : {nombre} lignes SQL au lieu de {len(frame)}")
        print(f"{nom} : {len(frame):,} lignes chargées depuis {path.name}", flush=True)
    finally:
        engine.dispose()


def main() -> None:
    for nom, path in SOURCES.items():
        charger(nom, path)


if __name__ == "__main__":
    main()
