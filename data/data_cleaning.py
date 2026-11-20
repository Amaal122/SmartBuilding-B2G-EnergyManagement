"""Nettoyage et standardisation génériques des séries temporelles.

Ces fonctions ne connaissent aucun jeu de données particulier : elles
prennent un DataFrame, un nom de colonne temporelle et des colonnes de
mesure, puis appliquent des règles explicites et testables.

Elles sont utilisées par :mod:`data.data_processing` avant l'assemblage du
scénario énergétique.
"""

from __future__ import annotations

from typing import Iterable, Sequence

import numpy as np
import pandas as pd

# Colonnes attendues après standardisation.
TIMESTAMP_COLUMN = "timestamp"
CONSUMPTION_COLUMN = "consumption_kwh"
SOLAR_COLUMN = "solar_production_kwh"


def standardize_column_names(
    df: pd.DataFrame, mapping: dict[str, str] | None = None
) -> pd.DataFrame:
    """Normalise les noms de colonnes en ``snake_case``.

    ``mapping`` permet de forcer des renommages métier explicites
    (par exemple ``meter_reading`` → ``consumption_kwh``).
    """
    if df is None or df.empty:
        return df.copy() if df is not None else pd.DataFrame()

    renamed = {}
    for column in df.columns:
        normalized = (
            str(column)
            .strip()
            .lower()
            .replace(" ", "_")
            .replace("-", "_")
            .replace("(", "")
            .replace(")", "")
        )
        renamed[column] = normalized

    work = df.rename(columns=renamed)
    if mapping:
        work = work.rename(columns=mapping)
    return work


def coerce_numeric(df: pd.DataFrame, columns: Iterable[str]) -> pd.DataFrame:
    """Convertit les colonnes demandées en nombres, sans lever d'exception."""
    work = df.copy()
    for column in columns:
        if column in work.columns:
            work[column] = pd.to_numeric(work[column], errors="coerce")
    return work


def clean_timeseries(
    df: pd.DataFrame,
    timestamp_col: str = TIMESTAMP_COLUMN,
    value_cols: Sequence[str] = (),
    *,
    clip_non_negative: bool = True,
    drop_invalid_timestamps: bool = True,
) -> pd.DataFrame:
    """Nettoyage de base d'une série temporelle.

    - conversion des horodatages et des mesures ;
    - suppression des lignes sans horodatage (ou sans mesure) ;
    - suppression des doublons d'horodatage (la dernière valeur gagne) ;
    - bornage optionnel à zéro pour les énergies et puissances.
    """
    if df is None or df.empty:
        return pd.DataFrame(columns=df.columns if df is not None else [])

    work = df.copy()
    if timestamp_col not in work.columns:
        raise KeyError(f"Colonne temporelle absente : {timestamp_col}")

    work[timestamp_col] = pd.to_datetime(work[timestamp_col], errors="coerce")
    if drop_invalid_timestamps:
        work = work.dropna(subset=[timestamp_col])

    work = coerce_numeric(work, value_cols)
    for column in value_cols:
        if column in work.columns and clip_non_negative:
            work[column] = work[column].clip(lower=0.0)

    work = (
        work.drop_duplicates(subset=[timestamp_col], keep="last")
        .sort_values(timestamp_col)
        .reset_index(drop=True)
    )
    return work


def reindex_hourly(
    df: pd.DataFrame,
    timestamp_col: str = TIMESTAMP_COLUMN,
    value_cols: Sequence[str] = (),
    *,
    start: pd.Timestamp | None = None,
    end: pd.Timestamp | None = None,
    fill_limit: int = 3,
) -> pd.DataFrame:
    """Réindexe une série sur un pas horaire régulier.

    Les trous courts (≤ ``fill_limit`` heures) sont interpolés linéairement,
    les trous longs restent à ``NaN`` afin d'être signalés dans les rapports
    de qualité plutôt que masqués.
    """
    if df is None or df.empty:
        return pd.DataFrame(columns=[timestamp_col, *value_cols])

    work = clean_timeseries(df, timestamp_col, value_cols)
    if work.empty:
        return work

    start = pd.Timestamp(start) if start is not None else work[timestamp_col].min()
    end = pd.Timestamp(end) if end is not None else work[timestamp_col].max()
    index = pd.date_range(start=start, end=end, freq="h")

    work = work.set_index(timestamp_col).reindex(index)
    work.index.name = timestamp_col
    for column in value_cols:
        if column in work.columns:
            work[column] = work[column].interpolate(
                method="time", limit=fill_limit, limit_direction="both"
            )
    return work.reset_index()


def split_outliers_iqr(
    series: pd.Series, factor: float = 1.5
) -> tuple[pd.Series, pd.Series]:
    """Retourne (masque de valeurs normales, masque de valeurs atypiques).

    Méthode de Tukey : ``[Q1 - factor·IQR ; Q3 + factor·IQR]``.
    """
    values = pd.to_numeric(series, errors="coerce")
    valid = values.dropna()
    if valid.empty:
        mask = pd.Series(False, index=series.index)
        return ~mask, mask
    q1, q3 = valid.quantile(0.25), valid.quantile(0.75)
    iqr = q3 - q1
    if not np.isfinite(iqr) or iqr <= 0:
        mask = pd.Series(False, index=series.index)
        return ~mask, mask
    low, high = q1 - factor * iqr, q3 + factor * iqr
    mask = (values < low) | (values > high)
    return ~mask.fillna(False), mask.fillna(False)


def quality_summary(
    df: pd.DataFrame,
    timestamp_col: str = TIMESTAMP_COLUMN,
    value_cols: Sequence[str] = (),
) -> dict[str, object]:
    """Résumé de qualité exploitable par la page Données & Configuration."""
    if df is None or df.empty:
        return {
            "rows": 0,
            "columns": 0,
            "missing_pct": None,
            "duplicate_timestamps": 0,
            "coverage_start": None,
            "coverage_end": None,
            "hours": 0,
            "expected_hours": 0,
            "completeness_pct": None,
            "frequency": "—",
        }

    rows = len(df)
    missing_pct = float(df.isna().mean().mean() * 100.0) if rows else 0.0
    duplicates = (
        int(df[timestamp_col].duplicated().sum())
        if timestamp_col in df.columns
        else 0
    )
    start = pd.Timestamp(df[timestamp_col].min()) if timestamp_col in df else None
    end = pd.Timestamp(df[timestamp_col].max()) if timestamp_col in df else None
    hours = int(len(df))
    expected = (
        int((end - start).total_seconds() // 3600) + 1
        if start is not None and end is not None
        else hours
    )
    completeness = 100.0 * hours / expected if expected > 0 else None

    frequency = "—"
    if timestamp_col in df.columns and hours >= 3:
        deltas = df[timestamp_col].diff().dropna().dt.total_seconds() / 60.0
        median = float(deltas.median()) if not deltas.empty else 0.0
        frequency = (
            "Horaire"
            if abs(median - 60.0) < 1.0
            else f"{median:.0f} min"
            if median > 0
            else "—"
        )

    return {
        "rows": rows,
        "columns": len(df.columns),
        "missing_pct": missing_pct,
        "duplicate_timestamps": duplicates,
        "coverage_start": start,
        "coverage_end": end,
        "hours": hours,
        "expected_hours": expected,
        "completeness_pct": completeness,
        "frequency": frequency,
    }


def missing_by_column(df: pd.DataFrame) -> pd.DataFrame:
    """Tableau des valeurs manquantes par colonne (page Données)."""
    if df is None or df.empty:
        return pd.DataFrame(columns=["Colonne", "Type", "Manquants", "Manquants (%)"])
    missing = df.isna().sum()
    return pd.DataFrame(
        {
            "Colonne": df.columns,
            "Type": [str(dtype) for dtype in df.dtypes],
            "Manquants": missing.to_numpy(),
            "Manquants (%)": (missing / len(df) * 100.0).round(2).to_numpy(),
        }
    )
