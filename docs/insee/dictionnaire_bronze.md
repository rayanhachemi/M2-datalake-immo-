# Bronze INSEE

Script : `python src/insee/main.py`  
Sortie : `bronze/insee/{DATASET}/region_{code}_{nom}/part_XXXX.json`  
Format : JSON SDMX (liste d'observations, pas un tableau)  
Licence : Licence Ouverte INSEE

| Jeu de données | Contenu |
|---|---|
| `DS_FILOSOFI_CC` | Revenu médian, taux de pauvreté (Filosofi) |
| `DS_RP_POPULATION_PRINC` | Population par âge et sexe |
| `DS_RP_LOGEMENT_PRINC` | Logements : occupation, pièces, époque de construction |
| `DS_RP_EMPLOI_LR_PRINC` | Emploi et activité |
| `DS_RP_DIPLOMES_PRINC` | Niveaux de diplôme |
| `DS_POPULATIONS_HISTORIQUES` | Populations légales annuelles |

## Structure d'une observation

```json
{
  "dimensions": { "GEO": "2026-COM-35238", "TIME_PERIOD": "2023", "FILOSOFI_MEASURE": "MED_SL" },
  "attributes":  { "OBS_STATUS": "A", "CONF_STATUS": "F" },
  "measures":    { "OBS_VALUE_NIVEAU": { "value": 25100 } }
}
```

| Champ | Description |
|---|---|
| `dimensions.GEO` | `{millésime}-COM-{code}` — millésime 2026 partout sauf `DS_POPULATIONS_HISTORIQUES` (2025) |
| `dimensions.*_MEASURE` | Indicateur : `MED_SL` (revenu médian), `PMUN` (population), `POP`… |
| `attributes.OBS_STATUS` | `A` diffusé · `O` non diffusé à ce niveau |
| `attributes.CONF_STATUS` | `F` libre · `C` secret statistique |
| `measures.OBS_VALUE_NIVEAU.value` | La valeur numérique — **objet vide `{}` si absente, pas `null`** |

## Modalités importantes

| Dimension | Valeur | Signification |
|---|---|---|
| toutes | `_T` | Total — **ne pas additionner aux autres modalités** |
| `FILOSOFI_MEASURE` | `MED_SL` / `PR_MD60` | Revenu médian / taux de pauvreté |
| `AGE` | `Y_LT15`, `Y15T24`, `Y25T39`, `Y40T54`, `Y55T64`, `Y_GE65` | Tranches d'âge |
| `OCS` | `DW_MAIN` / `DW_SEC_DW_OCC` / `DW_VAC` | Résidence principale / secondaire / vacante |
