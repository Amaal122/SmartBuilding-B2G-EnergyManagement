"""Page 6 — Données & Configuration."""

from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st

from components.header import render_header
from components.ui import (
    dataset_card,
    demo_notice,
    panel_head,
    section_heading,
    status_pill,
    system_row,
    upload_note,
)
from data.mock_data import DATASETS
from utils.config import (
    APP_VERSION,
    CURRENCIES,
    DEFAULT_CONFIG,
)
from utils import calculations as calc
from utils import formatting as fmt
from utils.icons import icon


def _reset_config() -> None:
    """Réinitialise la configuration de session et les widgets associés."""
    st.session_state["config"] = DEFAULT_CONFIG.copy()
    # Les valeurs des widgets sont écrites explicitement : les retirer du
    # session_state ne suffit pas, Streamlit peut réutiliser l'état du front-end.
    st.session_state.update(
        {
            "cfg_building": DEFAULT_CONFIG["building_name"],
            "cfg_location": DEFAULT_CONFIG["location"],
            "cfg_pv": DEFAULT_CONFIG["pv_capacity_kwp"],
            "cfg_battery": DEFAULT_CONFIG["battery_capacity_kwh"],
            "cfg_currency": CURRENCIES[str(DEFAULT_CONFIG["currency"])]["label"],
            "cfg_cost": DEFAULT_CONFIG["energy_cost"],
        }
    )
    st.session_state["config_reset"] = True


def render(df: pd.DataFrame, config: dict[str, Any]) -> None:
    render_header(
        "Données & Configuration",
        "Préparation de l'intégration backend : jeux de données, paramètres du bâtiment, "
        "tarification et état des services. Aucune connexion réelle n'est établie.",
        config,
    )

    latest_ts = calc.latest_timestamp(df)
    last_update = fmt.fr_datetime(latest_ts)

    if st.session_state.pop("config_saved", False):
        st.success(
            "Configuration enregistrée pour la session courante. Elle sera réinitialisée "
            "au prochain démarrage de l'application (aucune persistance backend)."
        )
    if st.session_state.pop("config_reset", False):
        st.info(
            "Configuration réinitialisée aux valeurs de démonstration. "
            "Aucune donnée n'a été envoyée vers un service externe.",
            icon="ℹ️",
        )

    # ==================================================================
    # Gestion des jeux de données
    # ==================================================================
    section_heading(
        "Gestion des jeux de données",
        "Jeux de données simulés, prêts à être remplacés par des sources réelles.",
        right_html=status_pill("Mode simulation", "purple"),
        kicker="DATASETS",
    )

    dataset_left, dataset_right = st.columns(2, gap="medium")
    for column, dataset, upload_label in (
        (dataset_left, DATASETS[0], "Importer un CSV ASHRAE"),
        (dataset_right, DATASETS[1], "Importer un CSV photovoltaïque"),
    ):
        with column:
            dataset_card(dataset, last_update)
            st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
            uploaded = st.file_uploader(
                upload_label,
                type=["csv"],
                key=f"upload_{dataset['key']}",
                help="Contrôle visuel de préparation. Aucun fichier n'est analysé.",
            )
            if uploaded is not None:
                st.info(
                    f"Fichier « {uploaded.name} » reçu "
                    f"({fmt.human_file_size(uploaded.size)}). "
                    "Aucune analyse ni persistance n'est effectuée dans cette version.",
                    icon="ℹ️",
                )
            upload_note()

    with st.container(border=True):
        panel_head(
            "Aperçu du jeu de données simulé",
            "Huit dernières lignes — structure prête pour l'intégration future",
            tag="Aperçu",
            icon_name="table",
        )
        preview_columns = {
            "timestamp": "Horodatage",
            "consumption_kwh": "Consommation (kWh)",
            "solar_production_kwh": "Production PV (kWh)",
            "grid_import_kwh": "Import réseau (kWh)",
            "grid_export_kwh": "Surplus (kWh)",
            "battery_soc": "SOC (%)",
            "temperature_indoor": "Temp. int. (°C)",
            "humidity": "Humidité (%)",
            "occupancy": "Occupation",
        }
        preview = df.tail(8)[list(preview_columns.keys())].rename(columns=preview_columns)
        st.dataframe(
            preview,
            width="stretch",
            hide_index=True,
            height=300,
            column_config={
                "Horodatage": st.column_config.DatetimeColumn(
                    format="DD/MM/YYYY HH:mm", width="medium"
                ),
                "Consommation (kWh)": st.column_config.NumberColumn(format="%.2f"),
                "Production PV (kWh)": st.column_config.NumberColumn(format="%.2f"),
                "Import réseau (kWh)": st.column_config.NumberColumn(format="%.2f"),
                "Surplus (kWh)": st.column_config.NumberColumn(format="%.2f"),
                "SOC (%)": st.column_config.NumberColumn(format="%.1f"),
                "Temp. int. (°C)": st.column_config.NumberColumn(format="%.1f"),
                "Humidité (%)": st.column_config.NumberColumn(format="%.0f"),
                "Occupation": st.column_config.NumberColumn(format="%d"),
            },
        )
        st.markdown(
            f"""
<div class="flow-note" style="margin-top:12px">
  {icon("info", size=14)}
  <div><strong>Formules du bilan simplifié :</strong>
  <code>grid_import = max(0, consommation − PV)</code> ·
  <code>surplus = max(0, PV − consommation)</code>.
  Une même énergie n'est jamais comptée en import et en export. Les séries
  horaires couvrent 14 jours et utilisent une graine fixe.</div>
</div>
""",
            unsafe_allow_html=True,
        )

    # ==================================================================
    # Configuration du système
    # ==================================================================
    section_heading(
        "Configuration du système",
        "Paramètres appliqués à l'interface pour la session courante.",
        right_html=status_pill("Session uniquement", "neutral"),
        kicker="PARAMÈTRES",
    )

    with st.container(border=True):
        panel_head(
            "Paramètres du bâtiment et de l'énergie",
            "Ces valeurs adaptent les libellés, le bilan et les estimations de coût.",
            tag="Éditable",
            icon_name="sliders",
        )
        currency_labels = [value["label"] for value in CURRENCIES.values()]
        currency_codes = list(CURRENCIES.keys())
        current_currency = str(config.get("currency", "EUR"))
        currency_index = (
            currency_codes.index(current_currency)
            if current_currency in currency_codes
            else 0
        )

        # Initialise les widgets une seule fois depuis la configuration de
        # session. Les valeurs sont ensuite pilotées par st.session_state,
        # ce qui permet au bouton « Réinitialiser » de les mettre à jour.
        widget_defaults = {
            "cfg_building": str(
                config.get("building_name", DEFAULT_CONFIG["building_name"])
            ),
            "cfg_location": str(config.get("location", DEFAULT_CONFIG["location"])),
            "cfg_pv": float(config.get("pv_capacity_kwp", 150.1)),
            "cfg_battery": float(config.get("battery_capacity_kwh", 200.0)),
            "cfg_currency": currency_labels[currency_index],
            "cfg_cost": float(config.get("energy_cost", 0.2516)),
        }
        for widget_key, widget_value in widget_defaults.items():
            st.session_state.setdefault(widget_key, widget_value)

        with st.form("configuration_form", clear_on_submit=False):
            line_1_left, line_1_right = st.columns(2)
            with line_1_left:
                building = st.text_input("Nom du bâtiment", key="cfg_building")
            with line_1_right:
                location = st.text_input("Localisation", key="cfg_location")

            line_2_left, line_2_right = st.columns(2)
            with line_2_left:
                pv_capacity = st.number_input(
                    "Puissance photovoltaïque installée (kWc)",
                    min_value=0.0,
                    max_value=2000.0,
                    step=5.0,
                    key="cfg_pv",
                )
            with line_2_right:
                battery_capacity = st.number_input(
                    "Capacité de la batterie (kWh)",
                    min_value=0.0,
                    max_value=5000.0,
                    step=10.0,
                    key="cfg_battery",
                )

            line_3_left, line_3_right = st.columns(2)
            with line_3_left:
                currency_label = st.selectbox(
                    "Devise",
                    options=currency_labels,
                    key="cfg_currency",
                )
            with line_3_right:
                energy_cost = st.number_input(
                    "Coût de l'énergie par kWh",
                    min_value=0.0,
                    max_value=5.0,
                    step=0.001,
                    format="%.4f",
                    key="cfg_cost",
                    help="Hypothèse tarifaire de démonstration, utilisée pour les coûts indicatifs.",
                )

            submitted = st.form_submit_button(
                "Enregistrer la configuration", type="primary"
            )

        if submitted:
            selected_code = currency_codes[currency_labels.index(currency_label)]
            st.session_state["config"] = {
                "building_name": building.strip() or DEFAULT_CONFIG["building_name"],
                "location": location.strip() or DEFAULT_CONFIG["location"],
                "pv_capacity_kwp": float(pv_capacity),
                "battery_capacity_kwh": float(battery_capacity),
                "currency": selected_code,
                "energy_cost": float(energy_cost),
            }
            st.session_state["config_saved"] = True
            st.rerun()

        reset_col, note_col = st.columns([1.0, 3.0], vertical_alignment="center")
        with reset_col:
            st.button(
                "Réinitialiser",
                on_click=_reset_config,
                key="cfg_reset",
                help="Restaure les valeurs de démonstration par défaut.",
            )
        with note_col:
            st.markdown(
                f'<div class="upload-note">{icon("info", size=12)} '
                "Configuration non persistée : un redémarrage restaure les valeurs par défaut.</div>",
                unsafe_allow_html=True,
            )

    # ==================================================================
    # Informations système
    # ==================================================================
    section_heading(
        "Informations système",
        "État des composants de l'application — front-end uniquement.",
        right_html=status_pill("Aucun backend", "bad"),
        kicker="DIAGNOSTIC",
    )

    system_left, system_right = st.columns(2, gap="medium")
    with system_left:
        with st.container(border=True):
            panel_head(
                "Application",
                "Version et mode d'exécution",
                tag="Système",
                icon_name="layers",
            )
            system_row("Version de l'application", APP_VERSION, "neutral", "layers")
            system_row("Mode courant", "Simulation", "purple", "eye")
            system_row("Backend", "Non connecté", "bad", "server")
            system_row("Base de données", "Non configurée", "bad", "database")
    with system_right:
        with st.container(border=True):
            panel_head(
                "Données et connectivité",
                "Sources et passerelles",
                tag="Diagnostic",
                icon_name="activity",
            )
            system_row("Passerelle IoT", "Non connectée", "bad", "wifi-off")
            system_row("Source de données", "Jeu synthétique local", "info", "file")
            system_row("Dernière mesure simulée", fmt.fr_datetime(latest_ts), "neutral", "clock")
            system_row("Persistance", "Désactivée", "neutral", "database")

    st.markdown(
        f"""
<div class="info-panel" style="background:#F8FAFC;border-color:#DCE4EF">
  <div class="ip-icon" style="background:#E2E8F0;color:#0B2545">{icon("layers", size=18)}</div>
  <div>
    <h4 style="color:#0B2545">Prêt pour l'intégration backend</h4>
    <p style="color:#475569">
      L'interface ne dépend que de <strong>get_energy_data()</strong>,
      <strong>get_zone_data()</strong> et <strong>get_end_use_data()</strong>.
      Ces fonctions pourront être remplacées par la lecture de CSV ASHRAE,
      une base de données, une passerelle MQTT ou des flux Modbus/BACnet sans
      réécrire les pages.
    </p>
    <div class="protocol-chips">
      <span class="protocol-chip">ASHRAE CSV</span>
      <span class="protocol-chip">Base de données</span>
      <span class="protocol-chip">MQTT</span>
      <span class="protocol-chip">Modbus TCP</span>
      <span class="protocol-chip">BACnet/IP</span>
    </div>
  </div>
</div>
""",
        unsafe_allow_html=True,
    )

    demo_notice(
        "Aucun fichier CSV n'est traité, aucune base de données n'est ouverte et "
        "aucune API n'est appelée. Toutes les valeurs affichées sont simulées."
    )
