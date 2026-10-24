WITH parametres AS (
    SELECT 'idf'::text AS region, 'Maison'::text AS type_bien
)
SELECT
    m.code_commune,
    c.departement,
    c.region,
    p.type_bien,
    SUM(m.nb_ventes) AS nb_ventes_total,
    ROUND(PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY m.prix_m2_median)::numeric, 0) AS prix_m2_median,
    ROUND(AVG(m.prix_m2_moyen)::numeric, 0) AS prix_m2_moyen,
    ROUND(MIN(m.prix_m2_median)::numeric, 0) AS prix_m2_min,
    ROUND(MAX(m.prix_m2_median)::numeric, 0) AS prix_m2_max
FROM "G_marche_commune_annee_type" AS m
JOIN "G_communes" AS c ON c.code_commune = m.code_commune
CROSS JOIN parametres AS p
WHERE m.type_bien = p.type_bien
  AND m.annee BETWEEN 2021 AND 2025
  AND (p.region IS NULL OR c.region = p.region)
GROUP BY m.code_commune, c.departement, c.region, p.type_bien
HAVING SUM(m.nb_ventes) >= 10
  AND COUNT(m.prix_m2_median) > 0
ORDER BY prix_m2_median DESC NULLS LAST;
