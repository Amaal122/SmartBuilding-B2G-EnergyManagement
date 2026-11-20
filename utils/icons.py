"""Bibliothèque d'icônes SVG inline.

Les icônes sont dessinées en trait (style « engineering dashboard ») et
héritent de la couleur du texte via ``currentColor``. Aucune police ni
ressource externe n'est nécessaire.
"""

from __future__ import annotations

PATHS: dict[str, str] = {
    "bolt": '<path d="M13 2 4.4 13.2a.9.9 0 0 0 .7 1.5h4.9L9 22l8.8-11.3a.9.9 0 0 0-.7-1.5h-5L13 2Z"/>',
    "sun": '<circle cx="12" cy="12" r="4.1"/><path d="M12 2v2.2M12 19.8V22M4.9 4.9l1.6 1.6M17.5 17.5l1.6 1.6M2 12h2.2M19.8 12H22M4.9 19.1l1.6-1.6M17.5 6.5l1.6-1.6"/>',
    "grid": '<path d="M8.5 22 10.6 2h2.8L15.5 22M6 7.2h12M6.9 12h10.2M7.8 16.8h8.4M4.5 22h15"/>',
    "battery": '<rect x="2.2" y="7" width="16.6" height="10" rx="2.4"/><path d="M22 10.2v3.6M5.4 10.2v3.6"/>',
    "battery-charge": '<rect x="2.2" y="7" width="16.6" height="10" rx="2.4"/><path d="M22 10.2v3.6M11.4 8.6l-2 3.4h2.4l-1.2 3.4"/>',
    "building": '<path d="M3 21h18M5.5 21V6.6L12 3l6.5 3.6V21"/><path d="M9.2 9.2h.01M14.8 9.2h.01M9.2 13h.01M14.8 13h.01M9.2 16.8h.01M14.8 16.8h.01M10.5 21v-2.2h3V21"/>',
    "gauge": '<path d="M3.4 18a9 9 0 1 1 17.2 0"/><path d="m12.8 14.4 4.1-4.1"/><circle cx="12" cy="15.2" r="1.6"/><path d="M5 18h14"/>',
    "leaf": '<path d="M20.4 3.6C10.2 3.6 4 8.2 4 14.8A5.2 5.2 0 0 0 9.2 20c6.6 0 11.2-6.2 11.2-16.4Z"/><path d="M4 20.4c2.2-5.6 6.6-9.4 12.6-11.6"/>',
    "alert": '<path d="M10.3 3.6 2.5 17.1A2 2 0 0 0 4.2 20h15.6a2 2 0 0 0 1.7-2.9L13.7 3.6a2 2 0 0 0-3.4 0Z"/><path d="M12 9v4M12 16.6h.01"/>',
    "info": '<circle cx="12" cy="12" r="9.2"/><path d="M12 11v5M12 7.7h.01"/>',
    "check": '<circle cx="12" cy="12" r="9.2"/><path d="m8.2 12.2 2.5 2.5 5.2-5.4"/>',
    "activity": '<path d="M3 12h4l2.4-6 4.2 12 2.4-6h5"/>',
    "thermometer": '<path d="M10 13.6V5a2 2 0 1 1 4 0v8.6a4.2 4.2 0 1 1-4 0Z"/><path d="M12 9.4v6.2"/>',
    "droplet": '<path d="M12 2.8s6.2 6.4 6.2 10.3a6.2 6.2 0 1 1-12.4 0C5.8 9.2 12 2.8 12 2.8Z"/>',
    "users": '<circle cx="9" cy="8" r="3.3"/><path d="M2.8 20a6.2 6.2 0 0 1 12.4 0"/><path d="M16.2 5.4a3.3 3.3 0 0 1 0 5.6M18.6 20a6.2 6.2 0 0 0-2.6-4.9"/>',
    "bulb": '<path d="M9.2 18h5.6M10.2 21.4h3.6"/><path d="M12 2.4A6.2 6.2 0 0 0 7.8 13c.9.8 1.4 1.7 1.6 2.7h5.2c.2-1 .7-1.9 1.6-2.7A6.2 6.2 0 0 0 12 2.4Z"/>',
    "hvac": '<circle cx="12" cy="12" r="2.1"/><path d="M12 9.9c0-3.2 1.1-5.4 3.7-5.4s2.6 3.5-.4 5M14.1 12c3.2 0 5.4 1.1 5.4 3.7s-3.5 2.6-5-.4M12 14.1c0 3.2-1.1 5.4-3.7 5.4s-2.6-3.5.4-5M9.9 12c-3.2 0-5.4-1.1-5.4-3.7s3.5-2.6 5 .4"/>',
    "database": '<ellipse cx="12" cy="5.2" rx="8.2" ry="3.1"/><path d="M3.8 5.2v6.4c0 1.7 3.7 3.1 8.2 3.1s8.2-1.4 8.2-3.1V5.2"/><path d="M3.8 11.6V18c0 1.7 3.7 3.1 8.2 3.1s8.2-1.4 8.2-3.1v-6.4"/>',
    "sliders": '<path d="M4 6.5h6M14.5 6.5H20M4 12h2.5M11 12h9M4 17.5h8M16.5 17.5H20"/><circle cx="12.2" cy="6.5" r="2.1"/><circle cx="8.7" cy="12" r="2.1"/><circle cx="14.3" cy="17.5" r="2.1"/>',
    "upload": '<path d="M12 15.8V3.8M7.6 8.2 12 3.8l4.4 4.4"/><path d="M4 14.8V18a2.2 2.2 0 0 0 2.2 2.2h11.6A2.2 2.2 0 0 0 20 18v-3.2"/>',
    "clock": '<circle cx="12" cy="12" r="9.2"/><path d="M12 6.8V12l3.4 2.2"/>',
    "trend-up": '<path d="m3.5 17 6-6 3.8 3.8L20.5 7.6"/><path d="M15.5 7.6h5v5"/>',
    "trend-down": '<path d="m3.5 7 6 6 3.8-3.8 7.2 7.2"/><path d="M15.5 16.4h5v-5"/>',
    "arrow-up-right": '<path d="M6.5 17.5 17.5 6.5M8.5 6.5h9v9"/>',
    "plug": '<path d="M9 2.5v5.7M15 2.5v5.7M6 8.2h12v3.1a6 6 0 0 1-12 0V8.2ZM12 17.3v4.2"/>',
    "shield": '<path d="M12 21.8s7.8-3.4 7.8-9.7V5.4L12 2.4 4.2 5.4v6.7c0 6.3 7.8 9.7 7.8 9.7Z"/><path d="m8.8 11.8 2.2 2.2 4.2-4.4"/>',
    "calendar": '<rect x="3.2" y="5" width="17.6" height="16" rx="2.4"/><path d="M3.2 9.6h17.6M8 2.8v4.4M16 2.8v4.4"/>',
    "euro": '<path d="M18 5.8a7.4 7.4 0 1 0 0 12.4M3.8 9.8h9.4M3.8 14.2h9.4"/>',
    "wifi": '<path d="M2.2 8.6a15.5 15.5 0 0 1 19.6 0M5.6 12.1a10.5 10.5 0 0 1 12.8 0M9 15.6a5.4 5.4 0 0 1 6 0"/><circle cx="12" cy="19.2" r="1.1"/>',
    "wifi-off": '<path d="M2 2 22 22M8.4 16.1a5.4 5.4 0 0 1 6.2-.6M5.2 12.2a10.5 10.5 0 0 1 4-2.1M14.4 9.8a10.5 10.5 0 0 1 4.4 2.3M2.2 8.6a15.5 15.5 0 0 1 4.6-2.7M13.8 5.7a15.5 15.5 0 0 1 8 2.9M12 19.2h.01"/>',
    "file": '<path d="M14 2.5H6.4a2.2 2.2 0 0 0-2.2 2.2v14.6a2.2 2.2 0 0 0 2.2 2.2h11.2a2.2 2.2 0 0 0 2.2-2.2V8.1Z"/><path d="M14 2.5v5.6h5.8M8 13h8M8 17h5"/>',
    "table": '<rect x="3" y="3.5" width="18" height="17" rx="2.2"/><path d="M3 9h18M3 14.8h18M9 3.5v17"/>',
    "server": '<rect x="3" y="3.5" width="18" height="7" rx="2"/><rect x="3" y="13.5" width="18" height="7" rx="2"/><path d="M7 7h.01M7 17h.01M11 7h5M11 17h5"/>',
    "layers": '<path d="m12 2.8 9 4.7-9 4.7-9-4.7 9-4.7Z"/><path d="m3 12.4 9 4.7 9-4.7M3 17.1l9 4.7 9-4.7"/>',
    "refresh": '<path d="M20.2 11a8.2 8.2 0 1 0-2.3 5.8"/><path d="M20.2 4.2v6.9h-6.9"/>',
    "search": '<circle cx="10.8" cy="10.8" r="7.2"/><path d="m16.1 16.1 5.1 5.1"/>',
    "eye": '<path d="M2.2 12S5.6 5.4 12 5.4 21.8 12 21.8 12 18.4 18.6 12 18.6 2.2 12 2.2 12Z"/><circle cx="12" cy="12" r="3.1"/>',
    "download": '<path d="M12 3.8v12M7.6 11.4 12 15.8l4.4-4.4"/><path d="M4 17.8V19a2.2 2.2 0 0 0 2.2 2.2h11.6A2.2 2.2 0 0 0 20 19v-1.2"/>',
    "pie-chart": '<path d="M12 3.2a8.8 8.8 0 1 0 8.8 8.8H12V3.2Z"/><path d="M15.4 2.9a8.8 8.8 0 0 1 5.7 5.7h-5.7V2.9Z"/>',
    "solar-panel": '<rect x="3" y="6" width="18" height="11" rx="1.8"/><path d="M3 11h18M9 6v11M15 6v11M12 17v3M8 20h8"/>',
    "wind": '<path d="M3 8h10.5a2.5 2.5 0 1 0-2.5-2.5M3 12h15a2.5 2.5 0 1 1-2.5 2.5M3 16h8.5a2.5 2.5 0 1 1-2.5 2.5"/>',
    "cloud": '<path d="M7 18h10.2a3.8 3.8 0 0 0 .3-7.6A6 6 0 0 0 6.2 9.5 4.3 4.3 0 0 0 7 18Z"/>',
}


def icon(name: str, size: int = 18, stroke_width: float = 1.8, class_name: str = "") -> str:
    """Retourne un SVG inline prêt à être inséré dans du HTML."""
    inner = PATHS.get(name, PATHS["info"])
    extra_class = f" ico {class_name}".strip()
    return (
        f'<svg class="{extra_class}" width="{size}" height="{size}" viewBox="0 0 24 24" '
        f'fill="none" stroke="currentColor" stroke-width="{stroke_width}" '
        f'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">{inner}</svg>'
    )
