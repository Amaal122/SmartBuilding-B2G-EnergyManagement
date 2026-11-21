"""Page 3 — Production Photovoltaïque (version présentation)."""

from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st

from components.charts import (
    fig_daily_solar,
    fig_solar_power,
    fig_solar_vs_consumption,
    fig_weather_overview,
    render_chart,
)
from components.header import render_header
from components.kpi_cards import kpi_grid
from components.ui import panel_head
from data.repository import ScenarioContext
from services.energy_calculations import daily_summary, energy_kpis
from utils import calculations as calc
from utils import formatting as fmt
from utils.icons import icon

PERIODS = {"24 heures": 1, "7 jours": 7, "14 jours": 14, "Tout": 100000}


def render(ctx: ScenarioContext, config: dict[str, Any]) -> None:
    render_header(
        "Production Photovoltaïque",
        "Production réelle de la centrale solaire et comparaison avec les besoins du bâtiment.",
        config,
    )
    df = ctx.frame
    if df.empty:
        st.error("Aucune production disponible.")
        return

    selected = st.segmented_control(
        "Période",
        options=list(PERIODS.keys()),
        default="7 jours",
        label_visibility="collapsed",
        key="solar_period",
    ) or "7 jours"
    period = calc.last_days(df, PERIODS[selected])
    kpis = energy_kpis(period)

    st.markdown(
        f"""
<div class="flow-note" style="background:#F0FDF4;border:1px solid #BBF7D0">
  {icon("sun", size=15)}
  <div><strong>Centrale PV réelle.</strong> Mesures sources toutes les 15 minutes,
  agrégées ici en pas horaire ({fmt.fr_number(ctx.quality.get("rows", 0), 0)} heures).
  Production mise à l'échelle à {fmt.fr_pct(ctx.pv_ratio * 100, 0)} de la consommation
  du bâtiment pour le scénario.</div>
</div>
""",
        unsafe_allow_html=True,
    )

    kpi_grid(
        [
            {
                "label": "Production PV",
                "value": fmt.fr_number(kpis["solar"], 0),
                "unit": "kWh",
                "icon": "sun",
                "accent": "green",
                "note": "scénario",
            },
            {
                "label": "Puissance actuelle",
                "value": fmt.fr_number(period.iloc[-1]["solar_production_kwh"], 1),
                "unit": "kW",
                "icon": "activity",
                "accent": "mint",
                "note": "dernier relevé",
            },
            {
                "label": "Production journalière",
                "value": fmt.fr_number(
                    kpis["solar"] / kpis["days"] if kpis["days"] else 0, 0
                ),
                "unit": "kWh/jour",
                "icon": "calendar",
                "accent": "sky",
                "note": f"{kpis['days']} jours",
            },
            {
                "label": "Autoconsommation",
                "value": fmt.fr_number(kpis["autoconsumption"], 1),
                "unit": "%",
                "icon": "leaf",
                "accent": "green",
                "note": "PV utilisé sur place",
            },
        ],
        columns=4,
    )

    with st.container(border=True):
        panel_head("Puissance solaire", "Profil horaire réel agrégé", tag="kW", icon_name="sun")
        render_chart(fig_solar_power(period), key="sol_power")

    left, right = st.columns(2, gap="medium")
    with left:
        with st.container(border=True):
            panel_head("Production journalière", "Énergie générée par jour", icon_name="calendar")
            render_chart(fig_daily_solar(daily_summary(period)), key="sol_daily")
    with right:
        with st.container(border=True):
            panel_head("PV vs consommation", "Comparaison des deux profils", icon_name="activity")
            render_chart(fig_solar_vs_consumption(period), key="sol_vs")

    with st.container(border=True):
        panel_head(
            "Météo et irradiation",
            "Température extérieure réelle et irradiation mesurée",
            tag="DONNÉES RÉELLES",
            icon_name="cloud",
        )
        render_chart(fig_weather_overview(period), key="sol_weather")

    st.caption(
        f"Centrale réelle : 22 onduleurs · facteur d'échelle {ctx.pv_scale:.5f} · "
        f"{ctx.quality.get('solar_corrected', 0)} heures corrigées. "
        "Couplage avec le bâtiment = scénario modélisé."
    )
