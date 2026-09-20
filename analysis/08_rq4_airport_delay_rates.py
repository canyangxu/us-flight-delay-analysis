"""
RQ4: Where are delays more common?

Chart:
Arrival delay rate at the 20 largest U.S. origin airports.

Purpose:
Show that airport context matters.

Airport selection:
Top 20 origin airports by scheduled flight volume.

Delay definition:
Arrival delay >= 15 minutes.
"""

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick

from _config import (
    DATA_FILE,
    CHART_DIR,
    CHART_DATA_DIR,
    NAVY,
    GRAY,
    LIGHT_GRAY,
    DARK_TEXT,
    SOURCE_NOTE,
    apply_chart_style
)

apply_chart_style()

USECOLS = [
    "ORIGIN",
    "ORIGIN_CITY_NAME",
    "ARR_DEL15"
]

airport_data = {}

print("Reading data for RQ4 - airport delay rates...")

for chunk in pd.read_csv(
    DATA_FILE,
    usecols=USECOLS,
    chunksize=250_000
):

    scheduled = (
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

    for key, count in scheduled.items():

        if key not in airport_data:
            airport_data[key] = {
                "scheduled_flights": 0,
                "delayed_flights": 0,
                "valid_arrival_flights": 0
            }

        airport_data[key]["scheduled_flights"] += count

    for key, row in delay_group.iterrows():

        airport_data[key]["delayed_flights"] += row["sum"]
        airport_data[key]["valid_arrival_flights"] += row["count"]


rows = []

for (airport, city), values in airport_data.items():

    delay_rate = (
        values["delayed_flights"]
        / values["valid_arrival_flights"]
        if values["valid_arrival_flights"] > 0
        else 0
    )

    rows.append({
        "airport": airport,
        "city": city,
        "scheduled_flights":
            int(values["scheduled_flights"]),
        "valid_arrival_flights":
            int(values["valid_arrival_flights"]),
        "delayed_flights":
            int(values["delayed_flights"]),
        "delay_rate": delay_rate
    })


df = pd.DataFrame(rows)

top20 = (
    df
    .nlargest(20, "scheduled_flights")
    .sort_values("delay_rate", ascending=True)
    .reset_index(drop=True)
)

overall_rate = (
    top20["delayed_flights"].sum()
    / top20["valid_arrival_flights"].sum()
)


data_output = (
    CHART_DATA_DIR
    / "08_rq4_airport_delay_rates.csv"
)

top20.to_csv(
    data_output,
    index=False
)


fig, ax = plt.subplots(
    figsize=(12, 8)
)

y = range(len(top20))


ax.barh(
    y,
    top20["delay_rate"],
    color=NAVY,
    height=0.62
)


ax.axvline(
    overall_rate,
    color=GRAY,
    linestyle="--",
    linewidth=1.5
)


ax.text(
    overall_rate + 0.002,
    len(top20) - 0.3,
    f"Top-20 average {overall_rate:.1%}",
    color=GRAY,
    fontsize=9
)


for i, row in top20.iterrows():

    ax.text(
        row["delay_rate"] + 0.002,
        i,
        f"{row['delay_rate']:.1%}",
        va="center",
        fontsize=9,
        color=DARK_TEXT
    )


ax.set_yticks(list(y))

ax.set_yticklabels(
    [
        f"{row.airport} — {row.city}"
        for _, row in top20.iterrows()
    ]
)


ax.set_title(
    "Airport context matters: delay rates vary widely across major hubs",
    loc="left",
    fontsize=17,
    fontweight="bold",
    pad=18
)


ax.text(
    0,
    1.01,
    (
        "Top 20 origin airports by scheduled flight volume. "
        "The airport is part of the delay environment—not just the airline."
    ),
    transform=ax.transAxes,
    fontsize=10,
    color=GRAY
)


ax.set_xlabel(
    "Arrival delay rate"
)

ax.set_ylabel("")


ax.xaxis.set_major_formatter(
    mtick.PercentFormatter(1.0)
)


ax.grid(
    axis="x",
    color=LIGHT_GRAY,
    linewidth=0.8
)

ax.grid(
    axis="y",
    visible=False
)


ax.text(
    0,
    -0.10,
    SOURCE_NOTE
    + " Top 20 airports selected by scheduled origin flight volume.",
    transform=ax.transAxes,
    fontsize=8,
    color=GRAY
)


plt.tight_layout()


chart_output = (
    CHART_DIR
    / "08_rq4_airport_delay_rates.png"
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

print("\nHighest among top 20:")

highest = top20.loc[
    top20["delay_rate"].idxmax()
]

print(
    highest["airport"],
    f"{highest['delay_rate']:.1%}"
)

print("\nLowest among top 20:")

lowest = top20.loc[
    top20["delay_rate"].idxmin()
]

print(
    lowest["airport"],
    f"{lowest['delay_rate']:.1%}"
)