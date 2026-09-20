from pathlib import Path
import zipfile
import shutil

base = Path(__file__).resolve().parent

folders = [
    base / "2025.7-2025.12",
    base / "2026.1-2026.6"
]

data_folder = base / "data"
data_folder.mkdir(exist_ok=True)

output_file = data_folder / "bts_2025_07_to_2026_06.csv"

zip_files = []

for folder in folders:
    zip_files.extend(sorted(folder.glob("*.zip")))

print("Number of zip files:", len(zip_files))

first_file = True
header = None

with open(output_file, "wb") as output:

    for zip_file in zip_files:

        print("Processing:", zip_file.name)

        with zipfile.ZipFile(zip_file, "r") as z:

            csv_files = [
                name for name in z.namelist()
                if name.lower().endswith(".csv")
            ]

            if len(csv_files) == 0:
                continue

            csv_name = csv_files[0]

            with z.open(csv_name, "r") as source:

                current_header = source.readline()

                if first_file:
                    header = current_header
                    output.write(current_header)
                    first_file = False
                else:
                    if current_header.strip() != header.strip():
                        raise ValueError(
                            "Columns do not match: " + zip_file.name
                        )

                shutil.copyfileobj(source, output)


print("\nMerge finished.")
print("Output:", output_file)