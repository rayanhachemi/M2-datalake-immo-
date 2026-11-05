-- B3 : uniquement les indicateurs présents dans les quatre tables Gold.
WITH parametres AS (
    -- PARAMETRES_DEBUT
    SELECT 'idf'::text AS region
    -- PARAMETRES_FIN
), prix_recents AS (
    SELECT t.code_commune,
           CASE WHEN COUNT(*) FILTER (WHERE t.type_bien = 'Maison') >= 10
                THEN PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY t.prix_m2)
                     FILTER (WHERE t.type_bien = 'Maison')
           END AS prix_m2_maison,
           CASE WHEN COUNT(*) FILTER (WHERE t.type_bien = 'Appartement') >= 10
                THEN PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY t.prix_m2)
                     FILTER (WHERE t.type_bien = 'Appartement')
           END AS prix_m2_appartement
    FROM "G_TRANSACTION" AS t
    JOIN "G_COMMUNE" AS c ON c.code_commune = t.code_commune
    CROSS JOIN parametres AS p
    WHERE t.date_mutation >= DATE '2024-01-01'
      AND t.date_mutation < DATE '2026-01-01'
      AND (p.region IS NULL OR c.region = p.region)
    GROUP BY t.code_commune
)
SELECT c.code_commune, c.nom_commune, c.departement, c.region,
       pr.population, pr.revenu_median, pr.taux_pauvrete,
       ROUND(pr.taux_chomage::numeric, 2) AS taux_chomage,
       ROUND(COALESCE(prix.prix_m2_maison, prix.prix_m2_appartement)::numeric, 2) AS prix_m2_recent,
       CASE WHEN prix.prix_m2_maison IS NOT NULL THEN 'Maison'
            WHEN prix.prix_m2_appartement IS NOT NULL THEN 'Appartement'
       END AS type_prix_m2_recent
FROM "G_COMMUNE" AS c
JOIN "G_PROFIL_COMMUNE" AS pr ON pr.code_commune = c.code_commune
LEFT JOIN prix_recents AS prix ON prix.code_commune = c.code_commune
CROSS JOIN parametres AS p
WHERE pr.population > 0
  AND pr.revenu_median IS NOT NULL
  AND (p.region IS NULL OR c.region = p.region)
ORDER BY pr.revenu_median DESC, c.code_commune;
