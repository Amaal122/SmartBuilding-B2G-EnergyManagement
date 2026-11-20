"""Validation des données et des paramètres de simulation.

Les validations renvoient des dictionnaires sérialisables (et non des
exceptions) afin que l'interface puisse afficher un diagnostic explicite.
Les exceptions sont réservées aux erreurs de programmation.
"""

from __future__ import annotations

from typing import Any, Iterable

import numpy as np
import pandas as pd

REQUIRED_SCENARIO_COLUMNS: tuple[str, ...] = (
    "timestamp",
    "consumption_kwh",
    "solar_production_kwh",
    "grid_import_kwh",
    "grid_export_kwh",
    "battery_soc",
    "temperature_outdoor",
)


def _check(condition: bool, message: str) -> dict[str, Any] | None:
    return None if condition else {"message": message}


def validate_scenario(df: pd.DataFrame) -> dict[str, Any]:
    """Contrôle la cohérence d'un scénario énergétique horaire.

    Vérifie la présence des colonnes, l'unicité et la régularité des
    horodatages, l'absence de valeurs négatives et l'égalité du bilan
    ``consommation = autoconsommée + import``.
    """
    errors: list[str] = []
    warnings: list[str] = []

    if df is None or df.empty:
        return {
            "valid": False,
            "errors": ["Le scénario est vide."],
            "warnings": [],
            "checks": {},
        }

    missing = [column for column in REQUIRED_SCENARIO_COLUMNS if column not in df]
    if missing:
        errors.append("Colonnes manquantes : " + ", ".join(missing))

    checks: dict[str, Any] = {}
    if not missing:
        ts = pd.to_datetime(df["timestamp"], errors="coerce")
        checks["timestamps_valides"] = bool(ts.notna().all())
        checks["doublons_horodatage"] = int(ts.duplicated().sum())
        checks["heures"] = int(len(df))
        if checks["doublons_horodatage"]:
            errors.append(
                f"{checks['doublons_horodatage']} horodatage(s) dupliqué(s)."
            )
        if not checks["timestamps_valides"]:
            errors.append("Certains horodatages sont invalides.")

        deltas = ts.diff().dropna().dt.total_seconds()
        checks["pas_regulier"] = bool(
            deltas.empty or (deltas == 3600).all()
        )
        if not checks["pas_regulier"]:
            warnings.append(
                "Le pas temporel n'est pas strictement horaire : les agrégats "
                "restent calculés par ligne."
            )

        for column in (
            "consumption_kwh",
            "solar_production_kwh",
            "grid_import_kwh",
            "grid_export_kwh",
        ):
            series = pd.to_numeric(df[column], errors="coerce")
            negatives = int((series < 0).sum())
            checks[f"{column}_negatifs"] = negatives
            if negatives:
                errors.append(f"{negatives} valeur(s) négative(s) dans {column}.")

        conso = pd.to_numeric(df["consumption_kwh"], errors="coerce").fillna(0.0)
        solar = pd.to_numeric(df["solar_production_kwh"], errors="coerce").fillna(0.0)
        grid_import = pd.to_numeric(df["grid_import_kwh"], errors="coerce").fillna(0.0)
        grid_export = pd.to_numeric(df["grid_export_kwh"], errors="coerce").fillna(0.0)

        self_consumed = np.minimum(conso, solar)
        residual_import = np.abs((conso - self_consumed) - grid_import)
        residual_export = np.abs((solar - self_consumed) - grid_export)
        checks["ecart_max_import_kwh"] = float(residual_import.max())
        checks["ecart_max_export_kwh"] = float(residual_export.max())
        if residual_import.max() > 1e-6 or residual_export.max() > 1e-6:
            errors.append(
                "Le bilan énergétique n'est pas conservé : "
                "import ≠ consommation − autoconsommation, ou "
                "surplus ≠ production − autoconsommation."
            )

        negative_soc = int((pd.to_numeric(df["battery_soc"], errors="coerce") < 0).sum())
        checks["soc_negatif"] = negative_soc
        if negative_soc:
            errors.append("Le SOC batterie contient des valeurs négatives.")

    return {
        "valid": not errors,
        "errors": errors,
        "warnings": warnings,
        "checks": checks,
    }


def validate_battery_parameters(
    *,
    capacity_kwh: float,
    initial_soc_pct: float,
    max_charge_kw: float,
    max_discharge_kw: float,
    charge_efficiency: float,
    discharge_efficiency: float,
    min_soc_pct: float,
    max_soc_pct: float,
) -> dict[str, Any]:
    """Valide les paramètres d'une batterie avant simulation.

    Retourne ``{"valid", "errors", "warnings"}``. La capacité nulle est
    acceptée : elle signifie « aucun stockage ».
    """
    errors: list[str] = []
    warnings: list[str] = []

    values = {
        "capacity_kwh": capacity_kwh,
        "initial_soc_pct": initial_soc_pct,
        "max_charge_kw": max_charge_kw,
        "max_discharge_kw": max_discharge_kw,
        "charge_efficiency": charge_efficiency,
        "discharge_efficiency": discharge_efficiency,
        "min_soc_pct": min_soc_pct,
        "max_soc_pct": max_soc_pct,
    }
    for name, value in values.items():
        if value is None or not np.isfinite(value):
            errors.append(f"Paramètre invalide : {name}.")

    if errors:
        return {"valid": False, "errors": errors, "warnings": warnings}

    if capacity_kwh < 0:
        errors.append("La capacité de la batterie ne peut pas être négative.")
    if not 0.0 <= min_soc_pct < max_soc_pct <= 100.0:
        errors.append("La plage SOC doit vérifier 0 ≤ min < max ≤ 100 %.")
    elif not min_soc_pct <= initial_soc_pct <= max_soc_pct:
        errors.append(
            "Le SOC initial doit être compris entre le SOC minimum et maximum."
        )
    if max_charge_kw < 0 or max_discharge_kw < 0:
        errors.append("Les puissances de charge et de décharge doivent être ≥ 0.")
    if not 0.0 < charge_efficiency <= 1.0:
        errors.append("Le rendement de charge doit être dans ]0 ; 1].")
    if not 0.0 < discharge_efficiency <= 1.0:
        errors.append("Le rendement de décharge doit être dans ]0 ; 1].")
    if capacity_kwh == 0 and (max_charge_kw > 0 or max_discharge_kw > 0):
        warnings.append(
            "Capacité nulle : la batterie est ignorée et les scénarios A/B sont identiques."
        )
    if charge_efficiency < 0.7 or discharge_efficiency < 0.7:
        warnings.append(
            "Rendement inférieur à 70 % : pertes importantes, vérifiez l'hypothèse."
        )

    return {"valid": not errors, "errors": errors, "warnings": warnings}


def validate_pv_ratio(ratio: float) -> dict[str, Any]:
    """Le taux de couverture PV modélisé doit rester dans une plage réaliste."""
    if ratio is None or not np.isfinite(ratio):
        return {"valid": False, "errors": ["Le taux de couverture PV est invalide."]}
    if not 0.0 < ratio <= 2.0:
        return {
            "valid": False,
            "errors": ["Le taux de couverture PV doit être compris entre 0 et 200 %."],
        }
    warnings = []
    if ratio > 1.2:
        warnings.append(
            "Au-delà de 120 %, le scénario devient très théorique (surplus massif)."
        )
    return {"valid": True, "errors": [], "warnings": warnings}


def validate_uploaded_table(df: pd.DataFrame) -> dict[str, Any]:
    """Analyse un CSV importé par l'utilisateur.

    Détecte une colonne temporelle et une colonne de consommation parmi des
    noms courants. Aucun fichier n'est exécuté ni persisté.
    """
    if df is None or df.empty:
        return {
            "valid": False,
            "errors": ["Le fichier est vide ou illisible."],
            "timestamp_column": None,
            "value_column": None,
            "rows": 0,
            "columns": [],
        }

    timestamp_candidates = (
        "timestamp",
        "date_time",
        "datetime",
        "date",
        "time",
        "horodatage",
    )
    value_candidates = (
        "meter_reading",
        "consumption_kwh",
        "consumption",
        "energie_kwh",
        "energy_kwh",
        "kwh",
        "puissance_kw",
    )

    columns = [str(column) for column in df.columns]
    lowered = {str(column).strip().lower(): str(column) for column in df.columns}
    timestamp_column = next(
        (lowered[name] for name in timestamp_candidates if name in lowered), None
    )
    value_column = next(
        (lowered[name] for name in value_candidates if name in lowered), None
    )

    errors: list[str] = []
    warnings: list[str] = []
    if timestamp_column is None:
        errors.append(
            "Aucune colonne temporelle reconnue (timestamp, date_time, date…)."
        )
    if value_column is None:
        errors.append(
            "Aucune colonne de consommation reconnue (meter_reading, consumption_kwh…)."
        )

    if timestamp_column is not None:
        parsed = pd.to_datetime(df[timestamp_column], errors="coerce")
        invalid = int(parsed.isna().sum())
        if invalid:
            warnings.append(f"{invalid} horodatage(s) invalide(s) seront ignorés.")
    if value_column is not None:
        values = pd.to_numeric(df[value_column], errors="coerce")
        invalid = int(values.isna().sum())
        negatives = int((values < 0).sum())
        if invalid:
            warnings.append(f"{invalid} mesure(s) non numérique(s).")
        if negatives:
            warnings.append(f"{negatives} mesure(s) négative(s) détectée(s).")

    return {
        "valid": not errors,
        "errors": errors,
        "warnings": warnings,
        "timestamp_column": timestamp_column,
        "value_column": value_column,
        "rows": int(len(df)),
        "columns": columns,
    }


def missing_columns(df: pd.DataFrame, columns: Iterable[str]) -> list[str]:
    """Liste les colonnes absentes d'un DataFrame."""
    if df is None:
        return list(columns)
    return [column for column in columns if column not in df.columns]
