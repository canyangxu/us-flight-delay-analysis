"""Small fixtures exercise passenger outcomes without touching real outputs."""
import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "analysis"))


def load_analysis():
    path = ROOT / "analysis" / "12_flight_outcomes_by_time.py"
    spec = importlib.util.spec_from_file_location("outcomes", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class FlightOutcomesTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue((ROOT / "analysis" / "12_flight_outcomes_by_time.py").exists(),
                        "The integrated analysis entry point is missing")
        self.module = load_analysis()

    def frame(self):
        # Expected categories are specified independently of production constants.
        cases = [
            (0, 0, 0, -5, "Completed, not delayed ≥15 min"),
            (0, 0, 0, 14, "Completed, not delayed ≥15 min"),
            (0, 0, 1, 15, "Completed, delayed ≥15 min"),
            (1, 0, "", "", "Cancelled"),
            (0, 1, 1, 30, "Diverted"),
            ("", 0, 0, 0, "Unknown/inconsistent"),
            (2, 0, 0, 0, "Unknown/inconsistent"),
            (1, 1, 0, 0, "Unknown/inconsistent"),
            (0, 0, 0, 15, "Unknown/inconsistent"),
            (0, 0, 1, -5, "Unknown/inconsistent"),
            (0, 0, "", 5, "Unknown/inconsistent"),
            (0, 0, 0, "", "Completed, not delayed ≥15 min"),
            (0, 0, 7, 5, "Unknown/inconsistent"),
            (0, "bad", 0, 0, "Unknown/inconsistent"),
        ]
        df = pd.DataFrame(cases, columns=["CANCELLED", "DIVERTED", "ARR_DEL15", "ARR_DELAY", "expected"])
        df["DEP_TIME_BLK"] = ["0600-0659"] * 12 + ["", "bad"]
        df["FL_DATE"] = "2025-07-01"
        return df

    def test_classification_boundaries(self):
        df = self.frame()
        self.assertEqual(self.module.classify_outcomes(df).tolist(), df.expected.tolist())

    def test_chunking_and_count_conservation(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "input.csv"
            self.frame().drop(columns="expected").to_csv(path, index=False)
            small, global_small, checks = self.module.analyze(path, chunksize=2)
            whole, global_whole, _ = self.module.analyze(path, chunksize=100)
            pd.testing.assert_frame_equal(small, whole)
            pd.testing.assert_frame_equal(global_small, global_whole)
            self.assertEqual(global_small["count"].sum(), 14)
            unknown = small[small.departure_time_block == "Unknown departure time"]
            self.assertEqual(unknown["count"].sum(), 2)
            for _, group in small.groupby("departure_time_block"):
                self.assertEqual(group["count"].sum(), group.total_records.iloc[0])
                self.assertAlmostEqual(group.share.sum(), 1)
            self.assertEqual(checks["completed_arrival_flag_delay_conflict"], 2)
            self.assertEqual(checks["completed_arr_delay_missing"], 1)

    def test_empty_missing_columns_and_bad_chunk_size(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "input.csv"
            self.frame().iloc[:0].to_csv(path, index=False)
            with self.assertRaisesRegex(ValueError, "no flight records"):
                self.module.analyze(path)
            pd.DataFrame({"CANCELLED": [0]}).to_csv(path, index=False)
            with self.assertRaisesRegex(ValueError, "Missing required"):
                self.module.analyze(path)
            with self.assertRaisesRegex(ValueError, "positive"):
                self.module.analyze(path, chunksize=0)

    def test_all_unknown_and_temporary_outputs(self):
        with tempfile.TemporaryDirectory() as directory:
            directory = Path(directory)
            path = directory / "input.csv"
            df = self.frame().iloc[[5]].copy()
            df["DEP_TIME_BLK"] = "bad"
            df.to_csv(path, index=False)
            by_time, overall, checks = self.module.analyze(path)
            self.assertEqual(overall.loc[overall.flight_outcome == "Unknown/inconsistent", "share"].iloc[0], 1)
            self.module.save_results(by_time, overall, checks, directory, directory)
            self.assertTrue((directory / "12_flight_outcomes_by_time.png").is_file())


if __name__ == "__main__":
    unittest.main()
