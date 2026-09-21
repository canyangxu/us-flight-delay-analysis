"""Merge monthly CSVs safely; publish output only after every ZIP validates."""
from pathlib import Path
import shutil
import tempfile
import zipfile


def main():
    base = Path(__file__).resolve().parent
    folders = [base / "2025.7-2025.12", base / "2026.1-2026.6"]
    zip_files = [path for folder in folders for path in sorted(folder.glob("*.zip"))]
    if not zip_files:
        raise ValueError("No monthly ZIP files found; existing output was not changed")
    data_folder = base / "data"
    data_folder.mkdir(exist_ok=True)
    output_file = data_folder / "bts_2025_07_to_2026_06.csv"
    # A same-directory temporary file keeps final replacement atomic.
    with tempfile.TemporaryDirectory(prefix="merge-", dir=data_folder) as temporary:
        candidate = Path(temporary) / "merged.csv"
        header = None
        has_rows = False
        with candidate.open("w+b") as output:
            for zip_file in zip_files:
                print("Processing:", zip_file.name)
                with zipfile.ZipFile(zip_file) as archive:
                    members = [name for name in archive.namelist() if name.lower().endswith(".csv")]
                    if len(members) != 1:
                        raise ValueError(f"Expected exactly one CSV in {zip_file.name}")
                    with archive.open(members[0]) as source:
                        current_header = source.readline()
                        if not current_header.strip():
                            raise ValueError(f"Empty CSV header in {zip_file.name}")
                        if header is None:
                            header = current_header
                            output.write(header.rstrip(b"\r\n") + b"\n")
                        elif current_header.strip() != header.strip():
                            raise ValueError(f"Columns do not match: {zip_file.name}")
                        start = output.tell()
                        shutil.copyfileobj(source, output)
                        if output.tell() == start:
                            raise ValueError(f"No flight records in {zip_file.name}")
                        has_rows = True
                        output.seek(-1, 2)
                        last_byte = output.read(1)
                        if last_byte != b"\n":
                            output.write(b"\n")
        if not has_rows:
            raise ValueError("No flight records found; existing output was not changed")
        candidate.replace(output_file)
    print("Merged", len(zip_files), "monthly files into", output_file)


if __name__ == "__main__":
    main()
