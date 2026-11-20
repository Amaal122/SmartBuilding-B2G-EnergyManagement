"""Tests unitaires de la simulation de batterie."""

from __future__ import annotations

import unittest

import numpy as np
import pandas as pd

from data.data_validation import validate_battery_parameters
from services.battery_simulation import (
    BatteryParams,
    check_energy_conservation,
    simulate_dispatch,
    summarize_dispatch,
)
from services.economic_analysis import EconomicAssumptions, analyze


class TestBatterySimulation(unittest.TestCase):
    def test_validation(self) -> None:
        valid = validate_battery_parameters(
            capacity_kwh=200,
            initial_soc_pct=50,
            max_charge_kw=50,
            max_discharge_kw=50,
            charge_efficiency=0.95,
            discharge_efficiency=0.95,
            min_soc_pct=10,
            max_soc_pct=95,
        )
        self.assertTrue(valid["valid"])
        invalid = validate_battery_parameters(
            capacity_kwh=200,
            initial_soc_pct=120,
            max_charge_kw=50,
            max_discharge_kw=50,
            charge_efficiency=0.95,
            discharge_efficiency=0.95,
            min_soc_pct=10,
            max_soc_pct=95,
        )
        self.assertFalse(invalid["valid"])

    def test_energy_conservation(self) -> None:
        params = BatteryParams(
            capacity_kwh=100,
            initial_soc_pct=50,
            max_charge_kw=30,
            max_discharge_kw=30,
            charge_efficiency=0.9,
            discharge_efficiency=0.9,
            min_soc_pct=10,
            max_soc_pct=95,
        )
        consumption = np.array([20.0, 40.0, 10.0, 60.0, 30.0] * 5)
        solar = np.array([0.0, 50.0, 60.0, 10.0, 5.0] * 5)
        result = simulate_dispatch(consumption, solar, params)
        check = check_energy_conservation(result)
        self.assertTrue(check["consistent"], check)
        self.assertLess(check["pv_balance_max_error"], 1e-9)
        self.assertLess(check["load_balance_max_error"], 1e-9)

    def test_soc_limits_and_power_limits(self) -> None:
        params = BatteryParams(
            capacity_kwh=50,
            initial_soc_pct=90,
            max_charge_kw=5,
            max_discharge_kw=7,
            charge_efficiency=1.0,
            discharge_efficiency=1.0,
            min_soc_pct=20,
            max_soc_pct=95,
        )
        result = simulate_dispatch(
            np.full(48, 50.0), np.full(48, 100.0), params
        )
        self.assertLessEqual(result["battery_soc"].max(), 95.0 + 1e-9)
        self.assertGreaterEqual(result["battery_soc"].min(), 20.0 - 1e-9)
        self.assertLessEqual(result["battery_charge_kwh"].max(), 5.0 + 1e-9)
        self.assertLessEqual(result["battery_discharge_kwh"].max(), 7.0 + 1e-9)

    def test_efficiency_losses(self) -> None:
        params = BatteryParams(
            capacity_kwh=100,
            initial_soc_pct=50,
            max_charge_kw=100,
            max_discharge_kw=100,
            charge_efficiency=0.8,
            discharge_efficiency=0.8,
            min_soc_pct=0,
            max_soc_pct=100,
        )
        result = simulate_dispatch([0.0, 100.0], [100.0, 0.0], params)
        summary = summarize_dispatch(result, params)
        # SOC initial 50 % = 50 kWh stockés ; seuls 50 kWh peuvent être ajoutés,
        # soit 62,5 kWh prélevés au PV avec un rendement de charge de 0,8.
        self.assertAlmostEqual(result["battery_charge_kwh"].iloc[0], 62.5)
        self.assertAlmostEqual(result["battery_energy_kwh"].iloc[0], 100.0)
        self.assertAlmostEqual(result["battery_discharge_kwh"].iloc[1], 80.0)
        self.assertAlmostEqual(summary["losses"], 32.5)

    def test_zero_capacity_equals_no_battery(self) -> None:
        params = BatteryParams(capacity_kwh=0)
        consumption = np.array([30.0, 50.0])
        solar = np.array([10.0, 70.0])
        result = simulate_dispatch(consumption, solar, params)
        np.testing.assert_allclose(result["grid_import_kwh"], [20.0, 0.0])
        np.testing.assert_allclose(result["grid_export_kwh"], [0.0, 20.0])
        self.assertTrue(np.isnan(result["battery_soc"]).all())

    def test_real_frame_reduction(self) -> None:
        from data.data_processing import build_scenario_frame

        frame = build_scenario_frame(520, 0.75, 200.0)
        if frame.empty:
            self.skipTest("Jeux de données réels absents.")
        params = BatteryParams()
        result = simulate_dispatch(
            frame["consumption_kwh"], frame["solar_production_kwh"], params,
            timestamps=frame["timestamp"],
        )
        baseline_import = frame["grid_import_kwh"].sum()
        with_battery = result["grid_import_kwh"].sum()
        self.assertLessEqual(with_battery, baseline_import)
        self.assertTrue(check_energy_conservation(result)["consistent"])


class TestEconomicAnalysis(unittest.TestCase):
    def test_payback_and_savings(self) -> None:
        before = {"grid_import": 1000.0, "grid_export": 200.0}
        after = {"grid_import": 600.0, "grid_export": 100.0}
        result = analyze(
            before, after, EconomicAssumptions(import_price=0.3, export_price=0.05),
            hours=100, capacity_kwh=100,
        )
        self.assertAlmostEqual(result["cost_before"], 290.0)
        self.assertAlmostEqual(result["cost_after"], 175.0)
        self.assertAlmostEqual(result["savings_period"], 115.0)
        self.assertAlmostEqual(result["annual_savings"], 115.0 * 87.6)
        self.assertGreater(result["payback_years"], 0)
        self.assertTrue(result["is_estimate"])

    def test_zero_annual_savings(self) -> None:
        result = analyze(
            {"grid_import": 100, "grid_export": 0},
            {"grid_import": 100, "grid_export": 0},
            EconomicAssumptions(), hours=100,
        )
        self.assertIsNone(result["payback_years"])


if __name__ == "__main__":
    unittest.main()
