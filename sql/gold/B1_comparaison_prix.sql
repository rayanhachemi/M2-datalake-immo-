-- B1 : prix communaux 2021-2025 calculés depuis les ventes Gold.
-- Comme dans la requête initiale, les prix résument les années ayant au moins
-- dix ventes ; le volume total compte toutes les années.
WITH parametres AS (
    -- PARAMETRES_DEBUT
    SELECT 'idf'::text AS region, 'Maison'::text AS type_bien
    -- PARAMETRES_FIN
), marche_annuel AS (
    SELECT t.code_commune,
           EXTRACT(YEAR FROM t.date_mutation)::integer AS annee,
           COUNT(*) AS nb_ventes,
           CASE WHEN COUNT(*) >= 10
                THEN PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY t.prix_m2)
           END AS prix_m2_median,
           CASE WHEN COUNT(*) >= 10 THEN AVG(t.prix_m2)
           END AS prix_m2_moyen
    FROM "G_TRANSACTION" AS t
    CROSS JOIN parametres AS p
    WHERE t.type_bien = p.type_bien
      AND t.date_mutation >= DATE '2021-01-01'
      AND t.date_mutation < DATE '2026-01-01'
    GROUP BY t.code_commune, EXTRACT(YEAR FROM t.date_mutation)::integer
)
SELECT m.code_commune, c.nom_commune, c.departement, c.region,
       p.type_bien,
       SUM(m.nb_ventes) AS nb_ventes_total,
       ROUND((PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY m.prix_m2_median))::numeric, 0) AS prix_m2_median,
       ROUND(AVG(m.prix_m2_moyen)::numeric, 0) AS prix_m2_moyen,
       ROUND(MIN(m.prix_m2_median)::numeric, 0) AS prix_m2_min,
       ROUND(MAX(m.prix_m2_median)::numeric, 0) AS prix_m2_max
FROM marche_annuel AS m
JOIN "G_COMMUNE" AS c ON c.code_commune = m.code_commune
CROSS JOIN parametres AS p
WHERE p.region IS NULL OR c.region = p.region
GROUP BY m.code_commune, c.nom_commune, c.departement, c.region, p.type_bien
HAVING SUM(m.nb_ventes) >= 10
   AND COUNT(m.prix_m2_median) > 0
ORDER BY prix_m2_median DESC NULLS LAST, m.code_commune;
