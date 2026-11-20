"""Page 2 — Surveillance Énergétique."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

import pandas as pd
import streamlit as st

from components.charts import (
    fig_daily_consumption,
    fig_hourly_consumption,
    fig_peak_demand,
    fig_zone_distribution,
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
from data.mock_data import ZONE_NAMES, get_zone_data
from utils import calculations as calc
from utils import formatting as fmt
from utils.icons import icon


def _status_for_power(power_kw: float) -> str:
    if power_kw >= calc.PEAK_POWER_THRESHOLD_KW:
        return "Critique"
    if power_kw >= calc.PEAK_POWER_THRESHOLD_KW * 0.76:
        return "Élevé"
    if power_kw < 20:
        return "Faible"
    return "Normal"


def _style_status(value: str) -> str:
    colors = {
        "Critique": "#B91C1C",
        "Élevé": "#B45309",
        "Normal": "#047857",
        "Faible": "#64748B",
    }
    return f"color: {colors.get(value, '#334155')}; font-weight: 700;"


def render(df: pd.DataFrame, config: dict[str, Any]) -> None:
    render_header(
        "Surveillance Énergétique",
        "Analyse de la consommation électrique du bâtiment par heure, par jour et par zone. "
        "Filtres interactifs appliqués à un jeu de mesures simulées.",
        config,
    )

    zone_data = get_zone_data()
    min_date = fmt.to_date(df["timestamp"].min())
    max_date = fmt.to_date(df["timestamp"].max())
    default_start = max(min_date, max_date - timedelta(days=6))

    # ------------------------------------------------------------------
    # Filtres
    # ------------------------------------------------------------------
    with st.container(border=True):
        panel_head(
            "Filtres d'analyse",
            "Les contrôles ci-dessous actualisent immédiatement les KPI, graphiques et le journal.",
            tag="Interaction locale",
            icon_name="sliders",
        )
        filter_col_1, filter_col_2, filter_col_3 = st.columns([1.1, 0.85, 1.95])
        with filter_col_1:
            date_value = st.date_input(
                "Plage de dates",
                value=(default_start, max_date),
                min_value=min_date,
                max_value=max_date,
                format="DD/MM/YYYY",
                key="energy_dates",
            )
        with filter_col_2:
            time_period = st.selectbox(
                "Plage horaire",
                options=list(calc.TIME_PERIODS.keys()),
                index=0,
                key="energy_time",
            )
        with filter_col_3:
            selected_zones = st.multiselect(
                "Zones du bâtiment",
                options=ZONE_NAMES,
                default=ZONE_NAMES,
                key="energy_zones",
                help="Sélectionnez une ou plusieurs zones pour recomposer la consommation.",
            )

    if isinstance(date_value, (tuple, list)):
        if len(date_value) == 2:
            start_date, end_date = date_value
        elif len(date_value) == 1:
            start_date = end_date = date_value[0]
        else:
            start_date, end_date = default_start, max_date
    elif isinstance(date_value, date):
        start_date = end_date = date_value
    else:
        start_date, end_date = default_start, max_date

    if not selected_zones:
        st.warning("Sélectionnez au moins une zone du bâtiment pour afficher les mesures.")
        demo_notice("Aucune donnée n'est chargée depuis un service externe.")
        return

    filtered_zones = calc.filter_zones(zone_data, selected_zones)
    filtered_zones = calc.filter_date_range(filtered_zones, start_date, end_date)
    filtered_zones = calc.filter_time_period(filtered_zones, time_period)

    if filtered_zones.empty:
        st.warning(
            "Aucune mesure ne correspond aux filtres sélectionnés. Élargissez la plage de dates."
        )
        demo_notice("Aucune donnée n'est chargée depuis un service externe.")
        return

    hourly = (
        filtered_zones.groupby("timestamp", as_index=False)["consumption_kwh"]
        .sum()
        .sort_values("timestamp")
    )
    hourly["power_kw"] = hourly["consumption_kwh"]  # pas horaire de 1 h

    total = float(hourly["consumption_kwh"].sum())
    hours = int(len(hourly))
    avg_power = total / hours if hours else 0.0
    peak_row = hourly.loc[hourly["consumption_kwh"].idxmax()]
    peak_power = float(peak_row["consumption_kwh"])
    peak_ts = pd.Timestamp(peak_row["timestamp"])
    days = int(hourly["timestamp"].dt.normalize().nunique())
    daily_avg = total / days if days else 0.0

    hourly["date"] = hourly["timestamp"].dt.normalize()
    daily = (
        hourly.groupby("date", as_index=False)
        .agg(
            consumption_kwh=("consumption_kwh", "sum"),
            peak_power_kw=("consumption_kwh", "max"),
            samples=("timestamp", "count"),
        )
        .sort_values("date")
        .reset_index(drop=True)
    )
    zone_summary = calc.zone_summary(filtered_zones)
    total_zone = float(zone_summary["consumption_kwh"].sum()) if not zone_summary.empty else 0.0

    # ------------------------------------------------------------------
    # KPI
    # ------------------------------------------------------------------
    kpi_grid(
        [
            {
                "label": "Consommation totale",
                "value": fmt.fr_number(total, 0),
                "unit": "kWh",
                "icon": "bolt",
                "accent": "blue",
                "note": f"{fmt.fr_number(hours, 0)} heures filtrées",
            },
            {
                "label": "Puissance moyenne",
                "value": fmt.fr_number(avg_power, 1),
                "unit": "kW",
                "icon": "activity",
                "accent": "sky",
                "note": "moyenne horaire du bâtiment",
            },
            {
                "label": "Pointe de consommation",
                "value": fmt.fr_number(peak_power, 1),
                "unit": "kW",
                "icon": "trend-up",
                "accent": "amber",
                "note": f"atteinte le {fmt.fr_date(peak_ts)} à {fmt.fr_time(peak_ts)}",
            },
            {
                "label": "Consommation journalière",
                "value": fmt.fr_number(daily_avg, 0),
                "unit": "kWh / jour",
                "icon": "calendar",
                "accent": "green",
                "note": f"moyenne sur {fmt.fr_number(days, 0)} jour(s)",
            },
        ],
        columns=4,
    )

    # ------------------------------------------------------------------
    # Graphiques
    # ------------------------------------------------------------------
    with st.container(border=True):
        panel_head(
            "Consommation électrique horaire",
            f"{fmt.fr_date(start_date)} → {fmt.fr_date(end_date)} · {time_period}",
            tag="kWh / h",
            icon_name="activity",
        )
        render_chart(fig_hourly_consumption(hourly), key="en_hourly")

    left, right = st.columns(2, gap="medium")
    with left:
        with st.container(border=True):
            panel_head(
                "Consommation journalière",
                "Somme des mesures horaires retenues par jour",
                tag="kWh / jour",
                icon_name="calendar",
            )
            render_chart(fig_daily_consumption(daily), key="en_daily")
    with right:
        with st.container(border=True):
            panel_head(
                "Consommation par zone",
                f"{fmt.fr_number(total_zone, 0)} kWh répartis sur {len(zone_summary)} zone(s)",
                tag="Répartition",
                icon_name="building",
            )
            render_chart(fig_zone_distribution(zone_summary), key="en_zones")

    with st.container(border=True):
        panel_head(
            "Analyse de la pointe de demande",
            "Puissance maximale horaire par jour et seuil de surveillance simulé",
            tag="kW",
            icon_name="trend-up",
        )
        render_chart(
            fig_peak_demand(daily, calc.PEAK_POWER_THRESHOLD_KW), key="en_peak"
        )

    # ------------------------------------------------------------------
    # Journal des mesures
    # ------------------------------------------------------------------
    section_heading(
        "Journal des mesures",
        "Dernières lignes correspondant aux filtres actifs · horodatage simulé.",
        right_html=status_pill(f"{fmt.fr_number(len(filtered_zones), 0)} mesures", "info"),
        kicker="DONNÉES DÉTAILLÉES",
    )

    table = filtered_zones.sort_values("timestamp", ascending=False).head(250).copy()
    table["status"] = table["timestamp"].map(
        hourly.set_index("timestamp")["consumption_kwh"].apply(_status_for_power)
    )
    display = pd.DataFrame(
        {
            "Horodatage": pd.to_datetime(table["timestamp"]),
            "Zone": table["zone"].astype(str),
            "Consommation (kWh)": table["consumption_kwh"].round(2),
            "Puissance (kW)": table["power_kw"].round(1),
            "Statut": table["status"].astype(str),
        }
    )

    styled = display.style.map(_style_status, subset=["Statut"])
    with st.container(border=True):
        st.dataframe(
            styled,
            width="stretch",
            hide_index=True,
            height=410,
            column_config={
                "Horodatage": st.column_config.DatetimeColumn(
                    "Horodatage", format="DD/MM/YYYY HH:mm", width="medium"
                ),
                "Zone": st.column_config.TextColumn("Zone du bâtiment", width="medium"),
                "Consommation (kWh)": st.column_config.NumberColumn(
                    "Consommation (kWh)", format="%.2f", width="small"
                ),
                "Puissance (kW)": st.column_config.NumberColumn(
                    "Puissance (kW)", format="%.1f", width="small"
                ),
                "Statut": st.column_config.TextColumn("Statut", width="small"),
            },
        )
        export_table, export_note = st.columns([1.1, 3.0], vertical_alignment="center")
        with export_table:
            csv = display.to_csv(index=False).encode("utf-8-sig")
            st.download_button(
                "Exporter en CSV",
                data=csv,
                file_name="sbems_mesures_simulees.csv",
                mime="text/csv",
                key="energy_export",
            )
        with export_note:
            st.markdown(
                f'<div class="upload-note">{icon("info", size=12)} '
                f"Affichage limité aux 250 lignes les plus récentes sur "
                f"{fmt.fr_number(len(filtered_zones), 0)}. Export local, sans backend.</div>",
                unsafe_allow_html=True,
            )

    demo_notice(
        "Les mesures, statuts et pointes sont calculés à partir des données synthétiques. "
        "Aucun compteur communicant n'est relié à l'application."
    )
