"""Page 6 — Données & Configuration (inventaire réel et paramètres)."""

from __future__ import annotations

from io import BytesIO
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
)
from data import data_loader, repository
from data.data_cleaning import missing_by_column
from data.data_validation import validate_uploaded_table
from data.repository import ScenarioContext
from utils.config import APP_VERSION, CURRENCIES, DEFAULT_CONFIG
from utils import formatting as fmt
from utils.icons import icon


def _reset_config() -> None:
    """Restaure la configuration et synchronise les widgets du formulaire."""
    st.session_state["config"] = DEFAULT_CONFIG.copy()
    labels = [value["label"] for value in CURRENCIES.values()]
    st.session_state.update(
        {
            "cfg_building": DEFAULT_CONFIG["building_name"],
            "cfg_location": DEFAULT_CONFIG["location"],
            "cfg_pv": DEFAULT_CONFIG["pv_capacity_kwp"],
            "cfg_battery": DEFAULT_CONFIG["battery_capacity_kwh"],
            "cfg_currency": labels[0],
            "cfg_cost": DEFAULT_CONFIG["energy_cost"],
            "cfg_export": DEFAULT_CONFIG["export_price"],
            "cfg_bat_cost": DEFAULT_CONFIG["battery_cost_per_kwh"],
            "cfg_om": DEFAULT_CONFIG["om_rate_pct"],
            "cfg_life": DEFAULT_CONFIG["lifetime_years"],
            "cfg_init_soc": DEFAULT_CONFIG["battery_initial_soc"],
            "cfg_charge_kw": DEFAULT_CONFIG["battery_max_charge_kw"],
            "cfg_discharge_kw": DEFAULT_CONFIG["battery_max_discharge_kw"],
            "cfg_charge_eff": DEFAULT_CONFIG["battery_charge_efficiency"],
            "cfg_discharge_eff": DEFAULT_CONFIG["battery_discharge_efficiency"],
            "cfg_min_soc": DEFAULT_CONFIG["battery_min_soc"],
            "cfg_max_soc": DEFAULT_CONFIG["battery_max_soc"],
        }
    )
    st.session_state["config_reset"] = True


def _read_upload(uploaded: Any) -> tuple[pd.DataFrame | None, str | None]:
    """Lit un CSV ou un XLSX importé, sans persistance."""
    try:
        if uploaded.name.lower().endswith((".xlsx", ".xls")):
            return pd.read_excel(uploaded), None
        raw = uploaded.getvalue()
        for encoding in ("utf-8-sig", "utf-8", "latin-1"):
            try:
                return pd.read_csv(BytesIO(raw), encoding=encoding), None
            except UnicodeDecodeError:
                continue
        return None, "Encodage illisible (utf-8 / latin-1)."
    except Exception as exc:  # noqa: BLE001
        return None, str(exc)


def _dataset_card(row: dict[str, Any], last_update: str) -> None:
    dataset = {
        "name": row["label"],
        "description": row.get("description", ""),
        "rows": row.get("rows", 0),
        "columns": row.get("columns_count", len(row.get("columns", []))),
        "frequency": row.get("frequency", "—"),
        "source": row["path"],
        "status": "RÉEL" if row["exists"] else "ABSENT",
    }
    dataset_card(dataset, last_update)


def render(ctx: ScenarioContext, config: dict[str, Any]) -> None:
    render_header(
        "Données & Configuration",
        "Inventaire des jeux réels, validation et aperçu des données, imports CSV/XLSX, "
        "export du scénario et paramètres de simulation.",
        config,
    )

    latest_ts = ctx.frame["timestamp"].max() if not ctx.frame.empty else None
    last_update = fmt.fr_datetime(latest_ts)

    if st.session_state.pop("config_saved", False):
        st.success(
            "Configuration enregistrée pour la session courante. Aucune donnée n'a été "
            "envoyée à un service externe."
        )
    if st.session_state.pop("config_reset", False):
        st.info("Configuration réinitialisée aux valeurs de démonstration.", icon="ℹ️")

    # ==================================================================
    # Jeux de données réels
    # ==================================================================
    section_heading(
        "Jeux de données disponibles",
        "Fichiers réels de la branche hanine : dimensions, colonnes, couverture et qualité.",
        right_html=status_pill(
            f"{sum(1 for item in repository.get_dataset_overview() if item['exists'])} sources présentes",
            "good",
        ),
        kicker="DATASETS",
    )

    datasets = repository.get_dataset_overview()
    available = [row for row in datasets if row["exists"]]
    missing = [row for row in datasets if not row["exists"]]

    if available:
        selected_key = st.selectbox(
            "Jeu de données à inspecter",
            options=[row["key"] for row in available],
            format_func=lambda key: next(
                row["label"] for row in available if row["key"] == key
            ),
            key="dataset_inspect",
        )
        row = next(item for item in available if item["key"] == selected_key)
        left, right = st.columns([1.0, 1.6], gap="medium")
        with left:
            _dataset_card(row, last_update)
            quality = row.get("quality", {})
            st.markdown(
                f"""
<div class="dataset-facts" style="border-top:none;padding-top:0">
  <div><div class="k">Lignes</div><div class="v">{fmt.fr_number(quality.get('rows', 0), 0)}</div></div>
  <div><div class="k">Colonnes</div><div class="v">{fmt.fr_number(quality.get('columns', 0), 0)}</div></div>
  <div><div class="k">Valeurs manquantes</div><div class="v">{fmt.fr_pct(quality.get('missing_pct'), 2)}</div></div>
  <div><div class="k">Doublons temporels</div><div class="v">{fmt.fr_number(quality.get('duplicate_timestamps', 0), 0)}</div></div>
  <div><div class="k">Début</div><div class="v">{fmt.fr_datetime(quality.get('coverage_start'))}</div></div>
  <div><div class="k">Fin</div><div class="v">{fmt.fr_datetime(quality.get('coverage_end'))}</div></div>
  <div><div class="k">Fréquence</div><div class="v">{quality.get('frequency', '—')}</div></div>
  <div><div class="k">Taille fichier</div><div class="v">{fmt.fr_number(row.get('size_mb', 0), 2)} Mo</div></div>
</div>
""",
                unsafe_allow_html=True,
            )
        with right:
            with st.container(border=True):
                panel_head(
                    "Aperçu des enregistrements",
                    "Huit premières lignes du fichier source",
                    tag="APERÇU",
                    icon_name="table",
                )
                preview = row.get("preview")
                if preview is not None and not preview.empty:
                    st.dataframe(
                        preview,
                        width="stretch",
                        hide_index=True,
                        height=280,
                    )
                else:
                    st.info("Aperçu indisponible.")

            with st.container(border=True):
                panel_head(
                    "Colonnes et types",
                    "Types pandas et taux de valeurs manquantes par colonne",
                    tag="SCHÉMA",
                    icon_name="layers",
                )
                full = None
                loaders = {
                    "electricity": data_loader.load_electricity,
                    "solar": data_loader.load_solar_hourly,
                    "scenario": data_loader.load_processed_scenario,
                    "weather": data_loader.load_weather,
                    "metadata": data_loader.load_building_metadata,
                    "solar_raw": data_loader.load_solar_raw_generation,
                }
                if selected_key in loaders:
                    full = loaders[selected_key]()
                if full is not None and not full.empty:
                    st.dataframe(
                        missing_by_column(full),
                        width="stretch",
                        hide_index=True,
                        height=240,
                    )
                else:
                    st.caption("Schéma détaillé non disponible pour cette source.")

    if missing:
        st.warning(
            "Fichiers absents : "
            + ", ".join(item["path"] for item in missing)
            + ". Les fonctionnalités correspondantes sont désactivées."
        )

    # ==================================================================
    # Import de fichiers
    # ==================================================================
    section_heading(
        "Importer un fichier",
        "Le fichier est lu en mémoire, validé et prévisualisé. Il n'est ni persisté ni envoyé.",
        right_html=status_pill("TRAITEMENT LOCAL", "info"),
        kicker="IMPORT",
    )
    with st.container(border=True):
        panel_head(
            "CSV ou Excel",
            "Colonnes attendues : un horodatage (timestamp, date_time, date…) et une mesure "
            "(meter_reading, consumption_kwh, energy_kwh…).",
            tag="OPTIONNEL",
            icon_name="upload",
        )
        uploaded = st.file_uploader(
            "Fichier de mesures",
            type=["csv", "xlsx", "xls"],
            key="dataset_upload",
            help="Lecture locale avec repli d'encodage. Aucune écriture sur le disque.",
        )
        if uploaded is not None:
            imported, error = _read_upload(uploaded)
            if error or imported is None:
                st.error(f"Lecture impossible : {error or 'erreur inconnue'}")
            else:
                report = validate_uploaded_table(imported)
                st.info(
                    f"Fichier « {uploaded.name} » · {fmt.fr_number(report['rows'], 0)} lignes · "
                    f"{fmt.fr_number(len(report['columns']), 0)} colonnes · "
                    f"{fmt.human_file_size(uploaded.size)}",
                    icon="ℹ️",
                )
                if report["valid"]:
                    st.success(
                        "Structure reconnue : "
                        f"horodatage « {report['timestamp_column']} » · "
                        f"mesure « {report['value_column']} »."
                    )
                    st.dataframe(imported.head(20), width="stretch", hide_index=True)
                else:
                    st.error(" ; ".join(report["errors"]))
                for warning in report["warnings"]:
                    st.warning(warning, icon="⚠️")
                st.caption(
                    "Le fichier importé n'alimente pas le scénario affiché : seules les "
                    "données réelles intégrées au projet sont utilisées."
                )

    # ==================================================================
    # Export
    # ==================================================================
    section_heading(
        "Exporter les données traitées",
        "Téléchargement local du scénario utilisé par les six pages.",
        right_html=status_pill("CSV UTF-8", "info"),
        kicker="EXPORT",
    )
    with st.container(border=True):
        panel_head(
            "Jeux calculés",
            "Le scénario combiné, la ventilation par zone et par usage final.",
            tag="TÉLÉCHARGEMENT",
            icon_name="download",
        )
        exports = st.columns(3)
        exports_specs = [
            ("Scénario horaire", ctx.frame, "sbems_scenario_horaire.csv"),
            ("Consommation par zone", ctx.zones, "sbems_zones_estimees.csv"),
            ("Consommation par usage", ctx.end_use, "sbems_usages_estimes.csv"),
        ]
        for column, (label, frame, filename) in zip(exports, exports_specs):
            with column:
                if frame is not None and not frame.empty:
                    st.download_button(
                        label,
                        data=frame.to_csv(index=False).encode("utf-8-sig"),
                        file_name=filename,
                        mime="text/csv",
                        key=f"export_{filename}",
                        width="stretch",
                    )
                else:
                    st.button(label, disabled=True, width="stretch")
        st.markdown(
            f'<div class="upload-note">{icon("info", size=12)} '
            "Export local, sans serveur. Les champs « estimés » sont des répartitions "
            "modélisées, pas des mesures de sous-comptage.</div>",
            unsafe_allow_html=True,
        )

    # ==================================================================
    # Configuration
    # ==================================================================
    section_heading(
        "Configuration de la simulation",
        "Paramètres appliqués à la session courante : libellés, tarifs et hypothèses de stockage.",
        right_html=status_pill("SESSION UNIQUEMENT", "neutral"),
        kicker="PARAMÈTRES",
    )

    with st.container(border=True):
        panel_head(
            "Bâtiment, tarifs et batterie",
            "Ces valeurs alimentent les calculs de coût et la simulation de la page Batterie & Réseau.",
            tag="ÉDITABLE",
            icon_name="sliders",
        )
        labels = [value["label"] for value in CURRENCIES.values()]
        codes = list(CURRENCIES.keys())
        current_code = str(config.get("currency", "EUR"))
        currency_index = codes.index(current_code) if current_code in codes else 0

        widget_defaults = {
            "cfg_building": str(config.get("building_name", DEFAULT_CONFIG["building_name"])),
            "cfg_location": str(config.get("location", DEFAULT_CONFIG["location"])),
            "cfg_pv": float(config.get("pv_capacity_kwp", 0.0)),
            "cfg_battery": float(config.get("battery_capacity_kwh", 200.0)),
            "cfg_currency": labels[currency_index],
            "cfg_cost": float(config.get("energy_cost", 0.2516)),
            "cfg_export": float(config.get("export_price", 0.05)),
            "cfg_bat_cost": float(config.get("battery_cost_per_kwh", 350.0)),
            "cfg_om": float(config.get("om_rate_pct", 1.0)),
            "cfg_life": int(config.get("lifetime_years", 15)),
            "cfg_init_soc": float(config.get("battery_initial_soc", 50.0)),
            "cfg_charge_kw": float(config.get("battery_max_charge_kw", 50.0)),
            "cfg_discharge_kw": float(config.get("battery_max_discharge_kw", 50.0)),
            "cfg_charge_eff": float(config.get("battery_charge_efficiency", 0.95)),
            "cfg_discharge_eff": float(config.get("battery_discharge_efficiency", 0.95)),
            "cfg_min_soc": float(config.get("battery_min_soc", 10.0)),
            "cfg_max_soc": float(config.get("battery_max_soc", 95.0)),
        }
        for key, value in widget_defaults.items():
            st.session_state.setdefault(key, value)

        with st.form("configuration_form", clear_on_submit=False):
            c1, c2 = st.columns(2)
            with c1:
                building = st.text_input("Nom du bâtiment", key="cfg_building")
            with c2:
                location = st.text_input("Localisation", key="cfg_location")

            c3, c4, c5 = st.columns(3)
            with c3:
                pv_capacity = st.number_input(
                    "Puissance PV déclarée (kWc)", 0.0, 2000.0, step=1.0, key="cfg_pv"
                )
            with c4:
                battery_capacity = st.number_input(
                    "Capacité batterie (kWh)", 0.0, 5000.0, step=10.0, key="cfg_battery"
                )
            with c5:
                currency_label = st.selectbox("Devise", options=labels, key="cfg_currency")

            c6, c7, c8 = st.columns(3)
            with c6:
                energy_cost = st.number_input(
                    "Prix d'achat (€/kWh)", 0.0, 5.0, step=0.001,
                    format="%.4f", key="cfg_cost",
                    help="Hypothèse tarifaire, non vérifiée.",
                )
            with c7:
                export_price = st.number_input(
                    "Prix de revente (€/kWh)", 0.0, 5.0, step=0.005,
                    format="%.3f", key="cfg_export",
                )
            with c8:
                battery_unit_cost = st.number_input(
                    "Coût batterie (€/kWh)", 0.0, 5000.0, step=10.0, key="cfg_bat_cost"
                )

            c9, c10, c11 = st.columns(3)
            with c9:
                om_rate = st.number_input(
                    "Coût de maintenance (%/an)", 0.0, 20.0, step=0.5, key="cfg_om"
                )
            with c10:
                lifetime = st.number_input(
                    "Durée de vie (années)", 1, 40, step=1, key="cfg_life"
                )
            with c11:
                initial_soc = st.number_input(
                    "SOC initial simulé (%)", 0.0, 100.0, step=5.0, key="cfg_init_soc"
                )

            c12, c13, c14 = st.columns(3)
            with c12:
                charge_kw = st.number_input(
                    "Charge max (kW)", 0.0, 1000.0, step=5.0, key="cfg_charge_kw"
                )
            with c13:
                discharge_kw = st.number_input(
                    "Décharge max (kW)", 0.0, 1000.0, step=5.0, key="cfg_discharge_kw"
                )
            with c14:
                min_soc = st.number_input(
                    "SOC minimum (%)", 0.0, 99.0, step=1.0, key="cfg_min_soc"
                )

            c15, c16, c17 = st.columns(3)
            with c15:
                max_soc = st.number_input(
                    "SOC maximum (%)", 1.0, 100.0, step=1.0, key="cfg_max_soc"
                )
            with c16:
                charge_eff = st.number_input(
                    "Rendement charge", 0.01, 1.0, step=0.01,
                    format="%.2f", key="cfg_charge_eff",
                )
            with c17:
                discharge_eff = st.number_input(
                    "Rendement décharge", 0.01, 1.0, step=0.01,
                    format="%.2f", key="cfg_discharge_eff",
                )

            submitted = st.form_submit_button(
                "Enregistrer la configuration", type="primary"
            )

        if submitted:
            selected_code = codes[labels.index(currency_label)]
            st.session_state["config"] = {
                "building_name": building.strip() or DEFAULT_CONFIG["building_name"],
                "location": location.strip() or DEFAULT_CONFIG["location"],
                "pv_capacity_kwp": float(pv_capacity),
                "battery_capacity_kwh": float(battery_capacity),
                "battery_initial_soc": float(initial_soc),
                "battery_max_charge_kw": float(charge_kw),
                "battery_max_discharge_kw": float(discharge_kw),
                "battery_charge_efficiency": float(charge_eff),
                "battery_discharge_efficiency": float(discharge_eff),
                "battery_min_soc": float(min_soc),
                "battery_max_soc": float(max_soc),
                "currency": selected_code,
                "energy_cost": float(energy_cost),
                "export_price": float(export_price),
                "battery_cost_per_kwh": float(battery_unit_cost),
                "pv_cost_per_kwp": float(config.get("pv_cost_per_kwp", 900.0)),
                "om_rate_pct": float(om_rate),
                "lifetime_years": int(lifetime),
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
                "Aucune persistance : un redémarrage restaure les valeurs par défaut.</div>",
                unsafe_allow_html=True,
            )

    # ==================================================================
    # Diagnostic
    # ==================================================================
    section_heading(
        "État du système",
        "Les statuts décrivent exactement ce qui est disponible : fichiers locaux, pas de backend.",
        right_html=status_pill("AUCUN BACKEND", "bad"),
        kicker="DIAGNOSTIC",
    )
    system_left, system_right = st.columns(2, gap="medium")
    with system_left:
        with st.container(border=True):
            panel_head("Application", "Version et mode d'exécution", tag="Système", icon_name="layers")
            system_row("Version de l'application", APP_VERSION, "neutral", "layers")
            system_row("Mode courant", "Démonstration", "purple", "eye")
            system_row("Source des données", "CSV réels locaux", "good", "file")
            system_row("Validation du scénario", "OK" if ctx.validated else "Erreurs", "good" if ctx.validated else "bad", "check")
    with system_right:
        with st.container(border=True):
            panel_head("Connectivité", "Services externes et stockage", tag="Diagnostic", icon_name="activity")
            system_row("Backend applicatif", "Non connecté", "bad", "server")
            system_row("Base de données", "Non configurée", "bad", "database")
            system_row("Passerelle IoT", "Non connectée", "bad", "wifi-off")
            system_row("Batterie / BMS", "Simulation logicielle", "purple", "battery")
            system_row("Dernier relevé réel", last_update, "neutral", "clock")

    st.markdown(
        f"""
<div class="info-panel" style="background:#F8FAFC;border-color:#DCE4EF">
  <div class="ip-icon" style="background:#E2E8F0;color:#0B2545">{icon("layers", size=18)}</div>
  <div>
    <h4 style="color:#0B2545">Architecture ouverte</h4>
    <p style="color:#475569">
      Les vues consomment un <strong>ScenarioContext</strong> construit par
      <strong>data/repository.py</strong>. Le remplacement des CSV par une base
      temporelle ou un flux MQTT se fera dans la couche
      <strong>data/data_loader.py</strong>, sans réécrire les pages.
    </p>
    <div class="protocol-chips">
      <span class="protocol-chip">CSV ASHRAE</span>
      <span class="protocol-chip">CSV centrale PV</span>
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
        "Aucun fichier importé n'est persisté, aucune base n'est ouverte et aucune API "
        "n'est appelée. Seuls les CSV historiques du projet sont utilisés."
    )
