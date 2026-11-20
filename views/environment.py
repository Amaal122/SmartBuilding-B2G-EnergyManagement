"""Page 5 — Environnement & Équipements (météo réelle, IoT non connecté)."""

from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st

from components.charts import (
    fig_occupancy,
    fig_temperature_trend,
    fig_weather_overview,
    render_chart,
)
from components.header import render_header
from components.ui import (
    demo_notice,
    equipment_table,
    info_panel_protocols,
    panel_head,
    section_heading,
    sensor_grid,
    stat_tiles,
    status_pill,
)
from data.mock_data import PROTOCOLS
from data.repository import ScenarioContext
from utils import calculations as calc
from utils import formatting as fmt
from utils.icons import icon


def _weather_value(series: pd.Series) -> float | None:
    clean = pd.to_numeric(series, errors="coerce").dropna()
    return float(clean.iloc[-1]) if not clean.empty else None


def render(ctx: ScenarioContext, config: dict[str, Any]) -> None:
    render_header(
        "Environnement & Équipements",
        "Météo réelle issue des jeux ASHRAE et de la centrale PV, ambiance intérieure "
        "simulée et inventaire des équipements. Aucun IoT n'est connecté.",
        config,
    )

    df = ctx.frame
    if df.empty:
        st.error("Aucune donnée environment disponible.")
        return

    latest = df.iloc[-1]
    outdoor = _weather_value(df["temperature_outdoor"])
    indoor = float(latest["temperature_indoor"])
    humidity = float(latest["humidity"])
    occupancy = int(latest["occupancy"])
    wind = _weather_value(df["wind_speed"])
    cloud = _weather_value(df["cloud_coverage"])
    dew = _weather_value(df["dew_temperature"])
    precipitation = _weather_value(df["precip_depth_1_hr"])
    pressure = _weather_value(df["sea_level_pressure"])
    stamp = pd.Timestamp(latest["timestamp"])

    comfort_ok = 19.0 <= indoor <= 25.0 and 35.0 <= humidity <= 65.0
    comfort_label = "Optimal" if comfort_ok else "À surveiller"
    comfort_tone = "good" if comfort_ok else "warn"
    comfort_color = "#047857" if comfort_ok else "#B45309"
    comfort_bg = "#F0FDF4" if comfort_ok else "#FFFBEB"
    comfort_border = "#BBF7D0" if comfort_ok else "#FDE68A"

    equipment = [
        {
            "equipment": "Compteur électrique ASHRAE",
            "type": "Jeu de données historique · meter 0",
            "state": "Données disponibles",
            "tone": "good",
            "last": f"Dernier relevé {fmt.fr_datetime(stamp)}",
            "icon": "gauge",
        },
        {
            "equipment": "Centrale PV n°1 (onduleurs)",
            "type": "Jeu de données historique · 15 min",
            "state": "Données disponibles",
            "tone": "good",
            "last": "Mai – juin 2020",
            "icon": "sun",
        },
        {
            "equipment": "Station météo site ASHRAE",
            "type": "Jeu de données historique · horaire",
            "state": "Données disponibles",
            "tone": "good",
            "last": f"Dernier relevé {fmt.fr_datetime(stamp)}",
            "icon": "cloud",
        },
        {
            "equipment": "Batterie / BMS",
            "type": "Simulation logicielle",
            "state": "Simulé",
            "tone": "purple",
            "last": "Aucun BMS physique",
            "icon": "battery",
        },
        {
            "equipment": "HVAC / CVC",
            "type": "Équipement du bâtiment",
            "state": "Non connecté",
            "tone": "bad",
            "last": "État scénarisé",
            "icon": "hvac",
        },
        {
            "equipment": "Capteurs IoT intérieurs",
            "type": "Température, humidité, présence",
            "state": "Non connectés",
            "tone": "bad",
            "last": "Valeurs simulées",
            "icon": "thermometer",
        },
        {
            "equipment": "Contrôleur EMS",
            "type": "Supervision / pilotage",
            "state": "Non connecté",
            "tone": "bad",
            "last": "Aucune commande envoyée",
            "icon": "server",
        },
        {
            "equipment": "Passerelle IoT",
            "type": "MQTT / Modbus / BACnet",
            "state": "Hors ligne",
            "tone": "bad",
            "last": "Intégration future",
            "icon": "wifi-off",
        },
    ]
    available = sum(1 for row in equipment if row["tone"] == "good")

    # ------------------------------------------------------------------
    # Confort
    # ------------------------------------------------------------------
    st.markdown(
        f"""
<div class="flow-note" style="background:{comfort_bg};border:1px solid {comfort_border}">
  <span style="color:{comfort_color}">{icon("thermometer", size=16)}</span>
  <div style="flex:1">
    <div style="display:flex;align-items:center;gap:9px;flex-wrap:wrap">
      <strong style="color:{comfort_color}">Confort intérieur simulé : {comfort_label}</strong>
      {status_pill(comfort_label, comfort_tone)}
      <span style="color:{comfort_color};font-weight:700">· {fmt.fr_number(indoor, 1)} °C · {fmt.fr_number(humidity, 0)} % HR</span>
    </div>
    <div style="margin-top:2px">
      La température extérieure est réelle (site ASHRAE). Les valeurs intérieures
      sont reconstituées par un modèle simple de confort : aucun capteur intérieur
      n'est disponible dans les jeux de données et aucun CVC n'est piloté.
    </div>
  </div>
</div>
""",
        unsafe_allow_html=True,
    )

    stat_tiles(
        [
            {
                "label": "Température extérieure",
                "value": fmt.fr_number(outdoor, 1),
                "unit": "°C",
                "icon": "sun",
                "accent": "sky",
                "sub": "mesure météo réelle · site ASHRAE",
            },
            {
                "label": "Vent",
                "value": fmt.fr_number(wind, 1),
                "unit": "m/s",
                "icon": "wind",
                "accent": "green",
                "sub": "mesure météo réelle",
            },
            {
                "label": "Nébulosité",
                "value": fmt.fr_number(cloud, 0),
                "unit": "%",
                "icon": "cloud",
                "accent": "blue",
                "sub": "mesure météo réelle",
            },
            {
                "label": "Occupation estimée",
                "value": fmt.fr_number(occupancy, 0),
                "unit": "pers.",
                "icon": "users",
                "accent": "purple",
                "sub": "profil scénarisé · non mesuré",
            },
        ],
        columns=4,
    )

    # ------------------------------------------------------------------
    # Capteurs
    # ------------------------------------------------------------------
    section_heading(
        "Points de mesure",
        "Chaque carte précise l'origine de la valeur : donnée historique réelle ou simulation.",
        right_html=status_pill("3 RÉELS · 3 SIMULÉS", "info"),
        kicker="ENVIRONNEMENT",
    )
    sensor_grid(
        [
            {
                "name": "Température extérieure",
                "room": "Station météo ASHRAE",
                "value": fmt.fr_number(outdoor, 1),
                "unit": "°C",
                "status": "Réel",
                "tone": "good",
                "state": "Jeu de données historique",
                "last": fmt.fr_datetime(stamp),
                "icon": "sun",
                "accent": "sky",
            },
            {
                "name": "Point de rosée",
                "room": "Station météo ASHRAE",
                "value": fmt.fr_number(dew, 1),
                "unit": "°C",
                "status": "Réel",
                "tone": "good",
                "state": "Jeu de données historique",
                "last": fmt.fr_datetime(stamp),
                "icon": "droplet",
                "accent": "blue",
            },
            {
                "name": "Précipitations",
                "room": "Station météo ASHRAE",
                "value": fmt.fr_number(precipitation, 1),
                "unit": "mm",
                "status": "Réel",
                "tone": "good",
                "state": "Jeu de données historique",
                "last": fmt.fr_datetime(stamp),
                "icon": "cloud",
                "accent": "green",
            },
            {
                "name": "Température intérieure",
                "room": "Bureaux · modèle de confort",
                "value": fmt.fr_number(indoor, 1),
                "unit": "°C",
                "status": "Simulé",
                "tone": "purple",
                "state": "Aucun capteur intérieur",
                "last": fmt.fr_datetime(stamp),
                "icon": "thermometer",
                "accent": "amber",
            },
            {
                "name": "Humidité relative",
                "room": "Bureaux · modèle de confort",
                "value": fmt.fr_number(humidity, 0),
                "unit": "%",
                "status": "Simulé",
                "tone": "purple",
                "state": "Plage cible 35–65 %",
                "last": fmt.fr_datetime(stamp),
                "icon": "droplet",
                "accent": "mint",
            },
            {
                "name": "Occupation",
                "room": "Bâtiment · profil horaire",
                "value": fmt.fr_number(occupancy, 0),
                "unit": "pers.",
                "status": "Simulé",
                "tone": "purple",
                "state": "Non mesuré",
                "last": fmt.fr_datetime(stamp),
                "icon": "users",
                "accent": "purple",
            },
        ]
    )

    # ------------------------------------------------------------------
    # Tendances
    # ------------------------------------------------------------------
    recent = calc.last_days(df, 7)
    left, right = st.columns(2, gap="medium")
    with left:
        with st.container(border=True):
            panel_head(
                "Températures sur 7 jours",
                "Extérieure réelle et intérieure simulée",
                tag="°C",
                icon_name="thermometer",
            )
            render_chart(fig_temperature_trend(recent), key="env_temp")
    with right:
        with st.container(border=True):
            panel_head(
                "Météo et irradiation",
                "Température extérieure réelle et irradiation de la centrale PV",
                tag="RÉEL",
                icon_name="cloud",
            )
            render_chart(fig_weather_overview(recent), key="env_weather")

    with st.container(border=True):
        panel_head(
            "Occupation simulée",
            "Nombre de personnes estimé heure par heure",
            tag="SIMULÉ",
            icon_name="users",
        )
        render_chart(fig_occupancy(recent), key="env_occ")

    st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
    with st.container(border=True):
        panel_head(
            "Autres variables météo réelles",
            "Valeurs du dernier relevé disponible",
            tag="RÉEL",
            icon_name="cloud",
        )
        st.markdown(
            f"""
<div class="dataset-facts" style="border-top:none;padding-top:0">
  <div><div class="k">Pression au niveau de la mer</div><div class="v">{fmt.fr_number(pressure, 0)} Pa</div></div>
  <div><div class="k">Direction du vent</div><div class="v">{fmt.fr_number(df['wind_direction'].iloc[-1], 0)}°</div></div>
  <div><div class="k">Point de rosée</div><div class="v">{fmt.fr_number(dew, 1)} °C</div></div>
  <div><div class="k">Précipitations</div><div class="v">{fmt.fr_number(precipitation, 1)} mm</div></div>
</div>
""",
            unsafe_allow_html=True,
        )

    # ------------------------------------------------------------------
    # Équipements
    # ------------------------------------------------------------------
    section_heading(
        "Parc d'équipements",
        "Les seules données disponibles sont historiques ; aucun équipement n'est en ligne.",
        right_html=status_pill(f"{available} sources historiques", "good"),
        kicker="INVENTAIRE",
    )
    with st.container(border=True):
        panel_head(
            "Équipements et origine des données",
            "Compteurs, station météo, onduleurs, stockage et passerelles",
            tag="TABLEAU",
            icon_name="table",
        )
        equipment_table(equipment)
        st.markdown(
            f'<div class="upload-note">{icon("info", size=12)} '
            "Les statuts « Données disponibles » désignent des fichiers CSV historiques, "
            "pas des équipements connectés en direct.</div>",
            unsafe_allow_html=True,
        )

    info_panel_protocols(PROTOCOLS)
    demo_notice(
        "Aucun bus MQTT, Modbus ou BACnet n'est ouvert. Les capteurs intérieurs et "
        "l'état du CVC sont simulés ; la météo provient des CSV réels."
    )
