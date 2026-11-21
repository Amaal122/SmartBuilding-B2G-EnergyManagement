"""Page 1 — Vue Générale (version présentation)."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
import streamlit as st

from components.charts import (
    fig_consumption_vs_solar,
    fig_energy_sources_donut,
    render_chart,
)
from components.energy_flow import energy_flow_diagram, flow_disclaimer
from components.header import render_header
from components.kpi_cards import kpi_grid
from components.ui import balance_stats, panel_head
from data.repository import ScenarioContext
from services.energy_calculations import energy_kpis
from utils import calculations as calc
from utils import formatting as fmt
from utils.icons import icon

PERIOD_OPTIONS = {"24 heures": 1, "7 jours": 7, "14 jours": 14, "Tout": 100000}


def _tone(delta: float | None, good_when_up: bool) -> str:
    if delta is None or not np.isfinite(delta):
        return "neutral"
    return "good" if (delta >= 0) == good_when_up else "bad"


def render(ctx: ScenarioContext, config: dict[str, Any]) -> None:
    render_header(
        "Vue Générale",
        "Consommation réelle, production solaire et bilan énergétique du bâtiment.",
        config,
    )
    df = ctx.frame
    if df.empty:
        st.error("Aucune donnée réelle disponible.")
        return

    # Période
    selected = st.segmented_control(
        "Période",
        options=list(PERIOD_OPTIONS.keys()),
        default="7 jours",
        label_visibility="collapsed",
        key="overview_period",
    ) or "7 jours"
    days = PERIOD_OPTIONS[selected]
    period = calc.last_days(df, days)
    previous = calc.previous_days(df, days)
    kpis = energy_kpis(period)
    previous_kpis = energy_kpis(previous)

    # Origine des données en une ligne
    st.markdown(
        f"""
<div class="flow-note" style="background:#F8FAFC;border:1px solid #DCE4EF">
  {icon("database", size=15)}
  <div><strong>Bâtiment {ctx.building_id} · site {ctx.site_id}</strong> ·
  {fmt.fr_number(ctx.quality.get("rows", 0), 0)} heures · consommation ASHRAE réelle ·
  production PV réelle mise à l'échelle ({fmt.fr_pct(ctx.pv_ratio * 100, 0)}) ·
  bilan modélisé.</div>
</div>
""",
        unsafe_allow_html=True,
    )

    # KPI
    def delta(key: str) -> float | None:
        return calc.comparison(kpis[key], previous_kpis[key])

    kpi_grid(
        [
            {
                "label": "Consommation totale",
                "value": fmt.fr_number(kpis["consumption"], 0),
                "unit": "kWh",
                "icon": "bolt",
                "accent": "blue",
                "delta": fmt.fr_delta(delta("consumption")) or "—",
                "delta_tone": _tone(delta("consumption"), False),
                "note": "mesure réelle",
            },
            {
                "label": "Production PV",
                "value": fmt.fr_number(kpis["solar"], 0),
                "unit": "kWh",
                "icon": "sun",
                "accent": "green",
                "delta": fmt.fr_delta(delta("solar")) or "—",
                "delta_tone": _tone(delta("solar"), True),
                "note": "PV réel ajusté",
            },
            {
                "label": "Import réseau",
                "value": fmt.fr_number(kpis["grid_import"], 0),
                "unit": "kWh",
                "icon": "grid",
                "accent": "sky",
                "delta": fmt.fr_delta(delta("grid_import")) or "—",
                "delta_tone": _tone(delta("grid_import"), False),
                "note": "sans batterie",
            },
            {
                "label": "Surplus potentiel",
                "value": fmt.fr_number(kpis["surplus"], 0),
                "unit": "kWh",
                "icon": "trend-up",
                "accent": "mint",
                "delta": fmt.fr_delta(delta("surplus")) or "—",
                "delta_tone": _tone(delta("surplus"), True),
                "note": "export possible",
            },
            {
                "label": "Autoconsommation",
                "value": fmt.fr_number(kpis["autoconsumption"], 1),
                "unit": "%",
                "icon": "gauge",
                "accent": "green",
                "delta": "—",
                "delta_tone": "neutral",
                "note": "PV utilisé sur place",
            },
            {
                "label": "Puissance max",
                "value": fmt.fr_number(kpis["peak_power_kw"], 1),
                "unit": "kW",
                "icon": "activity",
                "accent": "amber",
                "delta": "—",
                "delta_tone": "neutral",
                "note": "pointe horaire",
            },
        ],
        columns=6,
    )

    # Graphique principal
    with st.container(border=True):
        panel_head(
            "Consommation vs production solaire",
            "Les deux profils horaires sur la période choisie",
            tag="DONNÉES RÉELLES",
            icon_name="activity",
        )
        render_chart(fig_consumption_vs_solar(period), key="ov_main")

    # Bilan
    left, right = st.columns([1.0, 1.4], gap="medium")
    with left:
        with st.container(border=True):
            panel_head("Sources d'énergie", "Part solaire / réseau", icon_name="pie-chart")
            render_chart(fig_energy_sources_donut(kpis), key="ov_donut")
    with right:
        with st.container(border=True):
            panel_head("Bilan simplifié", "Flux calculés sans stockage", icon_name="layers")
            balance_stats(calc.energy_balance(kpis))
            energy_flow_diagram(kpis, float(config.get("battery_capacity_kwh", 200)))

    flow_disclaimer()
    st.caption(
        "Les graphiques et KPI utilisent les jeux historiques réels. Le couplage des deux "
        "installations est un scénario modélisé ; la batterie est simulée."
    )
