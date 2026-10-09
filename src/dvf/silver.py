"""Silver DVF — une ligne par vente d'un logement unique (maison ou appartement), clé code_commune.

Lit bronze/dvf/dvf_{year}_cibles.txt et écrit :
    silver/dvf_ventes.parquet      une ligne par vente, prix au m² calculé
    silver/dvf_silver_stats.json   volumes après chaque règle, par millésime

Structure DVF (cf. docs/dvf/profiling) : une vente est éclatée en plusieurs lignes, une par
local × nature de culture du terrain. La valeur foncière est répétée sur chaque ligne et un
même local est répété sur chaque ligne de culture : rien ne s'additionne ligne à ligne.

Règles :
    - encodage : le bronze a été décodé en latin-1 alors que la source est en UTF-8
      ("DÃ©pendance") ; réparé ici par ré-encodage latin-1 -> UTF-8
    - lignes strictement identiques supprimées
    - vente = (date, nature, valeur, département, commune, section, n° de plan) ; DVF public n'a
      pas d'identifiant de mutation. Une vente sur plusieurs parcelles est découpée par parcelle,
      seule la parcelle portant le logement est gardée
    - locaux dédoublonnés sur (type, surface, pièces, 1er lot), terrain sur (culture, surface)
    - natures gardées : Vente et VEFA (adjudications, échanges, expropriations exclues)
    - un seul logement par vente, aucun local professionnel (sinon prix non attribuable) ;
      les dépendances (caves, parkings) sont tolérées et comptées
    - valeur >= 1 000 €, surface bâtie entre 9 et 1 000 m², prix au m² entre 100 et 30 000 €
    - arrondissements rattachés à leur commune (751xx -> 75056, 6938x -> 69123) pour la jointure
      avec INSEE et OSM ; le code d'arrondissement est conservé à part
    - un même logement (parcelle + lot + type + surface, cf. profiling --reventes) vendu le même
      jour à des prix différents : vente en plusieurs parts ou double saisie, prix non fiable,
      toutes ses ventes de ce jour sont exclues
    - reventes à dates différentes gardées (vraies transactions) ; revente_moins_30j signale
      une autre vente du même logement à moins de 30 jours, avant ou après

CGU DGFiP : ni adresse, ni numéro de voie, ni parcelle dans le silver (ré-identification).

Usage :
    python src/dvf/silver.py
"""

import json
import sys
from pathlib import Path

import pandas as pd
import pyarrow as pa
import pyarrow.csv as pacsv

from main import BRONZE, MILLÉSIMES, REGIONS

SILVER = Path(__file__).resolve().parents[2] / "silver"

COLONNES = [
    "Date mutation", "Nature mutation", "Valeur fonciere", "Code departement", "Code commune",
    "Commune", "Section", "No plan", "1er lot", "Type local", "Surface reelle bati",
    "Nombre pieces principales", "Nature culture", "Surface terrain",
]
CLE_VENTE = ["Date mutation", "Nature mutation", "Valeur fonciere", "Code departement",
             "Code commune", "Section", "No plan"]
NATURES = {"Vente", "Vente en l'état futur d'achèvement"}
LOGEMENTS = {"Maison", "Appartement"}
LOCAL_PRO = "Local industriel. commercial ou assimilé"

VALEUR_MIN = 1_000
SURFACE_MIN, SURFACE_MAX = 9, 1_000
PRIX_M2_MIN, PRIX_M2_MAX = 100, 30_000

# arrondissements DVF -> commune INSEE (Marseille hors régions cibles)
ARRONDISSEMENTS = {"751": "75056", "6938": "69123"}

# identité approchée d'un logement, utilisée en interne puis retirée (parcelle non publiée)
BIEN = ["Code departement", "Code commune", "Section", "No plan", "Type local", "1er lot",
        "Surface reelle bati"]
DELAI_REVENTE_J = 30

REGION_PAR_DEPT = {d: r for r, depts in REGIONS.items() for d in depts}


def reparer_encodage(s: pd.Series) -> pd.Series:
    """Annule le double décodage UTF-8 lu en latin-1, sur les modalités distinctes seulement."""
    def un(v):
        try:
            return v.encode("latin-1").decode("utf-8")
        except (UnicodeEncodeError, UnicodeDecodeError):
            return v
    return s.map({v: un(v) for v in s.dropna().unique()})


def num(s: pd.Series) -> pd.Series:
    """String DVF (virgule décimale) -> float64."""
    return pd.to_numeric(s.str.replace(",", ".", regex=False), errors="coerce")


def lire(year: int) -> pd.DataFrame:
    src = BRONZE / f"dvf_{year}_cibles.txt"
    table = pacsv.read_csv(
        src,
        parse_options=pacsv.ParseOptions(delimiter="|"),
        convert_options=pacsv.ConvertOptions(
            include_columns=COLONNES,
            column_types={c: pa.string() for c in COLONNES},  # garde les zéros initiaux ("01")
            strings_can_be_null=True,
        ),
    )
    return table.to_pandas()


def cle_bien(df: pd.DataFrame) -> pd.Series:
    """Identité approchée d'un logement : colonnes BIEN concaténées (vectorisé)."""
    cle = df[BIEN[0]].fillna("")
    for col in BIEN[1:]:
        cle = cle + "|" + df[col].fillna("")
    return cle


def code_commune(dept: pd.Series, commune: pd.Series) -> tuple[pd.Series, pd.Series]:
    """Code INSEE de la commune entière, et code d'arrondissement (sinon vide)."""
    code = dept + commune.str.zfill(3)
    commune_entiere = code.copy()
    for prefixe, cible in ARRONDISSEMENTS.items():
        commune_entiere = commune_entiere.mask(code.str.startswith(prefixe), cible)
    arrondissement = code.where(commune_entiere != code)
    return commune_entiere, arrondissement


def ventes_annee(year: int, stats: dict) -> pd.DataFrame:
    st = stats.setdefault(str(year), {})
    df = lire(year)
    st["lignes_bronze"] = len(df)

    for col in ("Nature mutation", "Type local", "Commune"):
        df[col] = reparer_encodage(df[col])

    df = df.drop_duplicates()
    st["lignes_apres_doublons"] = len(df)

    df = df[df["Nature mutation"].isin(NATURES)]
    st["lignes_vente_ou_vefa"] = len(df)

    df["id"] = df.groupby(CLE_VENTE, sort=False, dropna=False).ngroup()
    st["ventes_vente_ou_vefa"] = int(df["id"].nunique())

    # --- locaux : un local répété sur chaque ligne de culture ne compte qu'une fois ---
    locaux = (df.dropna(subset=["Type local"])
                .drop_duplicates(["id", "Type local", "Surface reelle bati",
                                  "Nombre pieces principales", "1er lot"]))
    compte = pd.crosstab(locaux["id"], locaux["Type local"])
    for t in ("Maison", "Appartement", "Dépendance", LOCAL_PRO):
        if t not in compte:
            compte[t] = 0
    st["exclues_sans_local_terrain_ou_parcelle_annexe"] = st["ventes_vente_ou_vefa"] - len(compte)

    nb_logements = compte["Maison"] + compte["Appartement"]
    unique = compte[(nb_logements == 1) & (compte[LOCAL_PRO] == 0)]
    st["exclues_sans_logement_dependance_ou_pro_seuls"] = int((nb_logements == 0).sum())
    st["exclues_plusieurs_logements"] = int((nb_logements >= 2).sum())
    st["exclues_logement_avec_local_pro"] = int(((nb_logements == 1) & (compte[LOCAL_PRO] > 0)).sum())
    st["ventes_un_seul_logement"] = len(unique)

    logement = locaux[locaux["Type local"].isin(LOGEMENTS) & locaux["id"].isin(unique.index)]
    logement = logement.set_index("id")

    # --- terrain : somme des parcelles de culture distinctes ---
    terrain = (df.dropna(subset=["Nature culture"])
                 .drop_duplicates(["id", "Nature culture", "Surface terrain"])
                 .assign(s=lambda d: num(d["Surface terrain"]))
                 .groupby("id")["s"].sum(min_count=1))

    v = pd.DataFrame({
        "date_mutation": pd.to_datetime(logement["Date mutation"], format="%d/%m/%Y"),
        "nature_mutation": logement["Nature mutation"],
        "valeur_fonciere": num(logement["Valeur fonciere"]),
        "type_bien": logement["Type local"],
        "surface_bati": num(logement["Surface reelle bati"]),
        "nb_pieces": num(logement["Nombre pieces principales"]),
        "nb_dependances": unique["Dépendance"].reindex(logement.index),
        "code_departement": logement["Code departement"],
        "code_commune_dvf": logement["Code commune"],
        "nom_commune": logement["Commune"],
        "_bien": cle_bien(logement),
    })
    # surface du terrain : pertinente pour une maison, pas pour un lot de copropriété
    v["surface_terrain"] = terrain.reindex(v.index).where(v["type_bien"] == "Maison")

    # --- filtres de plausibilité ---
    n = len(v)
    v = v[v["valeur_fonciere"] >= VALEUR_MIN]
    st["exclues_valeur_absente_ou_inf_1000"] = n - len(v)

    n = len(v)
    v = v[v["surface_bati"].between(SURFACE_MIN, SURFACE_MAX)]
    st[f"exclues_surface_hors_{SURFACE_MIN}_{SURFACE_MAX}"] = n - len(v)

    v["prix_m2"] = (v["valeur_fonciere"] / v["surface_bati"]).round(0)
    n = len(v)
    v = v[v["prix_m2"].between(PRIX_M2_MIN, PRIX_M2_MAX)]
    st[f"exclues_prix_m2_hors_{PRIX_M2_MIN}_{PRIX_M2_MAX}"] = n - len(v)

    v["code_commune"], v["code_arrondissement"] = code_commune(v["code_departement"],
                                                               v.pop("code_commune_dvf"))
    v["region"] = v["code_departement"].map(REGION_PAR_DEPT)
    v["annee"] = year
    v["id_vente"] = f"{year}-" + v.index.astype(str)

    print(f"   {year} : {st['lignes_bronze']:>10,} lignes -> {len(v):>8,} ventes", flush=True)
    return v


def traiter_reventes(df: pd.DataFrame, stats: dict) -> pd.DataFrame:
    """Inter-millésimes : exclut les prix multiples d'un même jour, signale les reventes rapides."""
    prix_du_jour = df.groupby(["_bien", "date_mutation"])["valeur_fonciere"].transform("nunique")
    exclues = df[prix_du_jour > 1]
    for year, n in exclues["annee"].value_counts().items():
        stats[str(year)]["exclues_meme_logement_meme_jour_prix_differents"] = int(n)
    df = df[prix_du_jour == 1].sort_values(["_bien", "date_mutation"])

    par_bien = df.groupby("_bien")["date_mutation"]
    avant = par_bien.diff().dt.days
    apres = -par_bien.diff(-1).dt.days
    df["revente_moins_30j"] = (avant < DELAI_REVENTE_J) | (apres < DELAI_REVENTE_J)

    for year, v in df.groupby("annee"):
        st = stats[str(year)]
        st.setdefault("exclues_meme_logement_meme_jour_prix_differents", 0)
        st["ventes_silver"] = len(v)
        st["ventes_revente_moins_30j"] = int(v["revente_moins_30j"].sum())
        st["ventes_par_type"] = v["type_bien"].value_counts().to_dict()
    return df.drop(columns="_bien")


def main():
    sys.stdout.reconfigure(encoding="utf-8")  # console Windows cp1252
    stats = {}

    print("lecture du bronze", flush=True)
    df = pd.concat([ventes_annee(y, stats) for y in sorted(MILLÉSIMES)], ignore_index=True)
    df = traiter_reventes(df, stats)

    df = df[[
        "id_vente", "annee", "date_mutation", "nature_mutation", "type_bien",
        "valeur_fonciere", "surface_bati", "prix_m2", "nb_pieces", "surface_terrain",
        "nb_dependances", "revente_moins_30j", "region", "code_departement", "code_commune", "code_arrondissement",
        "nom_commune",
    ]].astype({
        "id_vente": "string", "nature_mutation": "category", "type_bien": "category",
        "region": "category", "code_departement": "string", "code_commune": "string",
        "code_arrondissement": "string", "nom_commune": "string",
        "nb_pieces": "Int16", "nb_dependances": "Int16", "annee": "int16",
    }).sort_values(["annee", "code_commune", "date_mutation"])

    stats["total"] = {
        "ventes": len(df),
        "exclues_meme_logement_meme_jour_prix_differents": sum(
            stats[str(y)]["exclues_meme_logement_meme_jour_prix_differents"] for y in MILLÉSIMES),
        "ventes_revente_moins_30j": int(df["revente_moins_30j"].sum()),
        "communes": int(df["code_commune"].nunique()),
        "ventes_par_region": df["region"].value_counts().to_dict(),
        "prix_m2_median_par_type": df.groupby("type_bien", observed=True)["prix_m2"].median().to_dict(),
        "remplissage_pct": {c: round(df[c].notna().mean() * 100, 1) for c in df.columns},
    }

    SILVER.mkdir(exist_ok=True)
    df.to_parquet(SILVER / "dvf_ventes.parquet", index=False)
    (SILVER / "dvf_silver_stats.json").write_text(json.dumps(stats, indent=2, ensure_ascii=False),
                                                  encoding="utf-8")
    print(json.dumps(stats["total"], indent=2, ensure_ascii=False))
    print(f"\n✔ {len(df):,} ventes × {len(df.columns)} colonnes → {SILVER / 'dvf_ventes.parquet'}")


if __name__ == "__main__":
    main()
