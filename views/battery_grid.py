"""Page 4 — Batterie & Réseau (version présentation)."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
import streamlit as st

from components.charts import (
    fig_dispatch_comparison,
    fig_soc_evolution,
    fig_sankey_balance,
    render_chart,
)
from components.header import render_header
from components.ui import panel_head, stat_tiles, status_pill
from data import repository
from data.repository import ScenarioContext
from services.battery_simulation import BatteryParams, check_energy_conservation
from services.economic_analysis import EconomicAssumptions, analyze
from utils import calculations as calc
from utils import formatting as fmt
from utils.config import currency_symbol


def _params() -> BatteryParams:
    return BatteryParams(
        capacity_kwh=float(st.session_state["bat_capacity"]),
        initial_soc_pct=float(st.session_state["bat_initial"]),
        max_charge_kw=float(st.session_state["bat_charge_kw"]),
        max_discharge_kw=float(st.session_state["bat_discharge_kw"]),
        charge_efficiency=float(st.session_state["bat_charge_eff"]),
        discharge_efficiency=float(st.session_state["bat_discharge_eff"]),
        min_soc_pct=float(st.session_state["bat_min_soc"]),
        max_soc_pct=float(st.session_state["bat_max_soc"]),
    )


def render(ctx: ScenarioContext, config: dict[str, Any]) -> None:
    render_header(
        "Batterie & Réseau",
        "Simulation du stockage : comparaison sans batterie / avec batterie.",
        config,
    )
    frame = ctx.frame
    if frame.empty:
        st.error("Aucune donnée disponible.")
        return

    selected = st.segmented_control(
        "Période",
        options=["24 heures", "7 jours", "14 jours", "Tout"],
        default="14 jours",
        label_visibility="collapsed",
        key="battery_period",
    ) or "14 jours"
    days = {"24 heures": 1, "7 jours": 7, "14 jours": 14, "Tout": 100000}[selected]
    period = calc.last_days(frame, days)

    st.markdown(
        """
<div class="flow-note" style="background:#F5F3FF;border-color:#DDD6FE">
  <div><strong>Batterie simulée.</strong> Aucun stockage physique n'existe dans les
  données. Les résultats ci-dessous proviennent d'un modèle configurable.</div>
</div>
""",
        unsafe_allow_html=True,
    )

    # Paramètres
    with st.container(border=True):
        st.markdown("**Paramètres de la batterie simulée**")
        defaults = {
            "bat_capacity": float(config.get("battery_capacity_kwh", 200)),
            "bat_initial": 50.0,
            "bat_charge_kw": 50.0,
            "bat_discharge_kw": 50.0,
            "bat_charge_eff": 0.95,
            "bat_discharge_eff": 0.95,
            "bat_min_soc": 10.0,
            "bat_max_soc": 95.0,
        }
        for key, value in defaults.items():
            st.session_state.setdefault(key, value)
        a, b, c, d = st.columns(4)
        with a:
            st.number_input("Capacité (kWh)", 0.0, 5000.0, key="bat_capacity", step=10.0)
            st.number_input("SOC initial (%)", 0.0, 100.0, key="bat_initial", step=5.0)
        with b:
            st.number_input("Charge max (kW)", 0.0, 1000.0, key="bat_charge_kw", step=5.0)
            st.number_input("Décharge max (kW)", 0.0, 1000.0, key="bat_discharge_kw", step=5.0)
        with c:
            st.number_input("Rendement charge", 0.01, 1.0, key="bat_charge_eff", step=0.01)
            st.number_input("Rendement décharge", 0.01, 1.0, key="bat_discharge_eff", step=0.01)
        with d:
            st.number_input("SOC min (%)", 0.0, 99.0, key="bat_min_soc", step=1.0)
            st.number_input("SOC max (%)", 1.0, 100.0, key="bat_max_soc", step=1.0)

    params = _params()
    check = params.validate()
    if not check["valid"]:
        st.error(" ; ".join(check["errors"]))
        return

    before = repository.no_battery_result(period)
    after = repository.get_reference_battery_result(period, params)
    before_kpi = repository.battery_summary(before, params)
    after_kpi = repository.battery_summary(after, params)
    conservation = check_energy_conservation(after)

    # Résultats A/B
    stat_tiles(
        [
            {
                "label": "Import A · sans batterie",
                "value": fmt.fr_number(before_kpi["grid_import"], 0),
                "unit": "kWh",
                "icon": "grid",
                "accent": "sky",
                "sub": "référence",
            },
            {
                "label": "Import B · avec batterie",
                "value": fmt.fr_number(after_kpi["grid_import"], 0),
                "unit": "kWh",
                "icon": "grid",
                "accent": "blue",
                "sub": "simulation",
            },
            {
                "label": "Export A",
                "value": fmt.fr_number(before_kpi["grid_export"], 0),
                "unit": "kWh",
                "icon": "trend-up",
                "accent": "mint",
                "sub": "surplus",
            },
            {
                "label": "Export B",
                "value": fmt.fr_number(after_kpi["grid_export"], 0),
                "unit": "kWh",
                "icon": "trend-up",
                "accent": "green",
                "sub": "après stockage",
            },
        ],
        columns=4,
    )

    left, right = st.columns([1.2, 1], gap="medium")
    with left:
        with st.container(border=True):
            panel_head("Import réseau : A vs B", "Effet du stockage sur l'import", icon_name="activity")
            render_chart(fig_dispatch_comparison(before, after), key="bat_ab")
    with right:
        with st.container(border=True):
            panel_head("État de charge", "SOC simulé", icon_name="battery")
            render_chart(fig_soc_evolution(after), key="bat_soc")

    # Synthèse courte
    assumptions = EconomicAssumptions(
        import_price=float(config.get("energy_cost", 0.2516)),
        export_price=float(config.get("export_price", 0.05)),
        battery_cost_per_kwh=float(config.get("battery_cost_per_kwh", 350.0)),
    )
    eco = analyze(
        before_kpi, after_kpi, assumptions,
        hours=len(period), capacity_kwh=params.capacity_kwh,
    )
    symbol = currency_symbol(config)

    with st.container(border=True):
        panel_head("Résultats", "Bilan et estimation économique", tag="ESTIMATIONS", icon_name="table")
        facts = st.columns(4)
        for col, (label, value) in zip(
            facts,
            [
                ("Import évité", f"{fmt.fr_number(before_kpi['grid_import'] - after_kpi['grid_import'], 0)} kWh"),
                ("Autoconsommation B", fmt.fr_pct(after_kpi["self_consumption_ratio"], 1)),
                ("Économie estimée", f"{fmt.fr_number(eco['savings_period'], 0)} {symbol}"),
                ("Retour simple", f"{fmt.fr_number(eco['payback_years'], 1)} an(s)"),
            ],
        ):
            with col:
                st.markdown(
                    f'<div class="dataset-facts" style="border:none;padding:0">'
                    f'<div><div class="k">{label}</div><div class="v">{value}</div></div></div>',
                    unsafe_allow_html=True,
                )
        st.caption(
            f"Bilan conservé : {conservation['consistent']} · "
            f"pertes {fmt.fr_number(after_kpi['losses'], 0)} kWh · "
            "tarifs et économies = hypothèses configurables."
        )
