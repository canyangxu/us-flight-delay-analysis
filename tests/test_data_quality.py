import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "analysis"))


class QualityTests(unittest.TestCase):
    def load(self):
        path = ROOT / "analysis" / "_quality.py"
        self.assertTrue(path.exists(), "Reusable quality checks are missing")
        spec = importlib.util.spec_from_file_location("quality", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def test_cross_chunk_duplicates_missing_flags_and_dates(self):
        quality = self.load()
        row = dict(FL_DATE="2025-07-01", OP_UNIQUE_CARRIER="AA", OP_CARRIER_FL_NUM="1",
                   ORIGIN="JFK", DEST="LAX", CRS_DEP_TIME="0600", DEP_TIME_BLK="0600-0659",
                   CANCELLED="0", DIVERTED="0", ARR_DEL15="0", ARR_DELAY="-1")
        # Same full row reappears across chunks. A third shares only its flight key.
        rows = [row, dict(row, FL_DATE="bad", CANCELLED=""), row.copy(), dict(row, ARR_DELAY="-2"),
                dict(row, FL_DATE="2026-07-01", CANCELLED="2"),
                dict(row, FL_DATE="2025-08-01", ARR_DELAY="15")]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "input.csv"
            pd.DataFrame(rows).to_csv(path, index=False)
            summary, checks, months, dates = quality.audit(path, chunksize=2)
            lookup = checks.set_index("check")["count"]
            self.assertEqual(lookup["full_row_duplicate_excess"], 1)
            self.assertEqual(lookup["candidate_key_duplicate_excess"], 2)
            self.assertEqual(lookup["CANCELLED_missing"], 1)
            self.assertEqual(lookup["CANCELLED_invalid"], 1)
            self.assertEqual(lookup["date_parse_failures"], 1)
            self.assertEqual(lookup["date_outside_expected_range"], 1)
            self.assertEqual(lookup["completed_arrival_flag_delay_conflict"], 1)
            self.assertEqual(len(months), 12)
            self.assertEqual(len(dates), 363)
            self.assertEqual(int(summary.set_index("Metric").loc["Total flight records", "Value"]), 6)

    def test_empty_input_and_undefined_arrival_rate(self):
        quality = self.load()
        row = dict(FL_DATE="", OP_UNIQUE_CARRIER="AA", OP_CARRIER_FL_NUM="1",
                   ORIGIN="JFK", DEST="LAX", CRS_DEP_TIME="0600", DEP_TIME_BLK="0600-0659",
                   CANCELLED="1", DIVERTED="0", ARR_DEL15="", ARR_DELAY="")
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "input.csv"
            pd.DataFrame([row]).to_csv(path, index=False)
            summary, _, _, _ = quality.audit(path)
            self.assertTrue(pd.isna(summary.set_index("Metric").loc["Arrival delay rate", "Value"]))
            pd.DataFrame([row]).iloc[:0].to_csv(path, index=False)
            with self.assertRaisesRegex(ValueError, "no flight records"):
                quality.audit(path)


if __name__ == "__main__":
    unittest.main()
