"""Page 4 — Batterie & Réseau."""

from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st

from components.charts import (
    fig_balance_comparison,
    fig_battery_flows,
    fig_grid_exchanges,
    fig_sankey_balance,
    fig_soc_evolution,
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
from utils import calculations as calc
from utils import formatting as fmt
from utils.config import currency_symbol
from utils.icons import icon

PERIOD_OPTIONS = {"24 heures": 1, "7 jours": 7, "14 jours": 14}


def render(df: pd.DataFrame, config: dict[str, Any]) -> None:
    render_header(
        "Batterie & Réseau",
        "Suivi du stockage simulé et des échanges avec le réseau électrique : "
        "état de charge, import, surplus potentiel et bilan énergétique.",
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
            key="battery_period",
        )
    if not selected:
        selected = "7 jours"
    days = PERIOD_OPTIONS[selected]

    period = calc.last_days(df, days)
    kpis = calc.energy_kpis(period)
    capacity = float(config.get("battery_capacity_kwh", 200.0))
    battery = calc.battery_snapshot(period, capacity)
    grid = calc.grid_snapshot(period)
    daily = calc.daily_summary(period)

    with control_right:
        st.markdown(
            f'<div class="filter-bar" style="justify-content:flex-end">'
            f'{icon("clock", size=13)} Dernière mesure simulée : '
            f'{fmt.fr_datetime(calc.latest_timestamp(period))}</div>',
            unsafe_allow_html=True,
        )

    # ==================================================================
    # A. Batterie
    # ==================================================================
    section_heading(
        "A. Surveillance de la batterie",
        "Indicateur visuel, état de charge et évolution sur la période · aucune commande physique.",
        right_html=status_pill("Stockage simulé", "purple"),
        kicker="STOCKAGE",
    )

    left, right = st.columns([1.0, 1.35], gap="medium")
    with left:
        with st.container(border=True):
            panel_head(
                "État de charge de la batterie",
                f"Capacité de référence : {fmt.fr_number(capacity, 0)} kWh",
                tag="SOC",
                icon_name="battery",
            )
            battery_panel(
                soc=battery["soc"],
                status=battery["status"],
                tone=battery["tone"],
                stored_kwh=battery["stored_kwh"],
                capacity_kwh=capacity,
                delta_pts=battery["soc_delta"],
                min_soc=battery["min_soc"],
                max_soc=battery["max_soc"],
            )
            st.markdown(
                f"""
<div class="flow-note">
  {icon("shield", size=14)}
  <div><strong>Batterie non pilotée.</strong> La charge et la décharge sont
  illustratives et ne déclenchent aucun ordre vers un système réel.</div>
</div>
""",
                unsafe_allow_html=True,
            )
    with right:
        with st.container(border=True):
            panel_head(
                "Évolution du State of Charge",
                "Trajectoire horaire du SOC simulé, plage cible 20–90 %",
                tag="% SOC",
                icon_name="activity",
            )
            render_chart(fig_soc_evolution(period), key="bat_soc")

    # ------------------------------------------------------------------
    # B. Réseau
    # ------------------------------------------------------------------
    section_heading(
        "B. Surveillance du réseau",
        "Échanges avec le réseau électrique sur la période sélectionnée.",
        right_html=status_pill(grid["status"], grid["tone"]),
        kicker="RÉSEAU",
    )

    cost = calc.estimated_cost(kpis, float(config.get("energy_cost", 0.2516)))
    symbol = currency_symbol(config)
    import_sub = "énergie fournie au bâtiment"
    if cost is not None:
        import_sub = f"coût indicatif {fmt.fr_number(cost, 0)} {symbol}"

    stat_tiles(
        [
            {
                "label": "Import réseau",
                "value": fmt.fr_number(grid["import_kwh"], 0),
                "unit": "kWh",
                "icon": "grid",
                "accent": "sky",
                "sub": import_sub,
            },
            {
                "label": "Surplus potentiel",
                "value": fmt.fr_number(grid["export_kwh"], 0),
                "unit": "kWh",
                "icon": "trend-up",
                "accent": "green",
                "sub": "export réseau non simulé",
            },
            {
                "label": "Statut des échanges",
                "value": grid["status"],
                "unit": "",
                "icon": "plug",
                "accent": "green" if grid["tone"] == "good" else "blue",
                "sub": "dernière mesure simulée",
            },
            {
                "label": "Dépendance au réseau",
                "value": fmt.fr_number(grid["dependency"], 1),
                "unit": "%",
                "icon": "gauge",
                "accent": "amber",
                "sub": "import / consommation totale",
            },
        ],
        columns=4,
    )

    with st.container(border=True):
        panel_head(
            "Échanges réseau horaires",
            "Import réel simulé et surplus PV potentiel — les deux flux ne se cumulent jamais",
            tag="kWh / h",
            icon_name="activity",
        )
        render_chart(fig_grid_exchanges(period), key="grid_exchanges")
        st.markdown(
            f'<div class="upload-note">{icon("info", size=12)} '
            "L'export vers le réseau n'est pas comptabilisé dans cette version : "
            "le surplus est un potentiel disponible.</div>",
            unsafe_allow_html=True,
        )

    # ------------------------------------------------------------------
    # C. Bilan énergétique
    # ------------------------------------------------------------------
    section_heading(
        "C. Bilan énergétique",
        "Comparaison des postes de consommation, production, stockage et échanges.",
        right_html=status_pill("Sans dispatch batterie", "info"),
        kicker="SYNTHÈSE",
    )

    left, right = st.columns([1.0, 1.25], gap="medium")
    with left:
        with st.container(border=True):
            panel_head(
                "Flux du bilan simplifié",
                "Solaire et réseau vers le bâtiment et le surplus",
                tag="Sankey",
                icon_name="layers",
            )
            render_chart(fig_sankey_balance(kpis), key="bat_sankey")
    with right:
        with st.container(border=True):
            panel_head(
                "Comparaison journalière",
                "Consommation, production, import et surplus par jour",
                tag="kWh / jour",
                icon_name="activity",
            )
            render_chart(fig_balance_comparison(daily), key="bat_balance")

    with st.container(border=True):
        panel_head(
            "Flux batterie illustratifs",
            "Charge et décharge simulées — hors bilan réseau de cette version",
            tag="Simulation",
            icon_name="battery-charge",
        )
        render_chart(fig_battery_flows(daily), key="bat_flows")

    # ------------------------------------------------------------------
    # Synthèse tabulaire
    # ------------------------------------------------------------------
    with st.container(border=True):
        panel_head(
            "Synthèse du bilan",
            "Valeurs cumulées sur la période et formule appliquée",
            tag="Détail",
            icon_name="table",
        )
        rows = [
            ("Demande du bâtiment", kpis["consumption"], "Somme horaire"),
            ("Production photovoltaïque", kpis["solar"], "Production solaire simulée"),
            ("Solaire autoconsommée", kpis["self_consumed"], "min(consommation, PV) cumulé"),
            ("Import réseau", kpis["grid_import"], "max(0, consommation − PV)"),
            ("Surplus potentiel", kpis["surplus"], "max(0, PV − consommation)"),
            (
                "Charge batterie",
                kpis["battery_charge"],
                "Illustratif — exclu du bilan réseau",
            ),
            (
                "Décharge batterie",
                kpis["battery_discharge"],
                "Illustratif — exclu du bilan réseau",
            ),
        ]
        body = "".join(
            f"""
<tr>
  <td class="cell-strong">{esc(label)}</td>
  <td class="cell-mono">{fmt.fr_number(value, 0)} kWh</td>
  <td class="cell-muted">{esc(note)}</td>
</tr>
"""
            for label, value, note in rows
        )
        st.markdown(
            f"""
<div class="table-scroll">
  <table class="sbems-table">
    <thead><tr><th>Poste énergétique</th><th>Valeur</th><th>Commentaire</th></tr></thead>
    <tbody>{body}</tbody>
  </table>
</div>
<div class="flow-note" style="margin-top:12px">
  {icon("info", size=14)}
  <div><strong>Bilan simplifié sans dispatch batterie.</strong>
  Le stockage ne modifie pas l'import réseau : celui-ci reste
  <code>max(0, consommation − production PV)</code>. Aucune énergie n'est
  comptée simultanément en import et en export.</div>
</div>
""",
            unsafe_allow_html=True,
        )

    demo_notice(
        "La batterie et les échanges réseau sont entièrement simulés. "
        "Aucun BMS, onduleur ou compteur bidirectionnel n'est connecté."
    )
