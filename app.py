"""SBEMS — Smart Building Energy Management System.

Point d'entrée Streamlit. L'application est volontairement limitée au
front-end : toutes les données proviennent de ``data.mock_data``.
"""

from __future__ import annotations

import streamlit as st

# Configuration de page : doit être le premier appel Streamlit.
st.set_page_config(
    page_title="SBEMS · Smart Building EMS",
    page_icon="assets/logo.png",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        "About": (
            "SBEMS — Smart Building Energy Management System\n\n"
            "Démonstrateur front-end · DEMO MODE – SIMULATED DATA\n"
            "Aucune connexion backend, base de données ou IoT."
        )
    },
)

from components.sidebar import render_sidebar  # noqa: E402
from components.ui import page_footer  # noqa: E402
from data.mock_data import get_energy_data  # noqa: E402
from utils.calculations import latest_timestamp  # noqa: E402
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

    df = get_energy_data()
    page_key = render_sidebar(latest_timestamp(df))
    config = get_config()

    renderer = PAGES.get(page_key, overview.render)
    renderer(df, config)

    page_footer(APP_VERSION)


if __name__ == "__main__":
    main()
