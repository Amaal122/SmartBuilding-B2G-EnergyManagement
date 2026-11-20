"""Page 1 — Vue Générale."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
import streamlit as st

from components.charts import (
    fig_consumption_area,
    fig_consumption_vs_solar,
    fig_daily_consumption,
    fig_energy_sources_donut,
    render_chart,
)
from components.energy_flow import energy_flow_diagram, flow_disclaimer
from components.header import render_header
from components.kpi_cards import kpi_grid
from components.ui import (
    alert_cards,
    alert_count_badge,
    balance_stats,
    demo_notice,
    panel_head,
    section_heading,
    status_pill,
)
from data.mock_data import get_end_use_data
from utils import calculations as calc
from utils import formatting as fmt
from utils.config import currency_symbol
from utils.icons import icon

PERIOD_OPTIONS = {
    "24 heures": 1,
    "7 jours": 7,
    "14 jours": 14,
}


def _delta_tone(delta: float | None, good_when_up: bool) -> str:
    if delta is None or not np.isfinite(delta):
        return "neutral"
    positive = delta >= 0
    return "good" if positive == good_when_up else "bad"


def _comparison_text(delta: float | None) -> str:
    return fmt.fr_delta(delta) if delta is not None else "—"


def render(df: pd.DataFrame, config: dict[str, Any]) -> None:
    render_header(
        "Vue Générale",
        "Pilotage global de la performance énergétique du bâtiment : consommation, "
        "production photovoltaïque, stockage et échanges réseau.",
        config,
    )

    # ------------------------------------------------------------------
    # Sélection de la période analysée
    # ------------------------------------------------------------------
    control_left, control_right = st.columns([2.1, 3.0], vertical_alignment="center")
    with control_left:
        st.markdown(
            f'<div class="filter-bar">{icon("calendar", size=13)} Période analysée</div>',
            unsafe_allow_html=True,
        )
        selected = st.segmented_control(
            "Période analysée",
            options=list(PERIOD_OPTIONS.keys()),
            default="7 jours",
            label_visibility="collapsed",
            key="overview_period",
        )
    if not selected:
        selected = "7 jours"
    days = PERIOD_OPTIONS[selected]

    period = calc.last_days(df, days)
    previous = calc.previous_days(df, days)
    kpis = calc.energy_kpis(period)
    previous_kpis = calc.energy_kpis(previous)
    end_use = get_end_use_data()
    if not end_use.empty:
        end_use = end_use[end_use["timestamp"] > period["timestamp"].min()]

    last_ts = calc.latest_timestamp(df)
    with control_right:
        st.markdown(
            f'<div class="filter-bar" style="justify-content:flex-end">'
            f'{icon("database", size=13)} {fmt.fr_number(len(period), 0)} heures simulées · '
            f'{fmt.fr_number(kpis["days"], 0)} jours · dernière mesure {fmt.fr_datetime(last_ts)}'
            f"</div>",
            unsafe_allow_html=True,
        )

    # ------------------------------------------------------------------
    # Cartes KPI
    # ------------------------------------------------------------------
    consumption_delta = calc.comparison(kpis["consumption"], previous_kpis["consumption"])
    solar_delta = calc.comparison(kpis["solar"], previous_kpis["solar"])
    import_delta = calc.comparison(kpis["grid_import"], previous_kpis["grid_import"])
    surplus_delta = calc.comparison(kpis["surplus"], previous_kpis["surplus"])
    auto_delta = (
        (kpis["autoconsumption"] - previous_kpis["autoconsumption"])
        if kpis["autoconsumption"] is not None and previous_kpis["autoconsumption"] is not None
        else None
    )

    tail = period.tail(24)
    autoconso_series = np.where(
        tail["solar_production_kwh"].to_numpy() > 0.5,
        np.minimum(
            tail["consumption_kwh"].to_numpy(), tail["solar_production_kwh"].to_numpy()
        )
        / np.maximum(tail["solar_production_kwh"].to_numpy(), 1e-6)
        * 100.0,
        np.nan,
    )

    kpi_grid(
        [
            {
                "label": "Consommation totale",
                "value": fmt.fr_number(kpis["consumption"], 0),
                "unit": "kWh",
                "icon": "bolt",
                "accent": "blue",
                "delta": _comparison_text(consumption_delta),
                "delta_tone": _delta_tone(consumption_delta, good_when_up=False),
                "note": "vs période préc.",
                "spark": period["consumption_kwh"].tail(24).tolist(),
            },
            {
                "label": "Production solaire",
                "value": fmt.fr_number(kpis["solar"], 0),
                "unit": "kWh",
                "icon": "sun",
                "accent": "green",
                "delta": _comparison_text(solar_delta),
                "delta_tone": _delta_tone(solar_delta, good_when_up=True),
                "note": "vs période préc.",
                "spark": period["solar_production_kwh"].tail(24).tolist(),
            },
            {
                "label": "Énergie importée réseau",
                "value": fmt.fr_number(kpis["grid_import"], 0),
                "unit": "kWh",
                "icon": "grid",
                "accent": "sky",
                "delta": _comparison_text(import_delta),
                "delta_tone": _delta_tone(import_delta, good_when_up=False),
                "note": "vs période préc.",
                "spark": period["grid_import_kwh"].tail(24).tolist(),
            },
            {
                "label": "Surplus énergétique",
                "value": fmt.fr_number(kpis["surplus"], 0),
                "unit": "kWh",
                "icon": "trend-up",
                "accent": "mint",
                "delta": _comparison_text(surplus_delta),
                "delta_tone": _delta_tone(surplus_delta, good_when_up=True),
                "note": "potentiel d'export",
                "spark": period["grid_export_kwh"].tail(24).tolist(),
            },
            {
                "label": "Taux d'autoconsommation",
                "value": fmt.fr_number(kpis["autoconsumption"], 1),
                "unit": "%",
                "icon": "gauge",
                "accent": "green",
                "delta": fmt.fr_points(auto_delta) if auto_delta is not None else "—",
                "delta_tone": _delta_tone(auto_delta, good_when_up=True),
                "note": "PV autoconsommée / PV produite",
                "spark": autoconso_series.tolist(),
                "spark_color": "#10B981",
            },
            {
                "label": "Battery State of Charge",
                "value": fmt.fr_number(kpis["soc"], 0),
                "unit": "% SOC",
                "icon": "battery",
                "accent": "amber",
                "delta": fmt.fr_points(kpis["soc_delta"]) if kpis["soc_delta"] is not None else "—",
                "delta_tone": _delta_tone(kpis["soc_delta"], good_when_up=True),
                "note": "dernière mesure simulée",
                "spark": period["battery_soc"].tail(24).tolist(),
            },
        ],
        columns=6,
    )

    # ------------------------------------------------------------------
    # Graphiques principaux
    # ------------------------------------------------------------------
    with st.container(border=True):
        panel_head(
            "Consommation vs production solaire",
            "Énergie horaire sur la période sélectionnée — échelle en kWh",
            tag="Données simulées",
            icon_name="activity",
        )
        render_chart(fig_consumption_vs_solar(period), key="ov_cons_solar")

    left, right = st.columns([1.35, 1.0], gap="medium")
    with left:
        with st.container(border=True):
            panel_head(
                "Répartition de la consommation",
                "Ventilation horaire par usage final (simulation)",
                tag="kWh",
                icon_name="layers",
            )
            render_chart(fig_consumption_area(end_use), key="ov_area")
    with right:
        with st.container(border=True):
            panel_head(
                "Sources d'énergie",
                "Part du solaire autoconsommé et du réseau dans la demande",
                tag="Bilan simplifié",
                icon_name="pie-chart",
            )
            render_chart(fig_energy_sources_donut(kpis), key="ov_donut")

    with st.container(border=True):
        panel_head(
            "Consommation journalière",
            "Énergie consommée par jour — la journée en cours peut être partielle",
            tag="kWh / jour",
            icon_name="calendar",
        )
        render_chart(fig_daily_consumption(calc.daily_summary(period)), key="ov_daily")

    # ------------------------------------------------------------------
    # Bilan énergétique
    # ------------------------------------------------------------------
    section_heading(
        "Bilan énergétique",
        "Flux estimés sur la période analysée · aucun dispatch batterie dans le bilan réseau.",
        right_html=status_pill("Bilan simplifié", "info"),
        kicker="FLUX ÉNERGÉTIQUES",
    )

    with st.container(border=True):
        balance_stats(calc.energy_balance(kpis))
        energy_flow_diagram(kpis, float(config.get("battery_capacity_kwh", 200)))
        flow_disclaimer()

        cost = calc.estimated_cost(kpis, float(config.get("energy_cost", 0.2516)))
        if cost is not None:
            symbol = currency_symbol(config)
            price = fmt.fr_number(config.get("energy_cost", 0.2516), 4)
            st.markdown(
                f"""
<div class="flow-note" style="background:#FFFFFF;border-style:solid">
  {icon("euro", size=14)}
  <div><strong>Coût indicatif de l'import réseau : {fmt.fr_number(cost, 0)} {symbol}</strong>
  — hypothèse tarifaire de démonstration à {price} {symbol}/kWh,
  configurable dans « Données & Configuration ».</div>
</div>
""",
                unsafe_allow_html=True,
            )

    # ------------------------------------------------------------------
    # Alertes
    # ------------------------------------------------------------------
    alerts = calc.build_alerts(df, kpis)
    section_heading(
        "Alertes actives",
        "Constats issus du scénario simulé — aucune action de pilotage réel n'est déclenchée.",
        right_html=alert_count_badge(alerts),
        kicker="SURVEILLANCE",
    )
    alert_cards(alerts)

    demo_notice(
        "Les KPI, graphiques et alertes sont générés à partir d'un jeu de données "
        "synthétique local. Aucun service externe, capteur ou API n'est sollicité."
    )
