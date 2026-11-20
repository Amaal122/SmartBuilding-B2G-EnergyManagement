"""Barre latérale : marque, navigation et rappel du mode démonstration."""

from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st

from utils.config import APP_NAME, APP_SHORT, APP_VERSION
from utils.formatting import fr_datetime
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


def render_sidebar(latest_timestamp: pd.Timestamp | None = None) -> str:
    """Affiche la navigation et retourne la clé de page sélectionnée."""
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

        last_measure = (
            fr_datetime(latest_timestamp) if latest_timestamp is not None else "—"
        )
        st.markdown(
            f"""
<div class="side-demo">
  <div class="side-demo-head"><span class="pulse-dot"></span> DEMO MODE</div>
  <p>Données synthétiques générées localement. Aucun capteur, onduleur,
  compteur ou batterie physique n'est connecté.</p>
</div>
<div class="side-status">
  <div class="side-status-row"><span>Mode</span><span class="val">Simulation</span></div>
  <div class="side-status-row"><span>Backend</span><span class="val off">Non connecté</span></div>
  <div class="side-status-row"><span>Base de données</span><span class="val off">Non configurée</span></div>
  <div class="side-status-row"><span>Passerelle IoT</span><span class="val off">Non connectée</span></div>
</div>
<div class="side-footer">
  <div>{icon("clock", size=11)} Dernière mesure simulée</div>
  <div style="color:#A9C4E2;margin-top:2px">{last_measure}</div>
  <div style="margin-top:9px"><strong>{APP_NAME}</strong><br>Version {APP_VERSION} · front-end</div>
</div>
""",
            unsafe_allow_html=True,
        )

    return PAGE_KEYS.get(selection, "overview")
