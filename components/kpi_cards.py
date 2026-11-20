"""Cartes KPI de la vue générale et des pages de surveillance."""

from __future__ import annotations

import html
import math
from typing import Any

import streamlit as st

from utils.icons import icon


ACCENTS: dict[str, tuple[str, str]] = {
    "blue": ("#2563EB", "#EFF6FF"),
    "sky": ("#0EA5E9", "#F0F9FF"),
    "green": ("#10B981", "#ECFDF5"),
    "mint": ("#14B8A6", "#F0FDFA"),
    "amber": ("#F59E0B", "#FFFBEB"),
    "red": ("#EF4444", "#FEF2F2"),
    "purple": ("#8B5CF6", "#F5F3FF"),
    "navy": ("#0B2545", "#F1F5F9"),
    "slate": ("#64748B", "#F8FAFC"),
}


def _rgba(hex_color: str, alpha: float) -> str:
    value = hex_color.lstrip("#")
    if len(value) != 6:
        return f"rgba(37, 99, 235, {alpha})"
    r, g, b = (int(value[i : i + 2], 16) for i in (0, 2, 4))
    return f"rgba({r}, {g}, {b}, {alpha})"


def sparkline(values: list[float] | None, color: str, width: int = 74, height: int = 28) -> str:
    """Mini-courbe SVG sans axes pour les cartes KPI."""
    if not values:
        return ""
    clean = [
        float(value)
        for value in values
        if value is not None and isinstance(value, (int, float)) and math.isfinite(float(value))
    ]
    if len(clean) < 2:
        return ""
    low, high = min(clean), max(clean)
    span = (high - low) or 1.0
    points = []
    for position, value in enumerate(clean):
        x = 2 + position * (width - 4) / (len(clean) - 1)
        y = height - 3 - (value - low) / span * (height - 6)
        points.append(f"{x:.1f},{y:.1f}")
    polyline = " ".join(points)
    polygon = f"2,{height - 1} {polyline} {width - 2},{height - 1}"
    last_x, last_y = points[-1].split(",")
    return (
        f'<svg class="kpi-spark" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" aria-hidden="true">'
        f'<polygon points="{polygon}" fill="{_rgba(color, 0.10)}" stroke="none"/>'
        f'<polyline points="{polyline}" fill="none" stroke="{color}" stroke-width="1.7" '
        f'stroke-linecap="round" stroke-linejoin="round"/>'
        f'<circle cx="{last_x}" cy="{last_y}" r="2" fill="{color}"/>'
        "</svg>"
    )


def kpi_grid(items: list[dict[str, Any]], columns: int = 6) -> None:
    """Affiche une grille de cartes KPI.

    Chaque élément accepte : label, value, unit, icon, accent, delta,
    delta_tone (good/bad/neutral), note, spark (liste de valeurs).
    """
    if not items:
        return

    cards = []
    for item in items:
        accent, soft = ACCENTS.get(str(item.get("accent", "blue")), ACCENTS["blue"])
        spark = item.get("spark")
        spark_svg = sparkline(
            spark if isinstance(spark, list) else None,
            str(item.get("spark_color", accent)),
        )
        unit_html = (
            f'<span class="kpi-unit">{html.escape(str(item["unit"]))}</span>'
            if item.get("unit")
            else ""
        )
        delta_html = ""
        if item.get("delta"):
            tone = str(item.get("delta_tone", "neutral"))
            delta_html = f'<span class="kpi-delta {tone}">{html.escape(str(item["delta"]))}</span>'
        note_html = (
            f'<span>{html.escape(str(item["note"]))}</span>'
            if item.get("note")
            else ""
        )
        icon_html = icon(str(item.get("icon", "activity")), size=16)
        cards.append(
            f"""
<div class="kpi-card" style="--accent:{accent};--accent-soft:{soft}">
  <div class="kpi-top">
    <div class="kpi-icon">{icon_html}</div>
    <div class="kpi-label">{html.escape(str(item.get("label", "")))}</div>
  </div>
  <div class="kpi-main">
    <div class="kpi-value">{html.escape(str(item.get("value", "—")))}{unit_html}</div>
    {spark_svg}
  </div>
  <div class="kpi-foot">{delta_html}{note_html}</div>
</div>
"""
        )

    grid_class = "" if columns == 6 else f" cols-{columns}"
    st.markdown(
        f'<div class="kpi-grid{grid_class}">{"".join(cards)}</div>',
        unsafe_allow_html=True,
    )
