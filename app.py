"""SBEMS — Smart Building Energy Management System.

Point d'entrée Streamlit. Les données proviennent des jeux réels extraits de
la branche ``hanine`` (ASHRAE 2016, centrale PV 2020) ; le scénario combiné
est explicitement modélisé et la batterie simulée.
"""

from __future__ import annotations

import streamlit as st

st.set_page_config(
    page_title="SBEMS · Smart Building EMS",
    page_icon="assets/logo.png",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        "About": (
            "SBEMS — Smart Building Energy Management System\n\n"
            "Données historiques réelles + scénario modélisé + batterie simulée.\n"
            "Aucune connexion backend, base de données ou IoT."
        )
    },
)

from components.sidebar import render_sidebar  # noqa: E402
from components.ui import page_footer  # noqa: E402
from data import repository  # noqa: E402
from utils.config import APP_VERSION, get_config, init_session_state  # noqa: E402
from utils.theme import inject_css  # noqa: E402
from views import (  # noqa: E402
    battery_grid,
    energy_monitoring,
    environment,
    overview,
    settings,
    solar_production,
)

PAGES = {
    "overview": overview.render,
    "energy": energy_monitoring.render,
    "solar": solar_production.render,
    "battery": battery_grid.render,
    "environment": environment.render,
    "settings": settings.render,
}


def main() -> None:
    inject_css()
    init_session_state()

    page_key = render_sidebar()

    building_id = int(st.session_state.get("building_id", 520))
    pv_ratio = float(st.session_state.get("pv_ratio", 0.75))
    config = get_config()
    capacity = float(config.get("battery_capacity_kwh", 200.0))

    ctx = repository.get_context(building_id, pv_ratio, capacity)

    renderer = PAGES.get(page_key, overview.render)
    renderer(ctx, config)

    page_footer(APP_VERSION)


if __name__ == "__main__":
    main()
