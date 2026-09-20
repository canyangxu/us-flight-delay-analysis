from pathlib import Path
import zipfile
import shutil
import duckdb

base = Path(__file__).resolve().parent

folders = [
    base / "2025.7-2025.12",
    base / "2026.1-2026.6"
]

data_folder = base / "data"
extract_folder = data_folder / "extracted"

data_folder.mkdir(exist_ok=True)

if extract_folder.exists():
    shutil.rmtree(extract_folder)

extract_folder.mkdir()

output_file = data_folder / "bts_2025_07_to_2026_06.parquet"


# find all zip files
zip_files = []

for folder in folders:
    zip_files.extend(sorted(folder.glob("*.zip")))

print("Number of zip files:", len(zip_files))


# extract monthly csv files
for i, zip_file in enumerate(zip_files, start=1):

    print("Extracting:", zip_file.name)

    with zipfile.ZipFile(zip_file, "r") as z:

        csv_files = [
            name for name in z.namelist()
            if name.lower().endswith(".csv")
        ]

        if len(csv_files) == 0:
            continue

        csv_name = csv_files[0]

        output_csv = extract_folder / f"month_{i:02d}.csv"

        with z.open(csv_name, "r") as source:
            with open(output_csv, "wb") as target:
                shutil.copyfileobj(source, target)


# merge csv files
csv_path = str(extract_folder / "*.csv").replace("\\", "/")
parquet_path = str(output_file).replace("\\", "/")

con = duckdb.connect()

con.execute(f"""
    COPY (
        SELECT *
        FROM read_csv_auto(
            '{csv_path}',
            header = true,
            union_by_name = true
        )
    )
    TO '{parquet_path}'
    (FORMAT PARQUET);
""")


# simple check
result = con.execute(f"""
    SELECT
        COUNT(*) AS total_rows,
        MIN(FL_DATE) AS first_date,
        MAX(FL_DATE) AS last_date
    FROM read_parquet('{parquet_path}')
""").fetchone()

con.close()


print("\nMerge finished.")
print("Rows:", f"{result[0]:,}")
print("Start date:", result[1])
print("End date:", result[2])
print("Output:", output_file)