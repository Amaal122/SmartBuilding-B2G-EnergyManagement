"""Page 5 — Environnement & Équipements (version présentation)."""

from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st

from components.charts import fig_temperature_trend, render_chart
from components.header import render_header
from components.ui import equipment_table, panel_head, sensor_grid, stat_tiles
from data.mock_data import PROTOCOLS
from data.repository import ScenarioContext
from utils import calculations as calc
from utils import formatting as fmt
from utils.icons import icon


def render(ctx: ScenarioContext, config: dict[str, Any]) -> None:
    render_header(
        "Environnement & Équipements",
        "Météo réelle, ambiance intérieure simulée et inventaire des équipements.",
        config,
    )
    df = ctx.frame
    if df.empty:
        st.error("Aucune donnée disponible.")
        return

    last = df.iloc[-1]
    stamp = pd.Timestamp(last["timestamp"])
    outdoor = float(last["temperature_outdoor"])
    indoor = float(last["temperature_indoor"])
    humidity = float(last["humidity"])

    st.markdown(
        """
<div class="flow-note" style="background:#F0FDF4;border-color:#BBF7D0">
  <div><strong>Météo réelle</strong> (jeux ASHRAE et centrale PV).
  <strong>Température intérieure, humidité et occupation simulées</strong> :
  aucun capteur intérieur n'est connecté.</div>
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
                "sub": "mesure réelle",
            },
            {
                "label": "Température intérieure",
                "value": fmt.fr_number(indoor, 1),
                "unit": "°C",
                "icon": "thermometer",
                "accent": "blue",
                "sub": "simulée",
            },
            {
                "label": "Humidité",
                "value": fmt.fr_number(humidity, 0),
                "unit": "%",
                "icon": "droplet",
                "accent": "green",
                "sub": "simulée",
            },
            {
                "label": "Dernier relevé",
                "value": fmt.fr_time(stamp),
                "unit": "",
                "icon": "clock",
                "accent": "blue",
                "sub": fmt.fr_date(stamp),
            },
        ],
        columns=4,
    )

    sensor_grid(
        [
            {
                "name": "Température extérieure", "room": "Station ASHRAE",
                "value": fmt.fr_number(outdoor, 1), "unit": "°C",
                "status": "RÉEL", "tone": "good", "state": "Donnée historique",
                "last": fmt.fr_datetime(stamp), "icon": "sun", "accent": "sky",
            },
            {
                "name": "Vent", "room": "Station ASHRAE",
                "value": fmt.fr_number(df["wind_speed"].iloc[-1], 1), "unit": "m/s",
                "status": "RÉEL", "tone": "good", "state": "Donnée historique",
                "last": fmt.fr_datetime(stamp), "icon": "wind", "accent": "green",
            },
            {
                "name": "Nébulosité", "room": "Station ASHRAE",
                "value": fmt.fr_number(df["cloud_coverage"].iloc[-1], 0), "unit": "%",
                "status": "RÉEL", "tone": "good", "state": "Donnée historique",
                "last": fmt.fr_datetime(stamp), "icon": "cloud", "accent": "blue",
            },
            {
                "name": "Température intérieure", "room": "Modèle de confort",
                "value": fmt.fr_number(indoor, 1), "unit": "°C",
                "status": "SIMULÉ", "tone": "purple", "state": "Aucun capteur",
                "last": fmt.fr_datetime(stamp), "icon": "thermometer", "accent": "amber",
            },
            {
                "name": "Humidité", "room": "Modèle de confort",
                "value": fmt.fr_number(humidity, 0), "unit": "%",
                "status": "SIMULÉ", "tone": "purple", "state": "Aucun capteur",
                "last": fmt.fr_datetime(stamp), "icon": "droplet", "accent": "mint",
            },
            {
                "name": "Occupation", "room": "Profil horaire",
                "value": fmt.fr_number(last["occupancy"], 0), "unit": "pers.",
                "status": "SIMULÉ", "tone": "purple", "state": "Non mesurée",
                "last": fmt.fr_datetime(stamp), "icon": "users", "accent": "purple",
            },
        ]
    )

    with st.container(border=True):
        panel_head("Températures sur 7 jours", "Extérieure réelle / intérieure simulée", icon_name="thermometer")
        render_chart(fig_temperature_trend(calc.last_days(df, 7)), key="env_temp")

    with st.container(border=True):
        panel_head(
            "Équipements",
            "Données historiques disponibles, aucun équipement connecté en direct",
            tag="INVENTAIRE",
            icon_name="table",
        )
        equipment_table(
            [
                {
                    "equipment": "Compteur électrique", "type": "ASHRAE · meter 0",
                    "state": "Données disponibles", "tone": "good",
                    "last": fmt.fr_datetime(stamp), "icon": "gauge",
                },
                {
                    "equipment": "Centrale PV", "type": "22 onduleurs · 15 min",
                    "state": "Données disponibles", "tone": "good",
                    "last": "Mai–juin 2020", "icon": "sun",
                },
                {
                    "equipment": "Station météo", "type": "ASHRAE · horaire",
                    "state": "Données disponibles", "tone": "good",
                    "last": fmt.fr_datetime(stamp), "icon": "cloud",
                },
                {
                    "equipment": "Batterie / BMS", "type": "Simulation logicielle",
                    "state": "Simulé", "tone": "purple",
                    "last": "Aucun BMS physique", "icon": "battery",
                },
                {
                    "equipment": "Capteurs IoT & CVC", "type": "Intérieur",
                    "state": "Non connectés", "tone": "bad",
                    "last": "Valeurs simulées", "icon": "thermometer",
                },
                {
                    "equipment": "Passerelle IoT", "type": ", ".join(PROTOCOLS),
                    "state": "Hors ligne", "tone": "bad",
                    "last": "Intégration future", "icon": "wifi-off",
                },
            ]
        )

    st.caption(
        f"Aucune connexion {', '.join(PROTOCOLS)} n'est ouverte. "
        "La passerelle IoT reste hors ligne dans cette démonstration."
    )
