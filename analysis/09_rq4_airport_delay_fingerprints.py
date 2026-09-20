"""
RQ4: Why do airports differ?

Chart:
Delay-cause fingerprints for the 10 largest origin airports.

Purpose:
Show that airports can have very different delay mechanisms.

Cause shares:
Based on recorded BTS delay minutes.
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


CAUSE_COLUMNS = {
    "Carrier": "CARRIER_DELAY",
    "Weather": "WEATHER_DELAY",
    "NAS": "NAS_DELAY",
    "Security": "SECURITY_DELAY",
    "Late Aircraft": "LATE_AIRCRAFT_DELAY"
}


USECOLS = [
    "ORIGIN",
    "ORIGIN_CITY_NAME",
    "ARR_DEL15",
    "CARRIER_DELAY",
    "WEATHER_DELAY",
    "NAS_DELAY",
    "SECURITY_DELAY",
    "LATE_AIRCRAFT_DELAY"
]


airports = {}


print("Reading data for RQ4 - airport delay fingerprints...")


for chunk in pd.read_csv(
    DATA_FILE,
    usecols=USECOLS,
    chunksize=250_000
):

    cause_cols = list(
        CAUSE_COLUMNS.values()
    )

    chunk[cause_cols] = (
        chunk[cause_cols]
        .fillna(0)
    )

    flight_counts = (
        chunk
        .groupby(["ORIGIN", "ORIGIN_CITY_NAME"])
        .size()
    )

    valid = chunk[
        chunk["ARR_DEL15"].notna()
    ]

    delay_group = (
        valid
        .groupby(["ORIGIN", "ORIGIN_CITY_NAME"])["ARR_DEL15"]
        .agg(["sum", "count"])
    )

    cause_group = (
        chunk
        .groupby(["ORIGIN", "ORIGIN_CITY_NAME"])[cause_cols]
        .sum()
    )


    all_keys = (
        set(flight_counts.index)
        | set(cause_group.index)
    )


    for key in all_keys:

        if key not in airports:

            airports[key] = {
                "scheduled_flights": 0,
                "delayed_flights": 0,
                "valid_arrival_flights": 0,
                **{
                    cause: 0.0
                    for cause in CAUSE_COLUMNS
                }
            }


        if key in flight_counts.index:

            airports[key][
                "scheduled_flights"
            ] += flight_counts.loc[key]


        if key in delay_group.index:

            airports[key][
                "delayed_flights"
            ] += delay_group.loc[
                key,
                "sum"
            ]

            airports[key][
                "valid_arrival_flights"
            ] += delay_group.loc[
                key,
                "count"
            ]


        if key in cause_group.index:

            for cause, column in CAUSE_COLUMNS.items():

                airports[key][cause] += (
                    cause_group.loc[
                        key,
                        column
                    ]
                )


rows = []


for (airport, city), values in airports.items():

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


    row = {
        "airport": airport,
        "city": city,
        "display_name":
            f"{airport} — {city}",
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


data_output = (
    CHART_DATA_DIR
    / "09_rq4_airport_delay_fingerprints.csv"
)

top10.to_csv(
    data_output,
    index=False
)


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
    "Major airports have distinct delay fingerprints",
    loc="left",
    fontsize=17,
    fontweight="bold",
    pad=18
)


ax.text(
    0,
    1.01,
    (
        "Top 10 origin airports by flight volume. "
        "The same observed delay rate can reflect different operational problems."
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
    + " Cause shares use recorded BTS delay minutes.",
    transform=ax.transAxes,
    fontsize=8,
    color=GRAY
)


plt.tight_layout()


chart_output = (
    CHART_DIR
    / "09_rq4_airport_delay_fingerprints.png"
)

plt.savefig(
    chart_output,
    dpi=300,
    bbox_inches="tight"
)

plt.close()


print("\nChart created:")
print(chart_output)

print("\nChart data saved:")
print(data_output)