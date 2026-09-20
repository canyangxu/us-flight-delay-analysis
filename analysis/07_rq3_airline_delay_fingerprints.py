"""
RQ3: Why do airline delay rates differ?

Chart:
Delay-cause fingerprints for the 10 largest airlines by flight volume.

Purpose:
Show that the same observed "delay" can have very different
underlying causes across airlines.

Cause shares:
Calculated from recorded BTS delay minutes.
"""

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
import numpy as np

from _config import (
    DATA_FILE,
    CHART_DIR,
    CHART_DATA_DIR,
    CAUSE_COLORS,
    GRAY,
    SOURCE_NOTE,
    apply_chart_style
)


apply_chart_style()


# =========================================================
# 1. Airline names
# =========================================================

AIRLINE_NAMES = {
    "AA": "American",
    "AS": "Alaska",
    "B6": "JetBlue",
    "DL": "Delta",
    "F9": "Frontier",
    "G4": "Allegiant",
    "HA": "Hawaiian",
    "MQ": "Envoy",
    "NK": "Spirit",
    "OH": "PSA",
    "OO": "SkyWest",
    "UA": "United",
    "WN": "Southwest",
    "YX": "Republic"
}


CAUSE_COLUMNS = {
    "Carrier": "CARRIER_DELAY",
    "Weather": "WEATHER_DELAY",
    "NAS": "NAS_DELAY",
    "Security": "SECURITY_DELAY",
    "Late Aircraft": "LATE_AIRCRAFT_DELAY"
}


USECOLS = [
    "OP_UNIQUE_CARRIER",
    "ARR_DEL15",
    "CARRIER_DELAY",
    "WEATHER_DELAY",
    "NAS_DELAY",
    "SECURITY_DELAY",
    "LATE_AIRCRAFT_DELAY"
]


airlines = {}


print("Reading data for RQ3 - airline delay fingerprints...")


# =========================================================
# 2. Aggregate
# =========================================================

for chunk in pd.read_csv(
    DATA_FILE,
    usecols=USECOLS,
    chunksize=250_000
):

    cause_columns = list(
        CAUSE_COLUMNS.values()
    )

    chunk[cause_columns] = (
        chunk[cause_columns]
        .fillna(0)
    )

    # flight volume
    flight_counts = (
        chunk
        .groupby(
            "OP_UNIQUE_CARRIER"
        )
        .size()
    )

    # arrival delay rate
    valid = chunk[
        chunk["ARR_DEL15"].notna()
    ]

    delay_group = (
        valid
        .groupby(
            "OP_UNIQUE_CARRIER"
        )["ARR_DEL15"]
        .agg(["sum", "count"])
    )

    # cause minutes
    cause_group = (
        chunk
        .groupby(
            "OP_UNIQUE_CARRIER"
        )[cause_columns]
        .sum()
    )

    airline_codes = (
        set(flight_counts.index)
        | set(cause_group.index)
    )

    for airline in airline_codes:

        if airline not in airlines:

            airlines[airline] = {
                "scheduled_flights": 0,
                "delayed_flights": 0,
                "valid_arrival_flights": 0,
                **{
                    cause: 0.0
                    for cause in CAUSE_COLUMNS
                }
            }

        if airline in flight_counts.index:

            airlines[airline][
                "scheduled_flights"
            ] += flight_counts.loc[
                airline
            ]

        if airline in delay_group.index:

            airlines[airline][
                "delayed_flights"
            ] += delay_group.loc[
                airline,
                "sum"
            ]

            airlines[airline][
                "valid_arrival_flights"
            ] += delay_group.loc[
                airline,
                "count"
            ]

        if airline in cause_group.index:

            for cause, column in CAUSE_COLUMNS.items():

                airlines[airline][cause] += (
                    cause_group.loc[
                        airline,
                        column
                    ]
                )


# =========================================================
# 3. Build summary table
# =========================================================

rows = []


for airline, values in airlines.items():

    total_delay_minutes = sum(
        values[cause]
        for cause in CAUSE_COLUMNS
    )

    delay_rate = (
        values["delayed_flights"]
        / values["valid_arrival_flights"]
        if values["valid_arrival_flights"] > 0
        else 0
    )

    airline_name = (
        AIRLINE_NAMES.get(
            airline,
            airline
        )
    )

    row = {
        "airline_code": airline,
        "airline_name": airline_name,
        "display_name":
            f"{airline_name} ({airline})",
        "scheduled_flights":
            int(values["scheduled_flights"]),
        "delay_rate":
            delay_rate,
        "total_recorded_delay_minutes":
            total_delay_minutes
    }

    for cause in CAUSE_COLUMNS:

        row[
            f"{cause}_minutes"
        ] = values[cause]

        row[
            f"{cause}_share"
        ] = (
            values[cause]
            / total_delay_minutes
            if total_delay_minutes > 0
            else 0
        )

    rows.append(row)


df = pd.DataFrame(rows)


# =========================================================
# 4. Select top 10 by flight volume
# =========================================================

top10 = (
    df
    .nlargest(
        10,
        "scheduled_flights"
    )
    .sort_values(
        "delay_rate",
        ascending=False
    )
    .reset_index(drop=True)
)


# =========================================================
# 5. Save chart data
# =========================================================

data_output = (
    CHART_DATA_DIR
    / "07_rq3_airline_delay_fingerprints.csv"
)


top10.to_csv(
    data_output,
    index=False
)


# =========================================================
# 6. Create stacked bar chart
# =========================================================

fig, ax = plt.subplots(
    figsize=(13, 7.5)
)


y = np.arange(
    len(top10)
)


left = np.zeros(
    len(top10)
)


cause_order = [
    "Carrier",
    "Weather",
    "NAS",
    "Security",
    "Late Aircraft"
]


for cause in cause_order:

    values = (
        top10[
            f"{cause}_share"
        ]
        .values
    )

    ax.barh(
        y,
        values,
        left=left,
        color=CAUSE_COLORS[cause],
        label=cause,
        height=0.64
    )

    left += values


# Invert so highest delay rate appears at top
ax.invert_yaxis()


ax.set_yticks(y)

ax.set_yticklabels(
    top10["display_name"]
)


ax.set_xlim(
    0,
    1
)


ax.xaxis.set_major_formatter(
    mtick.PercentFormatter(1.0)
)


ax.set_xlabel(
    "Share of recorded delay minutes"
)

ax.set_ylabel("")


ax.set_title(
    'The same "delay" can mean very different things across airlines',
    loc="left",
    fontsize=17,
    fontweight="bold",
    pad=18
)


ax.text(
    0,
    1.01,
    (
        "Top 10 carriers by flight volume. "
        "Cause mix is based on recorded delay minutes, not total flights."
    ),
    transform=ax.transAxes,
    fontsize=10,
    color=GRAY
)


ax.legend(
    ncol=5,
    frameon=False,
    loc="upper center",
    bbox_to_anchor=(0.5, -0.10)
)


ax.grid(
    axis="x",
    alpha=0.20
)

ax.grid(
    axis="y",
    visible=False
)


ax.text(
    0,
    -0.19,
    SOURCE_NOTE
    + " Cause shares use recorded delay minutes.",
    transform=ax.transAxes,
    fontsize=8,
    color=GRAY
)


plt.tight_layout()


# =========================================================
# 7. Save chart
# =========================================================

chart_output = (
    CHART_DIR
    / "07_rq3_airline_delay_fingerprints.png"
)


plt.savefig(
    chart_output,
    dpi=300,
    bbox_inches="tight"
)

plt.close()


# =========================================================
# 8. Print
# =========================================================

print("\nChart created:")
print(chart_output)

print("\nChart data saved:")
print(data_output)

print("\nTop 10 airlines by flight volume:")

for _, row in top10.iterrows():

    print(
        f"{row['display_name']:<22}",
        f"{int(row['scheduled_flights']):,}",
        "flights |",
        f"delay rate {row['delay_rate']:.1%}"
    )