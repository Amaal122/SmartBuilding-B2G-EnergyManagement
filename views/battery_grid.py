"""Page 4 — Batterie & Réseau (simulation de dispatch A/B)."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
import streamlit as st

from components.charts import (
    fig_battery_dispatch,
    fig_dispatch_comparison,
    fig_export_comparison,
    fig_grid_exchanges,
    fig_soc_evolution,
    fig_sankey_balance,
    render_chart,
)
from components.header import render_header
from components.ui import (
    battery_panel,
    demo_notice,
    esc,
    panel_head,
    section_heading,
    stat_tiles,
    status_pill,
)
from data import repository
from data.repository import ScenarioContext
from services.battery_simulation import BatteryParams, check_energy_conservation
from services.economic_analysis import EconomicAssumptions, analyze
from services.energy_calculations import daily_summary, energy_kpis
from utils import calculations as calc
from utils import formatting as fmt
from utils.config import currency_symbol
from utils.icons import icon

PERIOD_OPTIONS = {"24 heures": 1, "7 jours": 7, "14 jours": 14, "Tout": 100000}


def _initialize_widgets(config: dict[str, Any]) -> None:
    defaults = {
        "bat_capacity": float(config.get("battery_capacity_kwh", 200.0)),
        "bat_initial": float(config.get("battery_initial_soc", 50.0)),
        "bat_charge_kw": float(config.get("battery_max_charge_kw", 50.0)),
        "bat_discharge_kw": float(config.get("battery_max_discharge_kw", 50.0)),
        "bat_charge_eff": float(config.get("battery_charge_efficiency", 0.95)),
        "bat_discharge_eff": float(config.get("battery_discharge_efficiency", 0.95)),
        "bat_min_soc": float(config.get("battery_min_soc", 10.0)),
        "bat_max_soc": float(config.get("battery_max_soc", 95.0)),
    }
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)


def _params_from_session() -> BatteryParams:
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
        "Simulation configurables du stockage et comparaison A/B : scénario sans "
        "batterie contre scénario avec batterie. Toutes les valeurs batterie sont simulées.",
        config,
    )

    frame = ctx.frame
    if frame.empty:
        st.error("Aucune donnée pour alimenter la simulation.")
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
            default="14 jours",
            label_visibility="collapsed",
            key="battery_period",
        )
    if not selected:
        selected = "14 jours"
    days = PERIOD_OPTIONS[selected]
    period = calc.last_days(frame, days)

    with control_right:
        st.markdown(
            f'<div class="filter-bar" style="justify-content:flex-end">'
            f'{icon("clock", size=13)} Scénario A/B · {fmt.fr_number(len(period), 0)} heures · '
            f"données réelles + stockage simulé</div>",
            unsafe_allow_html=True,
        )

    # ------------------------------------------------------------------
    # Paramètres de simulation
    # ------------------------------------------------------------------
    section_heading(
        "Paramètres de la batterie simulée",
        "Aucune batterie physiquement présente dans les jeux de données : ces valeurs configurent une simulation.",
        right_html=status_pill("SIMULATION", "purple"),
        kicker="CONFIGURATION",
    )
    _initialize_widgets(config)

    with st.container(border=True):
        panel_head(
            "Dispatch et limites d'exploitation",
            "Modèle horaire : PV → charge, surplus → batterie puis réseau, déficit → batterie puis réseau.",
            tag="ÉDITABLE",
            icon_name="sliders",
        )
        p1, p2, p3, p4 = st.columns(4)
        with p1:
            capacity = st.number_input(
                "Capacité (kWh)", 0.0, 5000.0, step=10.0, key="bat_capacity"
            )
            initial = st.number_input(
                "SOC initial (%)", 0.0, 100.0, step=5.0, key="bat_initial"
            )
        with p2:
            charge_kw = st.number_input(
                "Charge max (kW)", 0.0, 1000.0, step=5.0, key="bat_charge_kw"
            )
            discharge_kw = st.number_input(
                "Décharge max (kW)", 0.0, 1000.0, step=5.0, key="bat_discharge_kw"
            )
        with p3:
            charge_eff = st.number_input(
                "Rendement charge", 0.01, 1.0, step=0.01, format="%.2f", key="bat_charge_eff"
            )
            discharge_eff = st.number_input(
                "Rendement décharge", 0.01, 1.0, step=0.01, format="%.2f", key="bat_discharge_eff"
            )
        with p4:
            min_soc = st.number_input(
                "SOC minimum (%)", 0.0, 99.0, step=1.0, key="bat_min_soc"
            )
            max_soc = st.number_input(
                "SOC maximum (%)", 1.0, 100.0, step=1.0, key="bat_max_soc"
            )

    params = _params_from_session()
    validation = params.validate()
    if not validation["valid"]:
        st.error("Paramètres invalides : " + " ; ".join(validation["errors"]))
        st.info("Corrigez les valeurs ci-dessus pour relancer la simulation.")
        return
    for warning in validation["warnings"]:
        st.warning(warning, icon="⚠️")

    # ------------------------------------------------------------------
    # Simulation A/B
    # ------------------------------------------------------------------
    before = repository.no_battery_result(period)
    after = repository.get_reference_battery_result(period, params)
    before_summary = repository.battery_summary(before, params)
    after_summary = repository.battery_summary(after, params)
    conservation = check_energy_conservation(after)

    assumptions = EconomicAssumptions(
        import_price=float(config.get("energy_cost", 0.2516)),
        export_price=float(config.get("export_price", 0.05)),
        battery_cost_per_kwh=float(config.get("battery_cost_per_kwh", 350.0)),
    )
    economics = analyze(
        before_summary,
        after_summary,
        assumptions,
        hours=len(period),
        capacity_kwh=params.capacity_kwh,
        pv_capacity_kwp=0.0,
    )
    symbol = currency_symbol(config)

    # Batterie — état de charge final
    soc_final = after_summary["soc_final"]
    if soc_final is not None and not np.isfinite(soc_final):
        soc_final = None
    soc_series = after["battery_soc"].dropna()
    last_delta = (
        float(soc_series.iloc[-1] - soc_series.iloc[-2]) if len(soc_series) >= 2 else None
    )
    if last_delta is None or abs(last_delta) < 0.05:
        battery_status, battery_tone = "En veille", "neutral"
    elif last_delta > 0:
        battery_status, battery_tone = "En charge", "good"
    else:
        battery_status, battery_tone = "En décharge", "warn"

    section_heading(
        "A. Batterie simulée",
        "État de charge et flux de stockage issus du dispatch configuré.",
        right_html=status_pill("SIMULÉ", "purple"),
        kicker="STOCKAGE",
    )
    left, right = st.columns([1.0, 1.4], gap="medium")
    with left:
        with st.container(border=True):
            panel_head(
                "État de charge final",
                f"Capacité simulée : {fmt.fr_number(params.capacity_kwh, 0)} kWh",
                tag="SOC",
                icon_name="battery",
            )
            battery_panel(
                soc=soc_final,
                status=battery_status,
                tone=battery_tone,
                stored_kwh=(
                    params.capacity_kwh * soc_final / 100.0
                    if soc_final is not None
                    else None
                ),
                capacity_kwh=params.capacity_kwh,
                delta_pts=last_delta,
                min_soc=after_summary["soc_min"],
                max_soc=after_summary["soc_max"],
            )
            st.markdown(
                f"""
<div class="flow-note">
  {icon("shield", size=14)}
  <div><strong>Aucun BMS réel.</strong> SOC, cycles et rendements sont calculés par
  le modèle. Aucune commande n'est envoyée à un équipement physique.</div>
</div>
""",
                unsafe_allow_html=True,
            )
    with right:
        with st.container(border=True):
            panel_head(
                "Trajectoire du SOC",
                "Plage autorisée "
                f"{fmt.fr_pct(params.min_soc_pct, 0)} – {fmt.fr_pct(params.max_soc_pct, 0)}",
                tag="% SOC simulé",
                icon_name="activity",
            )
            render_chart(fig_soc_evolution(after), key="bat_soc")

    with st.container(border=True):
        panel_head(
            "Charge et décharge simulées",
            "Barres positives = charge ; barres négatives = décharge ; ligne = SOC",
            tag="SIMULATION",
            icon_name="battery-charging-full",
        )
        render_chart(fig_battery_dispatch(after), key="bat_dispatch")

    # ------------------------------------------------------------------
    # Réseau A/B
    # ------------------------------------------------------------------
    section_heading(
        "B. Échanges avec le réseau",
        "Comparaison du scénario A (sans batterie) et du scénario B (avec batterie).",
        right_html=status_pill(
            "BILAN CONSERVÉ" if conservation["consistent"] else "INCOHÉRENT",
            "good" if conservation["consistent"] else "bad",
        ),
        kicker="COMPARAISON A/B",
    )

    stat_tiles(
        [
            {
                "label": "Import A · sans batterie",
                "value": fmt.fr_number(before_summary["grid_import"], 0),
                "unit": "kWh",
                "icon": "grid",
                "accent": "sky",
                "sub": "max(0, consommation − PV)",
            },
            {
                "label": "Import B · avec batterie",
                "value": fmt.fr_number(after_summary["grid_import"], 0),
                "unit": "kWh",
                "icon": "grid",
                "accent": "blue",
                "sub": (
                    f"− {fmt.fr_number(before_summary['grid_import'] - after_summary['grid_import'], 0)} kWh"
                    if after_summary["grid_import"] <= before_summary["grid_import"]
                    else "augmentation simulée"
                ),
            },
            {
                "label": "Export A · sans batterie",
                "value": fmt.fr_number(before_summary["grid_export"], 0),
                "unit": "kWh",
                "icon": "trend-up",
                "accent": "mint",
                "sub": "surplus potentiel",
            },
            {
                "label": "Export B · avec batterie",
                "value": fmt.fr_number(after_summary["grid_export"], 0),
                "unit": "kWh",
                "icon": "trend-up",
                "accent": "green",
                "sub": "après charge de la batterie",
            },
        ],
        columns=4,
    )

    with st.container(border=True):
        panel_head(
            "Import réseau horaire — A vs B",
            "La batterie réduit l'import en restituant l'énergie stockée aux heures de pointe.",
            tag="kWh / h",
            icon_name="activity",
        )
        render_chart(fig_dispatch_comparison(before, after), key="bat_ab_import")
    with st.container(border=True):
        panel_head(
            "Surplus exporté — A vs B",
            "Une partie du surplus PV est stockée au lieu d'être exportée.",
            tag="kWh / h",
            icon_name="trend-up",
        )
        render_chart(fig_export_comparison(before, after), key="bat_ab_export")

    with st.container(border=True):
        panel_head(
            "Bilan réseau du scénario A",
            "Sans stockage : référence utilisée pour la comparaison.",
            tag="BILAN SIMPLIFIÉ",
            icon_name="layers",
        )
        render_chart(fig_sankey_balance(before_summary), key="bat_sankey")

    # ------------------------------------------------------------------
    # Synthèse chiffrée
    # ------------------------------------------------------------------
    section_heading(
        "Synthèse et analyse économique",
        "Économies estimées à partir de tarifs configurables — aucune économie mesurée.",
        right_html=status_pill("ESTIMATIONS", "warn"),
        kicker="RÉSULTATS",
    )

    def _fmt_ratio(value: float | None) -> str:
        return fmt.fr_pct(value, 1) if value is not None else "—"

    rows = [
        ("Import réseau", fmt.fr_number(before_summary["grid_import"], 0),
         fmt.fr_number(after_summary["grid_import"], 0), "kWh"),
        ("Export / surplus", fmt.fr_number(before_summary["grid_export"], 0),
         fmt.fr_number(after_summary["grid_export"], 0), "kWh"),
        ("Autoconsommation", _fmt_ratio(before_summary["self_consumption_ratio"]),
         _fmt_ratio(after_summary["self_consumption_ratio"]), "%"),
        ("Autosuffisance", _fmt_ratio(before_summary["self_sufficiency_ratio"]),
         _fmt_ratio(after_summary["self_sufficiency_ratio"]), "%"),
        ("Coût net de l'énergie", fmt.fr_number(economics["cost_before"], 0),
         fmt.fr_number(economics["cost_after"], 0), symbol),
    ]
    body = "".join(
        f"""
<tr>
  <td class="cell-strong">{esc(label)}</td>
  <td class="cell-mono">{a} {unit}</td>
  <td class="cell-mono">{b} {unit}</td>
</tr>
"""
        for label, a, b, unit in rows
    )
    with st.container(border=True):
        panel_head(
            "Indicateurs A / B",
            "Cumuls sur la période analysée · scénario B simulateur",
            tag="DÉTAIL",
            icon_name="table",
        )
        st.markdown(
            f"""
<div class="table-scroll">
  <table class="sbems-table">
    <thead><tr><th>Indicateur</th><th>Scénario A · sans batterie</th><th>Scénario B · avec batterie</th></tr></thead>
    <tbody>{body}</tbody>
  </table>
</div>
<div class="flow-note" style="margin-top:12px">
  {icon("info", size=14)}
  <div><strong>Équations vérifiées :</strong>
  <code>PV = direct + charge + export</code> et
  <code>charge du bâtiment = direct + décharge + import</code>.
  Écart maximal : {fmt.fr_number(conservation['pv_balance_max_error'], 6)} kWh (PV) et
  {fmt.fr_number(conservation['load_balance_max_error'], 6)} kWh (charge).</div>
</div>
""",
            unsafe_allow_html=True,
        )

        st.markdown(
            f"""
<div class="dataset-facts" style="border-top:none;padding-top:0">
  <div><div class="k">Économie sur la période</div><div class="v">{fmt.fr_number(economics['savings_period'], 0)} {symbol}</div></div>
  <div><div class="k">Économie annualisée</div><div class="v">{fmt.fr_number(economics['annual_savings'], 0)} {symbol}</div></div>
  <div><div class="k">Investissement batterie estimé</div><div class="v">{fmt.fr_number(economics['investment'], 0)} {symbol}</div></div>
  <div><div class="k">Retour simple estimé</div><div class="v">{fmt.fr_number(economics['payback_years'], 1)} an(s)</div></div>
  <div><div class="k">Cycles équivalents</div><div class="v">{fmt.fr_number(after_summary['cycles'], 2)}</div></div>
  <div><div class="k">Pertes de conversion</div><div class="v">{fmt.fr_number(after_summary['losses'], 0)} kWh</div></div>
</div>
<div class="upload-note" style="margin-top:10px">
  Prix d'achat {fmt.fr_number(assumptions.import_price, 4)} {symbol}/kWh · prix de revente
  {fmt.fr_number(assumptions.export_price, 3)} {symbol}/kWh · coût batterie
  {fmt.fr_number(assumptions.battery_cost_per_kwh, 0)} {symbol}/kWh. Hypothèses
  configurables, hors actualisation, dégradation et frais d'installation.
</div>
""",
            unsafe_allow_html=True,
        )

    demo_notice(
        "La batterie, son dispatch, les coûts et les économies sont entièrement simulés. "
        "Aucun BMS, onduleur bidirectionnel ou contrat d'électricité n'est connecté."
    )
