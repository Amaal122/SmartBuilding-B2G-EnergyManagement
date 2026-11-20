"""Calculs métier et agrégations à partir des données simulées.

Aucune dépendance à Streamlit : ces fonctions sont testables et pourront
recevoir plus tard des données issues d'un backend réel.
"""

from __future__ import annotations

from datetime import date
from typing import Any

import numpy as np
import pandas as pd

from services import energy_calculations as _energy
from utils import formatting as fmt

# Seuils de démonstration (non contractuels).
PEAK_POWER_THRESHOLD_KW = 68.0
LOW_BATTERY_WARNING = 30.0
LOW_BATTERY_CRITICAL = 20.0
SOLAR_LOW_RATIO = 0.80
CONSUMPTION_HIGH_RATIO = 1.12

TIME_PERIODS: dict[str, tuple[int, int] | None] = {
    "Toutes les heures": None,
    "Nuit · 00–06": (0, 6),
    "Matin · 06–12": (6, 12),
    "Après-midi · 12–18": (12, 18),
    "Soir · 18–24": (18, 24),
}


# ---------------------------------------------------------------------------
# Filtres temporels
# ---------------------------------------------------------------------------
def _safe_divide(numerator: float, denominator: float) -> float | None:
    if denominator is None or not np.isfinite(denominator) or denominator == 0:
        return None
    return float(numerator) / float(denominator)


def latest_timestamp(df: pd.DataFrame) -> pd.Timestamp | None:
    if df is None or df.empty or "timestamp" not in df:
        return None
    return pd.Timestamp(df["timestamp"].max())


def last_days(df: pd.DataFrame, days: int) -> pd.DataFrame:
    """Fenêtre d'analyse lisible par un humain.

    ``1`` correspond aux 24 dernières heures glissantes ; au-delà, la fenêtre
    est alignée sur des journées civiles (aujourd'hui inclus), ce qui évite des
    barres journalières artificiellement tronquées en début de période.
    """
    if df is None or df.empty:
        return df.iloc[0:0] if df is not None else pd.DataFrame()
    end = latest_timestamp(df)
    if days <= 1:
        return df[df["timestamp"] > end - pd.Timedelta(hours=24)].copy()
    start = end.normalize() - pd.Timedelta(days=days - 1)
    return df[df["timestamp"] >= start].copy()


def previous_days(df: pd.DataFrame, days: int) -> pd.DataFrame:
    """Fenêtre précédente de même durée, pour les comparaisons."""
    if df is None or df.empty:
        return df.iloc[0:0] if df is not None else pd.DataFrame()
    end = latest_timestamp(df)
    if days <= 1:
        current_start = end - pd.Timedelta(hours=24)
        return df[
            (df["timestamp"] > current_start - pd.Timedelta(hours=24))
            & (df["timestamp"] <= current_start)
        ].copy()
    current_start = end.normalize() - pd.Timedelta(days=days - 1)
    previous_end = current_start
    previous_start = previous_end - pd.Timedelta(days=days)
    return df[
        (df["timestamp"] >= previous_start) & (df["timestamp"] < previous_end)
    ].copy()


def filter_date_range(
    df: pd.DataFrame, start_date: date, end_date: date
) -> pd.DataFrame:
    """Filtre inclusif sur des dates (journées complètes)."""
    if df is None or df.empty:
        return df
    start = pd.Timestamp(start_date)
    end = pd.Timestamp(end_date) + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)
    if start > end:
        start, end = end, start
    return df[(df["timestamp"] >= start) & (df["timestamp"] <= end)].copy()


def filter_time_period(df: pd.DataFrame, period_label: str) -> pd.DataFrame:
    """Filtre sur une plage horaire de la journée."""
    if df is None or df.empty:
        return df
    bounds = TIME_PERIODS.get(period_label)
    if bounds is None:
        return df
    start_hour, end_hour = bounds
    return df[df["timestamp"].dt.hour.isin(range(start_hour, end_hour))].copy()


def period_days(df: pd.DataFrame) -> int:
    """Nombre de jours couverts, exprimé en jours pleins équivalents."""
    if df is None or df.empty:
        return 0
    hours = len(df)
    if hours >= 20:
        return max(1, int(round(hours / 24)))
    return int(df["timestamp"].dt.normalize().nunique())


def filter_zones(zone_df: pd.DataFrame, zones: list[str]) -> pd.DataFrame:
    if zone_df is None or zone_df.empty or not zones:
        return zone_df.iloc[0:0]
    return zone_df[zone_df["zone"].isin(zones)].copy()


# ---------------------------------------------------------------------------
# KPI et agrégations
# ---------------------------------------------------------------------------
def energy_kpis(df: pd.DataFrame) -> dict[str, Any]:
    """Calcule les indicateurs clés d'une fenêtre énergétique."""
    if df is None or df.empty:
        return {
            "consumption": 0.0,
            "solar": 0.0,
            "grid_import": 0.0,
            "surplus": 0.0,
            "self_consumed": 0.0,
            "autoconsumption": None,
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

    solar = float(df["solar_production_kwh"].sum())
    consumption = float(df["consumption_kwh"].sum())
    self_consumed_series = np.minimum(
        df["consumption_kwh"].to_numpy(dtype=float),
        df["solar_production_kwh"].to_numpy(dtype=float),
    )
    self_consumed = float(np.sum(self_consumed_series))
    grid_import = float(df["grid_import_kwh"].sum())
    surplus = float(df["grid_export_kwh"].sum())

    soc_series = df["battery_soc"].dropna()
    soc = float(soc_series.iloc[-1]) if not soc_series.empty else None
    soc_previous = float(soc_series.iloc[-2]) if len(soc_series) >= 2 else None

    peak_index = df["consumption_kwh"].idxmax() if not df.empty else None
    peak_power = float(df.loc[peak_index, "consumption_kwh"]) if peak_index is not None else 0.0
    peak_timestamp = (
        pd.Timestamp(df.loc[peak_index, "timestamp"]) if peak_index is not None else None
    )

    hours = int(len(df))
    return {
        "consumption": consumption,
        "solar": solar,
        "grid_import": grid_import,
        "surplus": surplus,
        "self_consumed": self_consumed,
        "autoconsumption": (
            _safe_divide(self_consumed, solar) * 100.0 if _safe_divide(self_consumed, solar) is not None else None
        ),
        "coverage": (
            _safe_divide(self_consumed, consumption) * 100.0
            if _safe_divide(self_consumed, consumption) is not None
            else None
        ),
        "grid_dependency": (
            _safe_divide(grid_import, consumption) * 100.0
            if _safe_divide(grid_import, consumption) is not None
            else None
        ),
        "soc": soc,
        "soc_previous": soc_previous,
        "soc_delta": (soc - soc_previous) if soc is not None and soc_previous is not None else None,
        "avg_power_kw": float(df["consumption_kwh"].mean()),
        "peak_power_kw": peak_power,
        "peak_timestamp": peak_timestamp,
        "battery_charge": float(df["battery_charge_kwh"].sum()),
        "battery_discharge": float(df["battery_discharge_kwh"].sum()),
        "hours": hours,
        "days": period_days(df),
    }


def comparison(current: float | None, previous: float | None) -> float | None:
    """Variation relative (%) entre deux valeurs."""
    if current is None or previous is None:
        return None
    if not np.isfinite(previous) or previous == 0:
        return None
    return (float(current) - float(previous)) / float(previous) * 100.0


def daily_summary(df: pd.DataFrame) -> pd.DataFrame:
    """Agrégation journalière prête pour les graphiques en barres."""
    if df is None or df.empty:
        return pd.DataFrame(
            columns=[
                "date",
                "consumption_kwh",
                "solar_production_kwh",
                "grid_import_kwh",
                "grid_export_kwh",
                "battery_charge_kwh",
                "battery_discharge_kwh",
                "soc_mean",
                "peak_power_kw",
            ]
        )

    work = df.copy()
    work["date"] = work["timestamp"].dt.normalize()
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


def zone_summary(zone_df: pd.DataFrame) -> pd.DataFrame:
    """Consommation agrégée par zone avec part relative."""
    if zone_df is None or zone_df.empty:
        return pd.DataFrame(columns=["zone", "consumption_kwh", "share_pct", "avg_power_kw"])

    summary = (
        zone_df.groupby("zone", as_index=False)
        .agg(consumption_kwh=("consumption_kwh", "sum"), samples=("timestamp", "count"))
        .sort_values("consumption_kwh", ascending=False)
        .reset_index(drop=True)
    )
    total = float(summary["consumption_kwh"].sum())
    summary["share_pct"] = (
        summary["consumption_kwh"] / total * 100.0 if total > 0 else 0.0
    )
    summary["avg_power_kw"] = summary["consumption_kwh"] / summary["samples"].replace(0, np.nan)
    return summary


def battery_snapshot(df: pd.DataFrame, capacity_kwh: float) -> dict[str, Any]:
    """État illustratif de la batterie à partir de la dernière mesure."""
    if df is None or df.empty:
        return {
            "soc": None,
            "soc_delta": None,
            "status": "Indisponible",
            "tone": "neutral",
            "stored_kwh": None,
            "capacity_kwh": capacity_kwh,
            "charge_kwh": 0.0,
            "discharge_kwh": 0.0,
            "min_soc": None,
            "max_soc": None,
        }

    soc_series = df["battery_soc"].dropna()
    soc = float(soc_series.iloc[-1]) if not soc_series.empty else None
    previous = float(soc_series.iloc[-2]) if len(soc_series) >= 2 else soc
    delta = (soc - previous) if soc is not None and previous is not None else None

    if delta is None:
        status, tone = "En veille", "neutral"
    elif delta > 0.15:
        status, tone = "En charge", "good"
    elif delta < -0.15:
        status, tone = "En décharge", "warn"
    else:
        status, tone = "En veille", "neutral"

    return {
        "soc": soc,
        "soc_delta": delta,
        "status": status,
        "tone": tone,
        "stored_kwh": (soc / 100.0 * capacity_kwh) if soc is not None else None,
        "capacity_kwh": capacity_kwh,
        "charge_kwh": float(df["battery_charge_kwh"].sum()),
        "discharge_kwh": float(df["battery_discharge_kwh"].sum()),
        "min_soc": float(soc_series.min()) if not soc_series.empty else None,
        "max_soc": float(soc_series.max()) if not soc_series.empty else None,
    }


def grid_snapshot(df: pd.DataFrame) -> dict[str, Any]:
    """Indicateurs d'échange réseau sur la fenêtre analysée."""
    if df is None or df.empty:
        return {
            "import_kwh": 0.0,
            "export_kwh": 0.0,
            "dependency": None,
            "status": "Indisponible",
            "tone": "neutral",
            "latest_import_kw": 0.0,
            "latest_export_kw": 0.0,
        }

    consumption = float(df["consumption_kwh"].sum())
    import_kwh = float(df["grid_import_kwh"].sum())
    export_kwh = float(df["grid_export_kwh"].sum())
    dependency = _safe_divide(import_kwh, consumption)
    dependency_pct = dependency * 100.0 if dependency is not None else None

    latest = df.iloc[-1]
    latest_import = float(latest["grid_import_kwh"])
    latest_export = float(latest["grid_export_kwh"])

    if latest_export > 0.5:
        status, tone = "Surplus disponible", "good"
    elif latest_import > 0.5:
        status, tone = "Import réseau actif", "info"
    else:
        status, tone = "Équilibre", "neutral"

    return {
        "import_kwh": import_kwh,
        "export_kwh": export_kwh,
        "dependency": dependency_pct,
        "status": status,
        "tone": tone,
        "latest_import_kw": latest_import,
        "latest_export_kw": latest_export,
    }


def solar_status(df: pd.DataFrame, capacity_kwp: float) -> dict[str, str]:
    """Statut synthétique de la production PV simulée."""
    if df is None or df.empty:
        return {
            "label": "Indisponible",
            "pill": "N/A",
            "tone": "neutral",
            "message": "Aucune mesure disponible.",
            "icon": "info",
        }

    latest = df.iloc[-1]
    power = float(latest["solar_production_kwh"])
    hour = int(pd.Timestamp(latest["timestamp"]).hour)

    if hour < 7 or hour >= 19 or power <= 0.3:
        return {
            "label": "Arrêt nocturne",
            "pill": "Veille",
            "tone": "neutral",
            "message": "Aucune production solaire attendue à cette heure (simulation).",
            "icon": "clock",
        }
    if power >= capacity_kwp * 0.45:
        return {
            "label": "Production soutenue",
            "pill": "Production",
            "tone": "good",
            "message": "Le champ photovoltaïque produit à un niveau élevé (simulation).",
            "icon": "sun",
        }
    return {
        "label": "Production réduite",
        "pill": "Réduite",
        "tone": "warn",
        "message": "Ensoleillement ou nébulosité limités dans le scénario simulé.",
        "icon": "sun",
    }


# ---------------------------------------------------------------------------
# Alertes de démonstration
# ---------------------------------------------------------------------------
def build_alerts(
    df: pd.DataFrame, kpis: dict[str, Any]
) -> list[dict[str, str]]:
    """Construit quatre alertes dynamiques à partir des données simulées.

    Les alertes sont des constats de surveillance, jamais des actions de
    pilotage. Les seuils sont ceux d'un scénario de démonstration.
    """
    alerts: list[dict[str, str]] = []
    if df is None or df.empty:
        return alerts

    window = last_days(df, 7)
    daily = daily_summary(window)
    today = pd.Timestamp(df["timestamp"].max()).normalize()
    complete_days = daily[daily["date"] < today]

    # 1. Pic de consommation -------------------------------------------------
    peak_index = window["consumption_kwh"].idxmax()
    peak_power = float(window.loc[peak_index, "consumption_kwh"])
    peak_ts = pd.Timestamp(window.loc[peak_index, "timestamp"])
    if peak_power >= PEAK_POWER_THRESHOLD_KW:
        alerts.append(
            {
                "severity": "critical" if peak_power >= PEAK_POWER_THRESHOLD_KW * 1.12 else "warning",
                "icon": "bolt",
                "title": "Consommation élevée",
                "message": (
                    f"Pic horaire de {fmt.fr_power(peak_power, 1)} relevé le "
                    f"{fmt.fr_date(peak_ts)} à {fmt.fr_time(peak_ts)}, au-dessus du "
                    f"seuil de surveillance de {fmt.fr_power(PEAK_POWER_THRESHOLD_KW, 0)}."
                ),
                "meta": "Surveillance énergétique · seuil simulé",
            }
        )
    else:
        alerts.append(
            {
                "severity": "success",
                "icon": "check",
                "title": "Consommation sous contrôle",
                "message": (
                    f"Pic horaire de {fmt.fr_power(peak_power, 1)} sur 7 jours, "
                    f"sous le seuil de {fmt.fr_power(PEAK_POWER_THRESHOLD_KW, 0)}."
                ),
                "meta": "Surveillance énergétique · seuil simulé",
            }
        )

    # 2. Production solaire faible ------------------------------------------
    if len(complete_days) >= 2:
        last_solar = float(complete_days.iloc[-1]["solar_production_kwh"])
        baseline = float(complete_days.iloc[:-1]["solar_production_kwh"].mean())
        ratio = _safe_divide(last_solar, baseline)
        last_day = pd.Timestamp(complete_days.iloc[-1]["date"])
        if ratio is not None and ratio < SOLAR_LOW_RATIO:
            alerts.append(
                {
                    "severity": "warning",
                    "icon": "sun",
                    "title": "Production solaire faible",
                    "message": (
                        f"Production de {fmt.fr_energy(last_solar)} le "
                        f"{fmt.fr_date(last_day)}, soit "
                        f"{fmt.fr_number(abs((1 - ratio) * 100), 0)} % sous la moyenne "
                        "des jours précédents (simulation)."
                    ),
                    "meta": "Production photovoltaïque · scénario météo simulé",
                }
            )
        else:
            alerts.append(
                {
                    "severity": "info",
                    "icon": "sun",
                    "title": "Production PV conforme",
                    "message": (
                        f"Production de {fmt.fr_energy(last_solar)} le "
                        f"{fmt.fr_date(last_day)}, proche ou supérieure à la moyenne "
                        "récente du scénario simulé."
                    ),
                    "meta": "Production photovoltaïque · scénario météo simulé",
                }
            )
    else:
        alerts.append(
            {
                "severity": "info",
                "icon": "sun",
                "title": "Historique solaire insuffisant",
                "message": "Le recul disponible ne permet pas encore de comparer la production PV.",
                "meta": "Production photovoltaïque",
            }
        )

    # 3. Batterie sous seuil ------------------------------------------------
    soc_series = window["battery_soc"]
    if not soc_series.empty:
        min_soc = float(soc_series.min())
        min_index = soc_series.idxmin()
        min_ts = pd.Timestamp(window.loc[min_index, "timestamp"])
        if min_soc < LOW_BATTERY_CRITICAL:
            severity = "critical"
            title = "Batterie très basse"
        elif min_soc < LOW_BATTERY_WARNING:
            severity = "warning"
            title = "Batterie sous le seuil"
        else:
            severity = "success"
            title = "Batterie dans la plage cible"
        alerts.append(
            {
                "severity": severity,
                "icon": "battery",
                "title": title,
                "message": (
                    f"SOC minimal de {fmt.fr_pct(min_soc)} atteint le "
                    f"{fmt.fr_date(min_ts)} à {fmt.fr_time(min_ts)}. "
                    f"Seuil d'alerte simulé : {fmt.fr_pct(LOW_BATTERY_WARNING)}."
                ),
                "meta": "Stockage batterie · comportement simulé",
            }
        )

    # 4. Consommation inhabituelle -----------------------------------------
    if len(complete_days) >= 3:
        last_consumption = float(complete_days.iloc[-1]["consumption_kwh"])
        baseline = float(complete_days.iloc[:-1]["consumption_kwh"].mean())
        ratio = _safe_divide(last_consumption, baseline)
        last_day = pd.Timestamp(complete_days.iloc[-1]["date"])
        if ratio is not None and ratio > CONSUMPTION_HIGH_RATIO:
            severity = "warning"
            title = "Consommation inhabituelle"
            message = (
                f"Consommation de {fmt.fr_energy(last_consumption)} le "
                f"{fmt.fr_date(last_day)}, en hausse de "
                f"{fmt.fr_number((ratio - 1) * 100, 0)} % par rapport à la moyenne "
                "des jours précédents."
            )
        elif ratio is not None and ratio < 0.85:
            severity = "info"
            title = "Consommation inhabituellement basse"
            message = (
                f"Consommation de {fmt.fr_energy(last_consumption)} le "
                f"{fmt.fr_date(last_day)}, inférieure de "
                f"{fmt.fr_number((1 - ratio) * 100, 0)} % à la moyenne récente."
            )
        else:
            severity = "success"
            title = "Profil de consommation stable"
            message = (
                f"Consommation de {fmt.fr_energy(last_consumption)} le "
                f"{fmt.fr_date(last_day)}, conforme au profil habituel du scénario."
            )
        alerts.append(
            {
                "severity": severity,
                "icon": "activity",
                "title": title,
                "message": message,
                "meta": "Analyse de tendance · données simulées",
            }
        )

    # 5. Diagnostic de connectivité ---------------------------------------
    # Volontairement visible : la passerelle n'existe pas dans cette version.
    alerts.append(
        {
            "severity": "critical",
            "icon": "wifi-off",
            "title": "Passerelle IoT hors ligne",
            "message": (
                "Aucune passerelle de collecte n'est connectée. Ce statut est normal "
                "en mode démonstration et ne reflète aucune panne physique."
            ),
            "meta": "Diagnostic système · aucun équipement terrain",
        }
    )

    return alerts


def count_active_alerts(alerts: list[dict[str, str]]) -> int:
    return sum(1 for alert in alerts if alert.get("severity") in {"warning", "critical"})


# ---------------------------------------------------------------------------
# Capteurs et équipements
# ---------------------------------------------------------------------------
def sensor_snapshot(df: pd.DataFrame) -> list[dict[str, str]]:
    """Prépare les cartes capteurs à partir de la dernière mesure."""
    empty = {
        "value": "—",
        "unit": "",
        "status": "Hors ligne",
        "tone": "bad",
        "last": "—",
        "state": "Indisponible",
    }
    if df is None or df.empty:
        return []

    latest = df.iloc[-1]
    stamp = pd.Timestamp(latest["timestamp"])
    measure = fmt.fr_datetime(stamp)
    indoor = float(latest["temperature_indoor"])
    outdoor = float(latest["temperature_outdoor"])
    humidity = float(latest["humidity"])
    occupancy = int(latest["occupancy"])
    lighting_on = bool(latest["lighting_on"])
    hvac_active = bool(latest["hvac_active"])

    humidity_status = "Normal" if 35 <= humidity <= 65 else "Avertissement"
    humidity_tone = "good" if humidity_status == "Normal" else "warn"

    return [
        {
            "name": "Température intérieure",
            "room": "Zone de vie · moyenne",
            "value": fmt.fr_number(indoor, 1),
            "unit": "°C",
            "status": "Normal",
            "tone": "good",
            "state": "Confort dans la plage cible",
            "last": measure,
            "icon": "thermometer",
            "accent": "blue",
        },
        {
            "name": "Température extérieure",
            "room": "Toiture · abri météo",
            "value": fmt.fr_number(outdoor, 1),
            "unit": "°C",
            "status": "Normal",
            "tone": "good",
            "state": "Mesure simulée",
            "last": measure,
            "icon": "sun",
            "accent": "sky",
        },
        {
            "name": "Humidité relative",
            "room": "Zone de vie · moyenne",
            "value": fmt.fr_number(humidity, 0),
            "unit": "%",
            "status": humidity_status,
            "tone": humidity_tone,
            "state": "Plage cible 35–65 %",
            "last": measure,
            "icon": "droplet",
            "accent": "green",
        },
        {
            "name": "Occupation",
            "room": "Bâtiment · comptage personnes",
            "value": fmt.fr_number(occupancy, 0),
            "unit": "pers.",
            "status": "Normal",
            "tone": "good",
            "state": "Présence estimée (simulation)",
            "last": measure,
            "icon": "users",
            "accent": "purple",
        },
        {
            "name": "Éclairage",
            "room": "Éclairage automatique",
            "value": "Allumé" if lighting_on else "Éteint",
            "unit": "",
            "status": "Normal",
            "tone": "good" if lighting_on else "neutral",
            "state": "Commande scénarisée",
            "last": measure,
            "icon": "bulb",
            "accent": "amber",
        },
        {
            "name": "CVC / HVAC",
            "room": "Centrale de traitement d'air",
            "value": "Actif" if hvac_active else "Veille",
            "unit": "",
            "status": "Normal",
            "tone": "good" if hvac_active else "neutral",
            "state": "Régulation simulée",
            "last": measure,
            "icon": "hvac",
            "accent": "red",
        },
    ]


def equipment_rows(df: pd.DataFrame) -> list[dict[str, str]]:
    """Liste des équipements avec leur dernier horodatage simulé."""
    stamp = latest_timestamp(df)
    last = fmt.fr_datetime(stamp) if stamp is not None else "—"
    return [
        {
            "equipment": "Compteur intelligent",
            "type": "Compteur d'énergie",
            "state": "En ligne",
            "tone": "good",
            "last": last,
            "icon": "gauge",
        },
        {
            "equipment": "Onduleur PV",
            "type": "Onduleur solaire",
            "state": "En ligne",
            "tone": "good",
            "last": last,
            "icon": "sun",
        },
        {
            "equipment": "Capteur de température",
            "type": "Capteur IoT",
            "state": "En ligne",
            "tone": "good",
            "last": last,
            "icon": "thermometer",
        },
        {
            "equipment": "Capteur de présence",
            "type": "Capteur IoT",
            "state": "En ligne",
            "tone": "good",
            "last": last,
            "icon": "users",
        },
        {
            "equipment": "CVC / HVAC",
            "type": "Équipement du bâtiment",
            "state": "Actif",
            "tone": "info",
            "last": last,
            "icon": "hvac",
        },
        {
            "equipment": "Passerelle IoT",
            "type": "Passerelle de communication",
            "state": "Hors ligne",
            "tone": "bad",
            "last": "Non connectée · version future",
            "icon": "wifi-off",
        },
    ]


def energy_balance(kpis: dict[str, Any]) -> list[dict[str, str]]:
    """Cinq valeurs du bilan énergétique simplifié."""
    return [
        {
            "label": "Demande du bâtiment",
            "value": fmt.fr_number(kpis.get("consumption", 0), 0),
            "unit": "kWh",
            "accent": "blue",
            "icon": "building",
        },
        {
            "label": "Production solaire",
            "value": fmt.fr_number(kpis.get("solar", 0), 0),
            "unit": "kWh",
            "accent": "green",
            "icon": "sun",
        },
        {
            "label": "Solaire autoconsommé",
            "value": fmt.fr_number(kpis.get("self_consumed", 0), 0),
            "unit": "kWh",
            "accent": "green",
            "icon": "leaf",
        },
        {
            "label": "Import réseau",
            "value": fmt.fr_number(kpis.get("grid_import", 0), 0),
            "unit": "kWh",
            "accent": "sky",
            "icon": "grid",
        },
        {
            "label": "Surplus potentiel",
            "value": fmt.fr_number(kpis.get("surplus", 0), 0),
            "unit": "kWh",
            "accent": "amber",
            "icon": "trend-up",
        },
    ]


def estimated_cost(kpis: dict[str, Any], price_per_kwh: float) -> float | None:
    """Coût indicatif de l'énergie importée du réseau."""
    imported = kpis.get("grid_import")
    if imported is None or not np.isfinite(imported):
        return None
    return float(imported) * float(price_per_kwh)


# ---------------------------------------------------------------------------
# Délégation aux services canoniques
# ---------------------------------------------------------------------------
# Les fonctions numériques principales sont implémentées et testées une seule
# fois dans services/energy_calculations.py. Les alias ci-dessus gardent la
# compatibilité avec les vues historiques qui importent ``utils.calculations``.
_safe_divide = _energy.safe_divide
energy_kpis = _energy.energy_kpis
comparison = _energy.comparison
daily_summary = _energy.daily_summary
period_days = _energy.period_days
