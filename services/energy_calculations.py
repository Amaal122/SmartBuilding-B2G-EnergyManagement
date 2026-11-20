"""Calculs énergétiques réutilisables (sans dépendance Streamlit).

Toutes les fonctions acceptent des DataFrame dont les colonnes canoniques
sont ``timestamp``, ``consumption_kwh``, ``solar_production_kwh``,
``grid_import_kwh`` et ``grid_export_kwh``. Le pas est horaire, donc une
valeur exprimée en kWh sur une heure est numériquement égale à une puissance
moyenne en kW ; les fonctions de puissance le documentent explicitement.

Conventions :
- ``autoconsommation`` = énergie PV consommée sur place / énergie PV produite ;
- ``autosuffisance`` = énergie PV consommée sur place / consommation totale.

Ces deux ratios ne doivent jamais être confondus.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

ENERGY_COLUMNS = (
    "consumption_kwh",
    "solar_production_kwh",
    "grid_import_kwh",
    "grid_export_kwh",
)


# ---------------------------------------------------------------------------
# Utilitaires numériques
# ---------------------------------------------------------------------------
def safe_divide(numerator: float | None, denominator: float | None) -> float | None:
    """Division protégée : retourne ``None`` si le dénominateur est nul/invalide."""
    if numerator is None or denominator is None:
        return None
    try:
        num, den = float(numerator), float(denominator)
    except (TypeError, ValueError):
        return None
    if not np.isfinite(num) or not np.isfinite(den) or den == 0:
        return None
    return num / den


def _series(df: pd.DataFrame, column: str) -> pd.Series:
    if df is None or column not in df:
        return pd.Series(dtype=float)
    return pd.to_numeric(df[column], errors="coerce").fillna(0.0)


def grid_flows(
    consumption_kwh: Any, solar_production_kwh: Any
) -> dict[str, np.ndarray]:
    """Bilan réseau simplifié, sans batterie.

    ``grid_import = max(0, consommation − PV)`` ;
    ``grid_export = max(0, PV − consommation)`` ;
    ``self_consumed = min(consommation, PV)``.
    """
    conso = np.clip(np.nan_to_num(np.asarray(consumption_kwh, dtype=float)), 0.0, None)
    solar = np.clip(np.nan_to_num(np.asarray(solar_production_kwh, dtype=float)), 0.0, None)
    self_consumed = np.minimum(conso, solar)
    return {
        "self_consumed": self_consumed,
        "grid_import": np.maximum(0.0, conso - self_consumed),
        "grid_export": np.maximum(0.0, solar - self_consumed),
    }


def self_consumption_ratio(
    solar_production_kwh: float, self_consumed_kwh: float
) -> float | None:
    """Taux d'autoconsommation (%) = autoconsommé / production PV."""
    ratio = safe_divide(self_consumed_kwh, solar_production_kwh)
    return ratio * 100.0 if ratio is not None else None


def self_sufficiency_ratio(
    consumption_kwh: float, self_consumed_kwh: float
) -> float | None:
    """Taux d'autosuffisance (%) = autoconsommé / consommation."""
    ratio = safe_divide(self_consumed_kwh, consumption_kwh)
    return ratio * 100.0 if ratio is not None else None


def comparison(current: float | None, previous: float | None) -> float | None:
    """Variation relative (%) entre deux valeurs."""
    if current is None or previous is None:
        return None
    base = safe_divide(float(current) - float(previous), float(previous))
    return base * 100.0 if base is not None else None


# ---------------------------------------------------------------------------
# KPI et agrégations
# ---------------------------------------------------------------------------
def energy_kpis(df: pd.DataFrame) -> dict[str, Any]:
    """Indicateurs clés d'une fenêtre horaire.

    Les clés historiques (``consumption``, ``solar``, ``grid_import``…)
    sont conservées pour compatibilité avec les composants existants.
    """
    empty = {
        "consumption": 0.0,
        "solar": 0.0,
        "pv_plant": 0.0,
        "grid_import": 0.0,
        "surplus": 0.0,
        "self_consumed": 0.0,
        "autoconsumption": None,
        "self_sufficiency": None,
        "coverage": None,
        "grid_dependency": None,
        "soc": None,
        "soc_previous": None,
        "soc_delta": None,
        "avg_power_kw": 0.0,
        "peak_power_kw": 0.0,
        "peak_timestamp": None,
        "battery_charge": 0.0,
        "battery_discharge": 0.0,
        "hours": 0,
        "days": 0,
    }
    if df is None or df.empty:
        return empty

    conso = _series(df, "consumption_kwh")
    solar = _series(df, "solar_production_kwh")
    flows = grid_flows(conso, solar)
    total_conso = float(conso.sum())
    total_solar = float(solar.sum())
    self_consumed = float(flows["self_consumed"].sum())
    grid_import = (
        float(_series(df, "grid_import_kwh").sum())
        if "grid_import_kwh" in df
        else float(flows["grid_import"].sum())
    )
    surplus = (
        float(_series(df, "grid_export_kwh").sum())
        if "grid_export_kwh" in df
        else float(flows["grid_export"].sum())
    )

    soc_series = (
        pd.to_numeric(df["battery_soc"], errors="coerce").dropna()
        if "battery_soc" in df
        else pd.Series(dtype=float)
    )
    soc = float(soc_series.iloc[-1]) if not soc_series.empty else None
    soc_previous = float(soc_series.iloc[-2]) if len(soc_series) >= 2 else None

    peak_index = conso.idxmax() if not conso.empty else None
    peak_power = float(conso.loc[peak_index]) if peak_index is not None else 0.0
    peak_timestamp = (
        pd.Timestamp(df.loc[peak_index, "timestamp"])
        if peak_index is not None and "timestamp" in df
        else None
    )

    hours = int(len(df))
    return {
        "consumption": total_conso,
        "solar": total_solar,
        "pv_plant": (
            float(_series(df, "pv_plant_kwh").sum())
            if "pv_plant_kwh" in df
            else total_solar
        ),
        "grid_import": grid_import,
        "surplus": surplus,
        "self_consumed": self_consumed,
        "autoconsumption": self_consumption_ratio(total_solar, self_consumed),
        "self_sufficiency": self_sufficiency_ratio(total_conso, self_consumed),
        "coverage": self_sufficiency_ratio(total_conso, self_consumed),
        "grid_dependency": (
            safe_divide(grid_import, total_conso) * 100.0
            if safe_divide(grid_import, total_conso) is not None
            else None
        ),
        "soc": soc,
        "soc_previous": soc_previous,
        "soc_delta": (soc - soc_previous)
        if soc is not None and soc_previous is not None
        else None,
        "avg_power_kw": total_conso / hours if hours else 0.0,
        "peak_power_kw": peak_power,
        "peak_timestamp": peak_timestamp,
        "battery_charge": (
            float(_series(df, "battery_charge_kwh").sum())
            if "battery_charge_kwh" in df
            else 0.0
        ),
        "battery_discharge": (
            float(_series(df, "battery_discharge_kwh").sum())
            if "battery_discharge_kwh" in df
            else 0.0
        ),
        "hours": hours,
        "days": period_days(df),
    }


def period_days(df: pd.DataFrame) -> int:
    """Nombre de jours couverts, exprimé en jours pleins équivalents."""
    if df is None or df.empty:
        return 0
    hours = len(df)
    if hours >= 20:
        return max(1, int(round(hours / 24)))
    if "timestamp" not in df:
        return 1
    return int(pd.to_datetime(df["timestamp"]).dt.normalize().nunique())


def daily_summary(df: pd.DataFrame) -> pd.DataFrame:
    """Agrégation journalière prête pour les graphiques en barres."""
    columns = [
        "date",
        "consumption_kwh",
        "solar_production_kwh",
        "grid_import_kwh",
        "grid_export_kwh",
        "battery_charge_kwh",
        "battery_discharge_kwh",
        "soc_mean",
        "peak_power_kw",
        "samples",
    ]
    if df is None or df.empty or "timestamp" not in df:
        return pd.DataFrame(columns=columns)

    work = df.copy()
    work["date"] = pd.to_datetime(work["timestamp"]).dt.normalize()
    for column in columns[1:-2]:
        if column not in work:
            work[column] = 0.0
        work[column] = pd.to_numeric(work[column], errors="coerce").fillna(0.0)
    if "battery_soc" not in work:
        work["battery_soc"] = np.nan

    daily = (
        work.groupby("date", as_index=False)
        .agg(
            consumption_kwh=("consumption_kwh", "sum"),
            solar_production_kwh=("solar_production_kwh", "sum"),
            grid_import_kwh=("grid_import_kwh", "sum"),
            grid_export_kwh=("grid_export_kwh", "sum"),
            battery_charge_kwh=("battery_charge_kwh", "sum"),
            battery_discharge_kwh=("battery_discharge_kwh", "sum"),
            soc_mean=("battery_soc", "mean"),
            peak_power_kw=("consumption_kwh", "max"),
            samples=("timestamp", "count"),
        )
        .sort_values("date")
        .reset_index(drop=True)
    )
    return daily


def hourly_profile(df: pd.DataFrame) -> pd.DataFrame:
    """Profil horaire moyen (0–23 h) sur la fenêtre analysée."""
    if df is None or df.empty or "timestamp" not in df:
        return pd.DataFrame(columns=["hour", "consumption_kwh", "solar_production_kwh"])
    work = df.copy()
    work["hour"] = pd.to_datetime(work["timestamp"]).dt.hour
    profile = (
        work.groupby("hour", as_index=False)
        .agg(
            consumption_kwh=("consumption_kwh", "mean"),
            solar_production_kwh=("solar_production_kwh", "mean"),
        )
        .sort_values("hour")
    )
    return profile


def monthly_summary(df: pd.DataFrame) -> pd.DataFrame:
    """Agrégation mensuelle (pertinente seulement au-delà d'un mois de données)."""
    if df is None or df.empty or "timestamp" not in df:
        return pd.DataFrame(columns=["month", "consumption_kwh", "solar_production_kwh"])
    work = df.copy()
    work["month"] = pd.to_datetime(work["timestamp"]).dt.to_period("M").dt.to_timestamp()
    return (
        work.groupby("month", as_index=False)
        .agg(
            consumption_kwh=("consumption_kwh", "sum"),
            solar_production_kwh=("solar_production_kwh", "sum"),
        )
        .sort_values("month")
        .reset_index(drop=True)
    )


# ---------------------------------------------------------------------------
# Détection d'anomalies (seuils statistiques simples, pas d'IA)
# ---------------------------------------------------------------------------
def detect_anomalies(
    df: pd.DataFrame,
    *,
    column: str = "consumption_kwh",
    z_threshold: float = 3.0,
    min_samples: int = 12,
    include_daily: bool = True,
) -> pd.DataFrame:
    """Détecte les valeurs atypiques par score Z (moyenne/écart-type).

    Méthode statistique simple et explicite : aucune intelligence
    artificielle n'est revendiquée. Retourne un DataFrame vide si
    l'échantillon est trop petit ou si l'écart-type est nul.

    Colonnes : ``timestamp``, ``value``, ``zscore``, ``direction``,
    ``severity``, ``scale``.
    """
    empty = pd.DataFrame(
        columns=["timestamp", "value", "zscore", "direction", "severity", "scale"]
    )
    if df is None or df.empty or column not in df or "timestamp" not in df:
        return empty

    work = df[["timestamp", column]].copy()
    work["timestamp"] = pd.to_datetime(work["timestamp"], errors="coerce")
    work[column] = pd.to_numeric(work[column], errors="coerce")
    work = work.dropna().sort_values("timestamp")
    if len(work) < min_samples:
        return empty

    mean = float(work[column].mean())
    std = float(work[column].std(ddof=0))
    if not np.isfinite(std) or std <= 0:
        return empty

    work["zscore"] = (work[column] - mean) / std
    flagged = work[work["zscore"].abs() >= z_threshold].copy()
    flagged["direction"] = np.where(flagged["zscore"] > 0, "Élevée", "Basse")
    flagged["severity"] = np.where(
        flagged["zscore"].abs() >= z_threshold * 1.5, "Critique", "Avertissement"
    )
    flagged["scale"] = "Horaire"

    parts = [
        flagged.rename(columns={column: "value"})[
            ["timestamp", "value", "zscore", "direction", "severity", "scale"]
        ]
    ]

    if include_daily and len(work) >= 24 * 3:
        work["date"] = work["timestamp"].dt.normalize()
        daily = work.groupby("date", as_index=False)[column].sum()
        daily_mean = float(daily[column].mean())
        daily_std = float(daily[column].std(ddof=0))
        if np.isfinite(daily_std) and daily_std > 0 and len(daily) >= 3:
            daily["zscore"] = (daily[column] - daily_mean) / daily_std
            daily_flagged = daily[daily["zscore"].abs() >= z_threshold].copy()
            if not daily_flagged.empty:
                daily_flagged["direction"] = np.where(
                    daily_flagged["zscore"] > 0, "Élevée", "Basse"
                )
                daily_flagged["severity"] = np.where(
                    daily_flagged["zscore"].abs() >= z_threshold * 1.5,
                    "Critique",
                    "Avertissement",
                )
                daily_flagged["scale"] = "Journalière"
                parts.append(
                    daily_flagged.rename(columns={"date": "timestamp", column: "value"})[
                        ["timestamp", "value", "zscore", "direction", "severity", "scale"]
                    ]
                )

    result = pd.concat(parts, ignore_index=True)
    return result.sort_values("timestamp").reset_index(drop=True)


def anomaly_thresholds(df: pd.DataFrame, column: str = "consumption_kwh") -> dict[str, float | None]:
    """Moyenne et bornes ±3σ utilisées par la détection d'anomalies."""
    if df is None or df.empty or column not in df:
        return {"mean": None, "std": None, "low": None, "high": None}
    values = pd.to_numeric(df[column], errors="coerce").dropna()
    if values.empty:
        return {"mean": None, "std": None, "low": None, "high": None}
    mean, std = float(values.mean()), float(values.std(ddof=0))
    return {
        "mean": mean,
        "std": std,
        "low": mean - 3 * std,
        "high": mean + 3 * std,
    }
