# Data quality — source INSEE

Périmètre : 4 régions (IdF, Occitanie, Bretagne, ARA), 37 départements, 7 jeux de données
Melodi = 406 fichiers, **4 419 302 observations**, 1,7 Go, **10 939 communes**.
Mesures bronze : `python src/insee/profiling.py` (sorties : `docs/insee/profiling/*.csv`).
Résultats silver : `python src/insee/silver.py` (sortie : `silver/insee_silver_stats.json`).

Grille d'analyse : les cinq dimensions de qualité les plus utilisées et leurs facteurs [Akoka+2007] —
exactitude, complétude, cohérence, fraîcheur, unicité.

Rappel de structure : Melodi ne renvoie pas un tableau mais une liste d'observations, chacune
portant ses étiquettes. Une ligne = un territoire, un indicateur, une année, une valeur.

```json
{"dimensions": {"GEO": "2026-COM-35238", "TIME_PERIOD": "2023",
                "FILOSOFI_MEASURE": "MED_SL", "UNIT_MEASURE": "EUR_YR"},
 "attributes": {"OBS_STATUS": "A", "CONF_STATUS": "F"},
 "measures":   {"OBS_VALUE_NIVEAU": {"value": 25100}}}
```

## Synthèse

| # | Dimension | Facteur | Problème | Volume (bronze) | Gravité | Traitement | Résultat |
|---|---|---|---|---|---|---|---|
| 1 | Complétude | Couverture | Filosofi : 25 indicateurs sur 27 sans aucune valeur à la commune | 283 408 observations vides (96 % du jeu) | Critique | Silver : indicateurs non repris | 2 indicateurs conservés (revenu médian, taux de pauvreté) |
| 2 | Complétude | Couverture | Arrondissements de Paris, Lyon et Marseille absents côté INSEE | 70 159 ventes DVF 2024 sans donnée (5 %) | Critique | Silver DVF : `751xx → 75056`, `6938x → 69123`, `132xx → 13055` | À faire côté DVF |
| 3 | Complétude | Couverture | Un seul millésime téléchargé (`TIME_PERIOD=2023`) sur 23 disponibles (1968-2023) | 7 jeux sur 7 | Critique | Ingestion : relancer les populations sans filtre d'année | À faire — bloque l'analyse d'évolution (besoin B2) |
| 4 | Complétude | Densité | Taux de pauvreté couvert par le secret statistique | 8 699 communes (79,5 %) | Forte | Silver : valeur qualifiée, usage limité aux communes urbaines | 2 233 communes renseignées (54,7 % des ventes DVF) |
| 5 | Complétude | Densité | Revenu médian sous secret statistique | 1 274 communes (11,7 %) | Moyenne | Silver : valeur qualifiée | 9 658 communes renseignées (92,5 % des ventes DVF) |
| 6 | Exactitude | Correction syntaxique | Valeur absente écrite `{}` et non `null` | 283 408 observations | Critique | Profiling et silver : test sur la clé `value` | Complétude réelle mesurée : 4 % sur Filosofi, et non 100 % |
| 7 | Cohérence | Intégrité de domaine | Millésime géographique divergent : 2025 pour les populations, 2026 ailleurs | 10 939 observations | Moyenne | Silver : code découpé, millésime retiré | Jointure possible entre les 7 jeux |
| 8 | Cohérence | Intégrité de domaine | Modalités totales (`_T`, `Y_LT2021`, `Y_GE15`) recouvrant les autres | 9 dimensions sur le jeu logement | Moyenne | Silver : modalités fixées explicitement | Aucun double comptage |
| 9 | Cohérence | Schéma | Schéma variable : 4 à 13 dimensions, nom d'indicateur différent par jeu, attributs absents sur un jeu | 7 jeux | Moyenne | Profiling : découverte dynamique ; silver : filtres par dimension | Les 7 jeux traités par le même code |
| 10 | Fraîcheur | Actualité | Données 2023, millésime géographique 2026, aucun horodatage dans les fichiers | — | Faible | Millésime conservé dans `profiling` | Accepté |
| 11 | Unicité | Unicité | Doublons d'observations (même combinaison de dimensions) | 0 | — | Contrôle dans `profiling.py` | 0 |

Bilan : 4 419 302 observations bronze → **10 939 communes × 36 colonnes** (`silver/insee_communes.parquet`).

## 1. Exactitude

### Correction syntaxique — valeur absente mal détectée (#6)
Melodi n'écrit pas `null` quand la valeur n'existe pas, mais un objet vide :

```json
"measures": {"OBS_VALUE_NIVEAU": {}}                     valeur absente
"measures": {"OBS_VALUE_NIVEAU": {"value": 25100}}       valeur présente
```

Un test sur la présence de la clé `OBS_VALUE_NIVEAU` conclut à **100 % de remplissage** alors que
Filosofi n'est rempli qu'à 4 %. Le profiling et le silver testent la clé `value`.

## 2. Complétude

### Couverture — Filosofi presque vide (#1)
Le jeu annonce 27 indicateurs de revenus ; **25 n'ont aucune valeur à l'échelle communale**
(déciles, indice de Gini, composition du revenu disponible). L'INSEE ne les diffuse qu'à des
échelles plus larges, ce que confirme `OBS_STATUS = O` (non diffusé à ce niveau) sur
273 435 observations.

| Indicateur | Observations | Renseignées | Communes |
|---|---|---|---|
| Revenu médian (`MED_SL`) | 10 937 | 88,3 % | 9 658 |
| Taux de pauvreté (`PR_MD60`) | 10 937 | 20,4 % | 2 233 |
| 25 autres | 273 425 | 0 % | 0 |

**Silver** : seuls les deux premiers sont repris. Les 25 autres colonnes ne sont pas créées.

### Couverture — arrondissements absents (#2)
L'INSEE publie pour la commune entière (`75056`), DVF enregistre par arrondissement (`75115`).
Mesure sur les 934 495 ventes DVF de 2024 :

| Donnée INSEE | Communes DVF couvertes | Ventes DVF couvertes |
|---|---|---|
| Recensement | 99,5 % | 95,0 % |
| Revenu médian | 89,2 % | 92,5 % |
| Taux de pauvreté | 20,7 % | 54,7 % |

Les communes DVF sans correspondance sont d'abord des arrondissements : 75115 (3 790 ventes),
75116 (3 334), 75118 (3 292). **Traitement côté DVF** : rattacher l'arrondissement à sa commune,
ce qui porte la couverture du recensement à près de 100 % des ventes.

### Couverture — un seul millésime (#3)
`src/insee/main.py` filtre sur `TIME_PERIOD=2023`. Or `DS_POPULATIONS_HISTORIQUES` expose
**23 millésimes de 1968 à 2023** (Paris : 2 590 771 habitants en 1968, 2 103 778 en 2023).
Sans historique, aucune évolution n'est calculable, donc le besoin « quelles communes montent »
reste sans réponse. Le fichier complet pèse 3 Mo.

### Densité — secret statistique (#4, #5)
Deux causes distinctes de valeur manquante, à ne pas confondre :

| Code | Signification | Observations |
|---|---|---|
| `OBS_STATUS = O` | indicateur non diffusé à l'échelle communale | 273 435 |
| `CONF_STATUS = C` | valeur protégée, commune trop petite | 9 973 |

**Silver** : chaque valeur absente est comptée sous son motif dans `insee_silver_stats.json`
(taux de pauvreté : 8 699 secrets et 5 non diffusées ; revenu médian : 1 274 et 5).

## 3. Cohérence

### Intégrité de domaine — millésimes géographiques (#7)
Le code géographique porte son millésime : `2026-COM-35238`. Six jeux sont en 2026,
`DS_POPULATIONS_HISTORIQUES` est en 2025. Une jointure sur le code brut échouerait.
**Silver** : le code est découpé en trois, seul le numéro de commune est conservé.

### Intégrité de domaine — modalités totales (#8)
Les découpages comportent une modalité « ensemble ». Sur l'époque de construction,
`Y_LT2021` vaut exactement la somme des cinq tranches : à Rennes, 119 432 résidences
principales, soit 7 287 + 29 809 + 36 317 + 19 760 + 21 186 + 5 073.
**Silver** : chaque indicateur fixe ses modalités, les dimensions non citées valent `_T`.

### Schéma — structure variable (#9)
| Jeu | Dimensions | Nom de l'indicateur | Attributs |
|---|---|---|---|
| Revenus (Filosofi) | 4 | `FILOSOFI_MEASURE` | `OBS_STATUS`, `CONF_STATUS` |
| Logements | 13 | `RP_MEASURE` | `OBS_STATUS` |
| Populations légales | 4 | `POPREF_MEASURE` | aucun |

Le profiling découvre les dimensions à la lecture ; le silver sélectionne par nom de dimension.

### Contrôle de cohérence inter-jeux
Population du recensement contre population municipale : **0 commune avec un écart supérieur
à 10 %** (10 939 communes comparées).

## 4. Fraîcheur (#10)
Les fichiers ne portent aucun horodatage d'extraction. La fraîcheur est celle du millésime
INSEE : recensement et Filosofi 2023, carte des communes 2026. Suffisant pour le projet,
les données étant annuelles.

## 5. Unicité (#11)
Aucun doublon : le profiling compare la combinaison complète des dimensions de chaque
observation. Aucun fichier vide, et aucune page manquante — la pagination est vérifiée par
`paging.count` et `paging.isLast`, fichier par fichier.

## À faire

1. Relancer `src/insee/main.py` sans filtre d'année pour les populations (besoin B2).
2. Rattacher les arrondissements à leur commune côté DVF.
3. Confirmer dans la documentation Melodi les codes `EDUC=500T702_RP` (lu comme diplôme du
   supérieur) et `EMPSTA_ENQ=1T2 / 2` (actifs, chômeurs), utilisés par le silver.
4. Ajouter `DS_RP_MENAGES_PRINC` au silver : ses dimensions n'ont pas de modalité « ensemble »,
   la sélection des modalités reste à définir.
