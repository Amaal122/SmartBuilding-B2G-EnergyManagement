"""Chargement des jeux de données réels du projet.

Sources disponibles (branche ``hanine``) :
- ``data/processed/electricity_office.csv`` : consommation horaire réelle de
  bâtiments de bureaux ASHRAE (compteur électrique, 2016) ;
- ``data/processed/solar_final.csv`` : production horaire réelle de la centrale
  photovoltaïque n°1, agrégée depuis des mesures de 15 minutes (2020) ;
- ``data/raw/weather_train.csv`` : météo horaire réelle ASHRAE par site ;
- ``data/raw/building_metadata (1).csv`` : métadonnées des bâtiments ;
- ``data/raw/Plant_1_Generation_Data.csv`` : mesures brutes des 22 onduleurs ;
- ``data/processed/smart_building.csv`` : scénario aligné préparé par Hanine.

Les fonctions sont mises en cache Streamlit et renvoient un DataFrame vide en
cas de fichier absent, afin que l'application puisse afficher un état explicite
plutôt que de planter.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st

DATA_DIR = Path(__file__).resolve().parent
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"

ELECTRICITY_FILE = PROCESSED_DIR / "electricity_office.csv"
SOLAR_FILE = PROCESSED_DIR / "solar_final.csv"
SCENARIO_FILE = PROCESSED_DIR / "smart_building.csv"
WEATHER_FILE = RAW_DIR / "weather_train.csv"
METADATA_FILE = RAW_DIR / "building_metadata (1).csv"
SOLAR_GENERATION_FILE = RAW_DIR / "Plant_1_Generation_Data.csv"
SOLAR_WEATHER_FILE = RAW_DIR / "Plant_1_Weather_Sensor_Data.csv"


def _empty(columns: list[str]) -> pd.DataFrame:
    return pd.DataFrame(columns=columns)


def _read_csv(path: Path, **kwargs: Any) -> pd.DataFrame:
    """Lecture robuste avec repli d'encodage."""
    if not path.exists():
        return pd.DataFrame()
    last_error: Exception | None = None
    for encoding in ("utf-8", "utf-8-sig", "latin-1"):
        try:
            return pd.read_csv(path, encoding=encoding, **kwargs)
        except UnicodeDecodeError as exc:  # pragma: no cover - dépend du fichier
            last_error = exc
            continue
    if last_error is not None:
        raise last_error
    return pd.DataFrame()


@st.cache_data(show_spinner=False)
def load_electricity() -> pd.DataFrame:
    """Mesures horaires réelles ASHRAE (compteur 0 = électricité)."""
    df = _read_csv(
        ELECTRICITY_FILE,
        usecols=["building_id", "meter", "timestamp", "meter_reading"],
        parse_dates=["timestamp"],
    )
    if df.empty:
        return _empty(["building_id", "meter", "timestamp", "meter_reading"])
    df["building_id"] = pd.to_numeric(df["building_id"], errors="coerce")
    df["meter"] = pd.to_numeric(df["meter"], errors="coerce")
    df["meter_reading"] = pd.to_numeric(df["meter_reading"], errors="coerce")
    df = df.dropna(subset=["building_id", "timestamp", "meter_reading"])
    df["building_id"] = df["building_id"].astype(int)
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    df = df.dropna(subset=["timestamp"])
    df = df[df["meter_reading"] >= 0]
    return df.drop_duplicates(subset=["building_id", "timestamp"]).sort_values(
        ["building_id", "timestamp"]
    )


@st.cache_data(show_spinner=False)
def load_solar_hourly() -> pd.DataFrame:
    """Production PV horaire réelle (centrale 1) et météo associée."""
    columns = [
        "DATE_TIME",
        "ENERGIE_KWH",
        "PUISSANCE_MOY_KW",
        "NB_PAS",
        "NB_CORRIGES",
        "AMBIENT_TEMPERATURE",
        "MODULE_TEMPERATURE",
        "IRRADIATION",
        "NB_PAS_METEO",
        "METEO_CORRIGEE",
    ]
    df = _read_csv(SOLAR_FILE, parse_dates=["DATE_TIME"])
    if df.empty:
        return _empty(columns)
    for column in columns:
        if column not in df:
            df[column] = pd.NA
    df = df[columns].copy()
    df["DATE_TIME"] = pd.to_datetime(df["DATE_TIME"], errors="coerce")
    numeric = [c for c in columns if c != "DATE_TIME"]
    for column in numeric:
        df[column] = pd.to_numeric(df[column], errors="coerce")
    df = df.dropna(subset=["DATE_TIME"])
    df = df.drop_duplicates(subset=["DATE_TIME"]).sort_values("DATE_TIME")
    for column in ("ENERGIE_KWH", "PUISSANCE_MOY_KW", "IRRADIATION"):
        df[column] = df[column].clip(lower=0)
    return df.reset_index(drop=True)


@st.cache_data(show_spinner=False)
def load_weather() -> pd.DataFrame:
    """Météo horaire réelle ASHRAE par site."""
    columns = [
        "site_id",
        "timestamp",
        "air_temperature",
        "cloud_coverage",
        "dew_temperature",
        "precip_depth_1_hr",
        "sea_level_pressure",
        "wind_direction",
        "wind_speed",
    ]
    df = _read_csv(WEATHER_FILE, parse_dates=["timestamp"])
    if df.empty:
        return _empty(columns)
    for column in columns:
        if column not in df:
            df[column] = pd.NA
    df = df[columns].copy()
    df["site_id"] = pd.to_numeric(df["site_id"], errors="coerce")
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    for column in columns[2:]:
        df[column] = pd.to_numeric(df[column], errors="coerce")
    df = df.dropna(subset=["site_id", "timestamp"])
    df["site_id"] = df["site_id"].astype(int)
    df["precip_depth_1_hr"] = df["precip_depth_1_hr"].clip(lower=0)
    df["wind_speed"] = df["wind_speed"].clip(lower=0)
    return df.drop_duplicates(subset=["site_id", "timestamp"]).sort_values(
        ["site_id", "timestamp"]
    )


@st.cache_data(show_spinner=False)
def load_building_metadata() -> pd.DataFrame:
    """Métadonnées ASHRAE des bâtiments (usage, surface, site)."""
    columns = [
        "site_id",
        "building_id",
        "primary_use",
        "square_feet",
        "year_built",
        "floor_count",
    ]
    path = METADATA_FILE if METADATA_FILE.exists() else RAW_DIR / "building_metadata.csv"
    df = _read_csv(path)
    if df.empty:
        return _empty(columns)
    for column in columns:
        if column not in df:
            df[column] = pd.NA
    df = df[columns].copy()
    df["building_id"] = pd.to_numeric(df["building_id"], errors="coerce")
    df["site_id"] = pd.to_numeric(df["site_id"], errors="coerce")
    df = df.dropna(subset=["building_id", "site_id"])
    df["building_id"] = df["building_id"].astype(int)
    df["site_id"] = df["site_id"].astype(int)
    df["square_feet"] = pd.to_numeric(df["square_feet"], errors="coerce")
    return df.drop_duplicates(subset=["building_id"])


@st.cache_data(show_spinner=False)
def load_solar_raw_generation() -> pd.DataFrame:
    """Mesures brutes 15 min des onduleurs de la centrale 1."""
    df = _read_csv(
        SOLAR_GENERATION_FILE,
        usecols=["DATE_TIME", "SOURCE_KEY", "DC_POWER", "AC_POWER"],
    )
    if df.empty:
        return _empty(["DATE_TIME", "SOURCE_KEY", "DC_POWER", "AC_POWER"])
    df["DATE_TIME"] = pd.to_datetime(
        df["DATE_TIME"], format="%d-%m-%Y %H:%M", errors="coerce"
    )
    for column in ("DC_POWER", "AC_POWER"):
        df[column] = pd.to_numeric(df[column], errors="coerce").clip(lower=0)
    return df.dropna(subset=["DATE_TIME"]).drop_duplicates(
        subset=["DATE_TIME", "SOURCE_KEY"]
    )


@st.cache_data(show_spinner=False)
def load_processed_scenario() -> pd.DataFrame:
    """Scénario aligné préparé dans la branche ``hanine`` (référence)."""
    df = _read_csv(SCENARIO_FILE, parse_dates=["DATE_TIME"])
    if df.empty:
        return pd.DataFrame()
    return df.sort_values("DATE_TIME").reset_index(drop=True)


def data_file_inventory() -> list[dict[str, Any]]:
    """Inventaire physique des fichiers de données (sans lecture complète)."""
    specs = [
        ("electricity", "Consommation ASHRAE", ELECTRICITY_FILE, "CSV"),
        ("solar", "Production PV centrale 1", SOLAR_FILE, "CSV"),
        ("scenario", "Scénario aligné", SCENARIO_FILE, "CSV"),
        ("weather", "Météo ASHRAE", WEATHER_FILE, "CSV"),
        ("metadata", "Métadonnées bâtiments", METADATA_FILE, "CSV"),
        ("solar_raw", "Génération PV brute", SOLAR_GENERATION_FILE, "CSV"),
        ("solar_weather", "Météo centrale PV", SOLAR_WEATHER_FILE, "CSV"),
    ]
    inventory: list[dict[str, Any]] = []
    for key, label, path, kind in specs:
        inventory.append(
            {
                "key": key,
                "label": label,
                "path": str(path.relative_to(DATA_DIR.parent)),
                "kind": kind,
                "exists": path.exists(),
                "size_mb": round(path.stat().st_size / 1024 / 1024, 2)
                if path.exists()
                else 0.0,
            }
        )
    return inventory
