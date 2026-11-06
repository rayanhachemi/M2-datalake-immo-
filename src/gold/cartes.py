"""Fonds Folium utilisés par les cartes métier B1 et B3."""

import json
from pathlib import Path

import folium


ROOT = Path(__file__).resolve().parents[2]
CONTOURS = ROOT / "bronze" / "contours"


def carte_avec_fonds(latitude: float, longitude: float, zoom: int,
                     codes_communes: list[str]) -> folium.Map:
    """Ajoute le fond CARTO basé sur OSM et les contours communaux locaux."""
    carte = folium.Map(
        location=[latitude, longitude], zoom_start=zoom,
        tiles=None, control_scale=True,
    )
    folium.TileLayer(
        "CartoDB positron", name="Fond de carte", show=True,
    ).add_to(carte)

    codes = set(codes_communes)
    contours = []
    for departement in sorted({code[:2] for code in codes}):
        fichier = CONTOURS / f"communes_{departement}.geojson"
        if not fichier.exists():
            continue
        with fichier.open(encoding="utf-8") as entree:
            donnees = json.load(entree)
        contours.extend(
            objet for objet in donnees.get("features", [])
            if objet.get("properties", {}).get("code") in codes
        )
    if contours:
        folium.GeoJson(
            {"type": "FeatureCollection", "features": contours},
            name="Contours communaux locaux", show=True,
            style_function=lambda _: {
                "color": "#1f6e8c", "weight": 2,
                "fillColor": "#b8dce8", "fillOpacity": 0.22,
            },
            tooltip=folium.GeoJsonTooltip(fields=["nom"], aliases=["Commune :"]),
        ).add_to(carte)
    return carte
