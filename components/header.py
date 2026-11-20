"""En-tête de page commun à toutes les vues."""

from __future__ import annotations

from datetime import datetime

import streamlit as st

from utils.config import APP_NAME, DATA_LABEL, DEMO_LABEL, get_config
from utils.formatting import fr_date, fr_time
from utils.icons import icon


def render_header(
    title: str,
    subtitle: str,
    config: dict[str, object] | None = None,
    data_label: str | None = None,
) -> None:
    """Bandeau supérieur : contexte, titre, provenance et mode démonstration."""
    cfg = config or get_config()
    building = str(cfg.get("building_name", "Bâtiment ASHRAE"))
    location = str(cfg.get("location", "Site 3 · ASHRAE GE III"))
    now = datetime.now()
    source = data_label or DATA_LABEL

    st.markdown(
        f"""
<div class="page-header">
  <div>
    <div class="page-eyebrow"><span class="line"></span> SMART BUILDING · B2G · SUPERVISION ÉNERGÉTIQUE</div>
    <h1>{title}</h1>
    <p class="subtitle">{subtitle}</p>
  </div>
  <div class="header-side">
    <div class="demo-pill" style="background:#ECFDF5;border-color:#BBF7D0;color:#065F46">
      <span class="dot" style="background:#10B981"></span> {source}
    </div>
    <div class="demo-pill"><span class="dot"></span> {DEMO_LABEL}</div>
    <div class="header-clock">{icon("clock", size=14)} {fr_date(now)} · {fr_time(now, with_seconds=True)}</div>
    <div class="header-building">{icon("building", size=13)} <strong>{building}</strong> · {location}</div>
  </div>
</div>
""",
        unsafe_allow_html=True,
    )
