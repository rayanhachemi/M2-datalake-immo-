# Dictionnaire bronze INSEE

Fichiers produits par `src/insee/main.py`.

- **Chemin** : `bronze/insee/{DATASET}/region_{code}_{nom}/part_XXXX.json`
- **Format** : JSON statistique (SDMX) — une liste d'observations, pas un tableau classique
- **Volume** : 7 jeux × 4 régions = 406 fichiers, 4 419 302 observations, ~1,7 Go
- **Licence** : Licence Ouverte INSEE

| Jeu de données | Contenu |
|---|---|
| `DS_FILOSOFI_CC` | Revenu médian et taux de pauvreté par commune |
| `DS_RP_POPULATION_PRINC` | Population par âge |
| `DS_RP_LOGEMENT_PRINC` | Logements : occupation, taille, époque de construction |
| `DS_RP_EMPLOI_LR_PRINC` | Emploi et activité |
| `DS_RP_DIPLOMES_PRINC` | Niveaux de diplôme |
| `DS_RP_MENAGES_PRINC` | Ménages et composition |
| `DS_POPULATIONS_HISTORIQUES` | Population légale de 1968 à 2023 |

## Structure d'une observation

```json
{
  "dimensions": {
    "GEO": "2026-COM-35238",
    "TIME_PERIOD": "2023",
    "FILOSOFI_MEASURE": "MED_SL"
  },
  "attributes": {
    "OBS_STATUS": "A",
    "CONF_STATUS": "F"
  },
  "measures": {
    "OBS_VALUE_NIVEAU": {"value": 25100}
  }
}
```

| Champ | Description |
|---|---|
| `dimensions.GEO` | Code territoire : `{millésime}-COM-{code_commune}` |
| `dimensions.TIME_PERIOD` | Année des données |
| `dimensions.*_MEASURE` | Indicateur mesuré (nom du champ varie selon le jeu) |
| `attributes.OBS_STATUS` | `A` = diffusé normalement, `O` = non diffusé à ce niveau |
| `attributes.CONF_STATUS` | `F` = librement diffusable, `C` = secret statistique |
| `measures.OBS_VALUE_NIVEAU.value` | La valeur numérique. **Absent = objet vide `{}`, pas `null`** |

La modalité `_T` représente toujours le total d'une dimension — ne jamais l'additionner aux autres.
