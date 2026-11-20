"""Page 3 — Production Photovoltaïque."""

from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st

from components.charts import (
    fig_daily_solar,
    fig_solar_period_donut,
    fig_solar_power,
    fig_solar_vs_consumption,
    render_chart,
)
from components.header import render_header
from components.kpi_cards import kpi_grid
from components.ui import (
    demo_notice,
    panel_head,
    section_heading,
    status_pill,
)
from data.mock_data import PV_INSTALLATION
from utils import calculations as calc
from utils import formatting as fmt
from utils.icons import icon

PERIOD_OPTIONS = {"24 heures": 1, "7 jours": 7, "14 jours": 14}


def _delta_tone(delta: float | None, good_when_up: bool = True) -> str:
    if delta is None:
        return "neutral"
    return "good" if (delta >= 0) == good_when_up else "bad"


def render(df: pd.DataFrame, config: dict[str, Any]) -> None:
    render_header(
        "Production Photovoltaïque",
        "Suivi de la production solaire simulée : puissance, énergie journalière, "
        "autoconsommation et état de l'installation photovoltaïque.",
        config,
    )

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
            key="solar_period",
        )
    if not selected:
        selected = "7 jours"
    days = PERIOD_OPTIONS[selected]

    period = calc.last_days(df, days)
    previous = calc.previous_days(df, days)
    kpis = calc.energy_kpis(period)
    previous_kpis = calc.energy_kpis(previous)
    capacity = float(config.get("pv_capacity_kwp", PV_INSTALLATION["capacity_kwp"]))
    status = calc.solar_status(period, capacity)
    latest = period.iloc[-1]
    current_power = float(latest["solar_production_kwh"])
    previous_power = (
        float(period.iloc[-2]["solar_production_kwh"]) if len(period) >= 2 else None
    )
    power_delta = (
        current_power - previous_power if previous_power is not None else None
    )

    with control_right:
        st.markdown(
            f'<div class="filter-bar" style="justify-content:flex-end">'
            f'{icon("clock", size=13)} Dernière mesure simulée : {fmt.fr_datetime(latest["timestamp"])}</div>',
            unsafe_allow_html=True,
        )

    # ------------------------------------------------------------------
    # Indicateur de statut
    # ------------------------------------------------------------------
    st.markdown(
        f"""
<div class="flow-note" style="background:#F0FDF4;border:1px solid #BBF7D0">
  <span style="color:#047857">{icon("sun", size=16)}</span>
  <div style="flex:1">
    <div style="display:flex;align-items:center;gap:9px;flex-wrap:wrap">
      <strong style="color:#065F46">Statut de production : {status["label"]}</strong>
      {status_pill(status["pill"], status["tone"])}
      <span style="color:#047857;font-weight:700">· {fmt.fr_power(current_power, 1)}</span>
    </div>
    <div style="margin-top:2px">{status["message"]} Aucune télémétrie d'onduleur réelle n'est reçue.</div>
  </div>
</div>
""",
        unsafe_allow_html=True,
    )

    # ------------------------------------------------------------------
    # KPI
    # ------------------------------------------------------------------
    total_delta = calc.comparison(kpis["solar"], previous_kpis["solar"])
    self_delta = calc.comparison(kpis["self_consumed"], previous_kpis["self_consumed"])
    avg_daily = kpis["solar"] / kpis["days"] if kpis["days"] else 0.0
    previous_avg_daily = (
        previous_kpis["solar"] / previous_kpis["days"] if previous_kpis["days"] else 0.0
    )
    avg_delta = calc.comparison(avg_daily, previous_avg_daily)

    kpi_grid(
        [
            {
                "label": "Production solaire totale",
                "value": fmt.fr_number(kpis["solar"], 0),
                "unit": "kWh",
                "icon": "sun",
                "accent": "green",
                "delta": fmt.fr_delta(total_delta) if total_delta is not None else "—",
                "delta_tone": _delta_tone(total_delta),
                "note": "vs période préc.",
                "spark": period["solar_production_kwh"].tail(24).tolist(),
            },
            {
                "label": "Puissance photovoltaïque actuelle",
                "value": fmt.fr_number(current_power, 1),
                "unit": "kW",
                "icon": "activity",
                "accent": "mint",
                "delta": (
                    f"{fmt.fr_number(power_delta, 1, signed=True)} kW"
                    if power_delta is not None
                    else "—"
                ),
                "delta_tone": _delta_tone(power_delta),
                "note": "vs heure précédente",
                "spark": period["solar_production_kwh"].tail(12).tolist(),
            },
            {
                "label": "Production moyenne journalière",
                "value": fmt.fr_number(avg_daily, 0),
                "unit": "kWh / jour",
                "icon": "calendar",
                "accent": "sky",
                "delta": fmt.fr_delta(avg_delta) if avg_delta is not None else "—",
                "delta_tone": _delta_tone(avg_delta),
                "note": f"moyenne sur {kpis['days']} jour(s)",
                "spark": calc.daily_summary(period)["solar_production_kwh"].tolist(),
            },
            {
                "label": "Énergie autoconsommée",
                "value": fmt.fr_number(kpis["self_consumed"], 0),
                "unit": "kWh",
                "icon": "leaf",
                "accent": "green",
                "delta": fmt.fr_delta(self_delta) if self_delta is not None else "—",
                "delta_tone": _delta_tone(self_delta),
                "note": f"soit {fmt.fr_pct(kpis['autoconsumption'])} de la production",
                "spark": period["consumption_kwh"].tail(24).tolist(),
                "spark_color": "#0EA5E9",
            },
        ],
        columns=4,
    )

    # ------------------------------------------------------------------
    # Graphiques
    # ------------------------------------------------------------------
    with st.container(border=True):
        panel_head(
            "Puissance solaire produite",
            "Profil horaire simulé — production nulle la nuit, maximale autour de midi",
            tag="kWh / h",
            icon_name="sun",
        )
        render_chart(fig_solar_power(period), key="sol_power")

    left, right = st.columns(2, gap="medium")
    with left:
        with st.container(border=True):
            panel_head(
                "Production photovoltaïque journalière",
                "Énergie solaire générée par jour",
                tag="kWh / jour",
                icon_name="calendar",
            )
            render_chart(fig_daily_solar(calc.daily_summary(period)), key="sol_daily")
    with right:
        with st.container(border=True):
            panel_head(
                "Production solaire vs consommation",
                "Comparaison des deux profils horaires",
                tag="kWh / h",
                icon_name="activity",
            )
            render_chart(fig_solar_vs_consumption(period), key="sol_vs_cons")

    left, right = st.columns([1.0, 1.15], gap="medium")
    with left:
        with st.container(border=True):
            panel_head(
                "Répartition par période de la journée",
                "Part de la production selon les plages horaires",
                tag="kWh",
                icon_name="pie-chart",
            )
            render_chart(fig_solar_period_donut(period), key="sol_period")

    with right:
        with st.container(border=True):
            panel_head(
                "Installation photovoltaïque",
                "Caractéristiques simulées du champ PV du bâtiment",
                tag="Simulation",
                icon_name="solar-panel",
            )
            st.markdown(
                f"""
<div class="dataset-facts" style="margin-top:2px;border-top:none;padding-top:0">
  <div><div class="k">Panneaux</div><div class="v">{fmt.fr_number(PV_INSTALLATION["panels"], 0)}</div></div>
  <div><div class="k">Puissance installée</div><div class="v">{fmt.fr_number(capacity, 1)} kWc</div></div>
  <div><div class="k">Onduleur</div><div class="v">{fmt.fr_number(PV_INSTALLATION["inverter_kw"], 0)} kW</div></div>
  <div><div class="k">Orientation</div><div class="v">Sud · {PV_INSTALLATION["tilt"]}</div></div>
  <div><div class="k">Production estimée</div><div class="v">{fmt.fr_number(avg_daily, 0)} kWh / j</div></div>
  <div><div class="k">Statut onduleur</div><div class="v" style="color:#047857">En service</div></div>
</div>
<div class="flow-note" style="margin-top:12px">
  {icon("info", size=14)}
  <div><strong>Valeurs simulées.</strong> Aucun onduleur, compteur de production
  ou capteur d'irradiance n'est connecté. La production estimée correspond à la
  moyenne de la période analysée.</div>
</div>
""",
                unsafe_allow_html=True,
            )

    demo_notice(
        "Le profil solaire est synthétique (lever 7 h, coucher 18 h, nébulosité scénarisée). "
        "Il ne provient ni d'un onduleur ni d'un service météo."
    )
