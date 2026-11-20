"""Page 5 — Environnement & Équipements."""

from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st

from components.charts import fig_occupancy, fig_temperature_trend, render_chart
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
from utils import calculations as calc
from utils import formatting as fmt
from utils.icons import icon


def render(df: pd.DataFrame, config: dict[str, Any]) -> None:
    render_header(
        "Environnement & Équipements",
        "Surveillance simulée du confort intérieur, de l'occupation, de l'éclairage, "
        "du CVC et inventaire des équipements IoT du bâtiment.",
        config,
    )

    latest = df.iloc[-1]
    indoor = float(latest["temperature_indoor"])
    outdoor = float(latest["temperature_outdoor"])
    humidity = float(latest["humidity"])
    occupancy = int(latest["occupancy"])

    comfort_ok = 19.0 <= indoor <= 25.0 and 35.0 <= humidity <= 65.0
    comfort_label = "Optimal" if comfort_ok else "À surveiller"
    comfort_tone = "good" if comfort_ok else "warn"
    comfort_color = "#047857" if comfort_ok else "#B45309"
    comfort_bg = "#F0FDF4" if comfort_ok else "#FFFBEB"
    comfort_border = "#BBF7D0" if comfort_ok else "#FDE68A"

    equipment = calc.equipment_rows(df)
    online = sum(1 for row in equipment if row["state"] in {"En ligne", "Actif"})

    # ------------------------------------------------------------------
    # Bandeau de confort
    # ------------------------------------------------------------------
    st.markdown(
        f"""
<div class="flow-note" style="background:{comfort_bg};border:1px solid {comfort_border}">
  <span style="color:{comfort_color}">{icon("thermometer", size=16)}</span>
  <div style="flex:1">
    <div style="display:flex;align-items:center;gap:9px;flex-wrap:wrap">
      <strong style="color:{comfort_color}">Confort intérieur : {comfort_label}</strong>
      {status_pill(comfort_label, comfort_tone)}
      <span style="color:{comfort_color};font-weight:700">· {fmt.fr_number(indoor, 1)} °C · {fmt.fr_number(humidity, 0)} % HR</span>
    </div>
    <div style="margin-top:2px">Ambiance intérieure estimée à partir de capteurs simulés.
    Aucune régulation réelle du CVC n'est effectuée.</div>
  </div>
</div>
""",
        unsafe_allow_html=True,
    )

    stat_tiles(
        [
            {
                "label": "Occupation actuelle",
                "value": fmt.fr_number(occupancy, 0),
                "unit": "pers.",
                "icon": "users",
                "accent": "purple",
                "sub": "présence estimée · dernière mesure",
            },
            {
                "label": "Température extérieure",
                "value": fmt.fr_number(outdoor, 1),
                "unit": "°C",
                "icon": "sun",
                "accent": "sky",
                "sub": "mesure simulée en toiture",
            },
            {
                "label": "Équipements disponibles",
                "value": f"{online} / {len(equipment)}",
                "unit": "",
                "icon": "server",
                "accent": "green",
                "sub": "passerelle IoT non connectée",
            },
            {
                "label": "Dernière mesure",
                "value": fmt.fr_time(latest["timestamp"]),
                "unit": "",
                "icon": "clock",
                "accent": "blue",
                "sub": fmt.fr_date(latest["timestamp"], long=True),
            },
        ],
        columns=4,
    )

    # ------------------------------------------------------------------
    # Capteurs
    # ------------------------------------------------------------------
    section_heading(
        "Capteurs IoT simulés",
        "Chaque carte présente le nom du point de mesure, la valeur, l'unité et l'état du capteur.",
        right_html=status_pill("6 points de mesure", "info"),
        kicker="ENVIRONNEMENT",
    )
    sensor_grid(calc.sensor_snapshot(df))

    # ------------------------------------------------------------------
    # Tendances
    # ------------------------------------------------------------------
    recent = calc.last_days(df, 1)
    left, right = st.columns(2, gap="medium")
    with left:
        with st.container(border=True):
            panel_head(
                "Températures sur 24 heures",
                "Intérieure et extérieure — profils simulés",
                tag="°C",
                icon_name="thermometer",
            )
            render_chart(fig_temperature_trend(recent), key="env_temp")
    with right:
        with st.container(border=True):
            panel_head(
                "Occupation du bâtiment",
                "Nombre de personnes estimé heure par heure",
                tag="Personnes",
                icon_name="users",
            )
            render_chart(fig_occupancy(recent), key="env_occ")

    # ------------------------------------------------------------------
    # Équipements
    # ------------------------------------------------------------------
    section_heading(
        "Parc d'équipements",
        "Inventaire fonctionnel et dernier horodatage de mesure simulé.",
        right_html=status_pill("1 équipement hors ligne", "bad"),
        kicker="INVENTAIRE",
    )
    with st.container(border=True):
        panel_head(
            "Équipements du bâtiment",
            "Compteur, onduleur, capteurs et CVC — état de démonstration",
            tag="Tableau",
            icon_name="table",
        )
        equipment_table(equipment)
        st.markdown(
            f'<div class="upload-note">{icon("info", size=12)} '
            "Les horodatages sont ceux de la dernière mesure synthétique. "
            "La passerelle IoT reste volontairement hors ligne dans cette version.</div>",
            unsafe_allow_html=True,
        )

    st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)
    info_panel_protocols(PROTOCOLS)

    demo_notice(
        "Les capteurs, états et valeurs environnementales sont synthétiques. "
        "Aucun bus MQTT, Modbus ou BACnet n'est ouvert et aucune donnée terrain n'est reçue."
    )
