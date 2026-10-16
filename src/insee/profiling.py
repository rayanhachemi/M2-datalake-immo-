"""Profiling bronze INSEE : complétude, couverture géographique, anomalies.

Usage:
    python src/insee/profiling.py
    python src/insee/profiling.py --dataset DS_FILOSOFI_CC
    python src/insee/profiling.py --region 53
"""

import argparse
import json
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path

import pandas as pd

from main import DATASETS, OUTPUT, REGIONS

PROFILING = Path(__file__).resolve().parents[2] / "docs" / "insee" / "profiling"

MILLESIME = "2026"
TOTAUX = {"_T", "Y_LT2021", "Y_GE15"}  # modalités qui recouvrent les autres : à exclure des sommes

JEUX = {
    "DS_FILOSOFI_CC": "Revenus des habitants (Filosofi)",
    "DS_POPULATIONS_HISTORIQUES": "Populations légales par année",
    "DS_RP_POPULATION_PRINC": "Recensement — habitants",
    "DS_RP_MENAGES_PRINC": "Recensement — ménages",
    "DS_RP_LOGEMENT_PRINC": "Recensement — logements",
    "DS_RP_EMPLOI_LR_PRINC": "Recensement — emploi",
    "DS_RP_DIPLOMES_PRINC": "Recensement — diplômes",
}
DIMENSIONS = {
    "TIME_PERIOD": "année", "FREQ": "périodicité", "UNIT_MEASURE": "unité",
    "FILOSOFI_MEASURE": "indicateur de revenu", "RP_MEASURE": "indicateur recensé",
    "POPREF_MEASURE": "indicateur de population", "SEX": "sexe", "AGE": "tranche d'âge",
    "EDUC": "niveau de diplôme", "EMPSTA_ENQ": "statut d'activité", "CIVIL_STATUS": "situation familiale",
    "COUPLE": "en couple", "NOC": "nombre d'enfants", "OCS": "type d'occupation du logement",
    "TDW": "type de logement", "NOR": "nombre de pièces", "BUILD_END": "époque de construction",
    "NRG_SRC": "mode de chauffage", "CARS": "nombre de voitures", "CARPARK": "stationnement",
    "TSH": "surface du logement", "L_STAY": "ancienneté d'emménagement",
}
INDICATEURS = {
    "MED_SL": "revenu médian", "PR_MD60": "taux de pauvreté", "GI_SL": "indice de Gini",
    "D1_SL": "1er décile de niveau de vie", "D9_SL": "9e décile de niveau de vie",
    "POP": "nombre de personnes", "PMUN": "population municipale", "ONEPERS": "personnes vivant seules",
    "DWELLINGS": "nombre de logements", "DWELLINGS_ROOMS": "nombre de pièces",
    "DWELLINGS_POPSIZE": "personnes vivant dans ces logements",
    "DWELLING_L_STAY": "logements selon l'ancienneté d'emménagement",
}
MODALITES = {
    "_T": "ensemble", "A": "annuel", "M": "hommes", "F": "femmes",
    "DW_MAIN": "résidence principale", "DW_SEC_DW_OCC": "résidence secondaire", "DW_VAC": "logement vacant",
    "Y_LT1919": "avant 1919", "Y1919T1945": "1919 à 1945", "Y1946T1970": "1946 à 1970",
    "Y1971T1990": "1971 à 1990", "Y1991T2005": "1991 à 2005", "Y2006TAAAA": "2006 et après",
    "Y_LT2021": "avant 2021 (total)", "Y_GE15": "15 ans et plus",
}
STATUTS = {
    "A": "diffusé normalement", "O": "non diffusé à ce niveau géographique",
    "F": "librement diffusable", "C": "secret statistique (commune trop petite)",
}


def libelle(code, table, avec_code=True):
    texte = table.get(code)
    if not texte:
        return code
    return f"{texte} ({code})" if avec_code else texte


def dossiers_regions(regions):
    return {"region_%s_%s" % (code, REGIONS[code]) for code in regions}


def profiler(jeu, regions):
    fichiers, modalites, indicateurs = [], defaultdict(Counter), defaultdict(Counter)
    valeurs, unites = defaultdict(list), defaultdict(Counter)
    niveaux, millesimes, statuts, secrets = Counter(), Counter(), Counter(), Counter()
    anomalies, communes, cles = Counter(), set(), set()
    total = vides = 0

    for chemin in sorted((OUTPUT / jeu).rglob("part_*.json")):
        if regions and chemin.parent.name not in dossiers_regions(regions):
            continue
        contenu = json.loads(chemin.read_text(encoding="utf-8"))
        observations = contenu.get("observations", [])
        paging = contenu.get("paging", {})
        vides_fichier = 0

        for obs in observations:
            dims, attrs = obs["dimensions"], obs.get("attributes", {})
            total += 1

            for dim, modalite in dims.items():
                if dim != "GEO":
                    modalites[dim][modalite] += 1

            millesime, niveau, code = (dims["GEO"].split("-") + ["", ""])[:3]
            millesimes[millesime] += 1
            niveaux[niveau] += 1
            if niveau == "COM":
                communes.add(code)
            if millesime != MILLESIME:
                anomalies["millésime géographique différent des autres jeux"] += 1

            if attrs:
                statuts[attrs.get("OBS_STATUS", "non renseigné")] += 1
                secrets[attrs.get("CONF_STATUS", "non renseigné")] += 1
            else:
                anomalies["observation sans statut de diffusion"] += 1

            nom = next((dims[d] for d in dims if d.endswith("_MEASURE") and d != "UNIT_MEASURE"), "?")
            unite = dims.get("UNIT_MEASURE", "?")
            unites[nom][unite] += 1
            indicateurs[nom]["total"] += 1

            valeur = obs["measures"]["OBS_VALUE_NIVEAU"].get("value")
            if valeur is None:
                vides += 1
                vides_fichier += 1
            else:
                indicateurs[nom]["rempli"] += 1
                valeurs[nom].append(valeur)
                if valeur < 0:
                    anomalies["valeur négative"] += 1
                if unite == "PT" and valeur > 100:
                    anomalies["pourcentage supérieur à 100"] += 1

            cle = hash(tuple(sorted(dims.items())))
            if cle in cles:
                anomalies["observation en double"] += 1
            cles.add(cle)

        if not observations:
            anomalies["fichier vide"] += 1
        if paging.get("count") not in (None, len(observations)):
            anomalies["page incomplète"] += 1
        if paging.get("isLast") is False:
            anomalies["page manquante à la suite"] += 1

        fichiers.append({
            "jeu": jeu, "region": chemin.parent.name, "fichier": chemin.name,
            "taille_mo": round(chemin.stat().st_size / 1e6, 2),
            "observations": len(observations), "vides": vides_fichier,
        })

    for dim, compte in modalites.items():
        totaux = sorted(TOTAUX & set(compte))
        if totaux:
            anomalies["%s : %s sont des totaux, ne pas les additionner aux autres modalités"
                      % (DIMENSIONS.get(dim, dim), ", ".join(totaux))] += 1

    return {
        "jeu": jeu, "fichiers": fichiers, "total": total, "vides": vides,
        "modalites": modalites, "indicateurs": indicateurs, "valeurs": valeurs, "unites": unites,
        "niveaux": niveaux, "millesimes": millesimes, "statuts": statuts, "secrets": secrets,
        "communes": communes, "anomalies": anomalies,
    }


def afficher(p):
    total, vides = p["total"], p["vides"]
    taille = sum(f["taille_mo"] for f in p["fichiers"])
    print("\n" + "=" * 78)
    print(f"{JEUX.get(p['jeu'], p['jeu'])}  [{p['jeu']}]")
    print("=" * 78)
    if not total:
        print("aucune observation : lancer d'abord python src/insee/main.py")
        return
    print(f"{len(p['fichiers'])} fichiers · {total:,} observations · {taille:,.0f} Mo")
    print(f"valeurs renseignées : {total - vides:,} ({(total - vides) / total:.1%})"
          f"   vides : {vides:,} ({vides / total:.1%})")
    print(f"territoires : {len(p['communes']):,} communes · millésimes {', '.join(sorted(p['millesimes']))}")

    if p["statuts"]:
        print("\nstatut de diffusion")
        for code, n in list(p["statuts"].most_common()) + list(p["secrets"].most_common()):
            if code in STATUTS:
                print(f"   {libelle(code, STATUTS):<55} {n:>10,}")

    renseignes = {n: c for n, c in p["indicateurs"].items() if c["rempli"]}
    absents = sorted(n for n, c in p["indicateurs"].items() if not c["rempli"])
    print("\nindicateurs")
    for nom, c in sorted(renseignes.items(), key=lambda x: -x[1]["rempli"]):
        vals = p["valeurs"][nom]
        print(f"   {libelle(nom, INDICATEURS):<52} {c['rempli'] / c['total']:>6.1%} rempli"
              f"   min {round(min(vals)):,}   médiane {round(statistics.median(vals)):,}"
              f"   max {round(max(vals)):,}")
    if absents:
        print(f"   {len(absents)} indicateurs sans aucune valeur, à écarter : {', '.join(absents)}")

    print("\ndécoupages disponibles")
    for dim, compte in sorted(p["modalites"].items()):
        exemples = ", ".join(libelle(m, MODALITES, avec_code=False) for m, _ in compte.most_common(3))
        print(f"   {libelle(dim, DIMENSIONS):<42} {len(compte):>3} modalités : {exemples}")

    print("\nanomalies")
    if not p["anomalies"]:
        print("   aucune")
    for nom, n in sorted(p["anomalies"].items(), key=lambda x: -x[1]):
        print(f"   {nom:<62} {n:>10,}")


def synthese(profils):
    profils = [p for p in profils if p["total"]]
    if not profils:
        return
    print("\n" + "=" * 78)
    print("SYNTHÈSE")
    print("=" * 78)
    total = sum(p["total"] for p in profils)
    vides = sum(p["vides"] for p in profils)
    union = set().union(*(p["communes"] for p in profils))
    print(f"{len(profils)} jeux · {total:,} observations · {vides:,} vides ({vides / total:.1%})"
          f" · {len(union):,} communes")

    for p in sorted(profils, key=lambda p: -len(p["communes"])):
        manquantes = len(union - p["communes"])
        print(f"   {JEUX.get(p['jeu'], p['jeu']):<40} {len(p['communes']):>6,} communes"
              f"{f'   ({manquantes} absentes)' if manquantes else ''}")

    divergents = {p["jeu"]: sorted(p["millesimes"]) for p in profils if sorted(p["millesimes"]) != [MILLESIME]}
    if divergents:
        print(f"\nmillésimes géographiques à harmoniser avant la jointure DVF : {divergents}")

    if not {c for c in union if c.startswith(("751", "6938", "132"))}:
        print("arrondissements de Paris, Lyon et Marseille absents : codes DVF à rattacher à leur commune")


def ecrire_csv(profils):
    profils = [p for p in profils if p["total"]]
    if not profils:
        return
    PROFILING.mkdir(parents=True, exist_ok=True)

    pd.DataFrame([f for p in profils for f in p["fichiers"]]).to_csv(
        PROFILING / "fichiers.csv", index=False, encoding="utf-8")

    pd.DataFrame([
        {"jeu": p["jeu"], "indicateur": nom, "libelle": INDICATEURS.get(nom, ""),
         "unite": "|".join(p["unites"][nom]), "observations": c["total"], "renseignees": c["rempli"],
         "pct_rempli": round(c["rempli"] / c["total"] * 100, 2),
         "min": min(p["valeurs"][nom], default=None),
         "mediane": statistics.median(p["valeurs"][nom]) if p["valeurs"][nom] else None,
         "max": max(p["valeurs"][nom], default=None)}
        for p in profils for nom, c in p["indicateurs"].items()
    ]).to_csv(PROFILING / "indicateurs.csv", index=False, encoding="utf-8")

    pd.DataFrame([
        {"jeu": p["jeu"], "dimension": dim, "libelle": DIMENSIONS.get(dim, ""), "modalites": len(compte),
         "exemples": " | ".join(f"{m}={n}" for m, n in compte.most_common(5))}
        for p in profils for dim, compte in p["modalites"].items()
    ]).to_csv(PROFILING / "dimensions.csv", index=False, encoding="utf-8")

    pd.DataFrame([
        {"jeu": p["jeu"], "niveau": niveau, "observations": n,
         "millesimes": "|".join(sorted(p["millesimes"])), "communes": len(p["communes"])}
        for p in profils for niveau, n in p["niveaux"].items()
    ]).to_csv(PROFILING / "couverture_geo.csv", index=False, encoding="utf-8")

    print(f"\nprofils écrits dans {PROFILING}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", action="append", choices=DATASETS, help="défaut : les sept jeux")
    parser.add_argument("--region", action="append", choices=REGIONS, help="défaut : les quatre régions")
    args = parser.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")

    profils = [profiler(jeu, args.region) for jeu in dict.fromkeys(args.dataset or DATASETS)]
    for p in profils:
        afficher(p)
    synthese(profils)
    ecrire_csv(profils)


if __name__ == "__main__":
    main()
