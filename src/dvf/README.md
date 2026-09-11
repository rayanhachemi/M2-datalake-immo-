# Module DVF — à faire (membre 2)

1. Bronze : télécharger les `.txt` DVF IdF par millésime (5 ans) dans `bronze/dvf/`.
2. Profilage : prix à 1 €, surfaces nulles, doublons `date + parcelle + valeur`, adresses incomplètes.
3. Silver : `silver/dvf_idf.parquet` dédupliqué, flag aberrants (IQR), `prix_m2`, géocodage BAN avec taux d'échec.
4. Attention CGU : données personnelles, pas de ré-identification ni indexation externe.
