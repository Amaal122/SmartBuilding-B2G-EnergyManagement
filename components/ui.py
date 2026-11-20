"""Composants d'interface réutilisables (HTML maîtrisé).

Ces briques produisent un rendu dense et professionnel tout en restant
compatibles avec le mode « unsafe_allow_html » de Streamlit. Aucune donnée
n'est chargée ici : les composants ne font qu'afficher les valeurs calculées.
"""

from __future__ import annotations

import html
from typing import Any

import streamlit as st

from utils.formatting import NBSP, fr_number, fr_pct
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

TONE_TO_PILL = {
    "good": "good",
    "warning": "warn",
    "warn": "warn",
    "critical": "bad",
    "bad": "bad",
    "info": "info",
    "neutral": "neutral",
    "purple": "purple",
    "success": "good",
}


def esc(value: Any) -> str:
    return html.escape(str(value), quote=True)


def status_pill(label: str, tone: str = "neutral") -> str:
    """Pastille de statut HTML."""
    css = TONE_TO_PILL.get(tone, "neutral")
    return (
        f'<span class="pill {css}"><span class="pdot"></span>{esc(label)}</span>'
    )


def section_heading(
    title: str,
    subtitle: str = "",
    right_html: str = "",
    kicker: str = "",
) -> None:
    """Titre de section avec sous-titre et contenu optionnel à droite."""
    kicker_html = f'<div class="section-kicker">{esc(kicker)}</div>' if kicker else ""
    subtitle_html = f"<p>{esc(subtitle)}</p>" if subtitle else ""
    st.markdown(
        f"""
<div class="section-heading">
  <div>{kicker_html}<h2>{esc(title)}</h2>{subtitle_html}</div>
  <div>{right_html}</div>
</div>
""",
        unsafe_allow_html=True,
    )


def panel_head(title: str, subtitle: str = "", tag: str = "", icon_name: str | None = None) -> None:
    """En-tête interne d'un panneau Streamlit (st.container border=True)."""
    icon_html = icon(icon_name, size=17) if icon_name else ""
    subtitle_html = f'<div class="panel-subtitle">{esc(subtitle)}</div>' if subtitle else ""
    tag_html = f'<span class="panel-tag">{esc(tag)}</span>' if tag else ""
    st.markdown(
        f"""
<div class="panel-head">
  <div>
    <div class="panel-title">{icon_html}<span>{esc(title)}</span></div>
    {subtitle_html}
  </div>
  {tag_html}
</div>
""",
        unsafe_allow_html=True,
    )


def stat_tiles(items: list[dict[str, Any]], columns: int = 4) -> None:
    """Grille de tuiles de statistiques compactes."""
    if not items:
        return
    tiles = []
    for item in items:
        accent, soft = ACCENTS.get(str(item.get("accent", "blue")), ACCENTS["blue"])
        icon_html = icon(str(item.get("icon", "activity")), size=17)
        unit = item.get("unit") or ""
        unit_html = f'<span class="unit">{esc(unit)}</span>' if unit else ""
        sub_html = (
            f'<div class="stat-sub">{esc(item["sub"])}</div>'
            if item.get("sub")
            else ""
        )
        tiles.append(
            f"""
<div class="stat-tile">
  <div class="stat-icon" style="--accent:{accent};--accent-soft:{soft}">{icon_html}</div>
  <div class="stat-body">
    <div class="stat-label">{esc(item.get("label", ""))}</div>
    <div class="stat-value">{esc(item.get("value", "—"))}{unit_html}</div>
    {sub_html}
  </div>
</div>
"""
        )
    cols_class = {3: " cols-3", 5: " cols-5"}.get(columns, "")
    st.markdown(
        f'<div class="stat-grid{cols_class}">{"".join(tiles)}</div>',
        unsafe_allow_html=True,
    )


def balance_stats(items: list[dict[str, str]]) -> None:
    """Cinq valeurs synthétiques du bilan énergétique."""
    cells = []
    for item in items:
        cells.append(
            f"""
<div class="balance-stat">
  <div class="lbl">{esc(item.get("label", ""))}</div>
  <div class="val">{esc(item.get("value", "—"))} <small>{esc(item.get("unit", ""))}</small></div>
</div>
"""
        )
    st.markdown(
        f'<div class="balance-stats">{"".join(cells)}</div>',
        unsafe_allow_html=True,
    )


def alert_count_badge(alerts: list[dict[str, str]]) -> str:
    active = sum(1 for alert in alerts if alert.get("severity") in {"warning", "critical"})
    tone = "bad" if active else "good"
    label = f"{active} alerte{'s' if active > 1 else ''} active{'s' if active > 1 else ''}" if active else "Aucune alerte critique"
    return status_pill(label, tone)


def alert_cards(alerts: list[dict[str, str]]) -> None:
    """Grille d'alertes colorées selon la sévérité."""
    if not alerts:
        st.markdown(
            '<div class="empty-note">Aucune alerte pour la période sélectionnée.</div>',
            unsafe_allow_html=True,
        )
        return

    severity_style = {
        "critical": ("#DC2626", "#FEF2F2", "alert"),
        "warning": ("#F59E0B", "#FFFBEB", "alert"),
        "info": ("#2563EB", "#EFF6FF", "info"),
        "success": ("#10B981", "#ECFDF5", "check"),
    }
    cards = []
    for alert in alerts:
        tone, soft, default_icon = severity_style.get(
            str(alert.get("severity", "info")), severity_style["info"]
        )
        alert_icon = icon(str(alert.get("icon", default_icon)), size=18)
        severity_label = {
            "critical": "Critique",
            "warning": "Avertissement",
            "info": "Information",
            "success": "Normal",
        }.get(str(alert.get("severity")), "Information")
        cards.append(
            f"""
<div class="alert-card" style="--tone:{tone};--tone-soft:{soft}">
  <div class="alert-icon">{alert_icon}</div>
  <div class="alert-body">
    <div class="alert-title">{esc(alert.get("title", ""))}
      {status_pill(severity_label, str(alert.get("severity", "info")))}
    </div>
    <div class="alert-msg">{esc(alert.get("message", ""))}</div>
    <div class="alert-meta">{icon("clock", size=11)} {esc(alert.get("meta", ""))}</div>
  </div>
</div>
"""
        )
    st.markdown(f'<div class="alert-grid">{"".join(cards)}</div>', unsafe_allow_html=True)


def sensor_grid(cards: list[dict[str, str]]) -> None:
    """Cartes de capteurs IoT simulés."""
    if not cards:
        st.markdown(
            '<div class="empty-note">Aucune mesure capteur disponible.</div>',
            unsafe_allow_html=True,
        )
        return

    rendered = []
    for card in cards:
        accent, soft = ACCENTS.get(str(card.get("accent", "blue")), ACCENTS["blue"])
        unit_html = f'<span class="sensor-unit">{esc(card.get("unit", ""))}</span>' if card.get("unit") else ""
        rendered.append(
            f"""
<div class="sensor-card" style="--accent:{accent};--accent-soft:{soft}">
  <div class="sensor-top">
    <div class="sensor-icon">{icon(str(card.get("icon", "activity")), size=18)}</div>
    <div>
      <div class="sensor-name">{esc(card.get("name", ""))}</div>
      <div class="sensor-room">{esc(card.get("room", ""))}</div>
    </div>
  </div>
  <div class="sensor-value-row">
    <div class="sensor-value">{esc(card.get("value", "—"))}{unit_html}</div>
    {status_pill(str(card.get("status", "Normal")), str(card.get("tone", "good")))}
  </div>
  <div class="sensor-foot">
    <span>{esc(card.get("state", ""))}</span>
    <span>{icon("clock", size=10)} {esc(card.get("last", "—"))}</span>
  </div>
</div>
"""
        )
    st.markdown(
        f'<div class="sensor-grid">{"".join(rendered)}</div>',
        unsafe_allow_html=True,
    )


def equipment_table(rows: list[dict[str, str]]) -> None:
    """Tableau des équipements avec états colorés."""
    if not rows:
        st.markdown(
            '<div class="empty-note">Aucun équipement configuré.</div>',
            unsafe_allow_html=True,
        )
        return
    body = []
    for row in rows:
        tone = str(row.get("tone", "neutral"))
        body.append(
            f"""
<tr>
  <td><span class="device-name">{icon(str(row.get("icon", "server")), size=15)}{esc(row.get("equipment", ""))}</span></td>
  <td class="cell-muted">{esc(row.get("type", ""))}</td>
  <td>{status_pill(str(row.get("state", "")), tone)}</td>
  <td class="cell-mono">{esc(row.get("last", "—"))}</td>
</tr>
"""
        )
    st.markdown(
        f"""
<div class="table-scroll">
  <table class="sbems-table">
    <thead>
      <tr>
        <th>Équipement</th>
        <th>Type</th>
        <th>État</th>
        <th>Dernière mesure</th>
      </tr>
    </thead>
    <tbody>{"".join(body)}</tbody>
  </table>
</div>
""",
        unsafe_allow_html=True,
    )


def battery_panel(
    soc: float | None,
    status: str,
    tone: str,
    stored_kwh: float | None,
    capacity_kwh: float,
    delta_pts: float | None,
    min_soc: float | None,
    max_soc: float | None,
) -> None:
    """Indicateur visuel de batterie (simulation)."""
    if soc is None:
        st.markdown(
            '<div class="empty-note">État de charge indisponible.</div>',
            unsafe_allow_html=True,
        )
        return

    safe_soc = max(0.0, min(100.0, float(soc)))
    width = max(2.0, safe_soc)
    fill_class = "high" if safe_soc >= 50 else ("low" if safe_soc < 20 else "")
    delta_text = "—" if delta_pts is None else f"{fr_number(delta_pts, 1, signed=True)} pts"
    range_text = (
        f"{fr_number(min_soc, 0)} – {fr_number(max_soc, 0)} %"
        if min_soc is not None and max_soc is not None
        else "—"
    )
    st.markdown(
        f"""
<div class="battery-block">
  <div class="battery-gauge-row">
    <div class="battery-shell">
      <div class="battery-fill {fill_class}" style="width:{width:.1f}%"></div>
    </div>
    <div class="battery-cap"></div>
  </div>
  <div class="battery-scale"><span>0 %</span><span>50 %</span><span>100 %</span></div>
  <div class="battery-readout">
    <strong>{fr_number(safe_soc, 0)} %</strong>
    <span>État de charge simulé</span>
    {status_pill(status, tone)}
  </div>
  <div class="battery-meta">
    <div><div class="lbl">Capacité installée</div><div class="val">{fr_number(capacity_kwh, 0)} kWh</div></div>
    <div><div class="lbl">Énergie stockée</div><div class="val">{fr_number(stored_kwh, 0)} kWh</div></div>
    <div><div class="lbl">Variation horaire</div><div class="val">{delta_text}</div></div>
    <div><div class="lbl">Plage sur la période</div><div class="val">{range_text}</div></div>
  </div>
</div>
""",
        unsafe_allow_html=True,
    )


def dataset_card(dataset: dict[str, Any], last_update: str = "—") -> None:
    status = str(dataset.get("status", "Simulation"))
    st.markdown(
        f"""
<div class="dataset-card">
  <div class="dataset-head">
    <div style="display:flex;gap:11px;align-items:flex-start">
      <div class="dataset-icon">{icon("file", size=19)}</div>
      <div>
        <div class="dataset-name">{esc(dataset.get("name", ""))}</div>
        <div class="dataset-desc">{esc(dataset.get("description", ""))}</div>
      </div>
    </div>
    {status_pill(status, "purple")}
  </div>
  <div class="dataset-facts">
    <div><div class="k">Lignes</div><div class="v">{fr_number(dataset.get("rows", 0), 0)}</div></div>
    <div><div class="k">Colonnes</div><div class="v">{fr_number(dataset.get("columns", 0), 0)}</div></div>
    <div><div class="k">Fréquence</div><div class="v">{esc(dataset.get("frequency", "—"))}</div></div>
  </div>
  <div class="dataset-foot">
    {icon("database", size=11)} {esc(dataset.get("source", ""))} · maj simulée {esc(last_update)}
  </div>
</div>
""",
        unsafe_allow_html=True,
    )


def upload_note() -> None:
    st.markdown(
        f"""
<div class="upload-note">{icon("info", size=12)}
  Import visuel uniquement — aucun fichier n'est analysé dans cette version.
</div>
""",
        unsafe_allow_html=True,
    )


def system_row(label: str, value: str, tone: str = "neutral", icon_name: str = "info") -> None:
    st.markdown(
        f"""
<div class="sysinfo-row">
  <div class="sysinfo-key">{icon(icon_name, size=14)} {esc(label)}</div>
  {status_pill(value, tone)}
</div>
""",
        unsafe_allow_html=True,
    )


def info_panel_protocols(protocols: list[str]) -> None:
    chips = "".join(f'<span class="protocol-chip">{esc(p)}</span>' for p in protocols)
    st.markdown(
        f"""
<div class="info-panel">
  <div class="ip-icon">{icon("wifi", size=18)}</div>
  <div>
    <h4>Communication industrielle — intégration future</h4>
    <p>
      Cette version n'établit aucune connexion. Les protocoles MQTT, Modbus TCP
      et BACnet/IP seront intégrés ultérieurement pour collecter les mesures des
      compteurs, capteurs et onduleurs. La couche d'accès aux données
      (<strong>get_energy_data()</strong>) est déjà isolée pour faciliter ce raccordement.
    </p>
    <div class="protocol-chips">{chips}</div>
  </div>
</div>
""",
        unsafe_allow_html=True,
    )


def demo_notice(text: str = "Données simulées localement — aucun équipement physique connecté.") -> None:
    st.markdown(
        f"""
<div class="flow-note">{icon("shield", size=14)}
  <div><strong>Mode démonstration.</strong> {esc(text)}</div>
</div>
""",
        unsafe_allow_html=True,
    )


def page_footer(version: str) -> None:
    st.markdown(
        f"""
<div class="page-footer">
  <div><strong>SBEMS</strong> · Smart Building Energy Management System · v{esc(version)}</div>
  <div>Front-end démonstrateur · DEMO MODE – SIMULATED DATA · Aucune connexion backend / IoT</div>
</div>
""",
        unsafe_allow_html=True,
    )
