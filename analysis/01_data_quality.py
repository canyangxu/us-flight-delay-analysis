"""
Data Quality Check

Purpose:
Validate the combined BTS dataset before analysis.

Checks:
- Total number of rows
- Date coverage
- Number of airlines
- Number of origin airports
- Number of destination airports
- Delayed flight rate
- Cancellation rate
"""

import pandas as pd

from _config import DATA_FILE, CHART_DATA_DIR


USECOLS = [
    "FL_DATE",
    "OP_UNIQUE_CARRIER",
    "ORIGIN",
    "DEST",
    "ARR_DEL15",
    "CANCELLED"
]


total_rows = 0
delayed_flights = 0
valid_arrival_flights = 0
cancelled_flights = 0

airlines = set()
origin_airports = set()
destination_airports = set()

first_date = None
last_date = None


print("Reading dataset...")


for chunk in pd.read_csv(
    DATA_FILE,
    usecols=USECOLS,
    chunksize=250_000
):

    total_rows += len(chunk)

    chunk["FL_DATE"] = pd.to_datetime(
        chunk["FL_DATE"],
        errors="coerce"
    )

    chunk_first_date = chunk["FL_DATE"].min()
    chunk_last_date = chunk["FL_DATE"].max()

    if first_date is None or chunk_first_date < first_date:
        first_date = chunk_first_date

    if last_date is None or chunk_last_date > last_date:
        last_date = chunk_last_date

    airlines.update(
        chunk["OP_UNIQUE_CARRIER"]
        .dropna()
        .unique()
    )

    origin_airports.update(
        chunk["ORIGIN"]
        .dropna()
        .unique()
    )

    destination_airports.update(
        chunk["DEST"]
        .dropna()
        .unique()
    )

    cancelled_flights += (
        chunk["CANCELLED"] == 1
    ).sum()

    valid_arrivals = chunk["ARR_DEL15"].notna()

    valid_arrival_flights += valid_arrivals.sum()

    delayed_flights += (
        chunk.loc[
            valid_arrivals,
            "ARR_DEL15"
        ] == 1
    ).sum()


arrival_delay_rate = (
    delayed_flights
    / valid_arrival_flights
)

cancellation_rate = (
    cancelled_flights
    / total_rows
)


summary = pd.DataFrame({
    "Metric": [
        "Total flight records",
        "Start date",
        "End date",
        "Airlines",
        "Origin airports",
        "Destination airports",
        "Valid arrival records",
        "Flights delayed >=15 min",
        "Arrival delay rate",
        "Cancelled flights",
        "Cancellation rate"
    ],

    "Value": [
        total_rows,
        first_date.date(),
        last_date.date(),
        len(airlines),
        len(origin_airports),
        len(destination_airports),
        valid_arrival_flights,
        delayed_flights,
        arrival_delay_rate,
        cancelled_flights,
        cancellation_rate
    ]
})


output_file = (
    CHART_DATA_DIR
    / "01_data_quality_summary.csv"
)

summary.to_csv(
    output_file,
    index=False
)


print("\n" + "=" * 55)
print("DATA QUALITY SUMMARY")
print("=" * 55)

print(f"Total rows: {total_rows:,}")
print(f"Date range: {first_date.date()} to {last_date.date()}")
print(f"Airlines: {len(airlines)}")
print(f"Origin airports: {len(origin_airports)}")
print(f"Destination airports: {len(destination_airports)}")

print(
    f"Arrival delay rate: "
    f"{arrival_delay_rate:.1%}"
)

print(
    f"Cancellation rate: "
    f"{cancellation_rate:.1%}"
)

print("\nSaved:")
print(output_file)