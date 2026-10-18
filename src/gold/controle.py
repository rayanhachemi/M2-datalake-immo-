"""Contrôles reproductibles des tables Gold, des sources Silver et de PostgreSQL.

Usage : python src/gold/controle.py [--sans-db]
Sorties : gold/controle_stats.json et docs/gold/controle.md
"""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from sqlalchemy import text

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from db import get_engine  # noqa: E402

SILVER = ROOT / "silver"
GOLD = ROOT / "gold"
DOCS = ROOT / "docs" / "gold"
SEUIL = 10


def controle(nom: str, anomalies: int, details: str = "") -> dict:
    return {"nom": nom, "statut": "OK" if anomalies == 0 else "ERREUR",
            "anomalies": int(anomalies), "details": details}


def ecarts_compteurs(source: pd.Series, gold: pd.Series) -> int:
    codes = source.index.union(gold.index)
    return int(source.reindex(codes, fill_value=0).ne(gold.reindex(codes, fill_value=0)).sum())


def par_commune(ventes: pd.DataFrame, masque: pd.Series) -> pd.Series:
    return ventes.loc[masque].groupby("code_commune", observed=True).size()


def verifier(sans_db: bool) -> dict:
    insee = pd.read_parquet(SILVER / "insee_communes.parquet")
    dvf = pd.read_parquet(SILVER / "dvf_ventes.parquet", columns=[
        "id_vente", "code_commune", "annee", "type_bien", "nature_mutation",
        "revente_moins_30j", "prix_m2", "valeur_fonciere"])
    osm = pd.read_parquet(SILVER / "osm_poi.parquet", columns=[
        "code_commune", "categorie", "id_arret", "is_vacant", "date_extract"])
    jointure = pd.read_parquet(GOLD / "jointure_communes.parquet")
    marche = pd.read_parquet(GOLD / "marche_commune_annee_type.parquet")
    communes = pd.read_parquet(GOLD / "communes.parquet")
    stats_jointure = json.loads((GOLD / "jointure_stats.json").read_text(encoding="utf-8"))
    stats_indicateurs = json.loads((GOLD / "indicateurs_stats.json").read_text(encoding="utf-8"))
    checks = []
    add = lambda nom, n, details="": checks.append(controle(nom, n, details))

    codes_insee = set(insee["code_commune"])
    for nom, table in (("INSEE Silver", insee), ("jointure Gold", jointure), ("communes Gold", communes)):
        mauvais = int(table["code_commune"].isna().sum() +
                      (~table["code_commune"].dropna().str.fullmatch(r"\d{5}")).sum() +
                      table["code_commune"].duplicated().sum())
        add(f"Clé communale unique et conforme : {nom}", mauvais)
    cles = ["code_commune", "annee", "type_bien"]
    add("Clé unique du marché et domaines année/type", int(
        marche[cles].isna().any(axis=1).sum() + marche.duplicated(cles).sum() +
        (~marche["code_commune"].str.fullmatch(r"\d{5}")).sum() +
        (~marche["annee"].between(2021, 2025)).sum() +
        (~marche["type_bien"].isin(["Maison", "Appartement"])).sum()))
    add("Communes Gold = référentiel INSEE", len(codes_insee.symmetric_difference(set(jointure["code_commune"]))) +
        len(codes_insee.symmetric_difference(set(communes["code_commune"]))))

    jointure = jointure.set_index("code_commune")
    communes = communes.set_index("code_commune")
    insee = insee.set_index("code_commune")
    colonnes_insee = insee.columns.tolist()
    add("Valeurs INSEE préservées dans la jointure", int(sum(
        (~insee[c].eq(jointure[c]).fillna(False) & ~(insee[c].isna() & jointure[c].isna())).sum()
        for c in colonnes_insee)))
    add("Colonnes de la jointure préservées dans G_communes", int(sum(
        (~jointure[c].eq(communes[c]).fillna(False) & ~(jointure[c].isna() & communes[c].isna())).sum()
        for c in jointure.columns)))
    vente = dvf["nature_mutation"].eq("Vente")
    comparable = vente & ~dvf["revente_moins_30j"]
    ventes = dvf.loc[comparable]
    recent = ventes["annee"].isin([2024, 2025])
    add("Identifiants DVF uniques", int(dvf["id_vente"].isna().sum() + dvf["id_vente"].duplicated().sum()))
    add("Ventes filtrées = volume du marché", abs(len(ventes) - int(marche["nb_ventes"].sum())))
    volumes = ventes.groupby(cles, observed=True).size()
    add("Ventes par commune, année et type", ecarts_compteurs(
        volumes, marche.set_index(cles)["nb_ventes"]), f"{len(volumes):,} groupes")
    add("Volumes DVF communaux joints", ecarts_compteurs(
        ventes.groupby("code_commune", observed=True).size().reindex(insee.index, fill_value=0),
        jointure["nb_ventes_comparables_2021_2025"]))
    add("Ventes récentes par commune", ecarts_compteurs(
        par_commune(ventes, recent).reindex(insee.index, fill_value=0), jointure["nb_ventes_2024_2025"]))
    for type_bien, suffixe in (("Maison", "maison"), ("Appartement", "appartement")):
        add(f"Ventes récentes {suffixe} par commune", ecarts_compteurs(
            par_commune(ventes, recent & ventes["type_bien"].eq(type_bien)).reindex(insee.index, fill_value=0),
            jointure[f"nb_ventes_{suffixe}_2024_2025"]))

    for suffixe, source in (
        ("poi_osm", osm.groupby("code_commune", observed=True).size()),
        ("ecoles", osm.loc[osm["categorie"].eq("education")].groupby("code_commune", observed=True).size()),
        ("sante", osm.loc[osm["categorie"].eq("sante")].groupby("code_commune", observed=True).size()),
        ("commerces_actifs", osm.loc[osm["categorie"].eq("commerce") & ~osm["is_vacant"].fillna(False)]
         .groupby("code_commune", observed=True).size()),
        ("arrets_transport", osm.groupby("code_commune", observed=True)["id_arret"].nunique()),
    ):
        add(f"OSM : nb_{suffixe} par commune", ecarts_compteurs(
            source.reindex(insee.index, fill_value=0), jointure[f"nb_{suffixe}"]))

    mesures = ["prix_m2_median", "prix_m2_moyen", "prix_m2_q1", "prix_m2_q3", "prix_vente_median"]
    petits = marche["nb_ventes"] < SEUIL
    add("Prix annuels masqués sous 10 ventes", int(marche.loc[petits, mesures].notna().sum().sum()))
    add("Prix annuels présents dès 10 ventes", int(marche.loc[~petits, mesures].isna().sum().sum()))
    attendu_mediane = ventes.groupby(cles, observed=True)["prix_m2"].median().round(2)
    publie = marche.loc[~petits].set_index(cles)["prix_m2_median"]
    add("Médianes annuelles recalculées depuis DVF", int((
        ~np.isclose(attendu_mediane.reindex(publie.index), publie, atol=0.011)).sum()))
    marche_trie = marche.sort_values(cles)
    groupes = marche_trie.groupby(["code_commune", "type_bien"], observed=True)
    precedent = groupes["prix_m2_median"].shift()
    annee_precedente = groupes["annee"].shift()
    variation_attendue = (100 * (marche_trie["prix_m2_median"] / precedent - 1)).where(
        marche_trie["annee"] - annee_precedente == 1).round(2)
    add("Variations annuelles et années consécutives", int((
        ~np.isclose(variation_attendue, marche_trie["variation_annuelle_pct"], atol=0.011, equal_nan=True)).sum()))
    v = marche["variation_annuelle_pct"]
    tendance = np.select([v >= 3, v <= -3, v.notna()], ["hausse", "baisse", "stable"], default="non_concluante")
    add("Tendances annuelles cohérentes", int((marche["tendance_annuelle"] != tendance).sum()))
    for suffixe in ("maison", "appartement"):
        nombre = communes[f"nb_ventes_{suffixe}_2024_2025"]
        for mesure in ("median", "moyen"):
            col = f"prix_m2_{mesure}_{suffixe}_2024_2025"
            add(f"Seuil prix récents {suffixe} {mesure}", int(
                communes.loc[nombre < SEUIL, col].notna().sum() +
                communes.loc[nombre >= SEUIL, col].isna().sum()))
        type_bien = "Maison" if suffixe == "maison" else "Appartement"
        prix_recents = ventes.loc[recent & ventes["type_bien"].eq(type_bien)].groupby(
            "code_commune", observed=True)["prix_m2"]
        for mesure, attendu in (("median", prix_recents.median()), ("moyen", prix_recents.mean())):
            col = f"prix_m2_{mesure}_{suffixe}_2024_2025"
            attendu = attendu.reindex(communes.index).where(nombre >= SEUIL).round(2)
            add(f"Prix récents {suffixe} {mesure} recalculés", int((
                ~np.isclose(attendu, communes[col], atol=0.011, equal_nan=True)).sum()))
    for suffixe, compteur in (("ecoles", "nb_ecoles"), ("sante", "nb_sante"),
                              ("commerces_actifs", "nb_commerces_actifs"),
                              ("arrets_transport", "nb_arrets_transport")):
        col = f"densite_{suffixe}_pour_1000_habitants"
        attendu = (1000 * communes[compteur] / communes["population"].where(communes["population"] > 0)).round(2)
        add(f"Densité {suffixe} recalculée", int((
            ~np.isclose(attendu, communes[col], atol=0.011, equal_nan=True)).sum()))

    eligible = (communes["population"].gt(0) & communes["nb_ventes_2024_2025"].ge(SEUIL)
                & communes["dynamique_prix_pct"].notna())
    add("Éligibilité du score", int((eligible != communes["score_eligible"]).sum()))
    scores = ["score_dynamique", "score_activite", "score_equipements", "score_attractivite"]
    add("Scores absents hors éligibilité et présents sinon", int(
        communes.loc[~eligible, scores].notna().sum().sum() + communes.loc[eligible, scores].isna().sum().sum()))
    add("Scores bornés entre 0 et 100", int(sum((~communes[c].dropna().between(0, 100)).sum() for c in scores)))
    combinaison = (0.4 * communes["score_dynamique"] + 0.3 * communes["score_activite"]
                   + 0.3 * communes["score_equipements"])
    add("Pondération 40/30/30 du score", int((
        ~np.isclose(combinaison.loc[eligible], communes.loc[eligible, "score_attractivite"], atol=0.056)).sum()))
    numeriques = [marche.select_dtypes(include="number"), communes.select_dtypes(include="number")]
    add("Aucune valeur numérique infinie", sum(int(np.isinf(t.to_numpy(dtype=float)).sum()) for t in numeriques))

    hors_insee = ventes.loc[~ventes["code_commune"].isin(codes_insee)]
    stats_attendues = [
        (len(dvf), stats_jointure["dvf"]["lignes_silver"]),
        (int((~vente).sum()), stats_jointure["dvf"]["vefa_exclues"]),
        (int((vente & dvf["revente_moins_30j"]).sum()), stats_jointure["dvf"]["reventes_rapides_exclues_parmi_ventes"]),
        (len(ventes), stats_jointure["dvf"]["ventes_comparables"]),
        (len(hors_insee), stats_jointure["jointure"]["ventes_comparables_hors_insee"]),
        (len(marche), stats_indicateurs["marche"]["lignes"]),
        (int(petits.sum()), stats_indicateurs["marche"]["groupes_prix_non_publies_moins_10_ventes"]),
        (int(eligible.sum()), stats_indicateurs["communes"]["score_eligibles"]),
    ]
    add("Statistiques JSON cohérentes", sum(a != b for a, b in stats_attendues))
    add("Codes DVF sans correspondance documentés", int(set(hors_insee["code_commune"]) !=
        set(stats_jointure["jointure"]["codes_dvf_hors_insee"])))
    dates = pd.to_datetime(osm["date_extract"], errors="coerce")
    add("Date d'extraction OSM renseignée", int(dates.isna().sum()))
    for source, sorties in ((SILVER / "insee_communes.parquet", [GOLD / "jointure_communes.parquet", GOLD / "communes.parquet"]),
                            (SILVER / "dvf_ventes.parquet", [GOLD / "jointure_communes.parquet", GOLD / "marche_commune_annee_type.parquet", GOLD / "communes.parquet"]),
                            (SILVER / "osm_poi.parquet", [GOLD / "jointure_communes.parquet", GOLD / "communes.parquet"])):
        add(f"Gold à jour après {source.name}", sum(source.stat().st_mtime > f.stat().st_mtime for f in sorties))

    if not sans_db:
        try:
            engine = get_engine()
            with engine.connect() as conn:
                for table, parquet in (("G_jointure_communes", jointure),
                                       ("G_marche_commune_annee_type", marche), ("G_communes", communes)):
                    quoted = engine.dialect.identifier_preparer.quote(table)
                    n = conn.execute(text(f"SELECT COUNT(*) FROM {quoted}")).scalar_one()
                    add(f"PostgreSQL {table} : nombre de lignes", abs(n - len(parquet)), f"{n:,} lignes")
                for table, colonne, attendu in (("G_jointure_communes", "nb_poi_osm", len(osm)),
                                                  ("G_marche_commune_annee_type", "nb_ventes", len(ventes)),
                                                  ("G_communes", "score_eligible", int(eligible.sum()))):
                    quoted = engine.dialect.identifier_preparer.quote(table)
                    expression = f'SUM("{colonne}"::integer)' if colonne == "score_eligible" else f'SUM("{colonne}")'
                    n = conn.execute(text(f"SELECT {expression} FROM {quoted}")).scalar_one()
                    add(f"PostgreSQL {table} : total {colonne}", abs(int(n) - attendu))
            engine.dispose()
        except Exception as exc:
            add("Accès et lecture PostgreSQL", 1, f"{type(exc).__name__}: {exc}")

    couverture = {
        "communes_insee": len(insee),
        "ventes_comparables": len(ventes),
        "ventes_hors_insee": len(hors_insee),
        "codes_dvf_hors_insee": sorted(hors_insee["code_commune"].unique().tolist()),
        "pourcentage_ventes_hors_insee": round(100 * len(hors_insee) / len(ventes), 3),
        "groupes_marche": len(marche),
        "groupes_prix_masques": int(petits.sum()),
        "communes_score_eligibles": int(eligible.sum()),
        "communes_sans_poi": int(communes["nb_poi_osm"].eq(0).sum()),
        "communes_sans_ventes_recentes": int(communes["nb_ventes_2024_2025"].eq(0).sum()),
        "revenu_median_disponible": int(insee["revenu_median"].notna().sum()),
        "taux_pauvrete_disponible": int(insee["taux_pauvrete"].notna().sum()),
        "dates_extraction_osm": sorted(dates.dropna().dt.date.astype(str).unique().tolist()),
    }
    return {"date_controle_utc": datetime.now(timezone.utc).isoformat(),
            "statut": "OK" if all(c["statut"] == "OK" for c in checks) else "ERREUR",
            "postgresql_controle": not sans_db, "controles": checks, "couverture": couverture}


def ecrire_rapport(rapport: dict) -> None:
    GOLD.mkdir(exist_ok=True)
    DOCS.mkdir(parents=True, exist_ok=True)
    (GOLD / "controle_stats.json").write_text(json.dumps(rapport, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    c = rapport["couverture"]
    lignes = ["# Contrôle Gold", "", f"Exécuté le {rapport['date_controle_utc']} — **{rapport['statut']}**.", "",
              "Rejouer depuis la racine : `python src/gold/controle.py`.", "",
              "## Résultat des contrôles", "", "| Contrôle | Résultat | Anomalies | Détail |",
              "|---|---:|---:|---|"]
    for check in rapport["controles"]:
        lignes.append(f"| {check['nom']} | {check['statut']} | {check['anomalies']} | {check['details']} |")
    lignes += ["", "## Couverture et limites", "",
               f"- Référentiel INSEE : {c['communes_insee']:,} communes ; marché : {c['ventes_comparables']:,} ventes comparables et {c['groupes_marche']:,} groupes annuels.",
               f"- DVF hors INSEE : {c['ventes_hors_insee']:,} ventes ({c['pourcentage_ventes_hors_insee']} %) sur {len(c['codes_dvf_hors_insee'])} codes. Ces ventes restent dans le marché annuel, mais ne sont pas rattachées aux scores communaux.",
               f"- Prix annuels masqués sous {SEUIL} ventes : {c['groupes_prix_masques']:,} groupes ; communes éligibles au score : {c['communes_score_eligibles']:,}.",
               f"- Sans POI OSM : {c['communes_sans_poi']:,} communes ; sans vente récente : {c['communes_sans_ventes_recentes']:,}.",
               f"- Revenu médian présent : {c['revenu_median_disponible']:,} communes ; taux de pauvreté présent : {c['taux_pauvrete_disponible']:,}. Les valeurs INSEE manquantes restent nulles.",
               f"- Dates d'extraction OSM : {', '.join(c['dates_extraction_osm'])}. INSEE concerne 2023 (COG 2026) et DVF 2021–2025 : ces millésimes ne décrivent pas une même année.",
               ""]
    (DOCS / "controle.md").write_text("\n".join(lignes), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sans-db", action="store_true", help="Contrôler uniquement les fichiers Silver et Gold")
    args = parser.parse_args()
    rapport = verifier(args.sans_db)
    ecrire_rapport(rapport)
    erreurs = [c for c in rapport["controles"] if c["statut"] != "OK"]
    print(f"Gold : {len(rapport['controles']) - len(erreurs)}/{len(rapport['controles'])} contrôles OK")
    for erreur in erreurs:
        print(f"ERREUR : {erreur['nom']} — {erreur['anomalies']} anomalie(s) {erreur['details']}")
    print(f"Rapport : {DOCS / 'controle.md'}")
    if erreurs:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
