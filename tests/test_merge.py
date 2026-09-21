"""Merging must preserve existing output on missing or malformed input."""
import importlib.util
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]


class MergeTests(unittest.TestCase):
    def run_script(self, directory):
        script = directory / "merge_bts_to_csv.py"
        script.write_text((ROOT / script.name).read_text())
        return subprocess.run([sys.executable, str(script)], capture_output=True, text=True)

    def test_no_input_preserves_existing_output(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            (directory / "data").mkdir()
            output = directory / "data/bts_2025_07_to_2026_06.csv"
            output.write_text("existing data\n")
            result = self.run_script(directory)
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(output.read_text(), "existing data\n")

    def test_mismatched_headers_preserve_output_and_valid_merge(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            (directory / "data").mkdir()
            output = directory / "data/bts_2025_07_to_2026_06.csv"
            output.write_text("existing data\n")
            folder = directory / "2025.7-2025.12"
            folder.mkdir()
            with zipfile.ZipFile(folder / "a.zip", "w") as archive:
                archive.writestr("month.csv", "A,B\n1,2\n")
            with zipfile.ZipFile(folder / "b.zip", "w") as archive:
                archive.writestr("month.csv", "A,C\n3,4\n")
            result = self.run_script(directory)
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(output.read_text(), "existing data\n")
            with zipfile.ZipFile(folder / "b.zip", "w") as archive:
                archive.writestr("month.csv", "A,B\n3,4\n")
            result = self.run_script(directory)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(output.read_text(), "A,B\n1,2\n3,4\n")

    @unittest.skipUnless(importlib.util.find_spec("duckdb"), "optional DuckDB is not installed")
    def test_parquet_no_input_and_valid_merge(self):
        import duckdb
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            script = directory / "merge_bts.py"
            script.write_text((ROOT / script.name).read_text())
            (directory / "data").mkdir()
            output = directory / "data/bts_2025_07_to_2026_06.parquet"
            output.write_bytes(b"existing data")
            result = subprocess.run([sys.executable, str(script)], capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(output.read_bytes(), b"existing data")
            # Existing extracted files belong to the user and must survive.
            extracted = directory / "data/extracted"
            extracted.mkdir(exist_ok=True)
            sentinel = extracted / "keep.txt"
            sentinel.write_text("keep")
            folder = directory / "2025.7-2025.12"
            folder.mkdir()
            with zipfile.ZipFile(folder / "a.zip", "w") as archive:
                archive.writestr("month.csv", "FL_DATE,A\n2025-07-01,1\n")
            result = subprocess.run([sys.executable, str(script)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(sentinel.exists())
            with duckdb.connect() as connection:
                count = connection.execute("SELECT count(*) FROM read_parquet(?)", [str(output)]).fetchone()[0]
            self.assertEqual(count, 1)
