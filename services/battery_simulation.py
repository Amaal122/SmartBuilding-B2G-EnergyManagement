"""Simulation de dispatch d'une batterie résidentielle/tertiaire.

Modèle volontairement simplifié, à pas horaire :

- le PV alimente d'abord la charge du bâtiment ;
- le surplus PV charge la batterie (puissance et capacité limitées) ;
- le reste du surplus est exporté vers le réseau ;
- si le PV ne couvre pas la charge, la batterie se décharge (puissance
  limitée) ;
- le complément est importé du réseau.

Rendements : l'énergie prélevée au PV pour charger est multipliée par le
rendement de charge avant stockage ; l'énergie disponible en décharge est
multipliée par le rendement de décharge avant d'alimenter la charge.

La batterie n'existe pas dans les jeux de données sources : tous les
résultats de ce module sont **simulés**.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any

import numpy as np
import pandas as pd

from data.data_validation import validate_battery_parameters


@dataclass(frozen=True)
class BatteryParams:
    """Paramètres d'exploitation de la batterie simulée."""

    capacity_kwh: float = 200.0
    initial_soc_pct: float = 50.0
    max_charge_kw: float = 50.0
    max_discharge_kw: float = 50.0
    charge_efficiency: float = 0.95
    discharge_efficiency: float = 0.95
    min_soc_pct: float = 10.0
    max_soc_pct: float = 95.0

    def validate(self) -> dict[str, Any]:
        return validate_battery_parameters(
            capacity_kwh=self.capacity_kwh,
            initial_soc_pct=self.initial_soc_pct,
            max_charge_kw=self.max_charge_kw,
            max_discharge_kw=self.max_discharge_kw,
            charge_efficiency=self.charge_efficiency,
            discharge_efficiency=self.discharge_efficiency,
            min_soc_pct=self.min_soc_pct,
            max_soc_pct=self.max_soc_pct,
        )

    def clamped(self) -> "BatteryParams":
        """Retourne une version bornée, utilisable même en cas de saisie invalide."""
        capacity = float(max(0.0, self.capacity_kwh))
        min_soc = float(np.clip(self.min_soc_pct, 0.0, 99.0))
        max_soc = float(np.clip(self.max_soc_pct, min_soc + 1.0, 100.0))
        initial = float(np.clip(self.initial_soc_pct, min_soc, max_soc))
        return replace(
            self,
            capacity_kwh=capacity,
            initial_soc_pct=initial,
            max_charge_kw=float(max(0.0, self.max_charge_kw)),
            max_discharge_kw=float(max(0.0, self.max_discharge_kw)),
            charge_efficiency=float(np.clip(self.charge_efficiency, 0.01, 1.0)),
            discharge_efficiency=float(np.clip(self.discharge_efficiency, 0.01, 1.0)),
            min_soc_pct=min_soc,
            max_soc_pct=max_soc,
        )


def _as_float_array(values: Any, length: int) -> np.ndarray:
    array = np.asarray(values, dtype=float).reshape(-1)
    if array.size != length:
        raise ValueError("Les séries de consommation et de PV doivent avoir la même taille.")
    return np.nan_to_num(array, nan=0.0, posinf=0.0, neginf=0.0)


def simulate_dispatch(
    consumption_kwh: Any,
    solar_production_kwh: Any,
    params: BatteryParams,
    timestamps: Any | None = None,
    dt_hours: float = 1.0,
) -> pd.DataFrame:
    """Simule le dispatch heure par heure et retourne les flux détaillés.

    Colonnes retournées :
    ``pv_direct_kwh``, ``battery_charge_kwh`` (énergie prélevée au PV),
    ``battery_discharge_kwh`` (énergie livrée à la charge),
    ``grid_import_kwh``, ``grid_export_kwh``, ``battery_soc`` (%),
    ``battery_energy_kwh``, ``battery_loss_kwh``.
    """
    p = params.clamped()
    consumption = np.clip(_as_float_array(consumption_kwh, np.asarray(consumption_kwh).size), 0.0, None)
    length = consumption.size
    solar = np.clip(_as_float_array(solar_production_kwh, length), 0.0, None)
    if dt_hours <= 0:
        raise ValueError("Le pas temporel doit être strictement positif.")

    capacity = p.capacity_kwh
    if timestamps is None:
        timestamps = pd.RangeIndex(length)
    index = pd.Index(timestamps)

    if capacity <= 0:
        direct = np.minimum(consumption, solar)
        result = pd.DataFrame(
            {
                "timestamp": index,
                "consumption_kwh": consumption,
                "solar_production_kwh": solar,
                "pv_direct_kwh": direct,
                "battery_charge_kwh": 0.0,
                "battery_discharge_kwh": 0.0,
                "grid_import_kwh": np.maximum(0.0, consumption - direct),
                "grid_export_kwh": np.maximum(0.0, solar - direct),
                "battery_soc": np.nan,
                "battery_energy_kwh": 0.0,
                "battery_loss_kwh": 0.0,
            }
        )
        return result

    min_energy = capacity * p.min_soc_pct / 100.0
    max_energy = capacity * p.max_soc_pct / 100.0
    level = capacity * p.initial_soc_pct / 100.0

    rows: list[dict[str, float]] = []
    for i in range(length):
        load = float(consumption[i])
        pv = float(solar[i])

        direct = min(load, pv)
        deficit = max(0.0, load - direct)
        surplus = max(0.0, pv - direct)

        # --- Charge depuis le surplus PV --------------------------------
        room_kwh = max(0.0, max_energy - level)
        charge_possible = min(
            surplus,
            p.max_charge_kw * dt_hours,
            room_kwh / p.charge_efficiency,
        )
        charge = max(0.0, charge_possible)
        stored = charge * p.charge_efficiency
        level += stored
        loss_charge = charge - stored
        export = surplus - charge

        # --- Décharge vers la charge du bâtiment -----------------------
        available = max(0.0, level - min_energy)
        withdraw = min(
            available,
            p.max_discharge_kw * dt_hours,
            deficit / p.discharge_efficiency,
        )
        withdraw = max(0.0, withdraw)
        delivered = withdraw * p.discharge_efficiency
        level -= withdraw
        loss_discharge = withdraw - delivered
        grid_import = max(0.0, deficit - delivered)

        level = float(np.clip(level, min_energy, max_energy))
        rows.append(
            {
                "pv_direct_kwh": direct,
                "battery_charge_kwh": charge,
                "battery_discharge_kwh": delivered,
                "grid_import_kwh": grid_import,
                "grid_export_kwh": export,
                "battery_soc": level / capacity * 100.0,
                "battery_energy_kwh": level,
                "battery_loss_kwh": loss_charge + loss_discharge,
            }
        )

    flows = pd.DataFrame(rows)
    result = pd.DataFrame(
        {
            "timestamp": index,
            "consumption_kwh": consumption,
            "solar_production_kwh": solar,
        }
    ).join(flows)
    return result


def simulate_scenario(
    frame: pd.DataFrame,
    params: BatteryParams,
    *,
    consumption_col: str = "consumption_kwh",
    solar_col: str = "solar_production_kwh",
) -> pd.DataFrame:
    """Applique :func:`simulate_dispatch` à un DataFrame de scénario."""
    if frame is None or frame.empty:
        return pd.DataFrame()
    return simulate_dispatch(
        frame[consumption_col].to_numpy(dtype=float),
        frame[solar_col].to_numpy(dtype=float),
        params,
        timestamps=pd.to_datetime(frame["timestamp"]),
    )


def summarize_dispatch(result: pd.DataFrame, params: BatteryParams) -> dict[str, Any]:
    """Agrège les flux d'une simulation en indicateurs de synthèse."""
    p = params.clamped()
    if result is None or result.empty:
        return {
            "consumption": 0.0,
            "solar": 0.0,
            "pv_direct": 0.0,
            "charge": 0.0,
            "discharge": 0.0,
            "grid_import": 0.0,
            "grid_export": 0.0,
            "self_consumed": 0.0,
            "self_consumption_ratio": None,
            "self_sufficiency_ratio": None,
            "cycles": 0.0,
            "soc_min": None,
            "soc_max": None,
            "soc_final": None,
            "losses": 0.0,
            "hours": 0,
        }

    def column_sum(column: str) -> float:
        return float(result[column].sum()) if column in result else 0.0

    def column_max(column: str) -> float:
        return float(result[column].max()) if column in result and len(result) else 0.0

    consumption = column_sum("consumption_kwh")
    solar = column_sum("solar_production_kwh")
    pv_direct = column_sum("pv_direct_kwh")
    discharge = column_sum("battery_discharge_kwh")
    charge = column_sum("battery_charge_kwh")
    grid_import = column_sum("grid_import_kwh")
    grid_export = column_sum("grid_export_kwh")
    self_consumed = pv_direct + charge * p.charge_efficiency

    soc = (
        pd.to_numeric(result["battery_soc"], errors="coerce").dropna()
        if "battery_soc" in result
        else pd.Series(dtype=float)
    )
    cycles = discharge / p.capacity_kwh if p.capacity_kwh > 0 else 0.0

    return {
        "consumption": consumption,
        "solar": solar,
        "pv_direct": pv_direct,
        "charge": charge,
        "discharge": discharge,
        "grid_import": grid_import,
        "grid_export": grid_export,
        "self_consumed": self_consumed,
        "self_consumption_ratio": (
            self_consumed / solar * 100.0 if solar > 0 else None
        ),
        "self_sufficiency_ratio": (
            (consumption - grid_import) / consumption * 100.0
            if consumption > 0
            else None
        ),
        "cycles": cycles,
        "soc_min": float(soc.min()) if not soc.empty else None,
        "soc_max": float(soc.max()) if not soc.empty else None,
        "soc_final": float(soc.iloc[-1]) if not soc.empty else None,
        "losses": column_sum("battery_loss_kwh"),
        "hours": int(len(result)),
        "peak_charge_kw": column_max("battery_charge_kwh"),
        "peak_discharge_kw": column_max("battery_discharge_kwh"),
        "peak_grid_import_kw": column_max("grid_import_kwh"),
    }


def check_energy_conservation(result: pd.DataFrame, tolerance: float = 1e-6) -> dict[str, Any]:
    """Vérifie les deux équations de conservation du modèle.

    - ``PV = direct + charge_prélevée + export``
    - ``charge_bâtiment = direct + décharge_livrée + import``
    """
    if result is None or result.empty:
        return {
            "pv_balance_max_error": 0.0,
            "load_balance_max_error": 0.0,
            "consistent": True,
        }

    pv_error = (
        result["solar_production_kwh"]
        - result["pv_direct_kwh"]
        - result["battery_charge_kwh"]
        - result["grid_export_kwh"]
    ).abs()
    load_error = (
        result["consumption_kwh"]
        - result["pv_direct_kwh"]
        - result["battery_discharge_kwh"]
        - result["grid_import_kwh"]
    ).abs()
    return {
        "pv_balance_max_error": float(pv_error.max()),
        "load_balance_max_error": float(load_error.max()),
        "consistent": bool(
            pv_error.max() <= tolerance and load_error.max() <= tolerance
        ),
    }
