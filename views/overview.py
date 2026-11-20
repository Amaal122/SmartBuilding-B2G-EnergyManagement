"""Page 1 — Vue Générale (données réelles + scénario modélisé)."""

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
    fig_hourly_profile,
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
    esc,
    panel_head,
    section_heading,
    status_pill,
)
from data.repository import ScenarioContext
from services.energy_calculations import daily_summary, energy_kpis, hourly_profile
from utils import calculations as calc
from utils import formatting as fmt
from utils.config import currency_symbol
from utils.icons import icon

PERIOD_OPTIONS = {"24 heures": 1, "7 jours": 7, "14 jours": 14, "Tout": 100000}


def _delta_tone(delta: float | None, good_when_up: bool) -> str:
    if delta is None or not np.isfinite(delta):
        return "neutral"
    return "good" if (delta >= 0) == good_when_up else "bad"


def _comparison_text(delta: float | None) -> str:
    return fmt.fr_delta(delta) if delta is not None else "—"


def _provenance_banner(ctx: ScenarioContext, kpis: dict[str, Any]) -> None:
    site = ctx.site_id if ctx.site_id is not None else "—"
    building = ctx.building
    area = building.get("square_feet")
    start = fmt.fr_date(ctx.quality.get("coverage_start"))
    end = fmt.fr_date(ctx.quality.get("coverage_end"))
    area_text = f"{fmt.fr_number(area, 0)} pi²" if area else "surface inconnue"
    st.markdown(
        f"""
<div class="flow-note" style="background:#F8FAFC;border:1px solid #DCE4EF">
  <span style="color:#0B2545">{icon("database", size=16)}</span>
  <div style="flex:1">
    <div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap">
      <strong>Scénario : bâtiment {ctx.building_id} · site {site}</strong>
      {status_pill("CONSOMMATION RÉELLE", "good")}
      {status_pill("PV RÉEL MIS À L'ÉCHELLE", "info")}
      {status_pill("BILAN MODÉLISÉ", "warn")}
    </div>
    <div style="margin-top:5px;color:#475569">
      {esc(area_text)} · {fmt.fr_number(ctx.quality.get("rows", 0), 0)} heures ·
      {start} → {end} · couverture PV modélisée {fmt.fr_pct(ctx.pv_ratio * 100, 0)} ·
      facteur d'échelle {ctx.pv_scale:.5f}
    </div>
    <div style="margin-top:4px;color:#64748B;font-size:11px">
      Consommation ASHRAE (2016) et production de la centrale PV n°1 (2020)
      proviennent de deux installations distinctes : leur combinaison est un
      scénario de démonstration, pas un bilan mesuré sur un site unique.
    </div>
  </div>
</div>
""",
        unsafe_allow_html=True,
    )
    if ctx.validation_issues:
        st.error("Validation du scénario : " + " ; ".join(ctx.validation_issues))
    for warning in ctx.warnings:
        st.warning(warning, icon="⚠️")


def render(ctx: ScenarioContext, config: dict[str, Any]) -> None:
    render_header(
        "Vue Générale",
        "Pilotage global de la performance énergétique : consommation réelle ASHRAE, "
        "production photovoltaïque réelle mise à l'échelle et bilan modélisé.",
        config,
    )

    df = ctx.frame
    if df.empty:
        st.error("Aucune donnée réelle disponible. Vérifiez le dossier data/.")
        demo_notice("Aucun service externe n'est sollicité.")
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
            key="overview_period",
        )
    if not selected:
        selected = "7 jours"
    days = PERIOD_OPTIONS[selected]

    period = calc.last_days(df, days)
    previous = calc.previous_days(df, days)
    kpis = energy_kpis(period)
    previous_kpis = energy_kpis(previous)
    end_use = ctx.end_use
    if not end_use.empty:
        end_use = end_use[end_use["timestamp"] >= period["timestamp"].min()]

    # Filtre de dates précis, en complément des raccourcis 24 h / 7 j / 14 j.
    use_custom = False
    with st.expander("Filtrer par une plage de dates précise", expanded=False):
        min_day = fmt.to_date(df["timestamp"].min())
        max_day = fmt.to_date(df["timestamp"].max())
        custom_col_1, custom_col_2 = st.columns(2)
        with custom_col_1:
            custom_start = st.date_input(
                "Du", value=min_day, min_value=min_day, max_value=max_day,
                format="DD/MM/YYYY", key="ov_custom_start",
            )
        with custom_col_2:
            custom_end = st.date_input(
                "Au", value=max_day, min_value=min_day, max_value=max_day,
                format="DD/MM/YYYY", key="ov_custom_end",
            )
        use_custom = st.checkbox("Appliquer cette plage", key="ov_use_custom")
    if use_custom:
        period = calc.filter_date_range(df, custom_start, custom_end)
        previous = period.iloc[0:0].copy()
        kpis = energy_kpis(period)
        previous_kpis = energy_kpis(previous)
        days = max(1, len(period) // 24)
        if not end_use.empty and not period.empty:
            end_use = end_use[end_use["timestamp"] >= period["timestamp"].min()]

    last_ts = calc.latest_timestamp(df)
    with control_right:
        st.markdown(
            f'<div class="filter-bar" style="justify-content:flex-end">'
            f'{icon("database", size=13)} {fmt.fr_number(len(period), 0)} heures · '
            f'{fmt.fr_number(kpis["days"], 0)} jours · dernier relevé {fmt.fr_datetime(last_ts)}'
            f"</div>",
            unsafe_allow_html=True,
        )

    _provenance_banner(ctx, kpis)

    # ------------------------------------------------------------------
    # KPI
    # ------------------------------------------------------------------
    consumption_delta = calc.comparison(kpis["consumption"], previous_kpis["consumption"])
    solar_delta = calc.comparison(kpis["solar"], previous_kpis["solar"])
    import_delta = calc.comparison(kpis["grid_import"], previous_kpis["grid_import"])
    surplus_delta = calc.comparison(kpis["surplus"], previous_kpis["surplus"])
    auto_delta = (
        (kpis["autoconsumption"] or 0) - (previous_kpis["autoconsumption"] or 0)
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
                "delta_tone": _delta_tone(consumption_delta, False),
                "note": "mesure ASHRAE réelle",
                "spark": period["consumption_kwh"].tail(24).tolist(),
            },
            {
                "label": "Production photovoltaïque",
                "value": fmt.fr_number(kpis["solar"], 0),
                "unit": "kWh",
                "icon": "sun",
                "accent": "green",
                "delta": _comparison_text(solar_delta),
                "delta_tone": _delta_tone(solar_delta, True),
                "note": "PV réel · mis à l'échelle",
                "spark": period["solar_production_kwh"].tail(24).tolist(),
            },
            {
                "label": "Importation réseau",
                "value": fmt.fr_number(kpis["grid_import"], 0),
                "unit": "kWh",
                "icon": "grid",
                "accent": "sky",
                "delta": _comparison_text(import_delta),
                "delta_tone": _delta_tone(import_delta, False),
                "note": "bilan calculé sans batterie",
                "spark": period["grid_import_kwh"].tail(24).tolist(),
            },
            {
                "label": "Surplus potentiel",
                "value": fmt.fr_number(kpis["surplus"], 0),
                "unit": "kWh",
                "icon": "trend-up",
                "accent": "mint",
                "delta": _comparison_text(surplus_delta),
                "delta_tone": _delta_tone(surplus_delta, True),
                "note": "export potentiel non mesuré",
                "spark": period["grid_export_kwh"].tail(24).tolist(),
            },
            {
                "label": "Taux d'autoconsommation",
                "value": fmt.fr_number(kpis["autoconsumption"], 1),
                "unit": "%",
                "icon": "gauge",
                "accent": "green",
                "delta": fmt.fr_points(auto_delta) if auto_delta is not None else "—",
                "delta_tone": _delta_tone(auto_delta, True),
                "note": "PV autoconsommée / PV produite",
                "spark": autoconso_series.tolist(),
                "spark_color": "#10B981",
            },
            {
                "label": "Puissance maximale",
                "value": fmt.fr_number(kpis["peak_power_kw"], 1),
                "unit": "kW",
                "icon": "activity",
                "accent": "amber",
                "delta": "—",
                "delta_tone": "neutral",
                "note": (
                    f"pointe le {fmt.fr_date(kpis['peak_timestamp'])} · "
                    f"autosuffisance {fmt.fr_pct(kpis['self_sufficiency'])}"
                ),
                "spark": period["consumption_kwh"].tail(24).tolist(),
            },
        ],
        columns=6,
    )

    # ------------------------------------------------------------------
    # Graphiques
    # ------------------------------------------------------------------
    with st.container(border=True):
        panel_head(
            "Consommation vs production solaire",
            "Énergie horaire sur la période sélectionnée — mesures réelles et PV mis à l'échelle",
            tag="DONNÉES RÉELLES",
            icon_name="activity",
        )
        render_chart(fig_consumption_vs_solar(period), key="ov_cons_solar")

    left, right = st.columns([1.35, 1.0], gap="medium")
    with left:
        with st.container(border=True):
            panel_head(
                "Répartition de la consommation",
                "Ventilation horaire estimée par usage final (sous-comptage indisponible)",
                tag="ESTIMATION",
                icon_name="layers",
            )
            render_chart(fig_consumption_area(end_use), key="ov_area")
    with right:
        with st.container(border=True):
            panel_head(
                "Sources d'énergie",
                "Part du solaire autoconsommé et du réseau dans la demande",
                tag="BILAN MODÉLISÉ",
                icon_name="pie-chart",
            )
            render_chart(fig_energy_sources_donut(kpis), key="ov_donut")

    left, right = st.columns(2, gap="medium")
    with left:
        with st.container(border=True):
            panel_head(
                "Consommation journalière",
                "Énergie réelle consommée par jour",
                tag="kWh / jour",
                icon_name="calendar",
            )
            render_chart(fig_daily_consumption(daily_summary(period)), key="ov_daily")
    with right:
        with st.container(border=True):
            panel_head(
                "Profil moyen par heure",
                "Consommation réelle et production PV moyennes (0–23 h)",
                tag="kWh / h",
                icon_name="clock",
            )
            render_chart(fig_hourly_profile(hourly_profile(period)), key="ov_profile")

    # ------------------------------------------------------------------
    # Bilan énergétique
    # ------------------------------------------------------------------
    section_heading(
        "Bilan énergétique",
        "Flux calculés sur la période · aucun dispatch batterie dans le bilan réseau.",
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
  <div><strong>Estimation du coût de l'import : {fmt.fr_number(cost, 0)} {symbol}</strong>
  — tarif hypothétique de {price} {symbol}/kWh, configurable dans
  « Données & Configuration ». Aucune facture réelle n'est utilisée.</div>
</div>
""",
                unsafe_allow_html=True,
            )

    # ------------------------------------------------------------------
    # Alertes
    # ------------------------------------------------------------------
    alerts = calc.build_alerts(df, kpis)
    section_heading(
        "Constats de surveillance",
        "Seuils statistiques de démonstration appliqués aux données réelles — aucune action de pilotage.",
        right_html=alert_count_badge(alerts),
        kicker="SURVEILLANCE",
    )
    alert_cards(alerts)

    demo_notice(
        "Les consommations, la production PV et la météo sont réelles (jeux ASHRAE et centrale PV). "
        "Le couplage des deux installations, la ventilation par usage et la batterie sont modélisés."
    )
