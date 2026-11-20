"""Barre latérale : marque, navigation, sélection du scénario et statuts."""

from __future__ import annotations

from typing import Any

import streamlit as st

from data.repository import get_building_options
from utils.config import APP_NAME, APP_SHORT, APP_VERSION
from utils.icons import icon

NAV_ITEMS: list[tuple[str, str]] = [
    ("overview", ":material/space_dashboard:  Vue Générale"),
    ("energy", ":material/bolt:  Surveillance Énergétique"),
    ("solar", ":material/solar_power:  Production Photovoltaïque"),
    ("battery", ":material/battery_charging_full:  Batterie & Réseau"),
    ("environment", ":material/thermostat:  Environnement & Équipements"),
    ("settings", ":material/folder_open:  Données & Configuration"),
]

PAGE_KEYS = {label: key for key, label in NAV_ITEMS}


def _status_row(label: str, value: str, tone: str = "") -> str:
    cls = f' class="val {tone}"' if tone else ' class="val"'
    return f"<div class=\"side-status-row\"><span>{label}</span><span{cls}>{value}</span></div>"


def render_sidebar() -> str:
    """Affiche la navigation et retourne la clé de page sélectionnée."""
    options = get_building_options()
    with st.sidebar:
        st.markdown(
            f"""
<div class="sbems-brand">
  <div class="sbems-brand-logo">{icon("building", size=23)}</div>
  <div>
    <div class="sbems-brand-title">{APP_SHORT}</div>
    <div class="sbems-brand-sub">Smart Building EMS</div>
  </div>
</div>
<div class="side-section-label">Navigation</div>
""",
            unsafe_allow_html=True,
        )

        selection = st.radio(
            "Navigation",
            options=[label for _, label in NAV_ITEMS],
            label_visibility="collapsed",
            key="nav_page",
        )

        st.markdown('<div class="side-section-label">Scénario de données</div>', unsafe_allow_html=True)
        if options:
            labels = [option["label"] for option in options]
            ids = [option["id"] for option in options]
            current_id = int(st.session_state.get("scenario_building", 520))
            index = ids.index(current_id) if current_id in ids else ids.index(520) if 520 in ids else 0
            chosen = st.selectbox(
                "Bâtiment (données ASHRAE réelles)",
                options=ids,
                format_func=lambda value: next(
                    (option["label"] for option in options if option["id"] == value),
                    f"Bâtiment {value}",
                ),
                index=index,
                key="scenario_building",
                help="174 bâtiments de bureaux disposant de 744 heures de mesures complètes.",
            )
            st.number_input(
                "Couverture PV modélisée (%)",
                min_value=10.0,
                max_value=150.0,
                value=float(st.session_state.get("pv_ratio", 0.75)) * 100.0,
                step=5.0,
                key="pv_ratio_pct",
                help=(
                    "La production réelle de la centrale est mise à l'échelle pour "
                    "représenter ce pourcentage de la consommation du bâtiment. "
                    "Ce bilan est modélisé, pas mesuré."
                ),
            )
            st.session_state["pv_ratio"] = float(st.session_state["pv_ratio_pct"]) / 100.0
            st.session_state["building_id"] = int(chosen)
        else:
            st.warning("Aucun jeu de données réel trouvé dans data/.")
            st.session_state["building_id"] = 520
            st.session_state["pv_ratio"] = 0.75

        st.markdown(
            f"""
<div class="side-demo">
  <div class="side-demo-head"><span class="pulse-dot"></span> MODE DÉMONSTRATION</div>
  <p>Consommation, production PV et météo réelles (2016 / 2020). Bilan combiné
  modélisé, batterie simulée. Aucun capteur, onduleur ou BMS n'est connecté.</p>
</div>
<div class="side-status">
  {_status_row("Source", "CSV réels · hanine", "good")}
  {_status_row("Bilan combiné", "Modélisé", "warn")}
  {_status_row("Batterie", "Simulée", "warn")}
  {_status_row("Backend", "Non connecté", "off")}
  {_status_row("Base de données", "Non configurée", "off")}
  {_status_row("Passerelle IoT", "Non connectée", "off")}
</div>
<div class="side-footer">
  <div>{icon("database", size=11)} ASHRAE 2016 · Centrale PV 2020</div>
  <div style="color:#A9C4E2;margin-top:2px">744 heures alignées · pas horaire</div>
  <div style="margin-top:9px"><strong>{APP_NAME}</strong><br>Version {APP_VERSION} · données réelles</div>
</div>
""",
            unsafe_allow_html=True,
        )

    return PAGE_KEYS.get(selection, "overview")
