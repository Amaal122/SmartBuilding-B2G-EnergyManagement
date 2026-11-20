"""Assemblage du scénario énergétique à partir des données réelles.

Deux jeux de données réels et indépendants sont combinés :

1. **Consommation** : ASHRAE « Great Energy Predictor III », compteur
   électrique (meter 0) de bâtiments de bureaux, pas horaire, mai–juin 2016.
2. **Production photovoltaïque** : centrale solaire n°1, agrégée à l'heure
   depuis des mesures d'onduleurs à 15 minutes, mai–juin 2020.

Les deux installations ne sont pas le même bâtiment. Le scénario consiste à
aligner leurs horodatages puis à **mettre à l'échelle** la production de la
centrale pour couvrir une fraction choisie de la consommation du bâtiment.
Ce bilan est donc **modélisé**, jamais mesuré sur un site unique.

Les variables intérieures (température, humidité, occupation, éclairage) ne
figurent dans aucun des deux jeux de données : elles sont simulées et
signalées comme telles. La météo extérieure du site ASHRAE est réelle.
"""

from __future__ import annotations

from datetime import timedelta
from typing import Any

import numpy as np
import pandas as pd

from data import data_loader
from data.data_cleaning import clean_timeseries, reindex_hourly, split_outliers_iqr
from data.data_validation import validate_pv_ratio
from services.battery_simulation import BatteryParams, simulate_dispatch

DEFAULT_BUILDING_ID = 520
DEFAULT_PV_RATIO = 0.75
MAX_PV_RATIO = 1.5
SEED = 20261120

# Répartition par zone : hypothèse de modélisation, faute de sous-comptage.
ZONE_DEFINITIONS: list[tuple[str, float]] = [
    ("RDC · Accueil et services", 0.17),
    ("Étage 1 · Bureaux", 0.31),
    ("Étage 2 · Bureaux et salles", 0.24),
    ("Étage 3 · Réunions", 0.16),
    ("Toiture · Technique", 0.12),
]
ZONE_NAMES = [name for name, _ in ZONE_DEFINITIONS]

# Ventilation par usage final : hypothèse documentée, non mesurée.
END_USE_DEFINITIONS: list[tuple[str, float]] = [
    ("CVC / HVAC", 0.42),
    ("Éclairage", 0.18),
    ("Équipements bureautiques", 0.22),
    ("Eau chaude sanitaire", 0.06),
    ("Auxiliaires et ascenseurs", 0.12),
]
END_USE_NAMES = [name for name, _ in END_USE_DEFINITIONS]

# Forme du profil d'occupation d'un immeuble de bureaux (0–1).
_OCCUPANCY_SHAPE = np.array(
    [
        0.00, 0.00, 0.00, 0.00, 0.00, 0.02, 0.08, 0.28, 0.62, 0.86, 0.96,
        0.98, 0.82, 0.98, 1.00, 0.99, 0.92, 0.74, 0.38, 0.14, 0.04, 0.00,
        0.00, 0.00,
    ],
    dtype=float,
)
_WEEKEND_SHAPE = np.array(
    [
        0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.05, 0.12, 0.16,
        0.18, 0.18, 0.16, 0.14, 0.12, 0.10, 0.06, 0.02, 0.00, 0.00, 0.00,
        0.00, 0.00,
    ],
    dtype=float,
)

SCENARIO_COLUMNS = [
    "timestamp",
    "consumption_kwh",
    "pv_plant_kwh",
    "solar_production_kwh",
    "grid_import_kwh",
    "grid_export_kwh",
    "battery_soc",
    "battery_charge_kwh",
    "battery_discharge_kwh",
    "temperature_outdoor",
    "temperature_indoor",
    "humidity",
    "occupancy",
    "lighting_on",
    "hvac_active",
    "irradiation",
    "ambient_temperature",
    "module_temperature",
    "cloud_coverage",
    "wind_speed",
    "dew_temperature",
    "precip_depth_1_hr",
    "sea_level_pressure",
    "wind_direction",
    "solar_corrected",
    "weather_corrected",
    "solar_missing",
    "consumption_missing",
    "is_weekend",
]


# ---------------------------------------------------------------------------
# Alignement temporel
# ---------------------------------------------------------------------------
def map_solar_timestamps(timestamps: pd.Series) -> pd.Series:
    """Projette les horodatages 2020 de la centrale sur l'année 2016.

    Reproduit l'alignement du notebook de la branche ``hanine`` :
    ``date.replace(year=2016) - 2 jours``. Le décalage de deux jours fait
    correspondre la fenêtre PV (15 mai–17 juin 2020) à la fenêtre ASHRAE
    (13 mai–15 juin 2016).
    """
    series = pd.to_datetime(timestamps, errors="coerce")
    mapped = series.map(
        lambda value: value.replace(year=2016) if pd.notna(value) else pd.NaT
    )
    mapped = pd.Series(pd.DatetimeIndex(mapped), index=series.index)
    return mapped - timedelta(days=2)


def solar_reference_index(solar: pd.DataFrame | None = None) -> pd.DatetimeIndex:
    """Index horaire aligné de la centrale PV (744 heures utiles)."""
    solar = data_loader.load_solar_hourly() if solar is None else solar
    if solar.empty:
        return pd.DatetimeIndex([])
    aligned = map_solar_timestamps(solar["DATE_TIME"])
    return pd.DatetimeIndex(aligned.dropna().sort_values().unique())


# ---------------------------------------------------------------------------
# Inventaire des bâtiments
# ---------------------------------------------------------------------------
def eligible_buildings(
    electricity: pd.DataFrame | None = None,
    metadata: pd.DataFrame | None = None,
    solar: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Bâtiments de bureaux disposant d'une série horaire complète sans zéro.

    Critères (identiques à la préparation de la branche ``hanine``) :
    usage ``Office``, compteur 0, 744 heures alignées sur la fenêtre PV,
    aucune mesure nulle ou négative.
    """
    electricity = data_loader.load_electricity() if electricity is None else electricity
    metadata = data_loader.load_building_metadata() if metadata is None else metadata
    reference = solar_reference_index(solar)
    empty = pd.DataFrame(
        columns=[
            "building_id",
            "site_id",
            "primary_use",
            "square_feet",
            "year_built",
            "rows",
            "zeros",
            "total_kwh",
            "mean_kw",
            "max_kw",
            "coverage_pct",
        ]
    )
    if electricity.empty or metadata.empty or reference.empty:
        return empty

    window = electricity[electricity["timestamp"].isin(reference)]
    if window.empty:
        return empty

    grouped = (
        window.groupby("building_id")
        .agg(
            rows=("meter_reading", "size"),
            zeros=("meter_reading", lambda values: int((values <= 0).sum())),
            total_kwh=("meter_reading", "sum"),
            mean_kw=("meter_reading", "mean"),
            max_kw=("meter_reading", "max"),
        )
        .reset_index()
    )
    grouped["coverage_pct"] = grouped["rows"] / len(reference) * 100.0

    merged = grouped.merge(
        metadata[["building_id", "site_id", "primary_use", "square_feet", "year_built"]],
        on="building_id",
        how="left",
    )
    eligible = merged[
        (merged["rows"] == len(reference))
        & (merged["zeros"] == 0)
        & (merged["primary_use"] == "Office")
    ].copy()
    eligible["building_id"] = eligible["building_id"].astype(int)
    eligible["site_id"] = eligible["site_id"].fillna(-1).astype(int)
    return eligible.sort_values("building_id").reset_index(drop=True)


def building_options(eligible: pd.DataFrame | None = None) -> list[dict[str, Any]]:
    """Options lisibles pour le sélecteur de bâtiment de la barre latérale."""
    eligible = eligible_buildings() if eligible is None else eligible
    options: list[dict[str, Any]] = []
    for row in eligible.itertuples(index=False):
        area = (
            f"{int(row.square_feet):,} pi²".replace(",", " ")
            if pd.notna(row.square_feet)
            else "surface inconnue"
        )
        options.append(
            {
                "id": int(row.building_id),
                "label": f"Bâtiment {int(row.building_id)} · site {int(row.site_id)} · {area}",
                "site_id": int(row.site_id),
                "square_feet": float(row.square_feet)
                if pd.notna(row.square_feet)
                else None,
                "year_built": float(row.year_built) if pd.notna(row.year_built) else None,
                "total_kwh": float(row.total_kwh),
                "mean_kw": float(row.mean_kw),
                "max_kw": float(row.max_kw),
            }
        )
    return options


def building_metadata(building_id: int) -> dict[str, Any]:
    """Métadonnées d'un bâtiment, avec valeurs de repli explicites."""
    metadata = data_loader.load_building_metadata()
    row = metadata[metadata["building_id"] == int(building_id)]
    if row.empty:
        return {
            "building_id": int(building_id),
            "site_id": None,
            "primary_use": "—",
            "square_feet": None,
            "year_built": None,
        }
    record = row.iloc[0]
    return {
        "building_id": int(building_id),
        "site_id": int(record["site_id"]),
        "primary_use": str(record["primary_use"]),
        "square_feet": float(record["square_feet"])
        if pd.notna(record["square_feet"])
        else None,
        "year_built": float(record["year_built"])
        if pd.notna(record["year_built"])
        else None,
    }


# ---------------------------------------------------------------------------
# Scénario énergétique
# ---------------------------------------------------------------------------
def _simulate_indoor(
    outdoor: pd.Series, occupancy: np.ndarray, rng: np.random.Generator
) -> tuple[np.ndarray, np.ndarray]:
    """Température et humidité intérieures simulées (aucun capteur disponible)."""
    values = pd.to_numeric(outdoor, errors="coerce").interpolate(
        limit_direction="both"
    )
    base = values.fillna(values.mean() if not values.empty else 20.0).to_numpy(dtype=float)
    occupancy_ratio = occupancy / max(1.0, float(occupancy.max()))
    indoor = (
        22.0
        + 0.07 * (base - 22.0)
        + 1.1 * occupancy_ratio
        + rng.normal(0.0, 0.22, len(base))
    )
    humidity = (
        47.0
        + 7.0 * np.sin((np.arange(len(base)) % 24) / 24.0 * 2 * np.pi - 1.2)
        + 0.04 * (base - 20.0) * 4
        + rng.normal(0.0, 1.4, len(base))
    )
    return np.clip(indoor, 17.0, 28.0), np.clip(humidity, 30.0, 72.0)


def _build_occupancy(
    timestamps: pd.Series, square_feet: float | None
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Occupation, éclairage et CVC simulés à partir du profil de bureaux."""
    index = pd.to_datetime(timestamps)
    hours = index.dt.hour.to_numpy()
    weekend = index.dt.dayofweek.to_numpy() >= 5
    area = float(square_feet) if square_feet else 30000.0
    # Densité d'occupation : ~1 personne pour 250 pi² en pointe.
    peak_people = max(6.0, area / 250.0)
    shape = np.where(weekend, _WEEKEND_SHAPE[hours], _OCCUPANCY_SHAPE[hours])
    rng = np.random.default_rng(SEED + 3)
    occupancy = np.clip(
        np.round(peak_people * shape + rng.normal(0.0, 1.6, len(index))), 0, None
    ).astype(int)
    lighting = (shape > 0.08) & ~weekend | (shape > 0.12)
    hvac = occupancy > max(2, int(peak_people * 0.08))
    return occupancy, lighting.astype(bool), hvac.astype(bool)


def build_scenario_frame(
    building_id: int = DEFAULT_BUILDING_ID,
    pv_ratio: float = DEFAULT_PV_RATIO,
    battery_capacity_kwh: float = 200.0,
) -> pd.DataFrame:
    """Construit le scénario horaire aligné pour un bâtiment donné."""
    if not validate_pv_ratio(float(pv_ratio))["valid"]:
        pv_ratio = DEFAULT_PV_RATIO
    ratio = float(np.clip(pv_ratio, 0.01, MAX_PV_RATIO))

    electricity = data_loader.load_electricity()
    if electricity.empty:
        return pd.DataFrame(columns=SCENARIO_COLUMNS)

    building = electricity[electricity["building_id"] == int(building_id)].copy()
    if building.empty:
        return pd.DataFrame(columns=SCENARIO_COLUMNS)

    consumption = clean_timeseries(
        building,
        "timestamp",
        ["meter_reading"],
        clip_non_negative=True,
    ).rename(columns={"meter_reading": "consumption_kwh"})
    consumption = consumption[["timestamp", "consumption_kwh"]]
    # Les jeux sources excluent volontairement trois journées sans mesure.
    # On conserve uniquement les heures réellement observées : aucune
    # consommation n'est inventée pour combler ces jours absents.
    consumption["consumption_missing"] = False

    solar = data_loader.load_solar_hourly()
    solar = solar.copy()
    if not solar.empty:
        solar["timestamp"] = map_solar_timestamps(solar["DATE_TIME"])
        solar = solar.dropna(subset=["timestamp"]).rename(
            columns={
                "ENERGIE_KWH": "pv_plant_kwh",
                "PUISSANCE_MOY_KW": "plant_power_kw",
                "NB_CORRIGES": "solar_corrected_count",
                "METEO_CORRIGEE": "weather_corrected_flag",
                "AMBIENT_TEMPERATURE": "plant_ambient_temperature",
                "MODULE_TEMPERATURE": "module_temperature",
                "IRRADIATION": "irradiation",
            }
        )
        keep = [
            "timestamp",
            "pv_plant_kwh",
            "plant_power_kw",
            "solar_corrected_count",
            "weather_corrected_flag",
            "plant_ambient_temperature",
            "module_temperature",
            "irradiation",
        ]
        solar = solar[keep].sort_values("timestamp").reset_index(drop=True)
    else:
        solar = pd.DataFrame(columns=["timestamp"])

    frame = consumption.merge(solar, on="timestamp", how="inner")
    frame["solar_missing"] = frame.get("pv_plant_kwh", pd.Series(index=frame.index)).isna()
    for column in (
        "pv_plant_kwh",
        "irradiation",
        "plant_ambient_temperature",
        "module_temperature",
        "solar_corrected_count",
        "weather_corrected_flag",
    ):
        if column not in frame:
            frame[column] = np.nan
    frame["pv_plant_kwh"] = (
        pd.to_numeric(frame["pv_plant_kwh"], errors="coerce")
        .interpolate(limit=3, limit_direction="both")
        .fillna(0.0)
    )
    frame["irradiation"] = (
        pd.to_numeric(frame["irradiation"], errors="coerce")
        .interpolate(limit=3, limit_direction="both")
        .fillna(0.0)
    )
    frame["solar_corrected"] = (
        pd.to_numeric(frame["solar_corrected_count"], errors="coerce").fillna(0) > 0
    )
    frame["weather_corrected"] = (
        pd.to_numeric(frame["weather_corrected_flag"], errors="coerce").fillna(0) > 0
    )

    total_consumption = float(frame["consumption_kwh"].sum())
    total_plant = float(frame["pv_plant_kwh"].sum())
    pv_scale = (
        ratio * total_consumption / total_plant if total_plant > 0 else 0.0
    )
    frame["solar_production_kwh"] = frame["pv_plant_kwh"] * pv_scale
    frame["solar_production_kwh"] = frame["solar_production_kwh"].clip(lower=0.0)

    conso = frame["consumption_kwh"].to_numpy(dtype=float)
    solar_values = frame["solar_production_kwh"].to_numpy(dtype=float)
    self_consumed = np.minimum(conso, solar_values)
    frame["grid_import_kwh"] = np.maximum(0.0, conso - self_consumed)
    frame["grid_export_kwh"] = np.maximum(0.0, solar_values - self_consumed)
    frame["self_consumed_kwh"] = self_consumed

    # --- Météo réelle du site ASHRAE --------------------------------
    meta = building_metadata(building_id)
    weather = data_loader.load_weather()
    if not weather.empty and meta.get("site_id") is not None:
        site_weather = weather[weather["site_id"] == int(meta["site_id"])]
        frame = frame.merge(
            site_weather.drop(columns=["site_id"]),
            on="timestamp",
            how="left",
        )
    weather_columns = [
        "air_temperature",
        "cloud_coverage",
        "dew_temperature",
        "precip_depth_1_hr",
        "sea_level_pressure",
        "wind_direction",
        "wind_speed",
    ]
    for column in weather_columns:
        if column not in frame:
            frame[column] = np.nan

    frame["temperature_outdoor"] = (
        pd.to_numeric(frame["air_temperature"], errors="coerce")
        .interpolate(limit=6, limit_direction="both")
    )
    fallback = pd.to_numeric(frame["plant_ambient_temperature"], errors="coerce")
    frame["temperature_outdoor"] = frame["temperature_outdoor"].fillna(fallback)
    frame["temperature_outdoor"] = frame["temperature_outdoor"].fillna(
        frame["temperature_outdoor"].mean()
    )

    occupancy, lighting, hvac = _build_occupancy(
        frame["timestamp"], meta.get("square_feet")
    )
    rng = np.random.default_rng(SEED)
    indoor, humidity = _simulate_indoor(frame["temperature_outdoor"], occupancy, rng)
    frame["occupancy"] = occupancy
    frame["lighting_on"] = lighting
    frame["hvac_active"] = hvac
    frame["temperature_indoor"] = np.round(indoor, 2)
    frame["humidity"] = np.round(humidity, 1)
    frame["is_weekend"] = pd.to_datetime(frame["timestamp"]).dt.dayofweek >= 5

    # --- Batterie de référence (simulation, hors bilan réseau) -------
    capacity = float(max(0.0, battery_capacity_kwh))
    params = BatteryParams(
        capacity_kwh=capacity,
        initial_soc_pct=50.0,
        max_charge_kw=max(1.0, capacity * 0.25),
        max_discharge_kw=max(1.0, capacity * 0.25),
        min_soc_pct=10.0,
        max_soc_pct=95.0,
    )
    dispatch = simulate_dispatch(
        frame["consumption_kwh"], frame["solar_production_kwh"], params,
        timestamps=frame["timestamp"],
    )
    frame["battery_soc"] = dispatch["battery_soc"].to_numpy()
    frame["battery_charge_kwh"] = dispatch["battery_charge_kwh"].to_numpy()
    frame["battery_discharge_kwh"] = dispatch["battery_discharge_kwh"].to_numpy()

    frame["net_energy_kwh"] = (
        frame["consumption_kwh"] - frame["solar_production_kwh"]
    )
    for column in (
        "cloud_coverage",
        "wind_speed",
        "dew_temperature",
        "precip_depth_1_hr",
        "sea_level_pressure",
        "wind_direction",
        "temperature_outdoor",
    ):
        frame[column] = pd.to_numeric(frame[column], errors="coerce")

    frame = frame.sort_values("timestamp").reset_index(drop=True)
    frame.attrs["pv_scale"] = pv_scale
    frame.attrs["pv_ratio"] = ratio
    frame.attrs["building_id"] = int(building_id)
    frame.attrs["pv_peak_kw"] = float(frame["solar_production_kwh"].max())
    return frame


def build_zone_frame(frame: pd.DataFrame) -> pd.DataFrame:
    """Ventile la consommation par zone (répartition **estimée**).

    La somme des zones est exactement égale à la consommation du bâtiment :
    le dernier poste absorbe l'arrondi.
    """
    if frame is None or frame.empty:
        return pd.DataFrame(
            columns=["timestamp", "zone", "consumption_kwh", "power_kw"]
        )
    rng = np.random.default_rng(SEED + 7)
    shares = np.array([share for _, share in ZONE_DEFINITIONS], dtype=float)
    rows: list[dict[str, Any]] = []
    for timestamp, total in zip(frame["timestamp"], frame["consumption_kwh"]):
        jitter = np.clip(shares * (1.0 + rng.normal(0.0, 0.02, len(shares))), 0.01, None)
        normalized = jitter / jitter.sum()
        values = normalized * float(total)
        values[-1] = float(total) - float(values[:-1].sum())
        for (name, _), value in zip(ZONE_DEFINITIONS, values):
            rows.append(
                {
                    "timestamp": timestamp,
                    "zone": name,
                    "consumption_kwh": max(0.0, float(value)),
                    "power_kw": max(0.0, float(value)),
                }
            )
    return pd.DataFrame(rows)


def build_end_use_frame(frame: pd.DataFrame) -> pd.DataFrame:
    """Ventile la consommation par usage final (répartition **estimée**)."""
    if frame is None or frame.empty:
        return pd.DataFrame(columns=["timestamp", "usage", "consumption_kwh"])
    rng = np.random.default_rng(SEED + 13)
    base = np.array([share for _, share in END_USE_DEFINITIONS], dtype=float)
    hours = pd.to_datetime(frame["timestamp"]).dt.hour.to_numpy()
    occupancy = frame["occupancy"].to_numpy(dtype=float) if "occupancy" in frame else np.zeros(len(frame))
    occupancy_ratio = occupancy / max(1.0, float(occupancy.max()) if len(occupancy) else 1.0)
    rows: list[dict[str, Any]] = []
    for i, (timestamp, total) in enumerate(
        zip(frame["timestamp"], frame["consumption_kwh"])
    ):
        hour = int(hours[i])
        occupied = 1.0 if 7 <= hour <= 19 else 0.0
        weights = base * np.array(
            [
                1.0 + 0.08 * occupied,
                1.0 + 0.10 * occupancy_ratio[i],
                1.0 + 0.12 * occupancy_ratio[i],
                1.0,
                1.0 + 0.04 * occupied,
            ]
        )
        weights = np.clip(weights * (1.0 + rng.normal(0.0, 0.015, len(base))), 0.01, None)
        normalized = weights / weights.sum()
        values = normalized * float(total)
        values[-1] = float(total) - float(values[:-1].sum())
        for (name, _), value in zip(END_USE_DEFINITIONS, values):
            rows.append(
                {
                    "timestamp": timestamp,
                    "usage": name,
                    "consumption_kwh": max(0.0, float(value)),
                }
            )
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Séries de comparaison (plusieurs bâtiments réels)
# ---------------------------------------------------------------------------
def building_series(building_id: int) -> pd.DataFrame:
    """Série horaire réelle d'un bâtiment, sans mise à l'échelle PV."""
    electricity = data_loader.load_electricity()
    if electricity.empty:
        return pd.DataFrame(columns=["timestamp", "consumption_kwh"])
    building = electricity[electricity["building_id"] == int(building_id)]
    if building.empty:
        return pd.DataFrame(columns=["timestamp", "consumption_kwh"])
    cleaned = clean_timeseries(
        building, "timestamp", ["meter_reading"], clip_non_negative=True
    ).rename(columns={"meter_reading": "consumption_kwh"})
    return cleaned[["timestamp", "consumption_kwh"]].sort_values("timestamp")


def comparison_frame(
    building_ids: list[int], reference: pd.DataFrame | None = None
) -> pd.DataFrame:
    """Consommations réelles de plusieurs bâtiments sur la fenêtre analysée."""
    reference = (
        data_loader.load_electricity() if reference is None else reference
    )
    if reference is None or reference.empty:
        return pd.DataFrame(columns=["timestamp", "building_id", "consumption_kwh"])
    electricity = data_loader.load_electricity()
    window = electricity[electricity["building_id"].isin(building_ids)]
    if window.empty:
        return pd.DataFrame(columns=["timestamp", "building_id", "consumption_kwh"])
    return (
        window.rename(columns={"meter_reading": "consumption_kwh"})[
            ["timestamp", "building_id", "consumption_kwh"]
        ]
        .sort_values(["building_id", "timestamp"])
        .reset_index(drop=True)
    )


# ---------------------------------------------------------------------------
# Qualité et provenance
# ---------------------------------------------------------------------------
def scenario_quality(frame: pd.DataFrame) -> dict[str, Any]:
    """Synthèse qualité du scénario assemblé."""
    if frame is None or frame.empty:
        return {
            "rows": 0,
            "missing_solar": 0,
            "missing_consumption": 0,
            "solar_corrected": 0,
            "weather_corrected": 0,
            "outlier_hours": 0,
            "coverage_start": None,
            "coverage_end": None,
            "completeness_pct": None,
        }
    _, outliers = split_outliers_iqr(frame["consumption_kwh"])
    start = pd.Timestamp(frame["timestamp"].min())
    end = pd.Timestamp(frame["timestamp"].max())
    expected = int((end - start).total_seconds() // 3600) + 1
    return {
        "rows": int(len(frame)),
        "missing_solar": int(frame["solar_missing"].sum())
        if "solar_missing" in frame
        else 0,
        "missing_consumption": int(frame["consumption_missing"].sum())
        if "consumption_missing" in frame
        else 0,
        "solar_corrected": int(frame["solar_corrected"].sum())
        if "solar_corrected" in frame
        else 0,
        "weather_corrected": int(frame["weather_corrected"].sum())
        if "weather_corrected" in frame
        else 0,
        "outlier_hours": int(outliers.sum()),
        "coverage_start": start,
        "coverage_end": end,
        "completeness_pct": 100.0 * len(frame) / expected if expected else None,
    }
