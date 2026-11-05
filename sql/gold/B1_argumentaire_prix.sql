-- B1 : Argumentaire de prix pour un bien donné
-- Partie 1 : prix du marché dans la commune (comparaison DVF)
-- Partie 2 : équipements dans un rayon de 500m (PostGIS sur G_POINT_INTERET)

-- ── PARTIE 1 : marché communal ──────────────────────────────────────────────
-- Paramètres à remplacer : :code_commune, :type_bien, :prix_propose, :surface
WITH parametres AS (
    -- PARAMETRES_DEBUT
    SELECT '75011'::text AS code_commune, 'Appartement'::text AS type_bien,
           350000::double precision AS prix_propose, 65::double precision AS surface
    -- PARAMETRES_FIN
), ventes AS (
    SELECT t.prix_m2,
           EXTRACT(YEAR FROM t.date_mutation)::integer AS annee
    FROM "G_TRANSACTION" AS t
    CROSS JOIN parametres AS p
    WHERE t.code_commune = p.code_commune
      AND t.type_bien    = p.type_bien
      AND t.date_mutation >= DATE '2023-01-01'
      AND t.date_mutation <  DATE '2026-01-01'
), stats AS (
    SELECT COUNT(*)::integer AS nb_ventes,
           ROUND(PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY prix_m2)::numeric, 0) AS prix_m2_median,
           ROUND(AVG(prix_m2)::numeric, 0)   AS prix_m2_moyen,
           ROUND(MIN(prix_m2)::numeric, 0)   AS prix_m2_min,
           ROUND(MAX(prix_m2)::numeric, 0)   AS prix_m2_max,
           ROUND(PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY prix_m2)::numeric, 0) AS q1,
           ROUND(PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY prix_m2)::numeric, 0) AS q3
    FROM ventes
)
SELECT c.nom_commune, c.departement,
       p.type_bien, p.surface, p.prix_propose,
       ROUND(p.prix_propose / p.surface, 0) AS prix_m2_propose,
       s.nb_ventes, s.prix_m2_median, s.prix_m2_moyen,
       s.prix_m2_min, s.prix_m2_max, s.q1, s.q3,
       ROUND(100.0 * (p.prix_propose / p.surface - s.prix_m2_median)
             / NULLIF(s.prix_m2_median, 0), 1) AS ecart_vs_median_pct,
       CASE
           WHEN p.prix_propose / p.surface < s.q1    THEN 'sous_marche'
           WHEN p.prix_propose / p.surface <= s.q3   THEN 'dans_la_norme'
           ELSE 'au_dessus_marche'
       END AS positionnement
FROM stats AS s
CROSS JOIN parametres AS p
JOIN "G_COMMUNE" AS c ON c.code_commune = p.code_commune;

-- ── PARTIE 2 : équipements dans un rayon de 500m (nécessite PostGIS) ────────
-- Remplacer :lat et :lon par les coordonnées géocodées de l'adresse du bien
-- Exemple : lat=48.8566, lon=2.3522 pour Paris centre
-- SELECT poi.categorie, poi.sous_type, poi.nom,
--        ROUND(ST_Distance(
--            ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography,
--            ST_SetSRID(ST_MakePoint(poi.longitude, poi.latitude), 4326)::geography
--        )::numeric, 0) AS distance_m
-- FROM "G_POINT_INTERET" AS poi
-- WHERE ST_DWithin(
--     ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography,
--     ST_SetSRID(ST_MakePoint(poi.longitude, poi.latitude), 4326)::geography,
--     500
-- )
-- ORDER BY distance_m, poi.categorie;
