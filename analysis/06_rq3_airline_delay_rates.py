"""
RQ3: How much do airlines differ in delay performance?

Chart:
Arrival delay rate by airline.

Purpose:
Establish that airline-level performance differences exist.

But:
A simple ranking cannot explain why the airlines differ.
The next chart decomposes each airline's delay causes.

Delay definition:
Arrival delay >= 15 minutes (ARR_DEL15 = 1).
"""

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick

from _config import (
    DATA_FILE,
    CHART_DIR,
    CHART_DATA_DIR,
    NAVY,
    LIGHT_GRAY,
    GRAY,
    DARK_TEXT,
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


USECOLS = [
    "OP_UNIQUE_CARRIER",
    "ARR_DEL15"
]


airlines = {}

total_delayed = 0
total_valid = 0


print("Reading data for RQ3 - airline delay rates...")


# =========================================================
# 2. Aggregate chunks
# =========================================================

for chunk in pd.read_csv(
    DATA_FILE,
    usecols=USECOLS,
    chunksize=250_000
):

    # total scheduled flights
    scheduled = (
        chunk
        .groupby(
            "OP_UNIQUE_CARRIER"
        )
        .size()
    )

    # only flights with valid arrival status
    valid = chunk[
        chunk["ARR_DEL15"].notna()
    ]

    grouped = (
        valid
        .groupby(
            "OP_UNIQUE_CARRIER"
        )["ARR_DEL15"]
        .agg(["sum", "count"])
    )

    for airline, flights in scheduled.items():

        if airline not in airlines:

            airlines[airline] = {
                "scheduled_flights": 0,
                "delayed_flights": 0,
                "valid_arrival_flights": 0
            }

        airlines[airline][
            "scheduled_flights"
        ] += flights

    for airline, row in grouped.iterrows():

        airlines[airline][
            "delayed_flights"
        ] += row["sum"]

        airlines[airline][
            "valid_arrival_flights"
        ] += row["count"]

        total_delayed += row["sum"]

        total_valid += row["count"]


# =========================================================
# 3. Summary table
# =========================================================

rows = []


for airline, values in airlines.items():

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

    rows.append({
        "airline_code": airline,
        "airline_name": airline_name,
        "display_name":
            f"{airline_name} ({airline})",
        "scheduled_flights":
            int(values["scheduled_flights"]),
        "valid_arrival_flights":
            int(values["valid_arrival_flights"]),
        "delayed_flights":
            int(values["delayed_flights"]),
        "delay_rate":
            delay_rate
    })


df = pd.DataFrame(rows)


df = (
    df
    .sort_values(
        "delay_rate",
        ascending=False
    )
    .reset_index(drop=True)
)


overall_rate = (
    total_delayed
    / total_valid
)


# =========================================================
# 4. Save data
# =========================================================

data_output = (
    CHART_DATA_DIR
    / "06_rq3_airline_delay_rates.csv"
)


df.to_csv(
    data_output,
    index=False
)


# =========================================================
# 5. Lollipop chart
# =========================================================

fig, ax = plt.subplots(
    figsize=(12, 7.5)
)


plot_df = (
    df
    .sort_values(
        "delay_rate",
        ascending=True
    )
    .reset_index(drop=True)
)


y = range(
    len(plot_df)
)


for i, row in plot_df.iterrows():

    ax.hlines(
        y=i,
        xmin=min(
            overall_rate,
            row["delay_rate"]
        ),
        xmax=max(
            overall_rate,
            row["delay_rate"]
        ),
        color=LIGHT_GRAY,
        linewidth=6,
        zorder=1
    )


ax.scatter(
    plot_df["delay_rate"],
    list(y),
    s=95,
    color=NAVY,
    zorder=2
)


# Overall line
ax.axvline(
    overall_rate,
    color=GRAY,
    linestyle="--",
    linewidth=1.5
)


ax.text(
    overall_rate + 0.002,
    len(plot_df) - 0.15,
    f"Overall {overall_rate:.1%}",
    color=GRAY,
    fontsize=10
)


# Labels
for i, row in plot_df.iterrows():

    ax.text(
        row["delay_rate"] + 0.002,
        i,
        f"{row['delay_rate']:.1%}",
        va="center",
        fontsize=9,
        color=DARK_TEXT
    )


ax.set_yticks(
    list(y)
)

ax.set_yticklabels(
    plot_df["display_name"]
)


ax.set_title(
    "Airline delay rates vary by nearly 9 percentage points",
    loc="left",
    fontsize=17,
    fontweight="bold",
    pad=18
)


ax.text(
    0,
    1.01,
    (
        "Performance differs, but the next chart shows why "
        "a single delay-rate ranking can hide very different underlying causes."
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
    -0.11,
    SOURCE_NOTE
    + " Delay = arrival >=15 minutes (ARR_DEL15).",
    transform=ax.transAxes,
    fontsize=8,
    color=GRAY
)


plt.tight_layout()


# =========================================================
# 6. Save
# =========================================================

chart_output = (
    CHART_DIR
    / "06_rq3_airline_delay_rates.png"
)


plt.savefig(
    chart_output,
    dpi=300,
    bbox_inches="tight"
)

plt.close()


# =========================================================
# 7. Print findings
# =========================================================

highest = df.iloc[0]

lowest = df.iloc[-1]

gap = (
    highest["delay_rate"]
    - lowest["delay_rate"]
)


print("\nChart created:")
print(chart_output)

print("\nChart data saved:")
print(data_output)

print(
    "\nHighest delay rate:",
    highest["display_name"],
    f"{highest['delay_rate']:.1%}"
)

print(
    "Lowest delay rate:",
    lowest["display_name"],
    f"{lowest['delay_rate']:.1%}"
)

print(
    "Gap:",
    f"{gap:.1%}"
)