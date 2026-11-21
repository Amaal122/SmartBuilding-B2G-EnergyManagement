"""Page 2 — Surveillance Énergétique (version présentation)."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

import pandas as pd
import streamlit as st

from components.charts import (
    fig_anomalies,
    fig_daily_consumption,
    fig_hourly_consumption,
    render_chart,
)
from components.header import render_header
from components.kpi_cards import kpi_grid
from components.ui import demo_notice, panel_head, status_pill
from data.data_processing import ZONE_NAMES
from data.repository import ScenarioContext
from services.energy_calculations import (
    anomaly_thresholds,
    detect_anomalies,
)
from utils import calculations as calc
from utils import formatting as fmt


def render(ctx: ScenarioContext, config: dict[str, Any]) -> None:
    render_header(
        "Surveillance Énergétique",
        "Analyse de la consommation électrique réelle : filtres, pointes et anomalies.",
        config,
    )
    frame = ctx.frame
    if frame.empty:
        st.error("Aucune mesure disponible.")
        return

    min_date = fmt.to_date(frame["timestamp"].min())
    max_date = fmt.to_date(frame["timestamp"].max())
    default_start = max(min_date, max_date - timedelta(days=13))

    # Filtres
    with st.container(border=True):
        c1, c2 = st.columns([1.2, 1])
        with c1:
            dates = st.date_input(
                "Plage de dates",
                value=(default_start, max_date),
                min_value=min_date,
                max_value=max_date,
                format="DD/MM/YYYY",
                key="energy_dates",
            )
        with c2:
            time_period = st.selectbox(
                "Plage horaire",
                options=list(calc.TIME_PERIODS.keys()),
                key="energy_time",
            )

    if isinstance(dates, (tuple, list)) and len(dates) == 2:
        start_date, end_date = dates
    elif isinstance(dates, date):
        start_date = end_date = dates
    else:
        start_date, end_date = default_start, max_date

    filtered = calc.filter_date_range(frame, start_date, end_date)
    filtered = calc.filter_time_period(filtered, time_period)
    if filtered.empty:
        st.warning("Aucune mesure pour ces filtres.")
        return

    total = float(filtered["consumption_kwh"].sum())
    hours = len(filtered)
    peak = float(filtered["consumption_kwh"].max())
    peak_ts = pd.Timestamp(
        filtered.loc[filtered["consumption_kwh"].idxmax(), "timestamp"]
    )
    days = filtered["timestamp"].dt.normalize().nunique()

    kpi_grid(
        [
            {
                "label": "Consommation totale",
                "value": fmt.fr_number(total, 0),
                "unit": "kWh",
                "icon": "bolt",
                "accent": "blue",
                "note": f"{hours} heures",
            },
            {
                "label": "Puissance moyenne",
                "value": fmt.fr_number(total / hours, 1),
                "unit": "kW",
                "icon": "activity",
                "accent": "sky",
                "note": "moyenne horaire",
            },
            {
                "label": "Pointe",
                "value": fmt.fr_number(peak, 1),
                "unit": "kW",
                "icon": "trend-up",
                "accent": "amber",
                "note": f"{fmt.fr_date(peak_ts)} · {fmt.fr_time(peak_ts)}",
            },
            {
                "label": "Jours couverts",
                "value": fmt.fr_number(days, 0),
                "unit": "jours",
                "icon": "calendar",
                "accent": "green",
                "note": "période filtrée",
            },
        ],
        columns=4,
    )

    with st.container(border=True):
        panel_head("Consommation horaire", "Mesures ASHRAE réelles", tag="kWh/h", icon_name="activity")
        render_chart(fig_hourly_consumption(filtered), key="en_hourly")

    with st.container(border=True):
        panel_head("Consommation journalière", "Somme par jour", tag="kWh/jour", icon_name="calendar")
        render_chart(fig_daily_consumption(calc.daily_summary(filtered)), key="en_daily")

    # Anomalies
    anomalies = detect_anomalies(filtered)
    thresholds = anomaly_thresholds(filtered)
    with st.container(border=True):
        panel_head(
            "Détection d'anomalies",
            "Méthode statistique simple : score Z ≥ 3 (pas d'IA)",
            tag=f"{len(anomalies)} point(s)",
            icon_name="alert",
        )
        render_chart(fig_anomalies(filtered, anomalies, thresholds), key="en_anomalies")
        if anomalies.empty:
            st.info("Aucune valeur atypique sur la période.")

    # Journal + export
    with st.container(border=True):
        panel_head("Journal des mesures", "Dernières lignes filtrées", tag="EXPORT CSV", icon_name="table")
        table = filtered.sort_values("timestamp", ascending=False).head(200).copy()
        display = pd.DataFrame(
            {
                "Horodatage": pd.to_datetime(table["timestamp"]),
                "Consommation (kWh)": table["consumption_kwh"].round(2).values,
            }
        )
        st.dataframe(
            display,
            width="stretch",
            hide_index=True,
            height=300,
            column_config={
                "Horodatage": st.column_config.DatetimeColumn(format="DD/MM/YYYY HH:mm"),
                "Consommation (kWh)": st.column_config.NumberColumn(format="%.2f"),
            },
        )
        st.download_button(
            "Exporter en CSV",
            data=display.to_csv(index=False).encode("utf-8-sig"),
            file_name="sbems_consommation.csv",
            mime="text/csv",
            key="energy_export",
        )

    demo_notice("Les consommations sont réelles ; le seuil d'anomalie est statistique.")
