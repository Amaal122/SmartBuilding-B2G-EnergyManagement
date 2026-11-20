"""Graphiques Plotly de SBEMS.

Toutes les figures partagent la même mise en forme (grille discrète, légende
haute, infobulles unifiées, séparateurs français) afin de produire un rendu
cohérent de type plateforme industrielle.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
import plotly.graph_objects as go

import streamlit as st

from utils.theme import (
    AMBER,
    BLUE,
    BLUE_DARK,
    END_USE_COLORS,
    FONT_STACK,
    GREEN,
    GREEN_DARK,
    GRID,
    MINT,
    NAVY,
    RED,
    SKY,
    SLATE,
    SLATE_LIGHT,
    ZONE_COLORS,
)

PLOTLY_CONFIG: dict[str, Any] = {
    "displayModeBar": False,
    "responsive": True,
    "scrollZoom": False,
}


def hex_to_rgba(hex_color: str, alpha: float) -> str:
    value = hex_color.lstrip("#")
    if len(value) != 6:
        return f"rgba(37, 99, 235, {alpha})"
    r, g, b = (int(value[i : i + 2], 16) for i in (0, 2, 4))
    return f"rgba({r}, {g}, {b}, {alpha})"


def render_chart(fig: go.Figure, key: str | None = None) -> None:
    """Affiche une figure en pleine largeur, sans barre d'outils."""
    try:
        st.plotly_chart(fig, width="stretch", config=PLOTLY_CONFIG, key=key)
    except TypeError:  # compatibilité Streamlit < 1.49
        st.plotly_chart(fig, use_container_width=True, config=PLOTLY_CONFIG, key=key)


def _time_axis(fig: go.Figure, df: pd.DataFrame) -> None:
    """Adapte le format de l'axe temporel à la fenêtre affichée."""
    if df is None or df.empty or "timestamp" not in df:
        return
    span = pd.Timestamp(df["timestamp"].max()) - pd.Timestamp(df["timestamp"].min())
    tickformat = "%H:%M" if span <= pd.Timedelta(days=2) else "%d/%m"
    fig.update_xaxes(
        tickformat=tickformat,
        nticks=9,
        hoverformat="%d/%m/%Y · %H:%M",
    )


def _layout(
    fig: go.Figure,
    height: int = 320,
    show_legend: bool = True,
    y_title: str | None = None,
    x_title: str | None = None,
    margin_top: int | None = None,
) -> go.Figure:
    top = margin_top if margin_top is not None else (34 if show_legend else 14)
    fig.update_layout(
        template="plotly_white",
        height=height,
        margin=dict(l=10, r=12, t=top, b=12),
        font=dict(family=FONT_STACK, size=11.5, color="#5B6B82"),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        colorway=[BLUE, GREEN, AMBER, SLATE, SKY],
        hoverlabel=dict(
            bgcolor=NAVY,
            bordercolor=NAVY,
            font=dict(color="#FFFFFF", size=11.5, family=FONT_STACK),
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            x=0,
            xanchor="left",
            font=dict(size=10.5, color="#5B6B82"),
            bgcolor="rgba(0,0,0,0)",
            itemclick="toggle",
            itemdoubleclick="toggleothers",
        ),
        showlegend=show_legend,
        hovermode="x unified",
        separators=", ",
        xaxis=dict(
            showgrid=False,
            zeroline=False,
            linecolor="#E6EBF3",
            ticks="outside",
            tickcolor="#E6EBF3",
            tickfont=dict(size=10.5),
        ),
        yaxis=dict(
            gridcolor=GRID,
            gridwidth=1,
            zeroline=False,
            linecolor="rgba(0,0,0,0)",
            tickfont=dict(size=10.5),
        ),
        yaxis_title=y_title,
    )
    if x_title:
        fig.update_xaxes(title=dict(text=x_title, font=dict(size=10.5)))
    fig.update_yaxes(title=dict(font=dict(size=10.5)))
    return fig


def empty_figure(message: str = "Aucune donnée sur la période sélectionnée.") -> go.Figure:
    fig = go.Figure()
    fig.update_layout(
        height=280,
        margin=dict(l=10, r=10, t=10, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
        annotations=[
            dict(
                text=message,
                x=0.5,
                y=0.5,
                xref="paper",
                yref="paper",
                showarrow=False,
                font=dict(size=12, color="#94A3B8", family=FONT_STACK),
            )
        ],
    )
    return fig


# ---------------------------------------------------------------------------
# Vue générale
# ---------------------------------------------------------------------------
def fig_consumption_vs_solar(df: pd.DataFrame) -> go.Figure:
    if df is None or df.empty:
        return empty_figure()
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=df["timestamp"],
            y=df["solar_production_kwh"],
            name="Production solaire",
            mode="lines",
            line=dict(color=GREEN, width=2.4, shape="spline", smoothing=0.45),
            fill="tozeroy",
            fillcolor=hex_to_rgba(GREEN, 0.12),
            hovertemplate="Production : %{y:.1f} kWh<extra></extra>",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=df["timestamp"],
            y=df["consumption_kwh"],
            name="Consommation du bâtiment",
            mode="lines",
            line=dict(color=BLUE, width=2.2, shape="spline", smoothing=0.4),
            hovertemplate="Consommation : %{y:.1f} kWh<extra></extra>",
        )
    )
    _layout(fig, height=330, y_title="Énergie horaire (kWh)")
    _time_axis(fig, df)
    return fig


def fig_consumption_area(end_use_df: pd.DataFrame) -> go.Figure:
    if end_use_df is None or end_use_df.empty:
        return empty_figure()
    pivot = (
        end_use_df.pivot_table(
            index="timestamp", columns="usage", values="consumption_kwh", aggfunc="sum"
        )
        .fillna(0.0)
        .sort_index()
    )
    fig = go.Figure()
    for position, usage in enumerate(pivot.columns):
        color = END_USE_COLORS[position % len(END_USE_COLORS)]
        fig.add_trace(
            go.Scatter(
                x=pivot.index,
                y=pivot[usage],
                name=str(usage),
                mode="lines",
                line=dict(width=0.7, color=color, shape="spline", smoothing=0.4),
                stackgroup="one",
                fillcolor=hex_to_rgba(color, 0.7),
                hovertemplate=f"{usage} : %{{y:.1f}} kWh<extra></extra>",
            )
        )
    _layout(fig, height=320, y_title="Énergie horaire (kWh)")
    _time_axis(fig, end_use_df)
    return fig


def fig_energy_sources_donut(kpis: dict[str, Any]) -> go.Figure:
    self_consumed = max(0.0, float(kpis.get("self_consumed") or 0.0))
    grid_import = max(0.0, float(kpis.get("grid_import") or 0.0))
    total = self_consumed + grid_import
    if total <= 0:
        return empty_figure("Aucune énergie consommée sur la période.")

    renewable = self_consumed / total * 100.0
    fig = go.Figure(
        go.Pie(
            labels=["Solaire autoconsommée", "Réseau électrique"],
            values=[self_consumed, grid_import],
            hole=0.66,
            marker=dict(
                colors=[GREEN, BLUE],
                line=dict(color="#FFFFFF", width=2),
            ),
            textinfo="none",
            sort=False,
            hovertemplate="%{label}<br>%{value:,.0f} kWh · %{percent}<extra></extra>",
        )
    )
    fig.update_layout(
        template="plotly_white",
        height=310,
        margin=dict(l=8, r=8, t=26, b=30),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family=FONT_STACK, size=11, color="#5B6B82"),
        separators=", ",
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=-0.08,
            x=0.5,
            xanchor="center",
            font=dict(size=10.5),
        ),
        hoverlabel=dict(
            bgcolor=NAVY,
            font=dict(color="#FFFFFF", size=11.5, family=FONT_STACK),
        ),
        annotations=[
            dict(
                text=(
                    f"<span style='font-size:20px;font-weight:800;color:{NAVY}'>"
                    f"{total:,.0f}</span>"
                    f"<br><span style='font-size:10px;color:#64748B'>kWh couverts</span>"
                    f"<br><span style='font-size:10.5px;font-weight:700;color:{GREEN_DARK}'>"
                    f"{renewable:.0f} % renouvelable</span>"
                ).replace(",", "\u202f"),
                x=0.5,
                y=0.5,
                showarrow=False,
                font=dict(family=FONT_STACK),
                align="center",
            )
        ],
    )
    return fig


def fig_daily_consumption(daily: pd.DataFrame) -> go.Figure:
    if daily is None or daily.empty:
        return empty_figure()
    values = daily["consumption_kwh"].to_numpy(dtype=float)
    max_index = int(np.argmax(values))
    colors = [BLUE if i != max_index else AMBER for i in range(len(values))]
    labels = [f"{v:,.0f}".replace(",", "\u202f") for v in values]
    fig = go.Figure(
        go.Bar(
            x=daily["date"],
            y=values,
            marker=dict(color=colors, line=dict(width=0)),
            text=labels if len(values) <= 14 else None,
            textposition="outside",
            textfont=dict(size=9.5, color="#64748B"),
            cliponaxis=False,
            hovertemplate="%{y:.0f} kWh<extra></extra>",
            name="Consommation",
        )
    )
    _layout(fig, height=310, show_legend=False, y_title="Énergie journalière (kWh)")
    fig.update_xaxes(tickformat="%d/%m", nticks=10)
    return fig


# ---------------------------------------------------------------------------
# Surveillance énergétique
# ---------------------------------------------------------------------------
def fig_hourly_consumption(df: pd.DataFrame) -> go.Figure:
    if df is None or df.empty:
        return empty_figure()
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=df["timestamp"],
            y=df["consumption_kwh"],
            name="Consommation horaire",
            mode="lines",
            line=dict(color=BLUE, width=2.1, shape="spline", smoothing=0.35),
            fill="tozeroy",
            fillcolor=hex_to_rgba(BLUE, 0.09),
            hovertemplate="%{y:.1f} kWh<extra></extra>",
        )
    )
    average = float(df["consumption_kwh"].mean())
    fig.add_hline(
        y=average,
        line=dict(color=AMBER, width=1.2, dash="dash"),
        annotation_text=f"Moyenne {average:.0f} kWh/h".replace(".", ","),
        annotation_position="top right",
        annotation_font=dict(size=9.5, color="#B45309"),
    )
    _layout(fig, height=330, show_legend=False, y_title="Énergie horaire (kWh)")
    _time_axis(fig, df)
    return fig


def fig_peak_demand(daily: pd.DataFrame, threshold: float) -> go.Figure:
    if daily is None or daily.empty:
        return empty_figure()
    peaks = daily["peak_power_kw"].to_numpy(dtype=float)
    colors = [RED if value >= threshold else BLUE for value in peaks]
    labels = [f"{v:,.0f}".replace(",", "\u202f") for v in peaks]
    fig = go.Figure(
        go.Bar(
            x=daily["date"],
            y=peaks,
            marker=dict(color=colors, line=dict(width=0)),
            text=labels if len(peaks) <= 14 else None,
            textposition="outside",
            textfont=dict(size=9.5, color="#64748B"),
            cliponaxis=False,
            hovertemplate="Pointe : %{y:.1f} kW<extra></extra>",
            name="Pointe journalière",
        )
    )
    fig.add_hline(
        y=threshold,
        line=dict(color=AMBER, width=1.4, dash="dash"),
        annotation_text=f"Seuil simulé {threshold:.0f} kW".replace(".", ","),
        annotation_position="top left",
        annotation_font=dict(size=9.5, color="#B45309"),
    )
    _layout(fig, height=310, show_legend=False, y_title="Puissance de pointe (kW)")
    fig.update_xaxes(tickformat="%d/%m", nticks=10)
    return fig


def fig_zone_distribution(zone_summary_df: pd.DataFrame) -> go.Figure:
    if zone_summary_df is None or zone_summary_df.empty:
        return empty_figure()
    data = zone_summary_df.sort_values("consumption_kwh", ascending=True)
    colors = [ZONE_COLORS[i % len(ZONE_COLORS)] for i in range(len(data))]
    fig = go.Figure(
        go.Bar(
            x=data["consumption_kwh"],
            y=data["zone"],
            orientation="h",
            marker=dict(color=colors, line=dict(width=0)),
            text=[f"{v:,.0f} kWh" for v in data["consumption_kwh"]],
            textposition="outside",
            textfont=dict(size=10, color="#475569"),
            cliponaxis=False,
            customdata=np.stack([data["share_pct"]], axis=-1),
            hovertemplate=(
                "%{y}<br>%{x:,.0f} kWh · %{customdata[0]:.1f} % du total<extra></extra>"
            ),
        )
    )
    _layout(fig, height=300, show_legend=False)
    fig.update_xaxes(title=dict(text="Énergie (kWh)", font=dict(size=10.5)))
    fig.update_yaxes(tickfont=dict(size=10.5), gridcolor="rgba(0,0,0,0)")
    fig.update_layout(margin=dict(l=10, r=60, t=12, b=12))
    return fig


# ---------------------------------------------------------------------------
# Production photovoltaïque
# ---------------------------------------------------------------------------
def fig_solar_power(df: pd.DataFrame) -> go.Figure:
    if df is None or df.empty:
        return empty_figure()
    fig = go.Figure(
        go.Scatter(
            x=df["timestamp"],
            y=df["solar_production_kwh"],
            name="Production PV",
            mode="lines",
            line=dict(color=GREEN, width=2.5, shape="spline", smoothing=0.45),
            fill="tozeroy",
            fillcolor=hex_to_rgba(GREEN, 0.14),
            hovertemplate="Puissance PV : %{y:.1f} kW<extra></extra>",
        )
    )
    _layout(fig, height=330, show_legend=False, y_title="Puissance moyenne horaire (kW)")
    _time_axis(fig, df)
    return fig


def fig_daily_solar(daily: pd.DataFrame) -> go.Figure:
    if daily is None or daily.empty:
        return empty_figure()
    values = daily["solar_production_kwh"].to_numpy(dtype=float)
    labels = [f"{v:,.0f}".replace(",", "\u202f") for v in values]
    fig = go.Figure(
        go.Bar(
            x=daily["date"],
            y=values,
            marker=dict(color=GREEN, line=dict(width=0)),
            text=labels if len(values) <= 14 else None,
            textposition="outside",
            textfont=dict(size=9.5, color="#64748B"),
            cliponaxis=False,
            hovertemplate="%{y:.0f} kWh<extra></extra>",
            name="Production PV",
        )
    )
    _layout(fig, height=300, show_legend=False, y_title="Énergie journalière (kWh)")
    fig.update_xaxes(tickformat="%d/%m", nticks=10)
    return fig


def fig_solar_vs_consumption(df: pd.DataFrame) -> go.Figure:
    if df is None or df.empty:
        return empty_figure()
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=df["timestamp"],
            y=df["solar_production_kwh"],
            name="Production solaire",
            mode="lines",
            line=dict(color=GREEN, width=2.2, shape="spline", smoothing=0.4),
            fill="tozeroy",
            fillcolor=hex_to_rgba(GREEN, 0.10),
            hovertemplate="PV : %{y:.1f} kWh<extra></extra>",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=df["timestamp"],
            y=df["consumption_kwh"],
            name="Consommation",
            mode="lines",
            line=dict(color=BLUE, width=2.0, shape="spline", smoothing=0.4),
            hovertemplate="Consommation : %{y:.1f} kWh<extra></extra>",
        )
    )
    _layout(fig, height=300, y_title="Énergie horaire (kWh)")
    _time_axis(fig, df)
    return fig


def fig_solar_period_donut(df: pd.DataFrame) -> go.Figure:
    if df is None or df.empty:
        return empty_figure()
    hours = df["timestamp"].dt.hour
    periods = [
        ("Matin · 7–10 h", (hours >= 7) & (hours < 10)),
        ("Milieu de journée · 10–14 h", (hours >= 10) & (hours < 14)),
        ("Après-midi · 14–18 h", (hours >= 14) & (hours < 18)),
        ("Soirée · 18–21 h", (hours >= 18) & (hours < 21)),
    ]
    labels, values = [], []
    for label, mask in periods:
        value = float(df.loc[mask, "solar_production_kwh"].sum())
        if value > 0:
            labels.append(label)
            values.append(value)
    total = sum(values)
    if total <= 0:
        return empty_figure("Aucune production solaire sur la période.")

    greens = ["#A7F3D0", "#6EE7B7", "#34D399", GREEN]
    fig = go.Figure(
        go.Pie(
            labels=labels,
            values=values,
            hole=0.66,
            marker=dict(
                colors=greens[: len(values)],
                line=dict(color="#FFFFFF", width=2),
            ),
            textinfo="none",
            sort=False,
            hovertemplate="%{label}<br>%{value:,.0f} kWh · %{percent}<extra></extra>",
        )
    )
    fig.update_layout(
        template="plotly_white",
        height=310,
        margin=dict(l=8, r=8, t=26, b=30),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family=FONT_STACK, size=11, color="#5B6B82"),
        separators=", ",
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=-0.10,
            x=0.5,
            xanchor="center",
            font=dict(size=10),
        ),
        hoverlabel=dict(
            bgcolor=NAVY,
            font=dict(color="#FFFFFF", size=11.5, family=FONT_STACK),
        ),
        annotations=[
            dict(
                text=(
                    f"<span style='font-size:20px;font-weight:800;color:{NAVY}'>"
                    f"{total:,.0f}</span>"
                    "<br><span style='font-size:10px;color:#64748B'>kWh produits</span>"
                ).replace(",", "\u202f"),
                x=0.5,
                y=0.5,
                showarrow=False,
                font=dict(family=FONT_STACK),
                align="center",
            )
        ],
    )
    return fig


# ---------------------------------------------------------------------------
# Batterie et réseau
# ---------------------------------------------------------------------------
def fig_soc_evolution(df: pd.DataFrame) -> go.Figure:
    if df is None or df.empty:
        return empty_figure()
    fig = go.Figure()
    fig.add_hrect(
        y0=20,
        y1=90,
        fillcolor=hex_to_rgba(GREEN, 0.05),
        line_width=0,
        layer="below",
    )
    fig.add_trace(
        go.Scatter(
            x=df["timestamp"],
            y=df["battery_soc"],
            name="SOC batterie",
            mode="lines",
            line=dict(color=AMBER, width=2.3, shape="spline", smoothing=0.4),
            fill="tozeroy",
            fillcolor=hex_to_rgba(AMBER, 0.09),
            hovertemplate="SOC : %{y:.1f} %<extra></extra>",
        )
    )
    fig.add_hline(
        y=20,
        line=dict(color=RED, width=1, dash="dot"),
        annotation_text="Seuil bas simulé · 20 %",
        annotation_position="bottom left",
        annotation_font=dict(size=9, color="#B91C1C"),
    )
    fig.add_hline(
        y=90,
        line=dict(color=GREEN, width=1, dash="dot"),
        annotation_text="Plage haute · 90 %",
        annotation_position="top left",
        annotation_font=dict(size=9, color=GREEN_DARK),
    )
    _layout(fig, height=320, show_legend=False, y_title="État de charge (%)")
    fig.update_yaxes(range=[0, 100], ticksuffix=" %")
    _time_axis(fig, df)
    return fig


def fig_grid_exchanges(df: pd.DataFrame) -> go.Figure:
    if df is None or df.empty:
        return empty_figure()
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=df["timestamp"],
            y=df["grid_import_kwh"],
            name="Import réseau",
            mode="lines",
            line=dict(color=BLUE, width=1.9, shape="spline", smoothing=0.35),
            fill="tozeroy",
            fillcolor=hex_to_rgba(BLUE, 0.10),
            hovertemplate="Import : %{y:.1f} kWh<extra></extra>",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=df["timestamp"],
            y=df["grid_export_kwh"],
            name="Surplus PV (potentiel)",
            mode="lines",
            line=dict(color=GREEN, width=1.9, shape="spline", smoothing=0.35),
            fill="tozeroy",
            fillcolor=hex_to_rgba(GREEN, 0.12),
            hovertemplate="Surplus : %{y:.1f} kWh<extra></extra>",
        )
    )
    _layout(fig, height=310, y_title="Énergie horaire (kWh)")
    _time_axis(fig, df)
    return fig


def fig_sankey_balance(kpis: dict[str, Any]) -> go.Figure:
    solar_self = max(0.0, float(kpis.get("self_consumed") or 0.0))
    solar_export = max(0.0, float(kpis.get("surplus") or 0.0))
    grid_import = max(0.0, float(kpis.get("grid_import") or 0.0))
    total_solar = solar_self + solar_export
    if total_solar + grid_import <= 0:
        return empty_figure("Bilan indisponible sur la période.")

    labels = [
        "Production solaire",
        "Import réseau",
        "Bâtiment",
        "Surplus potentiel",
    ]
    node_colors = [GREEN, BLUE, NAVY, MINT]
    sources = [0, 0, 1]
    targets = [2, 3, 2]
    values = [solar_self, solar_export, grid_import]
    link_colors = [
        hex_to_rgba(GREEN, 0.38),
        hex_to_rgba(MINT, 0.32),
        hex_to_rgba(BLUE, 0.32),
    ]

    fig = go.Figure(
        go.Sankey(
            arrangement="snap",
            node=dict(
                pad=18,
                thickness=17,
                line=dict(color="#FFFFFF", width=1.5),
                label=labels,
                color=node_colors,
                hovertemplate="%{label}<br>%{value:,.0f} kWh<extra></extra>",
            ),
            link=dict(
                source=sources,
                target=targets,
                value=values,
                color=link_colors,
                hovertemplate="%{source.label} → %{target.label}<br>%{value:,.0f} kWh<extra></extra>",
            ),
            textfont=dict(family=FONT_STACK, size=11, color=NAVY),
        )
    )
    fig.update_layout(
        height=300,
        margin=dict(l=10, r=10, t=12, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family=FONT_STACK, size=11, color=NAVY),
        separators=", ",
        hoverlabel=dict(
            bgcolor=NAVY,
            font=dict(color="#FFFFFF", size=11.5, family=FONT_STACK),
        ),
    )
    return fig


def fig_balance_comparison(daily: pd.DataFrame) -> go.Figure:
    if daily is None or daily.empty:
        return empty_figure()
    fig = go.Figure()
    series = [
        ("Consommation", "consumption_kwh", BLUE),
        ("Production PV", "solar_production_kwh", GREEN),
        ("Import réseau", "grid_import_kwh", SKY),
        ("Surplus PV", "grid_export_kwh", MINT),
    ]
    for name, column, color in series:
        fig.add_trace(
            go.Bar(
                x=daily["date"],
                y=daily[column],
                name=name,
                marker=dict(color=color, line=dict(width=0)),
                hovertemplate=f"{name} : %{{y:.0f}} kWh<extra></extra>",
            )
        )
    _layout(fig, height=330, y_title="Énergie journalière (kWh)")
    fig.update_layout(barmode="group", bargap=0.22, bargroupgap=0.06)
    fig.update_xaxes(tickformat="%d/%m", nticks=10)
    return fig


def fig_battery_flows(daily: pd.DataFrame) -> go.Figure:
    if daily is None or daily.empty:
        return empty_figure()
    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=daily["date"],
            y=daily["battery_charge_kwh"],
            name="Charge simulée",
            marker=dict(color=AMBER, line=dict(width=0)),
            hovertemplate="Charge : %{y:.0f} kWh<extra></extra>",
        )
    )
    fig.add_trace(
        go.Bar(
            x=daily["date"],
            y=daily["battery_discharge_kwh"],
            name="Décharge simulée",
            marker=dict(color=SLATE_LIGHT, line=dict(width=0)),
            hovertemplate="Décharge : %{y:.0f} kWh<extra></extra>",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=daily["date"],
            y=daily["soc_mean"],
            name="SOC moyen",
            mode="lines+markers",
            line=dict(color=NAVY, width=2, dash="dot"),
            marker=dict(size=5, color=NAVY),
            yaxis="y2",
            hovertemplate="SOC moyen : %{y:.0f} %<extra></extra>",
        )
    )
    _layout(fig, height=320, y_title="Énergie journalière (kWh)")
    fig.update_layout(
        barmode="group",
        bargap=0.25,
        bargroupgap=0.08,
        yaxis2=dict(
            title=dict(text="SOC moyen (%)", font=dict(size=10.5)),
            overlaying="y",
            side="right",
            range=[0, 100],
            showgrid=False,
            ticksuffix=" %",
            tickfont=dict(size=10),
        ),
    )
    fig.update_xaxes(tickformat="%d/%m", nticks=10)
    return fig


# ---------------------------------------------------------------------------
# Environnement
# ---------------------------------------------------------------------------
def fig_temperature_trend(df: pd.DataFrame) -> go.Figure:
    if df is None or df.empty:
        return empty_figure()
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=df["timestamp"],
            y=df["temperature_indoor"],
            name="Intérieure",
            mode="lines",
            line=dict(color=BLUE, width=2.2, shape="spline", smoothing=0.4),
            hovertemplate="Intérieur : %{y:.1f} °C<extra></extra>",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=df["timestamp"],
            y=df["temperature_outdoor"],
            name="Extérieure",
            mode="lines",
            line=dict(color=SKY, width=2, dash="dot", shape="spline", smoothing=0.4),
            hovertemplate="Extérieur : %{y:.1f} °C<extra></extra>",
        )
    )
    _layout(fig, height=300, y_title="Température (°C)")
    fig.layout.yaxis.ticksuffix = " °C"
    _time_axis(fig, df)
    return fig


def fig_occupancy(df: pd.DataFrame) -> go.Figure:
    if df is None or df.empty:
        return empty_figure()
    fig = go.Figure(
        go.Scatter(
            x=df["timestamp"],
            y=df["occupancy"],
            name="Occupation",
            mode="lines",
            line=dict(color="#8B5CF6", width=1.9, shape="spline", smoothing=0.35),
            fill="tozeroy",
            fillcolor=hex_to_rgba("#8B5CF6", 0.13),
            hovertemplate="Occupation : %{y:.0f} pers.<extra></extra>",
        )
    )
    _layout(fig, height=300, show_legend=False, y_title="Personnes estimées")
    fig.update_yaxes(rangemode="tozero")
    _time_axis(fig, df)
    return fig


# ---------------------------------------------------------------------------
# Graphiques ajoutés pour les données réelles et la simulation batterie
# ---------------------------------------------------------------------------
def fig_hourly_profile(profile: pd.DataFrame) -> go.Figure:
    """Profil moyen par heure de la journée (consommation et PV)."""
    if profile is None or profile.empty:
        return empty_figure()
    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=profile["hour"],
            y=profile["consumption_kwh"],
            name="Consommation moyenne",
            marker=dict(color=hex_to_rgba(BLUE, 0.75), line=dict(width=0)),
            hovertemplate="%{x} h · consommation : %{y:.1f} kWh<extra></extra>",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=profile["hour"],
            y=profile["solar_production_kwh"],
            name="Production PV moyenne",
            mode="lines+markers",
            line=dict(color=GREEN, width=2.4),
            marker=dict(size=5, color=GREEN),
            hovertemplate="%{x} h · PV : %{y:.1f} kWh<extra></extra>",
        )
    )
    _layout(fig, height=300, y_title="Énergie moyenne (kWh)")
    fig.update_xaxes(
        title=dict(text="Heure de la journée", font=dict(size=10.5)),
        tickmode="linear",
        dtick=2,
    )
    return fig


def fig_building_comparison(comparison: pd.DataFrame) -> go.Figure:
    """Consommation journalière réelle de plusieurs bâtiments ASHRAE."""
    if comparison is None or comparison.empty:
        return empty_figure("Aucun bâtiment sélectionné.")
    work = comparison.copy()
    work["timestamp"] = pd.to_datetime(work["timestamp"])
    work["date"] = work["timestamp"].dt.normalize()
    daily = (
        work.groupby(["date", "building_id"], as_index=False)["consumption_kwh"]
        .sum()
        .sort_values("date")
    )
    fig = go.Figure()
    for building_id, group in daily.groupby("building_id"):
        fig.add_trace(
            go.Scatter(
                x=group["date"],
                y=group["consumption_kwh"],
                name=f"Bâtiment {int(building_id)}",
                mode="lines+markers",
                line=dict(width=1.8),
                marker=dict(size=4),
                hovertemplate=(
                    f"Bâtiment {int(building_id)}<br>%{{x|%d/%m/%Y}}"
                    " · %{y:,.0f} kWh<extra></extra>"
                ),
            )
        )
    _layout(fig, height=330, y_title="Consommation journalière (kWh)")
    fig.update_xaxes(tickformat="%d/%m", nticks=10)
    return fig


def fig_anomalies(
    df: pd.DataFrame, anomalies: pd.DataFrame, thresholds: dict[str, float | None]
) -> go.Figure:
    """Série de consommation avec points atypiques et bornes ±3σ."""
    if df is None or df.empty:
        return empty_figure()
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=df["timestamp"],
            y=df["consumption_kwh"],
            name="Consommation réelle",
            mode="lines",
            line=dict(color=BLUE, width=1.7),
            hovertemplate="%{y:.1f} kWh<extra></extra>",
        )
    )
    for key, color, label in (
        ("high", RED, "Seuil haut (+3σ)"),
        ("low", SKY, "Seuil bas (−3σ)"),
    ):
        value = thresholds.get(key)
        if value is not None and np.isfinite(value):
            fig.add_hline(
                y=value,
                line=dict(color=color, width=1.1, dash="dash"),
                annotation_text=label,
                annotation_position="top left",
                annotation_font=dict(size=9, color=color),
            )
    if anomalies is not None and not anomalies.empty:
        hourly = anomalies[anomalies["scale"] == "Horaire"]
        if not hourly.empty:
            colors = [
                RED if severity == "Critique" else AMBER
                for severity in hourly["severity"]
            ]
            fig.add_trace(
                go.Scatter(
                    x=hourly["timestamp"],
                    y=hourly["value"],
                    name="Valeur atypique",
                    mode="markers",
                    marker=dict(color=colors, size=9, line=dict(color="#FFFFFF", width=1.5)),
                    customdata=np.stack(
                        [hourly["zscore"], hourly["direction"]], axis=-1
                    ),
                    hovertemplate=(
                        "%{x|%d/%m/%Y %H:%M}<br>%{y:.1f} kWh"
                        "<br>Score Z : %{customdata[0]:.2f} (%{customdata[1]})"
                        "<extra></extra>"
                    ),
                )
            )
    _layout(fig, height=330, y_title="Consommation horaire (kWh)")
    _time_axis(fig, df)
    return fig


def fig_weather_overview(df: pd.DataFrame) -> go.Figure:
    """Température extérieure réelle et irradiation PV sur deux axes."""
    if df is None or df.empty:
        return empty_figure()
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=df["timestamp"],
            y=df["temperature_outdoor"],
            name="Température extérieure (site ASHRAE)",
            mode="lines",
            line=dict(color=SKY, width=2.1),
            hovertemplate="%{y:.1f} °C<extra></extra>",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=df["timestamp"],
            y=df["irradiation"],
            name="Irradiation (centrale PV)",
            mode="lines",
            line=dict(color=AMBER, width=1.4),
            yaxis="y2",
            hovertemplate="%{y:.0f} W/m²<extra></extra>",
        )
    )
    _layout(fig, height=300, y_title="Température (°C)")
    fig.update_layout(
        yaxis2=dict(
            title=dict(text="Irradiation (W/m²)", font=dict(size=10.5)),
            overlaying="y",
            side="right",
            showgrid=False,
            tickfont=dict(size=10),
        )
    )
    fig.update_yaxes(ticksuffix=" °C")
    _time_axis(fig, df)
    return fig


def fig_dispatch_comparison(before: pd.DataFrame, after: pd.DataFrame) -> go.Figure:
    """Comparaison A/B des imports réseau (scénarios sans / avec batterie)."""
    if before is None or after is None or before.empty or after.empty:
        return empty_figure()
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=before["timestamp"],
            y=before["grid_import_kwh"],
            name="Scénario A · sans batterie",
            mode="lines",
            line=dict(color=SLATE, width=1.6, dash="dot"),
            hovertemplate="Import A : %{y:.1f} kWh<extra></extra>",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=after["timestamp"],
            y=after["grid_import_kwh"],
            name="Scénario B · avec batterie",
            mode="lines",
            line=dict(color=BLUE, width=2.0),
            fill="tozeroy",
            fillcolor=hex_to_rgba(BLUE, 0.08),
            hovertemplate="Import B : %{y:.1f} kWh<extra></extra>",
        )
    )
    _layout(fig, height=320, y_title="Import réseau horaire (kWh)")
    _time_axis(fig, before)
    return fig


def fig_export_comparison(before: pd.DataFrame, after: pd.DataFrame) -> go.Figure:
    """Comparaison A/B des surplus exportés."""
    if before is None or after is None or before.empty or after.empty:
        return empty_figure()
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=before["timestamp"],
            y=before["grid_export_kwh"],
            name="Scénario A · sans batterie",
            mode="lines",
            line=dict(color=MINT, width=1.5, dash="dot"),
            hovertemplate="Export A : %{y:.1f} kWh<extra></extra>",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=after["timestamp"],
            y=after["grid_export_kwh"],
            name="Scénario B · avec batterie",
            mode="lines",
            line=dict(color=GREEN, width=2.0),
            fill="tozeroy",
            fillcolor=hex_to_rgba(GREEN, 0.10),
            hovertemplate="Export B : %{y:.1f} kWh<extra></extra>",
        )
    )
    _layout(fig, height=300, y_title="Surplus exporté horaire (kWh)")
    _time_axis(fig, before)
    return fig


def fig_battery_dispatch(result: pd.DataFrame) -> go.Figure:
    """Charge / décharge et SOC sur la fenêtre simulée."""
    if result is None or result.empty:
        return empty_figure()
    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=result["timestamp"],
            y=result["battery_charge_kwh"],
            name="Charge (simulée)",
            marker=dict(color=hex_to_rgba(GREEN, 0.75), line=dict(width=0)),
            hovertemplate="Charge : %{y:.2f} kWh<extra></extra>",
        )
    )
    fig.add_trace(
        go.Bar(
            x=result["timestamp"],
            y=-result["battery_discharge_kwh"],
            name="Décharge (simulée)",
            marker=dict(color=hex_to_rgba(AMBER, 0.85), line=dict(width=0)),
            hovertemplate="Décharge : %{y:.2f} kWh<extra></extra>",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=result["timestamp"],
            y=result["battery_soc"],
            name="SOC",
            mode="lines",
            line=dict(color=NAVY, width=2),
            yaxis="y2",
            hovertemplate="SOC : %{y:.1f} %<extra></extra>",
        )
    )
    _layout(fig, height=330, y_title="Flux batterie (kWh)")
    fig.update_layout(
        barmode="relative",
        yaxis2=dict(
            title=dict(text="SOC (%)", font=dict(size=10.5)),
            overlaying="y",
            side="right",
            range=[0, 100],
            showgrid=False,
            ticksuffix=" %",
            tickfont=dict(size=10),
        ),
    )
    _time_axis(fig, result)
    return fig
