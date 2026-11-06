-- B3 : communes candidates pour un couple, à partir des quatre tables Gold.
-- Les distances partent de l'adresse de travail si ses coordonnées sont fournies,
-- puis du centre moyen des POI de chaque commune candidate. Sans coordonnées
-- de travail, elles partent du centre moyen des POI de sa commune.
-- Le coût immobilier provient des ventes passées ; Gold ne contient ni annonces
-- disponibles, ni coordonnées des logements, ni indice général du coût de la vie.
WITH parametres AS (
    -- PARAMETRES_DEBUT
    SELECT '75056'::text AS code_commune_travail,
           NULL::double precision AS latitude_travail,
           NULL::double precision AS longitude_travail,
           'Maison'::text AS type_bien,
           60000::double precision AS revenu_annuel_couple,
           80::double precision AS surface_souhaitee_m2,
           25::double precision AS tolerance_surface_pct,
           30::double precision AS distance_max_km,
           NULL::double precision AS budget_max_achat,
           10::integer AS limite
    -- PARAMETRES_FIN
), poi_commune AS (
    SELECT code_commune,
           AVG(latitude) AS latitude_centre_poi,
           AVG(longitude) AS longitude_centre_poi,
           COUNT(*) FILTER (WHERE categorie = 'transport') AS nb_poi_transport,
           COUNT(*) FILTER (WHERE categorie = 'education') AS nb_education_osm,
           COUNT(*) FILTER (WHERE categorie = 'sante') AS nb_sante_osm,
           COUNT(*) FILTER (WHERE categorie = 'commerce') AS nb_commerces_osm
    FROM "G_POINT_INTERET"
    WHERE latitude BETWEEN 41 AND 52 AND longitude BETWEEN -6 AND 10
    GROUP BY code_commune
), lieu_travail AS (
    SELECT COALESCE(p.latitude_travail, poi.latitude_centre_poi) AS latitude_travail,
           COALESCE(p.longitude_travail, poi.longitude_centre_poi) AS longitude_travail
    FROM parametres AS p
    LEFT JOIN poi_commune AS poi ON poi.code_commune = p.code_commune_travail
    WHERE (p.latitude_travail IS NOT NULL AND p.longitude_travail IS NOT NULL)
       OR poi.code_commune IS NOT NULL
), marche_recent AS (
    SELECT t.code_commune, COUNT(*) AS nb_ventes_comparables,
           PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY t.prix_m2) AS prix_m2_median,
           PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY t.valeur_fonciere)
               AS prix_median_biens_comparables
    FROM "G_TRANSACTION" AS t
    CROSS JOIN parametres AS p
    WHERE t.type_bien = p.type_bien
      AND t.date_mutation >= DATE '2024-01-01'
      AND t.date_mutation < DATE '2026-01-01'
      AND t.surface_bati BETWEEN
          p.surface_souhaitee_m2 * (1 - p.tolerance_surface_pct / 100)
          AND p.surface_souhaitee_m2 * (1 + p.tolerance_surface_pct / 100)
    GROUP BY t.code_commune
    HAVING COUNT(*) >= 10
), communes_candidates AS (
    SELECT c.code_commune, c.nom_commune, c.departement, c.region,
           pr.population, pr.revenu_median, pr.taux_chomage, pr.taux_pauvrete,
           m.nb_ventes_comparables, m.prix_m2_median,
           m.prix_median_biens_comparables,
           poi.latitude_centre_poi, poi.longitude_centre_poi,
           poi.nb_poi_transport, poi.nb_education_osm,
           poi.nb_sante_osm, poi.nb_commerces_osm,
           6371.0 * ACOS(LEAST(1.0, GREATEST(-1.0,
               SIN(RADIANS(poi.latitude_centre_poi)) * SIN(RADIANS(travail.latitude_travail))
             + COS(RADIANS(poi.latitude_centre_poi)) * COS(RADIANS(travail.latitude_travail))
               * COS(RADIANS(poi.longitude_centre_poi - travail.longitude_travail))
           ))) AS distance_travail_approx_km
    FROM "G_COMMUNE" AS c
    JOIN "G_PROFIL_COMMUNE" AS pr ON pr.code_commune = c.code_commune
    JOIN marche_recent AS m ON m.code_commune = c.code_commune
    JOIN poi_commune AS poi ON poi.code_commune = c.code_commune
    CROSS JOIN lieu_travail AS travail
    WHERE pr.population > 0
), prix_estimes AS (
    SELECT candidat.*,
           CASE WHEN p.revenu_annuel_couple > 0
                THEN candidat.prix_median_biens_comparables / p.revenu_annuel_couple
           END AS ratio_prix_revenu_annuel
    FROM communes_candidates AS candidat
    CROSS JOIN parametres AS p
)
SELECT code_commune, nom_commune, departement, region,
       p.code_commune_travail, p.type_bien, p.surface_souhaitee_m2,
       p.revenu_annuel_couple,
       latitude_centre_poi AS latitude_centre_commune,
       longitude_centre_poi AS longitude_centre_commune,
       ROUND(distance_travail_approx_km::numeric, 1) AS distance_travail_approx_km,
       nb_poi_transport, nb_education_osm, nb_sante_osm, nb_commerces_osm,
       nb_ventes_comparables,
       ROUND(prix_m2_median::numeric, 0) AS prix_m2_median,
       ROUND(prix_median_biens_comparables::numeric, 0) AS prix_median_biens_comparables,
       ROUND(ratio_prix_revenu_annuel::numeric, 2) AS ratio_prix_revenu_annuel,
       revenu_median AS revenu_median_commune, population,
       ROUND(taux_chomage::numeric, 2) AS taux_chomage,
       ROUND(taux_pauvrete::numeric, 2) AS taux_pauvrete
FROM prix_estimes
CROSS JOIN parametres AS p
WHERE distance_travail_approx_km <= p.distance_max_km
  AND nb_poi_transport > 0
  AND (nb_education_osm + nb_sante_osm + nb_commerces_osm) > 0
  AND (p.budget_max_achat IS NULL OR prix_median_biens_comparables <= p.budget_max_achat)
ORDER BY distance_travail_approx_km, ratio_prix_revenu_annuel NULLS LAST,
         nb_poi_transport DESC, code_commune
LIMIT (SELECT limite FROM parametres);
