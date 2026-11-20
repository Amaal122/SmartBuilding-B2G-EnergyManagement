"""Point d'accès unique au scénario et aux métadonnées de l'application.

Les vues ne lisent jamais directement les fichiers CSV : elles reçoivent un
:class:`ScenarioContext` construit ici. Ce contexte est mis en cache par
Streamlit, ce qui évite de relire les fichiers à chaque interaction.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pandas as pd
import streamlit as st

from data import data_loader, data_processing
from data.data_cleaning import quality_summary
from data.data_processing import DEFAULT_BUILDING_ID, DEFAULT_PV_RATIO
from services.battery_simulation import BatteryParams, simulate_scenario, summarize_dispatch
from services.energy_calculations import energy_kpis, grid_flows


@dataclass
class ScenarioContext:
    """Toutes les données nécessaires aux six pages."""

    building_id: int
    pv_ratio: float
    frame: pd.DataFrame
    zones: pd.DataFrame
    end_use: pd.DataFrame
    building: dict[str, Any]
    buildings: list[dict[str, Any]]
    solar_plant: pd.DataFrame
    quality: dict[str, Any]
    warnings: list[str] = field(default_factory=list)
    pv_scale: float = 0.0
    pv_peak_kw: float = 0.0
    baseline_kpis: dict[str, Any] = field(default_factory=dict)
    validated: bool = False
    validation_issues: list[str] = field(default_factory=list)

    @property
    def provenance(self) -> str:
        return "Données réelles · scénario modélisé"

    @property
    def site_id(self) -> int | None:
        value = self.building.get("site_id")
        return int(value) if value is not None else None


@st.cache_data(show_spinner=False)
def get_building_options() -> list[dict[str, Any]]:
    """Bâtiments réels éligibles, mis en cache pour la barre latérale."""
    return data_processing.building_options()


@st.cache_data(show_spinner=False, max_entries=12)
def get_context(
    building_id: int = DEFAULT_BUILDING_ID,
    pv_ratio: float = DEFAULT_PV_RATIO,
    battery_capacity_kwh: float = 200.0,
) -> ScenarioContext:
    """Construit et met en cache le contexte complet d'un scénario."""
    from data.data_validation import validate_scenario

    options = data_processing.building_options()
    if not options:
        return ScenarioContext(
            building_id=int(building_id),
            pv_ratio=float(pv_ratio),
            frame=pd.DataFrame(),
            zones=pd.DataFrame(),
            end_use=pd.DataFrame(),
            building={"building_id": int(building_id), "site_id": None},
            buildings=[],
            solar_plant=pd.DataFrame(),
            quality={},
            warnings=["Aucune donnée réelle disponible : vérifiez le dossier data/."],
        )

    ids = {option["id"] for option in options}
    selected_id = int(building_id) if int(building_id) in ids else DEFAULT_BUILDING_ID
    if selected_id not in ids and options:
        selected_id = int(options[0]["id"])

    frame = data_processing.build_scenario_frame(
        building_id=selected_id,
        pv_ratio=pv_ratio,
        battery_capacity_kwh=battery_capacity_kwh,
    )
    zones = data_processing.build_zone_frame(frame)
    end_use = data_processing.build_end_use_frame(frame)
    validation = validate_scenario(frame)
    solar = data_loader.load_solar_hourly()

    warnings: list[str] = []
    if frame.empty:
        warnings.append("Scénario vide : aucun bâtiment exploitable.")
    else:
        if frame.get("solar_missing", pd.Series(dtype=bool)).sum():
            warnings.append(
                f"{int(frame['solar_missing'].sum())} heure(s) sans mesure PV : "
                "production interpolée et signalée."
            )
        if frame.get("consumption_missing", pd.Series(dtype=bool)).sum():
            warnings.append(
                f"{int(frame['consumption_missing'].sum())} heure(s) de consommation "
                "interpolée(s)."
            )
    warnings.extend(validation["warnings"])

    baseline_kpis = (
        energy_kpis(frame.head(168)) if not frame.empty else energy_kpis(pd.DataFrame())
    )
    return ScenarioContext(
        building_id=selected_id,
        pv_ratio=float(pv_ratio),
        frame=frame,
        zones=zones,
        end_use=end_use,
        building=data_processing.building_metadata(selected_id),
        buildings=options,
        solar_plant=solar,
        quality=data_processing.scenario_quality(frame),
        warnings=warnings,
        pv_scale=float(frame.attrs.get("pv_scale", 0.0)),
        pv_peak_kw=float(frame.attrs.get("pv_peak_kw", 0.0)),
        baseline_kpis=baseline_kpis,
        validated=validation["valid"],
        validation_issues=validation["errors"],
    )


@st.cache_data(show_spinner=False)
def get_dataset_overview() -> list[dict[str, Any]]:
    """Inventaire enrichi des fichiers réellement disponibles."""
    inventory = data_loader.data_file_inventory()
    specs = {
        "electricity": data_loader.load_electricity,
        "solar": data_loader.load_solar_hourly,
        "scenario": data_loader.load_processed_scenario,
        "weather": data_loader.load_weather,
        "metadata": data_loader.load_building_metadata,
        "solar_raw": data_loader.load_solar_raw_generation,
        "solar_weather": lambda: data_loader._read_csv(
            data_loader.SOLAR_WEATHER_FILE
        ),
    }
    descriptions = {
        "electricity": "Consommation électrique horaire ASHRAE (bureaux, meter 0).",
        "solar": "Production horaire de la centrale PV n°1 (source 15 min).",
        "scenario": "Scénario aligné préparé dans la branche hanine (référence).",
        "weather": "Météo horaire réelle par site ASHRAE.",
        "metadata": "Usage, surface et site des bâtiments ASHRAE.",
        "solar_raw": "Mesures brutes des onduleurs (15 minutes).",
        "solar_weather": "Météo de la centrale solaire (15 minutes).",
    }
    frequency = {
        "electricity": "Horaire",
        "solar": "Horaire (source 15 min)",
        "scenario": "Horaire",
        "weather": "Horaire",
        "metadata": "Statique",
        "solar_raw": "15 minutes",
        "solar_weather": "15 minutes",
    }
    result: list[dict[str, Any]] = []
    for item in inventory:
        key = item["key"]
        row = dict(item)
        row["description"] = descriptions.get(key, "")
        row["frequency"] = frequency.get(key, "—")
        row["columns"] = []
        row["preview"] = pd.DataFrame()
        row["quality"] = {}
        if item["exists"] and key in specs:
            try:
                df = specs[key]()
                row["columns"] = list(df.columns)
                row["preview"] = df.head(8).copy()
                row["quality"] = quality_summary(df)
                row["rows"] = len(df)
                row["columns_count"] = len(df.columns)
            except Exception as exc:  # pragma: no cover - dépend des fichiers
                row["error"] = str(exc)
        result.append(row)
    return result


@st.cache_data(show_spinner=False)
def get_comparison_series(building_ids: tuple[int, ...]) -> pd.DataFrame:
    """Séries réelles de plusieurs bâtiments (page Surveillance)."""
    if not building_ids:
        return pd.DataFrame(columns=["timestamp", "building_id", "consumption_kwh"])
    electricity = data_loader.load_electricity()
    return data_processing.comparison_frame(list(building_ids), electricity)


@st.cache_data(show_spinner=False)
def get_reference_battery_result(
    frame: pd.DataFrame, params: BatteryParams
) -> pd.DataFrame:
    """Dispatch batterie calculé pour la configuration courante."""
    return simulate_scenario(frame, params)


def battery_summary(result: pd.DataFrame, params: BatteryParams) -> dict[str, Any]:
    return summarize_dispatch(result, params)


def no_battery_result(frame: pd.DataFrame) -> pd.DataFrame:
    """Scénario A : aucun stockage ; flux réseau simplifiés."""
    if frame is None or frame.empty:
        return pd.DataFrame()
    conso = frame["consumption_kwh"].to_numpy(dtype=float)
    solar = frame["solar_production_kwh"].to_numpy(dtype=float)
    flows = grid_flows(conso, solar)
    return pd.DataFrame(
        {
            "timestamp": frame["timestamp"].to_numpy(),
            "consumption_kwh": conso,
            "solar_production_kwh": solar,
            "grid_import_kwh": flows["grid_import"],
            "grid_export_kwh": flows["grid_export"],
            "pv_direct_kwh": flows["self_consumed"],
            "battery_charge_kwh": 0.0,
            "battery_discharge_kwh": 0.0,
            "battery_soc": 0.0,
        }
    )
