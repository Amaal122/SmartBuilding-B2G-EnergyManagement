"""Identité visuelle et feuille de style de SBEMS.

Le thème repose sur une base claire (blanc / gris très clair), des titres
bleu marine et un code couleur énergétique constant :
- vert  : production renouvelable
- bleu  : électricité réseau / consommation
- ambre : stockage batterie et avertissements
- rouge : criticité
"""

from __future__ import annotations

import streamlit as st

# ---------------------------------------------------------------------------
# Palette de l'application (également utilisée par les graphiques Plotly)
# ---------------------------------------------------------------------------
NAVY = "#0B2545"
NAVY_SOFT = "#13315C"
BLUE = "#2563EB"
BLUE_DARK = "#1D4ED8"
SKY = "#0EA5E9"
GREEN = "#10B981"
GREEN_DARK = "#047857"
MINT = "#34D399"
AMBER = "#F59E0B"
AMBER_DARK = "#B45309"
RED = "#EF4444"
SLATE = "#64748B"
SLATE_LIGHT = "#94A3B8"
GRID = "#EDF1F7"
BORDER = "#E5EAF2"
CARD_BG = "#FFFFFF"
APP_BG = "#F4F6FA"

ZONE_COLORS = ["#2563EB", "#0EA5E9", "#10B981", "#8B5CF6", "#F59E0B"]
END_USE_COLORS = ["#1D4ED8", "#38BDF8", "#10B981", "#F59E0B", "#8B5CF6"]

FONT_STACK = (
    "'Segoe UI', 'Inter', 'Helvetica Neue', Arial, system-ui, sans-serif"
)


CSS = """
<style>
/* --------------------------------------------------------------------- */
/* Base                                                                   */
/* --------------------------------------------------------------------- */
html, body, [class*="css"] {
    font-family: 'Segoe UI', 'Inter', 'Helvetica Neue', Arial, system-ui, sans-serif;
}
.stApp { background: #F4F6FA; }
[data-testid="stHeader"] {
    background: rgba(244, 246, 250, 0.92);
    backdrop-filter: blur(8px);
    border-bottom: 1px solid rgba(229, 234, 242, 0.7);
    height: 2.6rem;
}
[data-testid="stAppDeployButton"],
[data-testid="stMainMenu"],
[data-testid="stStatusWidget"] { display: none !important; }
#MainMenu, footer { visibility: hidden; }

.block-container {
    padding-top: 3.4rem;
    padding-bottom: 2.5rem;
    max-width: 1560px;
}

h1, h2, h3, h4 { color: #0B2545; letter-spacing: -0.015em; }

/* --------------------------------------------------------------------- */
/* Barre latérale                                                         */
/* --------------------------------------------------------------------- */
[data-testid="stSidebar"] {
    background:
        radial-gradient(120% 60% at 0% 0%, rgba(37, 99, 235, 0.28) 0%, rgba(11, 37, 69, 0) 55%),
        linear-gradient(180deg, #0A1F3C 0%, #0B2545 52%, #081A31 100%);
    border-right: 1px solid rgba(255, 255, 255, 0.06);
}
[data-testid="stSidebar"] > div { padding-top: 0.4rem; }
[data-testid="stSidebar"] p,
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] span { color: #D8E3F3; }
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p { color: #D8E3F3; }

.sbems-brand {
    display: flex; align-items: center; gap: 12px;
    padding: 6px 4px 18px 4px;
}
.sbems-brand-logo {
    width: 44px; height: 44px; border-radius: 12px;
    background: linear-gradient(145deg, #123B6D 0%, #0B2545 100%);
    border: 1px solid rgba(148, 197, 255, 0.25);
    display: flex; align-items: center; justify-content: center;
    box-shadow: 0 8px 18px -10px rgba(0, 0, 0, 0.8);
    flex: 0 0 44px;
}
.sbems-brand-title {
    color: #FFFFFF !important; font-size: 18px; font-weight: 800;
    letter-spacing: 0.08em; line-height: 1.1;
}
.sbems-brand-sub {
    color: #8FB3DB !important; font-size: 10.5px; font-weight: 600;
    letter-spacing: 0.11em; text-transform: uppercase; margin-top: 3px;
}
.side-section-label {
    color: #7FA3CB !important; font-size: 10px; font-weight: 700;
    letter-spacing: 0.16em; text-transform: uppercase;
    padding: 2px 6px 8px 6px;
}
.side-separator {
    height: 1px; background: rgba(255, 255, 255, 0.10);
    margin: 16px 4px;
}
[data-testid="stSidebar"] [data-testid="stRadio"] { margin-top: -2px; }
[data-testid="stSidebar"] div[role="radiogroup"] { gap: 3px; }
[data-testid="stSidebar"] div[role="radiogroup"] > label {
    width: 100%;
    margin: 0;
    padding: 9px 12px;
    border-radius: 10px;
    cursor: pointer;
    transition: background 0.16s ease, box-shadow 0.16s ease;
    border: 1px solid transparent;
}
[data-testid="stSidebar"] div[role="radiogroup"] > label:hover {
    background: rgba(255, 255, 255, 0.065);
}
[data-testid="stSidebar"] div[role="radiogroup"] > label[data-selected="true"],
[data-testid="stSidebar"] div[role="radiogroup"] > label:has(input:checked) {
    background: linear-gradient(90deg, rgba(37, 99, 235, 0.38) 0%, rgba(56, 189, 248, 0.12) 100%);
    border-color: rgba(56, 189, 248, 0.24);
    box-shadow: inset 3px 0 0 #38BDF8, 0 6px 14px -12px #000000;
}
[data-testid="stSidebar"] label[data-testid="stRadioOption"] > div > div:first-child {
    display: none !important;
}
[data-testid="stSidebar"] label[data-testid="stRadioOption"] > div {
    align-items: center;
    gap: 0;
}
[data-testid="stSidebar"] label[data-testid="stRadioOption"] {
    width: 100%;
}
[data-testid="stSidebar"] label[data-testid="stRadioOption"] p {
    display: flex;
    align-items: center;
}
[data-testid="stSidebar"] div[role="radiogroup"] > label p {
    font-size: 13.5px !important;
    font-weight: 600 !important;
    color: #DCE7F7 !important;
    line-height: 1.25;
}
[data-testid="stSidebar"] div[role="radiogroup"] > label:has(input:checked) p {
    color: #FFFFFF !important;
}
[data-testid="stSidebar"] div[role="radiogroup"] > label [data-testid="stIconMaterial"] {
    font-size: 19px !important;
    color: #7FB3E8 !important;
    vertical-align: -4px;
    margin-right: 6px;
}
[data-testid="stSidebar"] div[role="radiogroup"] > label:has(input:checked) [data-testid="stIconMaterial"] {
    color: #38BDF8 !important;
}

.side-demo {
    margin: 18px 2px 0 2px;
    padding: 13px 14px;
    border-radius: 12px;
    background: rgba(245, 158, 11, 0.10);
    border: 1px solid rgba(245, 158, 11, 0.28);
}
.side-demo-head {
    display: flex; align-items: center; gap: 8px;
    color: #FBBF24 !important; font-size: 10.5px; font-weight: 800;
    letter-spacing: 0.12em; text-transform: uppercase;
}
.side-demo p {
    margin: 7px 0 0 0; color: #B9CBE3 !important;
    font-size: 11.5px; line-height: 1.5;
}
.pulse-dot {
    width: 7px; height: 7px; border-radius: 50%;
    background: #FBBF24; box-shadow: 0 0 0 3px rgba(251, 191, 36, 0.16);
    flex: 0 0 7px;
}
.side-status { margin: 14px 2px 0 2px; }
.side-status-row {
    display: flex; justify-content: space-between; align-items: center;
    padding: 7px 2px; border-bottom: 1px solid rgba(255, 255, 255, 0.06);
    font-size: 11.5px;
}
.side-status-row span:first-child { color: #8FB3DB !important; }
.side-status-row .val { color: #F1F5F9 !important; font-weight: 600; }
.side-status-row .val.off { color: #FCA5A5 !important; }
.side-footer {
    margin: 22px 4px 4px 4px; padding-top: 12px;
    border-top: 1px solid rgba(255, 255, 255, 0.09);
    color: #6F8FB5 !important; font-size: 10.5px; line-height: 1.6;
}
.side-footer strong { color: #A9C4E2 !important; }

/* --------------------------------------------------------------------- */
/* En-tête de page                                                        */
/* --------------------------------------------------------------------- */
.page-header {
    display: flex; justify-content: space-between; align-items: flex-start;
    gap: 22px; padding: 4px 0 20px 0;
    border-bottom: 1px solid #E2E8F2;
    margin-bottom: 20px;
}
.page-eyebrow {
    display: flex; align-items: center; gap: 8px;
    color: #2563EB; font-size: 10.5px; font-weight: 800;
    letter-spacing: 0.15em; text-transform: uppercase;
    margin-bottom: 7px;
}
.page-eyebrow .line { width: 22px; height: 2px; background: #2563EB; border-radius: 2px; }
.page-header h1 {
    margin: 0 0 6px 0; font-size: 28px; line-height: 1.15;
    font-weight: 800; color: #0B2545;
}
.page-header .subtitle {
    margin: 0; color: #64748B; font-size: 13px; max-width: 720px;
    line-height: 1.5;
}
.header-side {
    display: flex; flex-direction: column; align-items: flex-end; gap: 8px;
    flex: 0 0 auto; padding-top: 3px;
}
.demo-pill {
    display: inline-flex; align-items: center; gap: 8px;
    background: #FFF7ED; border: 1px solid #FCD9A8;
    color: #B45309; border-radius: 999px;
    padding: 6px 12px; font-size: 10px; font-weight: 800;
    letter-spacing: 0.09em; text-transform: uppercase;
    white-space: nowrap;
}
.demo-pill .dot {
    width: 7px; height: 7px; border-radius: 50%;
    background: #F59E0B; box-shadow: 0 0 0 3px rgba(245, 158, 11, 0.14);
}
.header-clock {
    display: flex; align-items: center; gap: 7px;
    color: #334155; font-size: 12px; font-weight: 600;
    background: #FFFFFF; border: 1px solid #E5EAF2;
    border-radius: 8px; padding: 6px 10px;
}
.header-building {
    color: #64748B; font-size: 11px;
    display: flex; align-items: center; gap: 6px;
}
.header-building strong { color: #0B2545; font-weight: 700; }

/* --------------------------------------------------------------------- */
/* Panneaux et sections                                                   */
/* --------------------------------------------------------------------- */
[data-testid="stVerticalBlockBorderWrapper"] {
    background: #FFFFFF;
    border: 1px solid #E5EAF2 !important;
    border-radius: 16px !important;
    box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04),
                0 10px 26px -22px rgba(15, 23, 42, 0.25);
    padding: 0.85rem 1rem 0.75rem 1rem;
}
[data-testid="stVerticalBlockBorderWrapper"] [data-testid="stVerticalBlockBorderWrapper"] {
    box-shadow: none;
    padding: 0.2rem;
}
.panel-head {
    display: flex; align-items: flex-start; justify-content: space-between;
    gap: 14px; margin: 0 0 2px 0;
}
.panel-title {
    font-size: 14.5px; font-weight: 700; color: #0B2545;
    display: flex; align-items: center; gap: 8px; line-height: 1.25;
}
.panel-title svg { color: #2563EB; flex: 0 0 auto; }
.panel-subtitle {
    color: #7B8AA0; font-size: 11.5px; margin-top: 3px; line-height: 1.4;
}
.panel-tag {
    font-size: 10px; font-weight: 700; letter-spacing: 0.06em;
    color: #64748B; background: #F1F5F9; border: 1px solid #E2E8F0;
    border-radius: 999px; padding: 4px 9px; white-space: nowrap;
}

.section-heading {
    display: flex; align-items: flex-end; justify-content: space-between;
    gap: 16px; margin: 26px 0 12px 0;
}
.section-heading h2 {
    margin: 0; font-size: 18px; font-weight: 800; color: #0B2545;
    display: flex; align-items: center; gap: 9px;
}
.section-heading p {
    margin: 4px 0 0 0; color: #7B8AA0; font-size: 12px;
}
.section-kicker {
    color: #2563EB; font-size: 10px; font-weight: 800;
    letter-spacing: 0.14em; text-transform: uppercase;
    margin-bottom: 4px;
}

/* --------------------------------------------------------------------- */
/* Cartes KPI                                                             */
/* --------------------------------------------------------------------- */
.kpi-grid {
    display: grid; grid-template-columns: repeat(6, minmax(0, 1fr));
    gap: 13px; margin-bottom: 4px;
}
.kpi-grid.cols-4 { grid-template-columns: repeat(4, minmax(0, 1fr)); }
.kpi-grid.cols-3 { grid-template-columns: repeat(3, minmax(0, 1fr)); }
.kpi-card {
    position: relative; background: #FFFFFF;
    border: 1px solid #E5EAF2; border-radius: 16px;
    padding: 15px 15px 13px 15px; min-height: 140px;
    box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04),
                0 12px 26px -24px rgba(15, 23, 42, 0.35);
    overflow: hidden;
    display: flex; flex-direction: column;
}
.kpi-card::before {
    content: ""; position: absolute; top: 0; left: 0; right: 0;
    height: 3px; background: var(--accent, #2563EB);
}
.kpi-top { display: flex; align-items: center; gap: 9px; margin-bottom: 10px; }
.kpi-icon {
    width: 30px; height: 30px; border-radius: 9px;
    display: flex; align-items: center; justify-content: center;
    background: var(--accent-soft, #EFF6FF); color: var(--accent, #2563EB);
    flex: 0 0 30px;
}
.kpi-label {
    font-size: 10.5px; font-weight: 700; letter-spacing: 0.035em;
    color: #64748B; text-transform: uppercase; line-height: 1.25;
}
.kpi-main {
    display: flex; align-items: flex-end; justify-content: space-between;
    gap: 6px; margin-top: auto;
}
.kpi-value {
    font-size: 25px; font-weight: 800; color: #0B2545;
    line-height: 1.05; letter-spacing: -0.02em; white-space: nowrap;
}
.kpi-unit {
    font-size: 11px; font-weight: 600; color: #7B8AA0;
    margin-left: 4px; letter-spacing: 0;
}
.kpi-spark { opacity: 0.95; flex: 0 0 auto; margin-bottom: 1px; }
.kpi-foot {
    display: flex; align-items: center; gap: 6px; flex-wrap: wrap;
    margin-top: 9px; font-size: 10.5px; color: #8A98AC;
}
.kpi-delta {
    font-weight: 800; font-size: 10.5px; padding: 2px 6px;
    border-radius: 5px; white-space: nowrap;
}
.kpi-delta.good { color: #047857; background: #ECFDF5; }
.kpi-delta.bad { color: #B91C1C; background: #FEF2F2; }
.kpi-delta.neutral { color: #475569; background: #F1F5F9; }

/* --------------------------------------------------------------------- */
/* Tuiles de statistiques                                                 */
/* --------------------------------------------------------------------- */
.stat-grid {
    display: grid; grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 12px;
}
.stat-grid.cols-3 { grid-template-columns: repeat(3, minmax(0, 1fr)); }
.stat-grid.cols-5 { grid-template-columns: repeat(5, minmax(0, 1fr)); }
.stat-tile {
    background: #FFFFFF; border: 1px solid #E5EAF2; border-radius: 13px;
    padding: 13px 14px; display: flex; gap: 11px; align-items: flex-start;
    min-height: 80px;
}
.stat-icon {
    width: 32px; height: 32px; border-radius: 9px; flex: 0 0 32px;
    display: flex; align-items: center; justify-content: center;
    background: var(--accent-soft, #EFF6FF); color: var(--accent, #2563EB);
}
.stat-body { min-width: 0; }
.stat-label {
    font-size: 10px; font-weight: 700; letter-spacing: 0.05em;
    color: #7B8AA0; text-transform: uppercase; line-height: 1.3;
}
.stat-value {
    font-size: 19px; font-weight: 800; color: #0B2545;
    line-height: 1.25; white-space: nowrap; letter-spacing: -0.01em;
}
.stat-value .unit {
    font-size: 10.5px; font-weight: 600; color: #7B8AA0; margin-left: 3px;
}
.stat-sub { font-size: 10.5px; color: #8A98AC; margin-top: 2px; line-height: 1.35; }

/* --------------------------------------------------------------------- */
/* Pastilles de statut                                                    */
/* --------------------------------------------------------------------- */
.pill {
    display: inline-flex; align-items: center; gap: 5px;
    font-size: 10px; font-weight: 800; letter-spacing: 0.045em;
    padding: 3px 8px; border-radius: 999px; white-space: nowrap;
    text-transform: uppercase;
}
.pill .pdot { width: 5px; height: 5px; border-radius: 50%; background: currentColor; }
.pill.good { color: #047857; background: #ECFDF5; border: 1px solid #BBF7D0; }
.pill.warn { color: #B45309; background: #FFFBEB; border: 1px solid #FDE68A; }
.pill.bad { color: #B91C1C; background: #FEF2F2; border: 1px solid #FECACA; }
.pill.info { color: #1D4ED8; background: #EFF6FF; border: 1px solid #BFDBFE; }
.pill.neutral { color: #475569; background: #F1F5F9; border: 1px solid #E2E8F0; }
.pill.purple { color: #6D28D9; background: #F5F3FF; border: 1px solid #DDD6FE; }

/* --------------------------------------------------------------------- */
/* Bilan énergétique                                                      */
/* --------------------------------------------------------------------- */
.balance-stats {
    display: grid; grid-template-columns: repeat(5, minmax(0, 1fr));
    gap: 10px; margin: 4px 0 16px 0;
}
.balance-stat {
    background: #F8FAFC; border: 1px solid #E9EEF6;
    border-radius: 11px; padding: 11px 12px;
}
.balance-stat .lbl {
    font-size: 9.5px; font-weight: 700; letter-spacing: 0.055em;
    color: #7B8AA0; text-transform: uppercase; line-height: 1.35;
}
.balance-stat .val {
    font-size: 17px; font-weight: 800; color: #0B2545;
    margin-top: 3px; white-space: nowrap;
}
.balance-stat .val small {
    font-size: 9.5px; color: #7B8AA0; font-weight: 600; margin-left: 3px;
}
.flow-wrap {
    background: linear-gradient(180deg, #FBFCFE 0%, #F6F9FD 100%);
    border: 1px solid #E9EEF6; border-radius: 14px;
    padding: 6px 8px 0 8px; overflow: hidden;
}
.flow-svg { display: block; width: 100%; height: auto; }
.flow-legend {
    display: flex; flex-wrap: wrap; gap: 16px; align-items: center;
    padding: 9px 12px 12px 12px; font-size: 10.5px; color: #64748B;
}
.flow-legend span { display: inline-flex; align-items: center; gap: 6px; }
.flow-legend i {
    width: 14px; height: 3px; border-radius: 3px; display: inline-block;
}
.flow-note {
    display: flex; align-items: flex-start; gap: 8px;
    background: #F8FAFC; border: 1px dashed #DCE4EF; border-radius: 10px;
    padding: 9px 12px; margin-top: 10px;
    color: #64748B; font-size: 11px; line-height: 1.5;
}
.flow-note strong { color: #334155; }

/* --------------------------------------------------------------------- */
/* Alertes                                                                */
/* --------------------------------------------------------------------- */
.alert-grid {
    display: grid; grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 12px;
}
.alert-card {
    background: #FFFFFF; border: 1px solid #E5EAF2;
    border-left: 4px solid var(--tone, #2563EB);
    border-radius: 12px; padding: 13px 15px;
    display: flex; gap: 12px; align-items: flex-start;
}
.alert-icon {
    width: 32px; height: 32px; border-radius: 9px; flex: 0 0 32px;
    display: flex; align-items: center; justify-content: center;
    background: var(--tone-soft, #EFF6FF); color: var(--tone, #2563EB);
}
.alert-body { min-width: 0; }
.alert-title {
    font-size: 13px; font-weight: 700; color: #0B2545;
    display: flex; align-items: center; gap: 8px; flex-wrap: wrap;
    line-height: 1.3;
}
.alert-msg {
    font-size: 11.5px; color: #5B6B82; line-height: 1.5;
    margin-top: 3px;
}
.alert-meta {
    font-size: 10px; color: #94A3B8; margin-top: 6px;
    display: flex; align-items: center; gap: 5px;
}

/* --------------------------------------------------------------------- */
/* Capteurs                                                               */
/* --------------------------------------------------------------------- */
.sensor-grid {
    display: grid; grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 13px;
}
.sensor-card {
    background: #FFFFFF; border: 1px solid #E5EAF2;
    border-radius: 15px; padding: 15px 16px;
    box-shadow: 0 1px 2px rgba(15, 23, 42, 0.03);
    position: relative; overflow: hidden;
}
.sensor-card::after {
    content: ""; position: absolute; top: 0; left: 0; width: 100%;
    height: 2px; background: var(--accent, #2563EB); opacity: 0.85;
}
.sensor-top { display: flex; align-items: center; gap: 9px; }
.sensor-icon {
    width: 34px; height: 34px; border-radius: 10px;
    display: flex; align-items: center; justify-content: center;
    background: var(--accent-soft, #EFF6FF); color: var(--accent, #2563EB);
    flex: 0 0 34px;
}
.sensor-name { font-size: 11.5px; font-weight: 700; color: #334155; line-height: 1.3; }
.sensor-room { font-size: 10px; color: #94A3B8; margin-top: 1px; }
.sensor-value-row {
    display: flex; align-items: flex-end; justify-content: space-between;
    gap: 8px; margin-top: 13px;
}
.sensor-value {
    font-size: 27px; font-weight: 800; color: #0B2545;
    line-height: 1; letter-spacing: -0.02em;
}
.sensor-unit { font-size: 12px; color: #7B8AA0; font-weight: 600; margin-left: 3px; }
.sensor-foot {
    display: flex; justify-content: space-between; align-items: center;
    gap: 8px; margin-top: 11px; padding-top: 9px;
    border-top: 1px solid #EEF2F7; font-size: 9.5px; color: #94A3B8;
}

/* --------------------------------------------------------------------- */
/* Tableaux personnalisés                                                 */
/* --------------------------------------------------------------------- */
.table-scroll { overflow-x: auto; border: 1px solid #E9EEF6; border-radius: 12px; }
.sbems-table { width: 100%; border-collapse: collapse; font-size: 12px; min-width: 620px; }
.sbems-table thead th {
    text-align: left; font-size: 9.5px; font-weight: 800;
    letter-spacing: 0.07em; text-transform: uppercase;
    color: #64748B; background: #F8FAFC;
    padding: 10px 12px; border-bottom: 1px solid #E9EEF6;
    white-space: nowrap;
}
.sbems-table tbody td {
    padding: 10px 12px; border-bottom: 1px solid #F0F3F8;
    color: #334155; vertical-align: middle;
}
.sbems-table tbody tr:last-child td { border-bottom: none; }
.sbems-table tbody tr:hover td { background: #F8FAFC; }
.cell-strong { color: #0B2545; font-weight: 700; }
.cell-mono { font-variant-numeric: tabular-nums; font-weight: 600; color: #0B2545; }
.cell-muted { color: #8A98AC; font-size: 11px; }
.device-name { display: flex; align-items: center; gap: 8px; font-weight: 700; color: #0B2545; }
.device-name svg { color: #2563EB; }

/* --------------------------------------------------------------------- */
/* Batterie                                                               */
/* --------------------------------------------------------------------- */
.battery-block { padding: 4px 2px 2px 2px; }
.battery-gauge-row { display: flex; align-items: center; gap: 12px; }
.battery-shell {
    position: relative; flex: 1; height: 66px;
    border: 3px solid #0B2545; border-radius: 14px;
    padding: 5px; background: #F8FAFC;
}
.battery-fill {
    height: 100%; border-radius: 8px;
    background: linear-gradient(90deg, #F59E0B 0%, #FBBF24 100%);
    box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.35);
    transition: width 0.4s ease;
}
.battery-fill.high { background: linear-gradient(90deg, #059669 0%, #34D399 100%); }
.battery-fill.low { background: linear-gradient(90deg, #DC2626 0%, #F87171 100%); }
.battery-cap {
    width: 9px; height: 28px; background: #0B2545;
    border-radius: 0 5px 5px 0; flex: 0 0 9px; margin-left: -4px;
}
.battery-scale {
    display: flex; justify-content: space-between;
    color: #94A3B8; font-size: 9.5px; margin: 6px 18px 0 2px;
}
.battery-readout {
    display: flex; align-items: baseline; gap: 8px; margin-top: 13px;
}
.battery-readout strong {
    font-size: 34px; font-weight: 800; color: #0B2545;
    letter-spacing: -0.03em; line-height: 1;
}
.battery-readout span { color: #64748B; font-size: 12px; font-weight: 600; }
.battery-meta {
    display: grid; grid-template-columns: 1fr 1fr; gap: 8px;
    margin-top: 14px;
}
.battery-meta div {
    background: #F8FAFC; border: 1px solid #E9EEF6;
    border-radius: 9px; padding: 8px 10px;
}
.battery-meta .lbl {
    font-size: 9px; color: #8A98AC; text-transform: uppercase;
    letter-spacing: 0.05em; font-weight: 700;
}
.battery-meta .val { font-size: 13px; font-weight: 800; color: #0B2545; margin-top: 2px; }

/* --------------------------------------------------------------------- */
/* Jeux de données et configuration                                       */
/* --------------------------------------------------------------------- */
.dataset-card {
    background: #FFFFFF; border: 1px solid #E5EAF2;
    border-radius: 15px; padding: 16px 17px; height: 100%;
}
.dataset-head { display: flex; align-items: flex-start; justify-content: space-between; gap: 10px; }
.dataset-icon {
    width: 38px; height: 38px; border-radius: 11px;
    display: flex; align-items: center; justify-content: center;
    background: #EFF6FF; color: #2563EB; flex: 0 0 38px;
}
.dataset-name { font-size: 14px; font-weight: 800; color: #0B2545; line-height: 1.3; }
.dataset-desc { font-size: 11px; color: #7B8AA0; margin-top: 2px; }
.dataset-facts {
    display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px;
    margin-top: 13px; padding-top: 12px; border-top: 1px solid #EEF2F7;
}
.dataset-facts div .k {
    font-size: 9px; color: #94A3B8; text-transform: uppercase;
    letter-spacing: 0.05em; font-weight: 700;
}
.dataset-facts div .v {
    font-size: 12.5px; font-weight: 800; color: #0B2545; margin-top: 2px;
}
.dataset-foot {
    display: flex; align-items: center; gap: 7px; margin-top: 11px;
    font-size: 10px; color: #8A98AC;
}

.sysinfo-row {
    display: flex; align-items: center; justify-content: space-between;
    gap: 12px; padding: 10px 2px;
    border-bottom: 1px solid #EEF2F7;
}
.sysinfo-row:last-child { border-bottom: none; }
.sysinfo-key {
    display: flex; align-items: center; gap: 8px;
    font-size: 12px; color: #334155; font-weight: 600;
}
.sysinfo-key svg { color: #94A3B8; }

.info-panel {
    background: #EFF6FF; border: 1px solid #BFDBFE;
    border-radius: 13px; padding: 15px 17px;
    display: flex; gap: 12px; align-items: flex-start;
}
.info-panel .ip-icon {
    width: 32px; height: 32px; border-radius: 9px;
    background: #DBEAFE; color: #1D4ED8; flex: 0 0 32px;
    display: flex; align-items: center; justify-content: center;
}
.info-panel h4 { margin: 0 0 4px 0; font-size: 12.5px; color: #1E3A8A; font-weight: 800; }
.info-panel p { margin: 0; font-size: 11.5px; color: #3B5B8C; line-height: 1.55; }
.protocol-chips { display: flex; flex-wrap: wrap; gap: 7px; margin-top: 9px; }
.protocol-chip {
    background: #FFFFFF; border: 1px solid #BFDBFE; color: #1D4ED8;
    border-radius: 6px; padding: 3px 8px; font-size: 9.5px;
    font-weight: 800; letter-spacing: 0.05em;
}

.upload-note {
    display: flex; align-items: center; gap: 7px; margin-top: 6px;
    font-size: 10.5px; color: #94A3B8;
}

/* --------------------------------------------------------------------- */
/* Divers                                                                 */
/* --------------------------------------------------------------------- */
[data-testid="stDataFrame"] {
    border: 1px solid #E9EEF6 !important;
    border-radius: 12px !important;
    overflow: hidden;
}
[data-testid="stFileUploaderDropzone"] {
    background: #F8FAFC;
    border: 1px dashed #C9D5E4;
    border-radius: 11px;
    padding: 10px;
}
[data-testid="stForm"] { border: none; padding: 0; }
div[data-testid="stExpander"] {
    border: 1px solid #E5EAF2; border-radius: 12px; background: #FFFFFF;
}
.stButton > button, .stDownloadButton > button {
    border-radius: 9px; font-weight: 700; font-size: 12.5px;
    border: 1px solid #DCE4EF;
}
.stButton > button[kind="primary"], .stFormSubmitButton > button[kind="primary"] {
    background: #1D4ED8; border-color: #1D4ED8;
}
[data-testid="stSegmentedControl"] button {
    font-size: 11.5px; font-weight: 700;
}
[data-testid="stSelectbox"] label p,
[data-testid="stDateInput"] label p,
[data-testid="stMultiSelect"] label p,
[data-testid="stNumberInput"] label p,
[data-testid="stTextInput"] label p,
[data-testid="stFileUploader"] label p {
    font-size: 11px; font-weight: 700; color: #475569;
    letter-spacing: 0.01em;
}
.filter-bar {
    display: flex; align-items: center; gap: 8px;
    color: #64748B; font-size: 11px; padding-bottom: 2px;
    flex-wrap: wrap;
}
.filter-bar svg { color: #2563EB; }
.filter-bar strong { color: #0B2545; }

.page-footer {
    margin-top: 30px; padding-top: 14px;
    border-top: 1px solid #E2E8F2;
    display: flex; justify-content: space-between; flex-wrap: wrap; gap: 8px;
    color: #94A3B8; font-size: 10.5px;
}
.page-footer strong { color: #475569; }

.empty-note {
    text-align: center; color: #94A3B8; font-size: 12px;
    padding: 24px 10px;
}

/* --------------------------------------------------------------------- */
/* Responsive                                                             */
/* --------------------------------------------------------------------- */
@media (max-width: 1400px) {
    .kpi-grid { grid-template-columns: repeat(3, minmax(0, 1fr)); }
    .kpi-grid.cols-4 { grid-template-columns: repeat(4, minmax(0, 1fr)); }
    .balance-stats { grid-template-columns: repeat(3, minmax(0, 1fr)); }
}
@media (max-width: 1100px) {
    .sensor-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
    .stat-grid, .stat-grid.cols-5 { grid-template-columns: repeat(2, minmax(0, 1fr)); }
    .page-header { flex-direction: column; gap: 14px; }
    .header-side { align-items: flex-start; flex-direction: row; flex-wrap: wrap; }
}
@media (max-width: 800px) {
    .block-container { padding-left: 1rem; padding-right: 1rem; }
    .kpi-grid, .kpi-grid.cols-4 { grid-template-columns: repeat(2, minmax(0, 1fr)); }
    .alert-grid { grid-template-columns: 1fr; }
    .balance-stats { grid-template-columns: repeat(2, minmax(0, 1fr)); }
    .page-header h1 { font-size: 23px; }
    .kpi-value { font-size: 22px; }
}
@media (max-width: 560px) {
    .kpi-grid, .kpi-grid.cols-4 { grid-template-columns: 1fr; }
    .sensor-grid { grid-template-columns: 1fr; }
    .stat-grid, .stat-grid.cols-3, .stat-grid.cols-5 { grid-template-columns: 1fr; }
    .balance-stats { grid-template-columns: 1fr; }
    .dataset-facts { grid-template-columns: 1fr 1fr; }
}
</style>
"""


def inject_css() -> None:
    """Injecte la feuille de style globale (une fois par exécution)."""
    st.markdown(CSS, unsafe_allow_html=True)
