"""Analyse économique simplifiée d'un scénario de stockage.

Les prix sont des hypothèses saisies par l'utilisateur, jamais des tarifs
« vérifiés ». Les montants sont des estimations et non des économies
constatées. Aucun investissement réel n'est engagé.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from services.energy_calculations import safe_divide


@dataclass(frozen=True)
class EconomicAssumptions:
    """Hypothèses tarifaires et de coût (devise de l'interface)."""

    import_price: float = 0.2516
    export_price: float = 0.05
    battery_cost_per_kwh: float = 350.0
    pv_cost_per_kwp: float = 900.0
    om_rate_pct: float = 1.0
    lifetime_years: int = 15

    def validated(self) -> "EconomicAssumptions":
        return EconomicAssumptions(
            import_price=float(max(0.0, self.import_price)),
            export_price=float(max(0.0, self.export_price)),
            battery_cost_per_kwh=float(max(0.0, self.battery_cost_per_kwh)),
            pv_cost_per_kwp=float(max(0.0, self.pv_cost_per_kwp)),
            om_rate_pct=float(max(0.0, self.om_rate_pct)),
            lifetime_years=int(max(1, self.lifetime_years)),
        )


def energy_cost(
    grid_import_kwh: float,
    grid_export_kwh: float,
    assumptions: EconomicAssumptions,
) -> dict[str, float]:
    """Coût net de l'énergie sur la période (import payé − export valorisé)."""
    a = assumptions.validated()
    import_cost = float(max(0.0, grid_import_kwh)) * a.import_price
    export_revenue = float(max(0.0, grid_export_kwh)) * a.export_price
    return {
        "import_cost": import_cost,
        "export_revenue": export_revenue,
        "net_cost": import_cost - export_revenue,
    }


def analyze(
    before: dict[str, Any],
    after: dict[str, Any],
    assumptions: EconomicAssumptions,
    *,
    hours: int | None = None,
    capacity_kwh: float = 0.0,
    pv_capacity_kwp: float = 0.0,
) -> dict[str, Any]:
    """Compare économiquement deux scénarios (A sans batterie, B avec).

    ``before`` et ``after`` doivent contenir ``grid_import`` et ``grid_export``
    (ou ``surplus``) en kWh sur la même période.
    """
    a = assumptions.validated()
    before_import = float(before.get("grid_import", 0.0) or 0.0)
    before_export = float(before.get("grid_export", before.get("surplus", 0.0)) or 0.0)
    after_import = float(after.get("grid_import", 0.0) or 0.0)
    after_export = float(after.get("grid_export", after.get("surplus", 0.0)) or 0.0)

    cost_before = energy_cost(before_import, before_export, a)
    cost_after = energy_cost(after_import, after_export, a)
    savings_period = cost_before["net_cost"] - cost_after["net_cost"]

    inferred_hours = int(hours) if hours else max(
        int(before.get("hours", 0) or 0), int(after.get("hours", 0) or 0)
    )
    annual_factor = 8760.0 / inferred_hours if inferred_hours > 0 else None
    annual_savings = (
        savings_period * annual_factor if annual_factor is not None else None
    )

    investment = (
        float(max(0.0, capacity_kwh)) * a.battery_cost_per_kwh
        + float(max(0.0, pv_capacity_kwp)) * a.pv_cost_per_kwp
    )
    om_cost = investment * a.om_rate_pct / 100.0
    payback_years = (
        safe_divide(investment, annual_savings)
        if annual_savings is not None and annual_savings > 0 and investment > 0
        else None
    )
    lifetime_savings = (
        annual_savings * a.lifetime_years - om_cost * a.lifetime_years
        if annual_savings is not None
        else None
    )
    roi_pct = (
        safe_divide(lifetime_savings, investment) * 100.0
        if lifetime_savings is not None and investment > 0
        else None
    )

    return {
        "assumptions": {
            "import_price": a.import_price,
            "export_price": a.export_price,
            "battery_cost_per_kwh": a.battery_cost_per_kwh,
            "pv_cost_per_kwp": a.pv_cost_per_kwp,
            "om_rate_pct": a.om_rate_pct,
            "lifetime_years": a.lifetime_years,
        },
        "before_import_kwh": before_import,
        "before_export_kwh": before_export,
        "after_import_kwh": after_import,
        "after_export_kwh": after_export,
        "cost_before": cost_before["net_cost"],
        "cost_after": cost_after["net_cost"],
        "import_cost_before": cost_before["import_cost"],
        "import_cost_after": cost_after["import_cost"],
        "export_revenue_before": cost_before["export_revenue"],
        "export_revenue_after": cost_after["export_revenue"],
        "savings_period": savings_period,
        "annual_savings": annual_savings,
        "annual_factor": annual_factor,
        "investment": investment,
        "om_cost_annual": om_cost,
        "payback_years": payback_years,
        "lifetime_savings": lifetime_savings,
        "roi_pct": roi_pct,
        "hours": inferred_hours,
        "is_estimate": True,
        "npv_note": (
            "Estimation simple, hors actualisation et hors dégradation. "
            "Aucune économie réelle n'est garantie."
        ),
    }


def scenario_economics(
    before_daily: Any,
    after_daily: Any,
    assumptions: EconomicAssumptions,
) -> dict[str, Any]:
    """Variante pratique : additionne des séries journalières ou horaires."""
    def totals(df: Any, prefix: str) -> dict[str, float]:
        if df is None or len(df) == 0:
            return {"grid_import": 0.0, "grid_export": 0.0}
        import_col = f"{prefix}grid_import_kwh"
        export_col = f"{prefix}grid_export_kwh"
        import_value = float(df[import_col].sum()) if import_col in df else 0.0
        export_value = float(df[export_col].sum()) if export_col in df else 0.0
        return {"grid_import": import_value, "grid_export": export_value}

    before = totals(before_daily, "")
    after = totals(after_daily, "")
    return analyze(before, after, assumptions, hours=len(before_daily))


def cost_per_kwh_savings(savings: float, hours: int) -> float | None:
    """Économie moyenne par heure, utile pour un affichage compact."""
    return safe_divide(savings, hours)
