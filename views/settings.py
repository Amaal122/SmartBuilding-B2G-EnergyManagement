"""Page 6 — Données & Configuration (version présentation)."""

from __future__ import annotations

from io import BytesIO
from typing import Any

import pandas as pd
import streamlit as st

from components.header import render_header
from components.ui import (
    dataset_card,
    panel_head,
    section_heading,
    status_pill,
    system_row,
)
from data import data_loader, repository
from data.data_validation import validate_uploaded_table
from data.repository import ScenarioContext
from utils.config import APP_VERSION, CURRENCIES, DEFAULT_CONFIG
from utils import formatting as fmt


def _reset_config() -> None:
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
    try:
        if uploaded.name.lower().endswith((".xlsx", ".xls")):
            return pd.read_excel(uploaded), None
        raw = uploaded.getvalue()
        for encoding in ("utf-8-sig", "utf-8", "latin-1"):
            try:
                return pd.read_csv(BytesIO(raw), encoding=encoding), None
            except UnicodeDecodeError:
                continue
        return None, "Encodage illisible."
    except Exception as exc:  # noqa: BLE001
        return None, str(exc)


def render(ctx: ScenarioContext, config: dict[str, Any]) -> None:
    render_header(
        "Données & Configuration",
        "Jeux de données réels, import/export et paramètres de simulation.",
        config,
    )
    if st.session_state.pop("config_saved", False):
        st.success("Configuration enregistrée pour cette session.")
    if st.session_state.pop("config_reset", False):
        st.info("Configuration réinitialisée.", icon="ℹ️")

    # ------------------------------------------------------------------
    # Jeux de données
    # ------------------------------------------------------------------
    section_heading(
        "Jeux de données réels",
        "Sélectionnez un fichier pour voir son aperçu et ses caractéristiques.",
        right_html=status_pill("7 SOURCES", "good"),
        kicker="DONNÉES",
    )
    datasets = repository.get_dataset_overview()
    available = [row for row in datasets if row["exists"]]
    if available:
        key = st.selectbox(
            "Jeu de données",
            options=[row["key"] for row in available],
            format_func=lambda k: next(r["label"] for r in available if r["key"] == k),
            key="dataset_inspect",
        )
        row = next(r for r in available if r["key"] == key)
        q = row.get("quality", {})
        left, right = st.columns([1.0, 1.5], gap="medium")
        with left:
            dataset_card(
                {
                    "name": row["label"],
                    "description": row.get("description", ""),
                    "rows": q.get("rows", 0),
                    "columns": q.get("columns", 0),
                    "frequency": row.get("frequency", "—"),
                    "source": row["path"],
                    "status": "RÉEL",
                },
                fmt.fr_datetime(ctx.frame["timestamp"].max() if not ctx.frame.empty else None),
            )
            st.markdown(
                f"""
<div class="dataset-facts" style="border-top:none;padding-top:0">
  <div><div class="k">Lignes</div><div class="v">{fmt.fr_number(q.get('rows', 0), 0)}</div></div>
  <div><div class="k">Colonnes</div><div class="v">{fmt.fr_number(q.get('columns', 0), 0)}</div></div>
  <div><div class="k">Fréquence</div><div class="v">{q.get('frequency', '—')}</div></div>
  <div><div class="k">Couverture</div><div class="v">{fmt.fr_date(q.get('coverage_start'))} → {fmt.fr_date(q.get('coverage_end'))}</div></div>
</div>
""",
                unsafe_allow_html=True,
            )
        with right:
            with st.container(border=True):
                panel_head("Aperçu", "Premières lignes du fichier", icon_name="table")
                preview = row.get("preview")
                if preview is not None and not preview.empty:
                    st.dataframe(preview, width="stretch", hide_index=True, height=250)
                else:
                    st.info("Aperçu indisponible.")

    # ------------------------------------------------------------------
    # Import / Export
    # ------------------------------------------------------------------
    section_heading("Importer / Exporter", "Fichiers traités localement, sans serveur.", kicker="ÉCHANGES")
    with st.container(border=True):
        up_col, ex_col = st.columns([1.2, 1])
        with up_col:
            st.markdown("**Importer un CSV ou XLSX**")
            uploaded = st.file_uploader(
                "Fichier de mesures", type=["csv", "xlsx", "xls"], key="dataset_upload"
            )
            if uploaded is not None:
                imported, error = _read_upload(uploaded)
                if error or imported is None:
                    st.error(f"Lecture impossible : {error}")
                else:
                    report = validate_uploaded_table(imported)
                    if report["valid"]:
                        st.success(
                            f"{report['rows']} lignes reconnues · "
                            f"horodatage « {report['timestamp_column']} » · "
                            f"mesure « {report['value_column']} »"
                        )
                        st.dataframe(imported.head(8), width="stretch", hide_index=True)
                    else:
                        st.error(" ; ".join(report["errors"]))
        with ex_col:
            st.markdown("**Télécharger les données traitées**")
            for label, frame, filename in (
                ("Scénario horaire", ctx.frame, "sbems_scenario.csv"),
                ("Zones (estimées)", ctx.zones, "sbems_zones.csv"),
                ("Usages (estimés)", ctx.end_use, "sbems_usages.csv"),
            ):
                if frame is not None and not frame.empty:
                    st.download_button(
                        label,
                        data=frame.to_csv(index=False).encode("utf-8-sig"),
                        file_name=filename,
                        mime="text/csv",
                        key=f"export_{filename}",
                        width="stretch",
                    )

    # ------------------------------------------------------------------
    # Configuration
    # ------------------------------------------------------------------
    section_heading("Configuration", "Paramètres de la session courante.", kicker="PARAMÈTRES")
    with st.container(border=True):
        labels = [value["label"] for value in CURRENCIES.values()]
        codes = list(CURRENCIES.keys())
        current = str(config.get("currency", "EUR"))
        currency_index = codes.index(current) if current in codes else 0
        defaults = {
            "cfg_building": str(config.get("building_name", DEFAULT_CONFIG["building_name"])),
            "cfg_location": str(config.get("location", DEFAULT_CONFIG["location"])),
            "cfg_pv": float(config.get("pv_capacity_kwp", 0.0)),
            "cfg_battery": float(config.get("battery_capacity_kwh", 200.0)),
            "cfg_currency": labels[currency_index],
            "cfg_cost": float(config.get("energy_cost", 0.2516)),
            "cfg_export": float(config.get("export_price", 0.05)),
            "cfg_bat_cost": float(config.get("battery_cost_per_kwh", 350.0)),
            "cfg_init_soc": float(config.get("battery_initial_soc", 50.0)),
            "cfg_charge_kw": float(config.get("battery_max_charge_kw", 50.0)),
            "cfg_discharge_kw": float(config.get("battery_max_discharge_kw", 50.0)),
            "cfg_charge_eff": float(config.get("battery_charge_efficiency", 0.95)),
            "cfg_discharge_eff": float(config.get("battery_discharge_efficiency", 0.95)),
            "cfg_min_soc": float(config.get("battery_min_soc", 10.0)),
            "cfg_max_soc": float(config.get("battery_max_soc", 95.0)),
        }
        for key, value in defaults.items():
            st.session_state.setdefault(key, value)

        with st.form("configuration_form"):
            a, b = st.columns(2)
            with a:
                building = st.text_input("Nom du bâtiment", key="cfg_building")
            with b:
                location = st.text_input("Localisation", key="cfg_location")
            a, b, c = st.columns(3)
            with a:
                cost = st.number_input("Prix achat (€/kWh)", 0.0, 5.0, step=0.001, format="%.4f", key="cfg_cost")
            with b:
                export_price = st.number_input("Prix revente (€/kWh)", 0.0, 5.0, step=0.005, format="%.3f", key="cfg_export")
            with c:
                currency_label = st.selectbox("Devise", options=labels, key="cfg_currency")
            a, b, c = st.columns(3)
            with a:
                battery = st.number_input("Capacité batterie (kWh)", 0.0, 5000.0, step=10.0, key="cfg_battery")
            with b:
                bat_cost = st.number_input("Coût batterie (€/kWh)", 0.0, 5000.0, step=10.0, key="cfg_bat_cost")
            with c:
                pv = st.number_input("Puissance PV (kWc)", 0.0, 2000.0, step=1.0, key="cfg_pv")
            a, b, c = st.columns(3)
            with a:
                soc_init = st.number_input("SOC initial (%)", 0.0, 100.0, step=5.0, key="cfg_init_soc")
            with b:
                min_soc = st.number_input("SOC min (%)", 0.0, 99.0, step=1.0, key="cfg_min_soc")
            with c:
                max_soc = st.number_input("SOC max (%)", 1.0, 100.0, step=1.0, key="cfg_max_soc")
            a, b, c = st.columns(3)
            with a:
                charge_kw = st.number_input("Charge max (kW)", 0.0, 1000.0, step=5.0, key="cfg_charge_kw")
            with b:
                discharge_kw = st.number_input("Décharge max (kW)", 0.0, 1000.0, step=5.0, key="cfg_discharge_kw")
            with c:
                eff = st.number_input("Rendement (charge/décharge)", 0.01, 1.0, step=0.01, format="%.2f", key="cfg_charge_eff")
            st.session_state["cfg_discharge_eff"] = eff
            submitted = st.form_submit_button("Enregistrer", type="primary")

        if submitted:
            st.session_state["config"] = {
                "building_name": building.strip() or DEFAULT_CONFIG["building_name"],
                "location": location.strip() or DEFAULT_CONFIG["location"],
                "pv_capacity_kwp": float(pv),
                "battery_capacity_kwh": float(battery),
                "battery_initial_soc": float(soc_init),
                "battery_max_charge_kw": float(charge_kw),
                "battery_max_discharge_kw": float(discharge_kw),
                "battery_charge_efficiency": float(eff),
                "battery_discharge_efficiency": float(eff),
                "battery_min_soc": float(min_soc),
                "battery_max_soc": float(max_soc),
                "currency": codes[labels.index(currency_label)],
                "energy_cost": float(cost),
                "export_price": float(export_price),
                "battery_cost_per_kwh": float(bat_cost),
                "pv_cost_per_kwp": float(config.get("pv_cost_per_kwp", 900.0)),
                "om_rate_pct": float(config.get("om_rate_pct", 1.0)),
                "lifetime_years": int(config.get("lifetime_years", 15)),
            }
            st.session_state["config_saved"] = True
            st.rerun()
        st.button("Réinitialiser", on_click=_reset_config, key="cfg_reset")

    # ------------------------------------------------------------------
    # Statut
    # ------------------------------------------------------------------
    section_heading("État du système", "Aucun service externe n'est connecté.", kicker="DIAGNOSTIC")
    with st.container(border=True):
        c1, c2 = st.columns(2)
        with c1:
            system_row("Version", APP_VERSION, "neutral", "layers")
            system_row("Source", "CSV réels (hanine)", "good", "file")
            system_row("Validation", "OK" if ctx.validated else "Erreurs", "good" if ctx.validated else "bad", "check")
        with c2:
            system_row("Backend", "Non connecté", "bad", "server")
            system_row("Base de données", "Non configurée", "bad", "database")
            system_row("Passerelle IoT", "Non connectée", "bad", "wifi-off")

    st.caption(
        "Les fichiers importés ne sont ni persistés ni envoyés. "
        "Seuls les CSV historiques du projet alimentent le tableau de bord."
    )
