"""Page 2 — Surveillance Énergétique (consommation ASHRAE réelle)."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

import pandas as pd
import streamlit as st

from components.charts import (
    fig_anomalies,
    fig_building_comparison,
    fig_daily_consumption,
    fig_hourly_consumption,
    fig_hourly_profile,
    fig_meter_distribution,
    fig_monthly_consumption,
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
from data import repository
from data.data_processing import ZONE_NAMES
from data.repository import ScenarioContext
from services.energy_calculations import (
    anomaly_thresholds,
    daily_summary,
    detect_anomalies,
    hourly_profile,
    monthly_summary,
)
from utils import calculations as calc
from utils import formatting as fmt
from utils.icons import icon


def _status_for_power(power_kw: float, threshold: float) -> str:
    if power_kw >= threshold:
        return "Critique"
    if power_kw >= threshold * 0.76:
        return "Élevé"
    if power_kw < threshold * 0.30:
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


def render(ctx: ScenarioContext, config: dict[str, Any]) -> None:
    render_header(
        "Surveillance Énergétique",
        "Analyse de la consommation électrique réelle (ASHRAE, compteur 0) : "
        "heures, jours, pointes, anomalies statistiques et comparaison de bâtiments.",
        config,
    )

    frame = ctx.frame
    if frame.empty:
        st.error("Aucune mesure réelle disponible.")
        return

    zone_data = ctx.zones
    min_date = fmt.to_date(frame["timestamp"].min())
    max_date = fmt.to_date(frame["timestamp"].max())
    default_start = max(min_date, max_date - timedelta(days=13))

    # ------------------------------------------------------------------
    # Filtres
    # ------------------------------------------------------------------
    with st.container(border=True):
        panel_head(
            "Filtres d'analyse",
            "Les contrôles actualisent immédiatement KPI, graphiques, anomalies et journal.",
            tag="DONNÉES RÉELLES",
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
                "Zones (répartition estimée)",
                options=ZONE_NAMES,
                default=ZONE_NAMES,
                key="energy_zones",
                help="Le bâtiment ne dispose que d'un compteur global : la répartition par zone est une estimation.",
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
        st.warning("Sélectionnez au moins une zone pour recomposer la consommation.")
        demo_notice("Aucun compteur par zone n'est présent dans le jeu ASHRAE.")
        return

    filtered_zones = calc.filter_zones(zone_data, selected_zones)
    filtered_zones = calc.filter_date_range(filtered_zones, start_date, end_date)
    filtered_zones = calc.filter_time_period(filtered_zones, time_period)
    filtered_frame = calc.filter_date_range(frame, start_date, end_date)
    filtered_frame = calc.filter_time_period(filtered_frame, time_period)

    if filtered_zones.empty or filtered_frame.empty:
        st.warning("Aucune mesure ne correspond aux filtres sélectionnés.")
        demo_notice("Élargissez la plage de dates ou la plage horaire.")
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
    threshold = float(calc.PEAK_POWER_THRESHOLD_KW)

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
                "note": f"{fmt.fr_number(hours, 0)} heures filtrées · réel",
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

    with st.container(border=True):
        panel_head(
            "Compteur et usage",
            "Nature des mesures disponibles dans le jeu de données ASHRAE traité",
            tag="MÉTADONNÉES",
            icon_name="database",
        )
        meter_left, meter_right = st.columns([1.4, 1.0], gap="medium")
        with meter_left:
            st.markdown(
                f"""
<div class="dataset-facts" style="border-top:none;padding-top:0">
  <div><div class="k">Compteur</div><div class="v">Électricité · meter 0</div></div>
  <div><div class="k">Bâtiment</div><div class="v">#{ctx.building_id} · site {ctx.site_id}</div></div>
  <div><div class="k">Pas de mesure</div><div class="v">Horaire</div></div>
  <div><div class="k">Autres compteurs</div><div class="v">Non fournis</div></div>
</div>
<div class="upload-note" style="margin-top:10px">
  Le jeu traité ne contient que le compteur électrique (0). Aucune donnée de chauffage,
  vapeur ou eau glacée n'est disponible : aucune autre catégorie n'est simulée.
</div>
""",
                unsafe_allow_html=True,
            )
        with meter_right:
            render_chart(
                fig_meter_distribution(total), key="en_meter"
            )

    # ------------------------------------------------------------------
    # Graphiques
    # ------------------------------------------------------------------
    with st.container(border=True):
        panel_head(
            "Consommation électrique horaire",
            f"{fmt.fr_date(start_date)} → {fmt.fr_date(end_date)} · {time_period}",
            tag="MESURES RÉELLES",
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
                f"{fmt.fr_number(total_zone, 0)} kWh estimés sur {len(zone_summary)} zone(s)",
                tag="ESTIMATION",
                icon_name="building",
            )
            render_chart(fig_zone_distribution(zone_summary), key="en_zones")

    left, right = st.columns(2, gap="medium")
    with left:
        with st.container(border=True):
            panel_head(
                "Analyse de la pointe de demande",
                "Puissance maximale horaire par jour et seuil de surveillance (hypothèse)",
                tag="kW",
                icon_name="trend-up",
            )
            render_chart(fig_peak_demand(daily, threshold), key="en_peak")
    with right:
        with st.container(border=True):
            panel_head(
                "Profil horaire moyen",
                "Consommation moyenne par heure de la journée",
                tag="kWh / h",
                icon_name="clock",
            )
            render_chart(
                fig_hourly_profile(hourly_profile(filtered_frame)), key="en_profile"
            )

    monthly = monthly_summary(filtered_frame)
    with st.container(border=True):
        panel_head(
            "Consommation mensuelle",
            "Agrégation disponible uniquement si l'historique couvre plusieurs mois",
            tag="kWh / mois",
            icon_name="calendar",
        )
        if len(monthly) >= 2:
            render_chart(fig_monthly_consumption(monthly), key="en_monthly")
        else:
            st.info(
                "La période filtrée ne couvre qu'un seul mois calendaire : "
                "l'agrégation mensuelle n'est pas pertinente. Utilisez la plage complète "
                "(13 mai – 15 juin) pour comparer mai et juin."
            )

    # ------------------------------------------------------------------
    # Comparaison entre bâtiments réels
    # ------------------------------------------------------------------
    section_heading(
        "Comparaison entre bâtiments",
        "Consommations réelles ASHRAE sur la même fenêtre — aucun scénario synthétique.",
        right_html=status_pill("DONNÉES RÉELLES", "good"),
        kicker="PARC DE BÂTIMENTS",
    )
    with st.container(border=True):
        panel_head(
            "Sélection de bâtiments de comparaison",
            "Choisissez jusqu'à 6 bâtiments de bureaux disposant de 744 heures complètes.",
            tag="FILTRE ACTIF",
            icon_name="building",
        )
        candidate_ids = [
            option["id"] for option in ctx.buildings if option["id"] != ctx.building_id
        ]
        defaults = [value for value in (520, 293, 375, 448) if value in candidate_ids][:3]
        selected_buildings = st.multiselect(
            "Bâtiments à comparer",
            options=candidate_ids,
            default=defaults,
            key="compare_buildings",
            format_func=lambda value: f"Bâtiment {value}",
        )
        if selected_buildings:
            comparison = repository.get_comparison_series(
                tuple([int(ctx.building_id), *[int(v) for v in selected_buildings]])
            )
            comparison = comparison[
                (comparison["timestamp"] >= pd.Timestamp(start_date))
                & (
                    comparison["timestamp"]
                    < pd.Timestamp(end_date) + pd.Timedelta(days=1)
                )
            ]
            render_chart(fig_building_comparison(comparison), key="en_compare")
        else:
            st.info("Sélectionnez au moins un bâtiment pour afficher la comparaison.")

    # ------------------------------------------------------------------
    # Anomalies statistiques
    # ------------------------------------------------------------------
    section_heading(
        "Identification d'anomalies",
        "Méthode statistique simple : score Z |z| ≥ 3 par rapport à la moyenne horaire. "
        "Aucun modèle d'apprentissage automatique n'est utilisé.",
        right_html=status_pill("SEUILS STATISTIQUES", "info"),
        kicker="ANOMALIES",
    )
    anomalies = detect_anomalies(filtered_frame)
    thresholds = anomaly_thresholds(filtered_frame)
    with st.container(border=True):
        panel_head(
            "Consommation et valeurs atypiques",
            f"Moyenne {fmt.fr_power(thresholds['mean'])} · écart-type "
            f"{fmt.fr_power(thresholds['std'])} · bornes ±3σ",
            tag=f"{len(anomalies)} point(s)",
            icon_name="activity",
        )
        render_chart(
            fig_anomalies(filtered_frame, anomalies, thresholds), key="en_anomalies"
        )
        if anomalies.empty:
            st.info(
                "Aucune valeur ne dépasse le seuil |z| ≥ 3 sur la période filtrée. "
                "Cela ne garantit pas l'absence d'anomalie de fonctionnement."
            )
        else:
            table = anomalies.copy()
            table["Horodatage"] = pd.to_datetime(table["timestamp"]).dt.strftime("%d/%m/%Y %H:%M")
            table["Valeur"] = table["value"].map(lambda v: fmt.fr_number(v, 1))
            table["Score Z"] = table["zscore"].map(lambda v: fmt.fr_number(v, 2))
            st.dataframe(
                table[["Horodatage", "scale", "Valeur", "Score Z", "direction", "severity"]]
                .rename(
                    columns={
                        "scale": "Échelle",
                        "direction": "Écart",
                        "severity": "Sévérité",
                    }
                )
                .head(100),
                width="stretch",
                hide_index=True,
                height=260,
            )

    # ------------------------------------------------------------------
    # Journal des mesures
    # ------------------------------------------------------------------
    section_heading(
        "Journal des mesures",
        "Dernières lignes correspondant aux filtres actifs · mesures ASHRAE réelles.",
        right_html=status_pill(
            f"{fmt.fr_number(len(filtered_zones), 0)} lignes", "info"
        ),
        kicker="DONNÉES DÉTAILLÉES",
    )

    table = filtered_zones.sort_values("timestamp", ascending=False).head(250).copy()
    table["status"] = table["timestamp"].map(
        hourly.set_index("timestamp")["consumption_kwh"].apply(
            lambda value: _status_for_power(value, threshold)
        )
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
                "Zone": st.column_config.TextColumn("Zone (estimée)", width="medium"),
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
                file_name="sbems_consommation_ashrae.csv",
                mime="text/csv",
                key="energy_export",
            )
        with export_note:
            st.markdown(
                f'<div class="upload-note">{icon("info", size=12)} '
                f"250 lignes affichées sur {fmt.fr_number(len(filtered_zones), 0)}. "
                "La répartition par zone est estimée ; le total est réel.</div>",
                unsafe_allow_html=True,
            )

    demo_notice(
        "Les consommations et les bâtiments comparés sont réels. Les zones, les usages "
        "finaux et le seuil de pointe sont des hypothèses de démonstration."
    )
