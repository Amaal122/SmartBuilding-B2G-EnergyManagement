"""Diagramme de flux énergétique (SVG inline).

Le schéma distingue clairement production, consommation, stockage et
échanges réseau. La batterie est volontairement représentée en pointillés :
son comportement est illustratif et n'entre pas dans le bilan réseau simplifié.
"""

from __future__ import annotations

from typing import Any

import streamlit as st

from utils.formatting import fr_number
from utils.icons import icon

NAVY = "#0B2545"


def _value(value: Any, decimals: int = 0) -> str:
    return fr_number(value, decimals)


def energy_flow_diagram(kpis: dict[str, Any], battery_capacity: float) -> None:
    solar = float(kpis.get("solar") or 0.0)
    self_consumed = float(kpis.get("self_consumed") or 0.0)
    grid_import = float(kpis.get("grid_import") or 0.0)
    surplus = float(kpis.get("surplus") or 0.0)
    soc = kpis.get("soc")
    soc_value = "—" if soc is None else f"{fr_number(soc, 0)} %"

    diagram_html = f"""
<div class="flow-wrap">
<svg class="flow-svg" viewBox="0 0 1000 382" role="img"
     aria-label="Diagramme des flux énergétiques simulés">
  <defs>
    <marker id="arrowGreen" viewBox="0 0 10 10" refX="8.5" refY="5" markerWidth="6"
            markerHeight="6" orient="auto-start-reverse">
      <path d="M0 0 L10 5 L0 10 z" fill="#10B981"/>
    </marker>
    <marker id="arrowBlue" viewBox="0 0 10 10" refX="8.5" refY="5" markerWidth="6"
            markerHeight="6" orient="auto-start-reverse">
      <path d="M0 0 L10 5 L0 10 z" fill="#2563EB"/>
    </marker>
    <marker id="arrowAmber" viewBox="0 0 10 10" refX="8.5" refY="5" markerWidth="6"
            markerHeight="6" orient="auto-start-reverse">
      <path d="M0 0 L10 5 L0 10 z" fill="#F59E0B"/>
    </marker>
  </defs>

  <!-- Connecteurs -->
  <path d="M280 86 H325 V150 H366" fill="none" stroke="#10B981" stroke-width="2.4"
        marker-end="url(#arrowGreen)"/>
  <path d="M280 296 H325 V230 H366" fill="none" stroke="#2563EB" stroke-width="2.4"
        marker-end="url(#arrowBlue)"/>
  <path d="M634 150 H682 V86 H716" fill="none" stroke="#F59E0B" stroke-width="2.1"
        stroke-dasharray="5 5" marker-start="url(#arrowAmber)" marker-end="url(#arrowAmber)"/>
  <path d="M634 230 H682 V296 H716" fill="none" stroke="#10B981" stroke-width="2.4"
        marker-end="url(#arrowGreen)"/>

  <text x="325" y="76" text-anchor="middle" font-size="8.5" font-weight="700"
        letter-spacing="0.9" fill="#047857">AUTOCONSOMMÉE</text>
  <text x="325" y="286" text-anchor="middle" font-size="8.5" font-weight="700"
        letter-spacing="0.9" fill="#1D4ED8">IMPORT</text>
  <text x="682" y="76" text-anchor="middle" font-size="8.5" font-weight="700"
        letter-spacing="0.9" fill="#B45309">ÉCHANGE</text>
  <text x="682" y="286" text-anchor="middle" font-size="8.5" font-weight="700"
        letter-spacing="0.9" fill="#047857">SURPLUS</text>

  <!-- Production solaire -->
  <rect x="24" y="30" width="252" height="112" rx="15" fill="#F0FDF4" stroke="#BBF7D0"/>
  <text x="48" y="62" font-size="9.5" font-weight="800" letter-spacing="1.1"
        fill="#047857">PRODUCTION SOLAIRE</text>
  <text x="48" y="98" font-size="27" font-weight="800" fill="{NAVY}">
    {_value(solar)}<tspan font-size="12" font-weight="600" fill="#64748B"> kWh</tspan>
  </text>
  <text x="48" y="122" font-size="10.5" fill="#64748B">Période analysée · donnée simulée</text>

  <!-- Import réseau -->
  <rect x="24" y="240" width="252" height="112" rx="15" fill="#EFF6FF" stroke="#BFDBFE"/>
  <text x="48" y="272" font-size="9.5" font-weight="800" letter-spacing="1.1"
        fill="#1D4ED8">IMPORT RÉSEAU</text>
  <text x="48" y="308" font-size="27" font-weight="800" fill="{NAVY}">
    {_value(grid_import)}<tspan font-size="12" font-weight="600" fill="#64748B"> kWh</tspan>
  </text>
  <text x="48" y="332" font-size="10.5" fill="#64748B">Fourniture électrique · simulée</text>

  <!-- Bâtiment -->
  <rect x="374" y="115" width="252" height="150" rx="16" fill="#F8FAFC" stroke="#CBD5E1"/>
  <rect x="374" y="115" width="252" height="4" rx="2" fill="{NAVY}"/>
  <text x="500" y="151" text-anchor="middle" font-size="9.5" font-weight="800"
        letter-spacing="1.1" fill="{NAVY}">BÂTIMENT</text>
  <text x="500" y="192" text-anchor="middle" font-size="29" font-weight="800" fill="{NAVY}">
    {_value(kpis.get("consumption"))}<tspan font-size="12" font-weight="600" fill="#64748B"> kWh</tspan>
  </text>
  <text x="500" y="217" text-anchor="middle" font-size="10.5" fill="#64748B">
    Demande des charges électriques
  </text>
  <text x="500" y="240" text-anchor="middle" font-size="9.5" font-weight="700" fill="#475569">
    Autoconsommation solaire : {_value(self_consumed)} kWh
  </text>

  <!-- Batterie -->
  <rect x="724" y="30" width="252" height="112" rx="15" fill="#FFFBEB" stroke="#FDE68A"/>
  <text x="748" y="62" font-size="9.5" font-weight="800" letter-spacing="1.1"
        fill="#B45309">STOCKAGE BATTERIE</text>
  <text x="748" y="98" font-size="27" font-weight="800" fill="{NAVY}">
    {soc_value}
  </text>
  <text x="748" y="122" font-size="10.5" fill="#64748B">
    Capacité {fr_number(battery_capacity, 0)} kWh · simulé
  </text>

  <!-- Surplus -->
  <rect x="724" y="240" width="252" height="112" rx="15" fill="#F0FDF4" stroke="#A7F3D0"/>
  <text x="748" y="272" font-size="9.5" font-weight="800" letter-spacing="1.1"
        fill="#047857">SURPLUS POTENTIEL</text>
  <text x="748" y="308" font-size="27" font-weight="800" fill="{NAVY}">
    {_value(surplus)}<tspan font-size="12" font-weight="600" fill="#64748B"> kWh</tspan>
  </text>
  <text x="748" y="332" font-size="10.5" fill="#64748B">Export réseau non simulé</text>
</svg>
<div class="flow-legend">
  <span><i style="background:#10B981"></i> Production solaire</span>
  <span><i style="background:#2563EB"></i> Consommation / réseau</span>
  <span><i style="background:#F59E0B"></i> Stockage simulé</span>
  <span><i style="background:#0B2545"></i> Bâtiment</span>
</div>
</div>
"""
    # Markdown termine un bloc HTML brut à la première ligne vide : on compacte
    # le SVG pour garantir son rendu complet dans st.markdown.
    st.markdown(
        "\n".join(line for line in diagram_html.splitlines() if line.strip()),
        unsafe_allow_html=True,
    )


def flow_disclaimer() -> None:
    st.markdown(
        f"""
<div class="flow-note">{icon("info", size=14)}
  <div><strong>Bilan simplifié.</strong> Import et surplus sont calculés heure par heure
  sans dispatch batterie : <code>import = max(0, consommation − PV)</code> et
  <code>surplus = max(0, PV − consommation)</code>. Le stockage affiché est illustratif
  et ne participe pas à ce bilan.</div>
</div>
""",
        unsafe_allow_html=True,
    )
