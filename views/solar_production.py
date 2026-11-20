"""Page 3 — Production Photovoltaïque (centrale solaire réelle)."""

from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st

from components.charts import (
    fig_daily_solar,
    fig_hourly_profile,
    fig_solar_period_donut,
    fig_solar_power,
    fig_solar_vs_consumption,
    fig_weather_overview,
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
from data import data_loader
from data.repository import ScenarioContext
from services.energy_calculations import daily_summary, energy_kpis, hourly_profile
from utils import calculations as calc
from utils import formatting as fmt
from utils.icons import icon

PERIOD_OPTIONS = {"24 heures": 1, "7 jours": 7, "14 jours": 14, "Tout": 100000}


def _delta_tone(delta: float | None, good_when_up: bool = True) -> str:
    if delta is None:
        return "neutral"
    return "good" if (delta >= 0) == good_when_up else "bad"


def _inline_facts(pairs: list[tuple[str, str]]) -> str:
    return "".join(
        f'<div><div class="k">{fmt.esc(key) if hasattr(fmt, "esc") else key}</div>'
        f'<div class="v">{value}</div></div>'
        for key, value in pairs
    )


def render(ctx: ScenarioContext, config: dict[str, Any]) -> None:
    render_header(
        "Production Photovoltaïque",
        "Production réelle de la centrale solaire n°1 (2020), mise à l'échelle pour le "
        "scénario du bâtiment ASHRAE. Données météo et qualité de mesure incluses.",
        config,
    )

    df = ctx.frame
    if df.empty:
        st.error("Aucune production photovoltaïque disponible.")
        return

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
    kpis = energy_kpis(period)
    previous_kpis = energy_kpis(previous)
    capacity = ctx.pv_peak_kw or float(config.get("pv_capacity_kwp", 100.0))
    status = calc.solar_status(period, capacity)
    latest = period.iloc[-1]
    current_power = float(latest["solar_production_kwh"])
    previous_power = (
        float(period.iloc[-2]["solar_production_kwh"]) if len(period) >= 2 else None
    )
    power_delta = current_power - previous_power if previous_power is not None else None

    with control_right:
        st.markdown(
            f'<div class="filter-bar" style="justify-content:flex-end">'
            f'{icon("clock", size=13)} Dernière mesure réelle : '
            f'{fmt.fr_datetime(latest["timestamp"])}</div>',
            unsafe_allow_html=True,
        )

    # ------------------------------------------------------------------
    # Provenance et qualité
    # ------------------------------------------------------------------
    q = ctx.quality
    st.markdown(
        f"""
<div class="flow-note" style="background:#F0FDF4;border:1px solid #BBF7D0">
  <span style="color:#047857">{icon("sun", size=16)}</span>
  <div style="flex:1">
    <div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap">
      <strong style="color:#065F46">Centrale PV n°1 · données réelles</strong>
      {status_pill("MESURES RÉELLES", "good")}
      {status_pill("MISE À L'ÉCHELLE POUR LE SCÉNARIO", "warn")}
    </div>
    <div style="margin-top:5px;color:#047857">
      Fréquence d'origine : <strong>15 minutes</strong> (onduleurs), agrégée en
      pas horaire. {fmt.fr_number(q.get("rows", 0), 0)} heures alignées ·
      {fmt.fr_number(ctx.solar_plant["ENERGIE_KWH"].sum() if "ENERGIE_KWH" in ctx.solar_plant else kpis["pv_plant"], 0)} kWh
      produits réellement sur la centrale.
    </div>
    <div style="margin-top:4px;color:#64748B;font-size:11px">
      {fmt.fr_number(q.get("solar_corrected", 0), 0)} heure(s) corrigée(s) ·
      {fmt.fr_number(q.get("weather_corrected", 0), 0)} correction(s) météo ·
      {fmt.fr_number(q.get("missing_solar", 0), 0)} heure(s) manquante(s) ·
     Trois journées sont exclues des jeux sources. Les valeurs affichées pour
      le bâtiment sont multipliées par {ctx.pv_scale:.5f} pour représenter
      {fmt.fr_pct(ctx.pv_ratio * 100, 0)} de sa consommation.
    </div>
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
    peak_solar = float(period["solar_production_kwh"].max())

    kpi_grid(
        [
            {
                "label": "Production solaire (scénario)",
                "value": fmt.fr_number(kpis["solar"], 0),
                "unit": "kWh",
                "icon": "sun",
                "accent": "green",
                "delta": fmt.fr_delta(total_delta) if total_delta is not None else "—",
                "delta_tone": _delta_tone(total_delta),
                "note": "PV réel mis à l'échelle",
                "spark": period["solar_production_kwh"].tail(24).tolist(),
            },
            {
                "label": "Puissance PV actuelle",
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
                "spark": daily_summary(period)["solar_production_kwh"].tolist(),
            },
            {
                "label": "Taux d'autoconsommation",
                "value": fmt.fr_number(kpis["autoconsumption"], 1),
                "unit": "%",
                "icon": "leaf",
                "accent": "green",
                "delta": fmt.fr_delta(self_delta) if self_delta is not None else "—",
                "delta_tone": _delta_tone(self_delta),
                "note": f"pointe PV {fmt.fr_power(peak_solar, 0)}",
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
            "Profil horaire réel agrégé et mis à l'échelle pour le scénario",
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
            render_chart(fig_daily_solar(daily_summary(period)), key="sol_daily")
    with right:
        with st.container(border=True):
            panel_head(
                "Production solaire vs consommation",
                "Comparaison des profils horaires du scénario modélisé",
                tag="kWh / h",
                icon_name="activity",
            )
            render_chart(fig_solar_vs_consumption(period), key="sol_vs_cons")

    left, right = st.columns([1.0, 1.25], gap="medium")
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
                "Profil horaire moyen",
                "Production PV et consommation moyennes par heure",
                tag="kWh / h",
                icon_name="clock",
            )
            render_chart(fig_hourly_profile(hourly_profile(period)), key="sol_profile")

    with st.container(border=True):
        panel_head(
            "Météo et irradiation",
            "Température extérieure réelle du site ASHRAE et irradiation mesurée sur la centrale",
            tag="DONNÉES RÉELLES",
            icon_name="thermometer",
        )
        render_chart(fig_weather_overview(period), key="sol_weather")

    # ------------------------------------------------------------------
    # Fiche installation
    # ------------------------------------------------------------------
    section_heading(
        "Installation photovoltaïque",
        "Caractéristiques de la centrale réelle et du scénario de couverture.",
        right_html=status_pill("SOURCE 15 MIN", "info"),
        kicker="FICHE TECHNIQUE",
    )
    raw_generation = data_loader.load_solar_raw_generation()
    inverters = (
        int(raw_generation["SOURCE_KEY"].nunique())
        if not raw_generation.empty and "SOURCE_KEY" in raw_generation
        else 22
    )
    with st.container(border=True):
        panel_head(
            "Centrale solaire n°1",
            "Les compteurs et onduleurs ne sont pas connectés en direct : cette fiche décrit les jeux de données.",
            tag="RÉEL",
            icon_name="solar-panel",
        )
        st.markdown(
            f"""
<div class="dataset-facts" style="margin-top:2px;border-top:none;padding-top:0">
  <div><div class="k">Onduleurs</div><div class="v">{inverters}</div></div>
  <div><div class="k">Puissance crête du scénario</div><div class="v">{fmt.fr_number(capacity, 1)} kW</div></div>
  <div><div class="k">Pas de mesure source</div><div class="v">15 minutes</div></div>
  <div><div class="k">Pas agrégé</div><div class="v">Horaire</div></div>
  <div><div class="k">Période source</div><div class="v">Mai – juin 2020</div></div>
  <div><div class="k">Prod. centrale (réelle)</div><div class="v">{fmt.fr_energy(kpis['pv_plant'])}</div></div>
  <div><div class="k">Facteur d'échelle</div><div class="v">{ctx.pv_scale:.5f}</div></div>
  <div><div class="k">Couverture visée</div><div class="v">{fmt.fr_pct(ctx.pv_ratio * 100, 0)}</div></div>
</div>
<div class="flow-note" style="margin-top:12px">
  {icon("info", size=14)}
  <div><strong>Données réelles, scénario modélisé.</strong> La production de la
  centrale et les variables météo sont mesurées. Le couplage avec le bâtiment
  ASHRAE et la mise à l'échelle sont une construction pédagogique.</div>
</div>
""",
            unsafe_allow_html=True,
        )

    demo_notice(
        "Aucune télémétrie d'onduleur n'est reçue en direct. Les valeurs proviennent "
        "des CSV historiques de la branche hanine."
    )
