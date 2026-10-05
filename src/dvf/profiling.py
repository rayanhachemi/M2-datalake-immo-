"""Profiling des fichiers bronze DVF : complétude, cardinalité, stats, anomalies.

Lit bronze/dvf/dvf_{year}_cibles.txt (produits par main.py) et écrit
docs/dvf/profiling/colonnes_{year}.csv. Uniquement des agrégats : aucune
ligne ni adresse n'est exportée (CGU DGFiP).

Usage :
    python src/dvf/profiling.py              # les 5 millésimes
    python src/dvf/profiling.py --year 2024  # un seul millésime
"""

import argparse
import sys
from pathlib import Path

import pandas as pd
import pyarrow as pa
import pyarrow.csv as pacsv

from main import BRONZE, DEPTS_CIBLES, MILLÉSIMES, REGIONS

PROFILING = Path(__file__).resolve().parents[2] / "docs" / "dvf" / "profiling"

# colonnes numériques DVF (décimales à virgule dans la source)
NUM_COLS = [
    "Valeur fonciere", "Surface reelle bati", "Nombre pieces principales",
    "Surface terrain", "Nombre de lots", "Surface Carrez du 1er lot",
]
# colonnes catégorielles dont on affiche les modalités (pas d'adresse : CGU DGFiP)
CAT_COLS = ["Nature mutation", "Type local", "Nature culture", "Code departement"]


def _num(s: pd.Series) -> pd.Series:
    """String DVF (virgule décimale) → float64, vides/invalides en NaN."""
    return pd.to_numeric(s.str.replace(",", ".", regex=False), errors="coerce").astype("float64")


def _region_of(dept: str) -> str:
    return next((r for r, depts in REGIONS.items() if dept in depts), "autre")


def profile_year(year: int) -> pd.DataFrame:
    """Profiling d'un fichier bronze DVF : complétude, cardinalité, stats, anomalies.

    Écrit docs/dvf/profiling/colonnes_{year}.csv (une ligne par colonne)
    et affiche un résumé console. Aucune donnée ligne à ligne n'est exportée.
    """
    src = BRONZE / f"dvf_{year}_cibles.txt"
    if not src.exists():
        raise FileNotFoundError(f"{src} absent — lancer d'abord l'ingestion")

    # tout en string : sinon inférence int → perte des zéros initiaux ("01" → "1")
    with open(src, encoding="utf-8") as f:
        header = f.readline().rstrip("\n").split("|")
    table = pacsv.read_csv(
        src,
        parse_options=pacsv.ParseOptions(delimiter="|"),
        convert_options=pacsv.ConvertOptions(
            column_types={c: pa.string() for c in header}, strings_can_be_null=True,
        ),
    )
    df = table.to_pandas(types_mapper=pd.ArrowDtype)
    n = len(df)
    print(f"\n=== DVF {year} — {n:,} lignes × {df.shape[1]} colonnes ===")

    # --- profil par colonne ---
    rows = []
    for col in df.columns:
        s = df[col].str.strip().replace("", pd.NA)
        nulls = int(s.isna().sum())
        top = s.value_counts().head(1)
        rows.append({
            "colonne": col,
            "non_nuls": n - nulls,
            "pct_nuls": round(nulls / n * 100, 2) if n else 0,
            "nb_distincts": int(s.nunique()),
            "valeur_la_plus_frequente": top.index[0] if len(top) and col in CAT_COLS else None,
        })
    prof = pd.DataFrame(rows)

    vides = prof.loc[prof["pct_nuls"] == 100, "colonne"].tolist()
    print(f"colonnes 100% vides ({len(vides)}) : {', '.join(vides) or '-'}")
    print(prof.loc[prof["pct_nuls"] < 100, ["colonne", "pct_nuls", "nb_distincts"]]
          .to_string(index=False))

    # --- doublons ---
    dup = int(df.duplicated().sum())
    print(f"\nlignes strictement dupliquées : {dup:,} ({dup / n * 100:.2f}%)")
    mut_key = ["Date mutation", "No disposition", "Valeur fonciere", "Code commune", "Section", "No plan"]
    nb_mut = df[mut_key].drop_duplicates().shape[0]
    print(f"mutations distinctes (approx.) : {nb_mut:,} → {n / nb_mut:.2f} lignes/mutation")

    # --- numériques ---
    print("\nstatistiques numériques :")
    for col in NUM_COLS:
        x = _num(df[col])
        d = x.describe(percentiles=[.01, .5, .99])
        print(f"  {col:<28} n={int(d['count']):>9,}  min={d['min']:>12,.0f}  "
              f"p1={d['1%']:>10,.0f}  med={d['50%']:>10,.0f}  p99={d['99%']:>12,.0f}  max={d['max']:>15,.0f}")
        prof.loc[prof["colonne"] == col, ["min", "mediane", "max"]] = [d["min"], d["50%"], d["max"]]

    # --- dates ---
    dates = pd.to_datetime(df["Date mutation"], format="%d/%m/%Y", errors="coerce")
    print(f"\ndates : {dates.min().date()} → {dates.max().date()}  "
          f"(invalides : {int(dates.isna().sum()):,})")
    print("mutations par mois :", dates.dt.month.value_counts().sort_index().to_dict())

    # --- catégorielles ---
    for col in CAT_COLS:
        print(f"\n{col} :")
        print(df[col].value_counts(dropna=False).head(15).to_string())

    print("\nlignes par région :")
    print(df["Code departement"].map(_region_of).value_counts().to_string())

    # --- anomalies métier ---
    vf = _num(df["Valeur fonciere"])
    surf = _num(df["Surface reelle bati"])
    bati = df["Type local"].isin(["Maison", "Appartement"])
    anomalies = {
        "valeur fonciere manquante": int(vf.isna().sum()),
        "valeur fonciere <= 1 €": int((vf <= 1).sum()),
        "valeur fonciere > 50 M€": int((vf > 50e6).sum()),
        "maison/appart surface bâtie nulle ou absente": int((bati & ~(surf > 0)).sum()),
        "maison/appart surface bâtie > 1000 m²": int((bati & (surf > 1000)).sum()),
        "département hors cibles": int((~df["Code departement"].isin(DEPTS_CIBLES)).sum()),
        "texte mal encodé (Ã)": int(df["Type local"].str.contains("Ã", regex=False).sum()),
    }
    print("\nanomalies :")
    for k, v in anomalies.items():
        print(f"  {k:<48} {v:>10,}")

    PROFILING.mkdir(parents=True, exist_ok=True)
    out = PROFILING / f"colonnes_{year}.csv"
    prof.to_csv(out, index=False, encoding="utf-8")
    print(f"\n✔ profil colonnes → {out}")
    return prof


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--year", type=int, choices=list(MILLÉSIMES), help="millésime unique à profiler")
    args = parser.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")  # console Windows cp1252

    for year in [args.year] if args.year else sorted(MILLÉSIMES):
        profile_year(year)


if __name__ == "__main__":
    main()
