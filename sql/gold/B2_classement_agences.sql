WITH parametres AS (
    SELECT 'idf'::text AS region, 10::integer AS limite
)
SELECT
    c.code_commune,
    c.departement,
    c.region,
    c.score_attractivite,
    c.score_dynamique,
    c.score_activite,
    c.score_equipements,
    c.dynamique_prix_pct,
    c.nb_ventes_2024_2025,
    c.nb_poi_osm,
    c.nb_arrets_transport,
    RANK() OVER (
        PARTITION BY c.region
        ORDER BY c.score_attractivite DESC
    ) AS rang_dans_la_region
FROM "G_communes" AS c
CROSS JOIN parametres AS p
WHERE c.score_eligible = TRUE
  AND (p.region IS NULL OR c.region = p.region)
ORDER BY c.score_attractivite DESC, c.nb_ventes_2024_2025 DESC, c.code_commune
LIMIT (SELECT limite FROM parametres);
