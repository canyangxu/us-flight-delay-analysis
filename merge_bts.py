"""Optional DuckDB Parquet merge with temporary extraction and atomic output."""
from pathlib import Path
import shutil
import tempfile
import zipfile

import duckdb


def main():
    base = Path(__file__).resolve().parent
    folders = [base / "2025.7-2025.12", base / "2026.1-2026.6"]
    zip_files = [path for folder in folders for path in sorted(folder.glob("*.zip"))]
    if not zip_files:
        raise ValueError("No monthly ZIP files found; existing output was not changed")
    data_folder = base / "data"
    data_folder.mkdir(exist_ok=True)
    output_file = data_folder / "bts_2025_07_to_2026_06.parquet"
    with tempfile.TemporaryDirectory(prefix="parquet-merge-", dir=data_folder) as temporary:
        temporary = Path(temporary)
        header = None
        for i, zip_file in enumerate(zip_files):
            with zipfile.ZipFile(zip_file) as archive:
                members = [name for name in archive.namelist() if name.lower().endswith(".csv")]
                if len(members) != 1:
                    raise ValueError(f"Expected exactly one CSV in {zip_file.name}")
                with archive.open(members[0]) as source:
                    current_header = source.readline()
                    if not current_header.strip():
                        raise ValueError(f"Empty CSV header in {zip_file.name}")
                    if header is not None and current_header.strip() != header.strip():
                        raise ValueError(f"Columns do not match: {zip_file.name}")
                    header = current_header
                    with (temporary / f"month_{i:02d}.csv").open("wb") as target:
                        target.write(header)
                        first_record = source.readline()
                        if not first_record.strip():
                            raise ValueError(f"No flight records in {zip_file.name}")
                        target.write(first_record)
                        shutil.copyfileobj(source, target)
        candidate = temporary / "merged.parquet"
        # SQL path literals escape apostrophes in user directory names.
        csv_path = str(temporary / "*.csv").replace("'", "''")
        parquet_path = str(candidate).replace("'", "''")
        with duckdb.connect() as connection:
            connection.execute(f"COPY (SELECT * FROM read_csv_auto('{csv_path}', header=true)) "
                               f"TO '{parquet_path}' (FORMAT PARQUET)")
            result = connection.execute(
                "SELECT COUNT(*), MIN(FL_DATE), MAX(FL_DATE) FROM read_parquet(?)", [str(candidate)]
            ).fetchone()
        if not result[0]:
            raise ValueError("No flight records; existing output was not changed")
        candidate.replace(output_file)
    print(f"Rows: {result[0]:,}; date range: {result[1]} to {result[2]}")
    print("Output:", output_file)


if __name__ == "__main__":
    main()
