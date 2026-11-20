"""Configuration de démonstration (session uniquement).

Aucune configuration n'est persistée : elle vit dans ``st.session_state`` et
disparaît à la fermeture de l'application. Elle est volontairement séparée de
la couche de données pour faciliter l'ajout d'un backend ultérieur.
"""

from __future__ import annotations

import streamlit as st

APP_NAME = "Smart Building Energy Management System"
APP_SHORT = "SBEMS"
APP_VERSION = "1.0.0"
DEMO_LABEL = "DEMO MODE – SIMULATED DATA"

DEFAULT_CONFIG: dict[str, object] = {
    "building_name": "Smart Campus Building",
    "location": "Paris, France",
    "pv_capacity_kwp": 150.1,
    "battery_capacity_kwh": 200.0,
    "currency": "EUR",
    "energy_cost": 0.2516,
}

CURRENCIES: dict[str, dict[str, str]] = {
    "EUR": {"label": "EUR — Euro (€)", "symbol": "€", "code": "EUR"},
    "USD": {"label": "USD — Dollar ($)", "symbol": "$", "code": "USD"},
    "MAD": {"label": "MAD — Dirham marocain", "symbol": "MAD", "code": "MAD"},
}

def init_session_state() -> None:
    """Initialise la configuration si nécessaire."""
    if "config" not in st.session_state or not isinstance(
        st.session_state["config"], dict
    ):
        st.session_state["config"] = DEFAULT_CONFIG.copy()
    else:
        # Complète les clés manquantes sans écraser les choix utilisateur.
        for key, value in DEFAULT_CONFIG.items():
            st.session_state["config"].setdefault(key, value)


def get_config() -> dict[str, object]:
    """Retourne la configuration courante de la session."""
    init_session_state()
    return st.session_state["config"]


def currency_symbol(config: dict[str, object] | None = None) -> str:
    """Symbole de la devise configurée."""
    cfg = config or get_config()
    code = str(cfg.get("currency", "EUR"))
    return CURRENCIES.get(code, CURRENCIES["EUR"])["symbol"]


def currency_code(config: dict[str, object] | None = None) -> str:
    """Code ISO de la devise configurée."""
    cfg = config or get_config()
    code = str(cfg.get("currency", "EUR"))
    return CURRENCIES.get(code, CURRENCIES["EUR"])["code"]
