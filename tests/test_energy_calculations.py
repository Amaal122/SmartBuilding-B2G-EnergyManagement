"""Tests unitaires des calculs énergétiques et du pipeline de données."""

from __future__ import annotations

import unittest

import numpy as np
import pandas as pd

from data import data_cleaning, data_processing, data_validation
from services import energy_calculations as energy


class TestEnergyCalculations(unittest.TestCase):
    def setUp(self) -> None:
        self.df = pd.DataFrame(
            {
                "timestamp": pd.date_range("2016-05-13", periods=72, freq="h"),
                "consumption_kwh": np.tile([10.0, 20.0, 30.0], 24),
                "solar_production_kwh": np.tile([0.0, 15.0, 5.0], 24),
            }
        )

    def test_safe_divide_zero_and_none(self) -> None:
        self.assertIsNone(energy.safe_divide(10, 0))
        self.assertIsNone(energy.safe_divide(None, 5))
        self.assertEqual(energy.safe_divide(10, 4), 2.5)

    def test_grid_balance_no_double_counting(self) -> None:
        flows = energy.grid_flows(self.df["consumption_kwh"], self.df["solar_production_kwh"])
        self.assertTrue(np.all(flows["grid_import"] >= 0))
        self.assertTrue(np.all(flows["grid_export"] >= 0))
        self.assertTrue(
            np.all(flows["self_consumed"] + flows["grid_import"] == self.df["consumption_kwh"])
        )
        self.assertTrue(
            np.all(flows["self_consumed"] + flows["grid_export"] == self.df["solar_production_kwh"])
        )

    def test_ratios_are_distinct(self) -> None:
        self.assertEqual(energy.self_consumption_ratio(100, 40), 40.0)
        self.assertEqual(energy.self_sufficiency_ratio(200, 40), 20.0)
        self.assertIsNone(energy.self_consumption_ratio(0, 0))

    def test_kpis(self) -> None:
        kpis = energy.energy_kpis(self.df)
        self.assertAlmostEqual(kpis["consumption"], 1440.0)
        self.assertAlmostEqual(kpis["solar"], 480.0)
        self.assertAlmostEqual(kpis["peak_power_kw"], 30.0)
        self.assertEqual(kpis["hours"], 72)
        self.assertAlmostEqual(kpis["autoconsumption"], 100.0)
        self.assertAlmostEqual(kpis["self_sufficiency"], 100.0 * 20.0 / 60.0)

    def test_daily_and_hourly_aggregations(self) -> None:
        daily = energy.daily_summary(self.df)
        self.assertEqual(len(daily), 3)
        profile = energy.hourly_profile(self.df)
        self.assertEqual(len(profile), 24)
        self.assertAlmostEqual(profile["consumption_kwh"].sum(), 480.0)

    def test_anomaly_detection(self) -> None:
        frame = self.df.copy()
        frame.loc[10, "consumption_kwh"] = 500.0
        anomalies = energy.detect_anomalies(frame, z_threshold=2.5)
        self.assertFalse(anomalies.empty)
        expected_timestamp = frame.loc[10, "timestamp"]
        self.assertTrue((anomalies["timestamp"] == expected_timestamp).any())
        self.assertTrue((anomalies["zscore"].abs() >= 2.5).all())

    def test_anomaly_small_sample(self) -> None:
        self.assertTrue(energy.detect_anomalies(self.df.head(5)).empty)


class TestDataPipeline(unittest.TestCase):
    def test_solar_mapping(self) -> None:
        dates = pd.Series(pd.to_datetime(["2020-05-15 00:00:00", "2020-06-17 23:00:00"]))
        mapped = data_processing.map_solar_timestamps(dates)
        self.assertEqual(mapped.iloc[0], pd.Timestamp("2016-05-13 00:00:00"))
        self.assertEqual(mapped.iloc[1], pd.Timestamp("2016-06-15 23:00:00"))

    def test_real_scenario_matches_reference(self) -> None:
        frame = data_processing.build_scenario_frame(520, 0.75, 200.0)
        if frame.empty:
            self.skipTest("Jeux de données réels absents.")
        self.assertEqual(len(frame), 744)
        self.assertAlmostEqual(frame["consumption_kwh"].sum(), 36309.35, places=1)
        self.assertAlmostEqual(frame["solar_production_kwh"].sum(), 27232.0125, places=1)
        kpis = energy.energy_kpis(frame)
        self.assertAlmostEqual(kpis["autoconsumption"], 70.65, places=1)
        self.assertAlmostEqual(kpis["self_sufficiency"], 52.99, places=1)

    def test_zones_and_end_use_conserve_total(self) -> None:
        frame = data_processing.build_scenario_frame(520, 0.75, 200.0)
        if frame.empty:
            self.skipTest("Jeux de données réels absents.")
        total = frame["consumption_kwh"].sum()
        self.assertAlmostEqual(data_processing.build_zone_frame(frame)["consumption_kwh"].sum(), total, places=4)
        self.assertAlmostEqual(data_processing.build_end_use_frame(frame)["consumption_kwh"].sum(), total, places=4)

    def test_validation_detects_broken_balance(self) -> None:
        df = pd.DataFrame(
            {
                "timestamp": pd.date_range("2016-01-01", periods=5, freq="h"),
                "consumption_kwh": [10.0] * 5,
                "solar_production_kwh": [4.0] * 5,
                "grid_import_kwh": [99.0] * 5,
                "grid_export_kwh": [0.0] * 5,
                "battery_soc": [50.0] * 5,
                "temperature_outdoor": [20.0] * 5,
            }
        )
        report = data_validation.validate_scenario(df)
        self.assertFalse(report["valid"])
        self.assertTrue(any("bilan" in error.lower() for error in report["errors"]))

    def test_cleaning_duplicates_and_negative(self) -> None:
        df = pd.DataFrame(
            {
                "timestamp": ["2016-01-01 00:00", "2016-01-01 00:00", "2016-01-01 01:00"],
                "meter_reading": [10.0, 12.0, -3.0],
            }
        )
        cleaned = data_cleaning.clean_timeseries(df, "timestamp", ["meter_reading"])
        self.assertEqual(len(cleaned), 2)
        self.assertEqual(cleaned["meter_reading"].iloc[0], 12.0)
        self.assertEqual(cleaned["meter_reading"].iloc[1], 0.0)

    def test_eligible_buildings(self) -> None:
        options = data_processing.building_options()
        if not options:
            self.skipTest("Jeux de données réels absents.")
        self.assertGreaterEqual(len(options), 150)
        self.assertTrue(any(option["id"] == 520 for option in options))


if __name__ == "__main__":
    unittest.main()
