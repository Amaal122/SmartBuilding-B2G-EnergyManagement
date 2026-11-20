"""Couche d'accès aux données — version simulation.

Le reste de l'application ne consomme que ``get_energy_data()``,
``get_zone_data()`` et ``get_end_use_data()``. Lors de l'intégration d'un
backend réel (CSV ASHRAE, base de données, MQTT, Modbus, BACnet), seules les
implémentations de ces fonctions devront être remplacées.

Toutes les séries sont générées localement avec une graine fixe : les
graphiques restent cohérents d'un rafraîchissement à l'autre.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import streamlit as st

SEED = 20261119
HISTORY_DAYS = 14
BATTERY_REFERENCE_KWH = 200.0

ZONE_DEFINITIONS = [
    {"name": "RDC · Accueil", "share": 0.17},
    {"name": "Étage 1 · Bureaux", "share": 0.31},
    {"name": "Étage 2 · Laboratoires", "share": 0.24},
    {"name": "Étage 3 · Réunions", "share": 0.16},
    {"name": "Toiture · Technique", "share": 0.12},
]

ZONE_NAMES = [zone["name"] for zone in ZONE_DEFINITIONS]

END_USE_NAMES = [
    "HVAC",
    "Éclairage",
    "Équipements bureautiques",
    "Eau chaude sanitaire",
    "Auxiliaires & ascenseurs",
]

PV_INSTALLATION = {
    "panels": 380,
    "panel_power_wc": 395,
    "capacity_kwp": 150.1,
    "inverter": "Onduleur central triphasé — 150 kW",
    "inverter_kw": 150.0,
    "inverter_status": "En service (simulé)",
    "orientation": "Sud",
    "tilt": "30°",
}

DATASETS = [
    {
        "key": "ashrae",
        "name": "ASHRAE — Consommation bâtiment",
        "description": "Profil horaire synthétique dérivé d'une structure ASHRAE",
        "rows": HISTORY_DAYS * 24,
        "columns": 12,
        "frequency": "Horaire",
        "source": "Généré localement (simulation)",
        "status": "Simulation",
    },
    {
        "key": "solar",
        "name": "Photovoltaïque — Production solaire",
        "description": "Profil solaire synthétique (irradiance, puissance, énergie)",
        "rows": HISTORY_DAYS * 24,
        "columns": 6,
        "frequency": "Horaire",
        "source": "Généré localement (simulation)",
        "status": "Simulation",
    },
]

PROTOCOLS = ["MQTT", "Modbus TCP", "BACnet/IP"]


# ---------------------------------------------------------------------------
# Profils horaires de référence
# ---------------------------------------------------------------------------
# Consommation moyenne horaire (kW) en jour ouvré, avant aléas.
_WEEKDAY_PROFILE = np.array(
    [15, 14, 14, 14, 14, 15, 19, 29, 45, 55, 59, 61, 54, 59, 62, 61, 57, 49, 38, 29, 24, 21, 19, 17],
    dtype=float,
)
_WEEKEND_PROFILE = np.array(
    [12, 11, 11, 11, 11, 12, 13, 15, 19, 22, 24, 26, 27, 25, 24, 23, 22, 21, 19, 18, 17, 16, 15, 14],
    dtype=float,
)
# Occupation moyenne (personnes) en jour ouvré.
_WEEKDAY_OCCUPANCY = np.array(
    [0, 0, 0, 0, 0, 0, 4, 22, 85, 145, 150, 148, 90, 152, 165, 162, 150, 120, 60, 20, 8, 3, 0, 0],
    dtype=float,
)


def _day_cloud_factors(timestamps: pd.DatetimeIndex, rng: np.random.Generator) -> np.ndarray:
    """Facteur de nébulosité par jour (0,55 à 1,0), déterministe."""
    dates = pd.Series(timestamps.date).to_numpy()
    factors: dict[object, float] = {}
    for day in pd.unique(dates):
        if rng.random() < 0.2:
            factors[day] = float(rng.uniform(0.56, 0.78))
        else:
            factors[day] = float(rng.uniform(0.86, 1.0))
    return np.array([factors[d] for d in dates], dtype=float)


def _simulate_battery(
    consumption_kwh: np.ndarray,
    solar_kwh: np.ndarray,
    capacity_kwh: float,
    rng: np.random.Generator,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Simule une série de SOC illustrative (hors bilan réseau simplifié).

    Le bilan réseau reste volontairement limité à la formule demandée :
        grid_import = max(0, consommation - production PV)
        surplus     = max(0, production PV - consommation)

    La batterie est présentée comme un objet de démonstration : sa série de SOC
    ne sert pas au calcul des flux réseau et ne représente aucun pilotage réel.
    """
    soc = np.zeros_like(consumption_kwh)
    charge = np.zeros_like(consumption_kwh)
    discharge = np.zeros_like(consumption_kwh)
    level = 64.0  # SOC initial simulé (%)

    for i in range(len(consumption_kwh)):
        if solar_kwh[i] > 1.0:
            room_kwh = max(0.0, (94.0 - level) / 100.0 * capacity_kwh)
            charge_kwh = min(solar_kwh[i] * 0.42, room_kwh)
            level += charge_kwh / capacity_kwh * 100.0
            charge[i] = charge_kwh
        else:
            available_kwh = max(0.0, (level - 12.0) / 100.0 * capacity_kwh)
            discharge_kwh = min(consumption_kwh[i] * 0.33, available_kwh)
            level -= discharge_kwh / capacity_kwh * 100.0
            discharge[i] = discharge_kwh
        # Bruit très léger pour éviter une courbe parfaitement mécanique.
        level = float(np.clip(level + rng.normal(0, 0.08), 0.0, 100.0))
        soc[i] = level

    return soc, charge, discharge


def generate_energy_data() -> pd.DataFrame:
    """Génère 14 jours de mesures horaires simulées et cohérentes."""
    rng = np.random.default_rng(SEED)

    end = pd.Timestamp.now().floor("h")
    timestamps = pd.date_range(
        end=end, periods=HISTORY_DAYS * 24, freq="h"
    )
    index = pd.DatetimeIndex(timestamps)
    n = len(index)

    hour = index.hour.to_numpy()
    weekday = index.dayofweek.to_numpy()
    is_weekend = weekday >= 5
    day_of_year = index.dayofyear.to_numpy()

    # --- Consommation électrique -----------------------------------------
    base = np.where(
        is_weekend,
        _WEEKEND_PROFILE[hour],
        _WEEKDAY_PROFILE[hour],
    )
    # Légère majoration hivernale (chauffage) bornée.
    season = np.cos((day_of_year - 172) / 365.0 * 2 * np.pi)
    winter_gain = np.clip(-season, 0, 1) * 0.08
    consumption_kw = base * (1.0 + winter_gain) * rng.normal(1.0, 0.045, n)

    # Pics ponctuels de consommation en journée (démonstration).
    spike_mask = (rng.random(n) < 0.018) & (hour >= 8) & (hour <= 18)
    consumption_kw = consumption_kw + np.where(
        spike_mask, rng.uniform(6.0, 18.0, n), 0.0
    )
    consumption_kw = np.clip(consumption_kw, 8.0, None)

    # --- Production photovoltaïque ---------------------------------------
    clouds = _day_cloud_factors(index, rng)
    # Courbe solaire : lever ~7 h, coucher ~18 h, maximum vers 12 h 30.
    elevation = np.clip(np.sin(np.pi * (hour - 7.0) / 11.0), 0.0, None)
    pv_capacity = 150.0
    seasonal = 0.78 + 0.22 * np.cos((day_of_year - 172) / 365.0 * 2 * np.pi)
    solar_kw = (
        pv_capacity
        * 0.82
        * elevation
        * seasonal
        * clouds
        * rng.normal(1.0, 0.025, n)
    )
    solar_kw = np.where((hour < 7) | (hour >= 19), 0.0, np.clip(solar_kw, 0.0, None))
    solar_kw = np.round(solar_kw, 2)

    # --- Bilan énergétique simplifié (sans dispatch batterie) ------------
    grid_import = np.maximum(0.0, consumption_kw - solar_kw)
    grid_export = np.maximum(0.0, solar_kw - consumption_kw)

    # --- Batterie (illustration) -----------------------------------------
    soc, battery_charge, battery_discharge = _simulate_battery(
        consumption_kw, solar_kw, BATTERY_REFERENCE_KWH, rng
    )

    # --- Environnement intérieur / extérieur -----------------------------
    occupied = ~is_weekend & (hour >= 7) & (hour <= 19)
    temperature_indoor = (
        21.2
        + 0.55 * np.sin((hour - 6) / 24.0 * 2 * np.pi)
        + np.where(occupied, 0.45, 0.0)
        + rng.normal(0, 0.22, n)
    )
    base_outdoor = 13.0 + 9.0 * season
    temperature_outdoor = (
        base_outdoor
        + 4.6 * np.sin((hour - 9) / 24.0 * 2 * np.pi)
        + rng.normal(0, 0.5, n)
    )
    humidity = (
        52.0
        + 7.0 * np.sin((hour - 4) / 24.0 * 2 * np.pi)
        + rng.normal(0, 1.6, n)
    )
    humidity = np.clip(humidity, 32.0, 76.0)

    occupancy_base = np.where(is_weekend, 0.0, _WEEKDAY_OCCUPANCY[hour])
    weekend_occupancy = np.where(
        (hour >= 9) & (hour <= 16), 16.0, np.where((hour >= 8) & (hour <= 18), 6.0, 0.0)
    )
    occupancy_base = np.where(is_weekend, weekend_occupancy, occupancy_base)
    occupancy = np.clip(
        np.round(occupancy_base + rng.normal(0, 4.0, n)), 0, None
    ).astype(int)

    lighting_on = occupancy > 5
    hvac_active = occupancy > 10

    df = pd.DataFrame(
        {
            "timestamp": index,
            "consumption_kwh": np.round(consumption_kw, 3),
            "solar_production_kwh": solar_kw,
            "grid_import_kwh": np.round(grid_import, 3),
            "grid_export_kwh": np.round(grid_export, 3),
            "battery_soc": np.round(np.clip(soc, 0, 100), 2),
            "battery_charge_kwh": np.round(battery_charge, 3),
            "battery_discharge_kwh": np.round(battery_discharge, 3),
            "temperature_indoor": np.round(temperature_indoor, 2),
            "temperature_outdoor": np.round(temperature_outdoor, 2),
            "humidity": np.round(humidity, 1),
            "occupancy": occupancy,
            "lighting_on": lighting_on,
            "hvac_active": hvac_active,
        }
    )

    # Chaque ligne représente un pas horaire : l'énergie (kWh) est donc
    # numériquement égale à la puissance moyenne horaire (kW) pendant 1 h.
    # Les calculs de puissance sont explicites dans utils/calculations.py.
    return _validate_energy_data(df)


def _validate_energy_data(df: pd.DataFrame) -> pd.DataFrame:
    """Borne les valeurs pour garantir la cohérence physique du jeu simulé."""
    if df.empty:
        return df
    df = df.sort_values("timestamp").reset_index(drop=True)
    for column in ("consumption_kwh", "solar_production_kwh", "grid_import_kwh", "grid_export_kwh"):
        df[column] = pd.to_numeric(df[column], errors="coerce").fillna(0.0).clip(lower=0.0)
    df["battery_soc"] = pd.to_numeric(df["battery_soc"], errors="coerce").fillna(0.0).clip(0.0, 100.0)
    df["humidity"] = df["humidity"].clip(0.0, 100.0)
    df["occupancy"] = df["occupancy"].clip(lower=0).astype(int)
    return df


def generate_zone_data(energy_df: pd.DataFrame) -> pd.DataFrame:
    """Répartit la consommation horaire entre les zones du bâtiment."""
    if energy_df.empty:
        return pd.DataFrame(
            columns=["timestamp", "zone", "consumption_kwh", "power_kw"]
        )

    rng = np.random.default_rng(SEED + 7)
    rows: list[dict[str, object]] = []
    base_shares = np.array([zone["share"] for zone in ZONE_DEFINITIONS], dtype=float)

    for _, row in energy_df.iterrows():
        jittered = base_shares * (1.0 + rng.normal(0, 0.035, len(base_shares)))
        jittered = np.clip(jittered, 0.02, None)
        shares = jittered / jittered.sum()
        for zone, share in zip(ZONE_DEFINITIONS, shares):
            kwh = float(row["consumption_kwh"]) * float(share)
            rows.append(
                {
                    "timestamp": row["timestamp"],
                    "zone": zone["name"],
                    "consumption_kwh": round(kwh, 3),
                    "power_kw": round(kwh, 3),  # pas horaire de 1 h
                }
            )

    return pd.DataFrame(rows)


def generate_end_use_data(energy_df: pd.DataFrame) -> pd.DataFrame:
    """Ventile la consommation par usage final (simulation)."""
    if energy_df.empty:
        return pd.DataFrame(columns=["timestamp", "usage", "consumption_kwh"])

    rng = np.random.default_rng(SEED + 13)
    rows: list[dict[str, object]] = []

    for _, row in energy_df.iterrows():
        hour = int(pd.Timestamp(row["timestamp"]).hour)
        occ_factor = min(float(row["occupancy"]) / 165.0, 1.0)
        is_day = 1.0 if 8 <= hour <= 18 else 0.0
        is_evening = 1.0 if 18 <= hour <= 22 else 0.0

        weights = np.array(
            [
                0.30 + 0.10 * is_day + rng.normal(0, 0.012),
                0.10 + 0.10 * occ_factor + rng.normal(0, 0.008),
                0.16 + 0.12 * occ_factor + rng.normal(0, 0.008),
                0.10 + 0.025 * is_evening + rng.normal(0, 0.006),
                0.12 + 0.025 * is_day + rng.normal(0, 0.006),
            ]
        )
        weights = np.clip(weights, 0.01, None)
        shares = weights / weights.sum()
        total = float(row["consumption_kwh"])
        for usage, share in zip(END_USE_NAMES, shares):
            rows.append(
                {
                    "timestamp": row["timestamp"],
                    "usage": usage,
                    "consumption_kwh": round(total * float(share), 4),
                }
            )

    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Point d'accès unique pour l'interface
# ---------------------------------------------------------------------------
@st.cache_data(show_spinner=False)
def get_energy_data() -> pd.DataFrame:
    """Retourne les mesures énergétiques.

    Version actuelle : données simulées.
    Version future : lecture CSV / base de données / passerelle IoT.
    """
    return generate_energy_data()


@st.cache_data(show_spinner=False)
def get_zone_data() -> pd.DataFrame:
    """Retourne la consommation horaire par zone (simulée)."""
    return generate_zone_data(get_energy_data())


@st.cache_data(show_spinner=False)
def get_end_use_data() -> pd.DataFrame:
    """Retourne la consommation horaire par usage final (simulée)."""
    return generate_end_use_data(get_energy_data())
