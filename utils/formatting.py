"""Fonctions de formatage francophone.

Toutes les valeurs affichées dans l'interface passent par ces helpers afin de
garantir une typographie cohérente (espace fine insécable, virgule décimale)
et une gestion uniforme des valeurs manquantes.
"""

from __future__ import annotations

import math
from datetime import date, datetime
from typing import Any

import pandas as pd

NBSP = "\u202f"  # espace fine insécable

MOIS_FR = [
    "janvier",
    "février",
    "mars",
    "avril",
    "mai",
    "juin",
    "juillet",
    "août",
    "septembre",
    "octobre",
    "novembre",
    "décembre",
]

MOIS_FR_COURT = [
    "janv.",
    "févr.",
    "mars",
    "avr.",
    "mai",
    "juin",
    "juil.",
    "août",
    "sept.",
    "oct.",
    "nov.",
    "déc.",
]

JOURS_FR = [
    "lundi",
    "mardi",
    "mercredi",
    "jeudi",
    "vendredi",
    "samedi",
    "dimanche",
]

JOURS_FR_COURT = ["lun.", "mar.", "mer.", "jeu.", "ven.", "sam.", "dim."]


def is_valid_number(value: Any) -> bool:
    """Retourne True si la valeur peut être affichée comme un nombre fini."""
    try:
        return value is not None and math.isfinite(float(value))
    except (TypeError, ValueError):
        return False


def fr_number(value: Any, decimals: int = 0, signed: bool = False) -> str:
    """Formate un nombre à la française : 12 345,6."""
    if not is_valid_number(value):
        return "—"
    formatted = f"{float(value):,.{decimals}f}"
    formatted = formatted.replace(",", "§").replace(".", ",").replace("§", NBSP)
    if signed and float(value) > 0:
        formatted = f"+{formatted}"
    return formatted


def fr_energy(kwh: Any, decimals: int = 0) -> str:
    """Formate une énergie en kWh ou MWh selon son ordre de grandeur."""
    if not is_valid_number(kwh):
        return "—"
    value = float(kwh)
    if abs(value) >= 1000:
        return f"{fr_number(value / 1000, 2)} MWh"
    return f"{fr_number(value, decimals)} kWh"


def fr_power(kw: Any, decimals: int = 1) -> str:
    """Formate une puissance en kW."""
    if not is_valid_number(kw):
        return "—"
    return f"{fr_number(kw, decimals)} kW"


def fr_pct(value: Any, decimals: int = 1) -> str:
    """Formate un pourcentage."""
    if not is_valid_number(value):
        return "—"
    return f"{fr_number(value, decimals)}{NBSP}%"


def fr_points(value: Any, decimals: int = 1) -> str:
    """Formate un écart en points de pourcentage."""
    if not is_valid_number(value):
        return "—"
    return f"{fr_number(value, decimals, signed=True)} pts"


def fr_delta(value: Any, decimals: int = 1) -> str:
    """Formate une variation relative en pourcentage signé."""
    if not is_valid_number(value):
        return "—"
    return f"{fr_number(value, decimals, signed=True)}{NBSP}%"


def _to_datetime(value: Any) -> datetime | None:
    if value is None:
        return None
    try:
        stamp = pd.Timestamp(value)
    except (TypeError, ValueError):
        return None
    if pd.isna(stamp):
        return None
    return stamp.to_pydatetime()


def fr_date(value: Any, long: bool = False) -> str:
    """Date française : « jeudi 19 novembre 2026 » ou « 19/11/2026 »."""
    stamp = _to_datetime(value)
    if stamp is None:
        return "—"
    if long:
        return (
            f"{JOURS_FR[stamp.weekday()]} {stamp.day} "
            f"{MOIS_FR[stamp.month - 1]} {stamp.year}"
        )
    return f"{stamp.day:02d}/{stamp.month:02d}/{stamp.year}"


def fr_date_short(value: Any) -> str:
    """Date courte pour les axes de graphiques : « 19 nov. »."""
    stamp = _to_datetime(value)
    if stamp is None:
        return "—"
    return f"{stamp.day} {MOIS_FR_COURT[stamp.month - 1]}"


def fr_time(value: Any, with_seconds: bool = False) -> str:
    """Heure locale : « 14:32 » (format 24 h)."""
    stamp = _to_datetime(value)
    if stamp is None:
        return "—"
    if with_seconds:
        return stamp.strftime("%H:%M:%S")
    return stamp.strftime("%H:%M")


def fr_datetime(value: Any, separator: str = " · ") -> str:
    """Horodatage complet français : « 19/11/2026 · 14:32 »."""
    stamp = _to_datetime(value)
    if stamp is None:
        return "—"
    return f"{fr_date(stamp)}{separator}{fr_time(stamp)}"


def fr_datetime_long(value: Any) -> str:
    """Horodatage long : « jeudi 19 novembre 2026 à 14:32 »."""
    stamp = _to_datetime(value)
    if stamp is None:
        return "—"
    return f"{fr_date(stamp, long=True)} à {fr_time(stamp)}"


def fr_relative_day(value: Any, reference: Any = None) -> str:
    """Libellé relatif simple pour les tableaux (« Aujourd'hui », « Hier »)."""
    stamp = _to_datetime(value)
    if stamp is None:
        return "—"
    ref = _to_datetime(reference) or datetime.now()
    delta_days = (ref.date() - stamp.date()).days
    if delta_days == 0:
        return "Aujourd'hui"
    if delta_days == 1:
        return "Hier"
    if delta_days == 2:
        return "Avant-hier"
    return fr_date(stamp)


def human_file_size(size_bytes: Any) -> str:
    """Taille de fichier lisible."""
    if not is_valid_number(size_bytes):
        return "—"
    size = float(size_bytes)
    for unit in ("o", "Ko", "Mo", "Go"):
        if size < 1024 or unit == "Go":
            return f"{fr_number(size, 1 if unit != 'o' else 0)} {unit}"
        size /= 1024
    return "—"


def to_date(value: Any) -> date:
    """Convertit une valeur en datetime.date, avec repli sur aujourd'hui."""
    stamp = _to_datetime(value)
    return stamp.date() if stamp else date.today()
