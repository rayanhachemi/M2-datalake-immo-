# Référentiel communal Silver

`python src/communes/silver.py` crée `silver/communes.parquet` et la table PostgreSQL `S_communes` avec `code_commune`, `nom_commune`, `departement` et `region`.

Les noms et codes actuels viennent des contours des communes déjà ingérés en Bronze par le traitement OSM. Les codes DVF Silver absents de ces contours sont ajoutés pour que chaque transaction Gold puisse référencer une commune. La table est construite après les Silver DVF, OSM et INSEE, puis utilisée par `src/gold/modele_conceptuel.py`.
