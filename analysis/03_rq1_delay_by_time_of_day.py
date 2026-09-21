"""
RQ1: When do flight delays happen?

Chart:
Arrival delay rate and late-aircraft share by scheduled departure time.

Purpose:
Examine how delay risk varies across the day and how
Late Aircraft Delay becomes increasingly important later in the day.

Interpretation:
The pattern is consistent with delays accumulating through the airline
network as aircraft complete multiple flights during the day.

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
    GRAY,
    LIGHT_GRAY,
    DARK_TEXT,
    SOURCE_NOTE,
    apply_chart_style
)


apply_chart_style()


# =========================================================
# 1. Columns needed
# =========================================================

USECOLS = [
    "DEP_TIME_BLK",
    "ARR_DEL15",
    "CARRIER_DELAY",
    "WEATHER_DELAY",
    "NAS_DELAY",
    "SECURITY_DELAY",
    "LATE_AIRCRAFT_DELAY"
]


summary = {}


# =========================================================
# 2. Read large CSV in chunks
# =========================================================

print("Reading data for RQ1 - time of day...")


for chunk in pd.read_csv(
    DATA_FILE,
    usecols=USECOLS,
    chunksize=250_000
):

    chunk = chunk.dropna(
        subset=["DEP_TIME_BLK"]
    )

    # -----------------------------------------------------
    # Arrival delay rate
    # -----------------------------------------------------

    valid_arrivals = chunk[
        chunk["ARR_DEL15"].notna()
    ]

    delay_group = (
        valid_arrivals
        .groupby("DEP_TIME_BLK")["ARR_DEL15"]
        .agg(["sum", "count"])
    )

    # -----------------------------------------------------
    # Delay-cause minutes
    # -----------------------------------------------------

    delay_columns = [
        "CARRIER_DELAY",
        "WEATHER_DELAY",
        "NAS_DELAY",
        "SECURITY_DELAY",
        "LATE_AIRCRAFT_DELAY"
    ]

    cause_data = chunk[
        ["DEP_TIME_BLK"] + delay_columns
    ].copy()

    cause_data[delay_columns] = (
        cause_data[delay_columns]
        .fillna(0)
    )

    cause_data["TOTAL_DELAY_MINUTES"] = (
        cause_data[delay_columns]
        .sum(axis=1)
    )

    cause_group = (
        cause_data
        .groupby("DEP_TIME_BLK")
        .agg(
            late_aircraft_minutes=(
                "LATE_AIRCRAFT_DELAY",
                "sum"
            ),
            total_delay_minutes=(
                "TOTAL_DELAY_MINUTES",
                "sum"
            )
        )
    )

    # -----------------------------------------------------
    # Combine chunk results
    # -----------------------------------------------------

    all_blocks = (
        set(delay_group.index)
        | set(cause_group.index)
    )

    for block in all_blocks:

        if block not in summary:
            summary[block] = {
                "delayed_flights": 0,
                "valid_arrival_flights": 0,
                "late_aircraft_minutes": 0,
                "total_delay_minutes": 0
            }

        if block in delay_group.index:

            summary[block][
                "delayed_flights"
            ] += delay_group.loc[block, "sum"]

            summary[block][
                "valid_arrival_flights"
            ] += delay_group.loc[block, "count"]

        if block in cause_group.index:

            summary[block][
                "late_aircraft_minutes"
            ] += cause_group.loc[
                block,
                "late_aircraft_minutes"
            ]

            summary[block][
                "total_delay_minutes"
            ] += cause_group.loc[
                block,
                "total_delay_minutes"
            ]


# =========================================================
# 3. Convert to DataFrame
# =========================================================

rows = []

for block, values in summary.items():

    arrival_delay_rate = (
        values["delayed_flights"]
        / values["valid_arrival_flights"]
        if values["valid_arrival_flights"] > 0
        else 0
    )

    late_aircraft_share = (
        values["late_aircraft_minutes"]
        / values["total_delay_minutes"]
        if values["total_delay_minutes"] > 0
        else 0
    )

    rows.append({
        "departure_time_block": block,
        "delayed_flights": int(
            values["delayed_flights"]
        ),
        "valid_arrival_flights": int(
            values["valid_arrival_flights"]
        ),
        "arrival_delay_rate":
            arrival_delay_rate,
        "late_aircraft_delay_minutes":
            values["late_aircraft_minutes"],
        "total_recorded_delay_minutes":
            values["total_delay_minutes"],
        "late_aircraft_share":
            late_aircraft_share
    })


df = pd.DataFrame(rows)


# =========================================================
# 4. Sort time blocks
# =========================================================

def time_sort_key(block):

    try:
        return int(
            str(block).split("-")[0]
        )
    except ValueError:
        return 9999


df["sort_key"] = (
    df["departure_time_block"]
    .apply(time_sort_key)
)

df = (
    df
    .sort_values("sort_key")
    .reset_index(drop=True)
)


# Short labels for chart
def short_time_label(block):

    start = str(block).split("-")[0]

    if start == "0001":
        return "00:01-05:59"

    hour = int(start) // 100

    return f"{hour:02d}"


df["time_label"] = (
    df["departure_time_block"]
    .apply(short_time_label)
)


# =========================================================
# 5. Save chart data
# =========================================================

data_output = (
    CHART_DATA_DIR
    / "03_rq1_delay_by_time_of_day.csv"
)

df.drop(
    columns=["sort_key"]
).to_csv(
    data_output,
    index=False
)


# =========================================================
# 6. Create chart
# =========================================================

fig, axes = plt.subplots(
    1,
    2,
    figsize=(14, 6.5)
)

ax1, ax2 = axes


# ---------------------------------------------------------
# Left: arrival delay rate
# ---------------------------------------------------------

ax1.plot(
    df["time_label"],
    df["arrival_delay_rate"],
    color=NAVY,
    linewidth=2.6,
    marker="o",
    markersize=5
)

ax1.fill_between(
    range(len(df)),
    df["arrival_delay_rate"],
    alpha=0.08,
    color=NAVY
)

ax1.set_title(
    "Delay risk peaks in the evening, then declines",
    loc="left",
    fontsize=14,
    fontweight="bold",
    pad=12
)

ax1.set_ylabel(
    "Arrival delay rate"
)

ax1.set_xlabel(
    "Scheduled local departure block"
)

ax1.yaxis.set_major_formatter(
    mtick.PercentFormatter(1.0)
)

ax1.grid(
    axis="y",
    color=LIGHT_GRAY,
    linewidth=0.8
)

ax1.grid(
    axis="x",
    visible=False
)


# Label first and highest value
first_row = df.iloc[0]

peak_delay_row = df.loc[
    df["arrival_delay_rate"].idxmax()
]

ax1.annotate(
    f"{first_row['arrival_delay_rate']:.1%}",
    (
        0,
        first_row["arrival_delay_rate"]
    ),
    xytext=(4, 10),
    textcoords="offset points",
    fontsize=9,
    color=DARK_TEXT
)

peak_index = (
    df["arrival_delay_rate"]
    .idxmax()
)

ax1.annotate(
    f"{peak_delay_row['arrival_delay_rate']:.1%}",
    (
        peak_index,
        peak_delay_row["arrival_delay_rate"]
    ),
    xytext=(0, 12),
    textcoords="offset points",
    ha="center",
    fontsize=9,
    fontweight="bold",
    color=NAVY
)


# ---------------------------------------------------------
# Right: late aircraft share
# ---------------------------------------------------------

ax2.plot(
    df["time_label"],
    df["late_aircraft_share"],
    color=NAVY,
    linewidth=2.6,
    marker="o",
    markersize=5
)

ax2.fill_between(
    range(len(df)),
    df["late_aircraft_share"],
    alpha=0.08,
    color=NAVY
)

ax2.set_title(
    "Late-aircraft share peaks in the evening",
    loc="left",
    fontsize=14,
    fontweight="bold",
    pad=12
)

ax2.set_ylabel(
    "Late Aircraft share of recorded delay minutes"
)

ax2.set_xlabel(
    "Scheduled local departure block"
)

ax2.yaxis.set_major_formatter(
    mtick.PercentFormatter(1.0)
)

ax2.grid(
    axis="y",
    color=LIGHT_GRAY,
    linewidth=0.8
)

ax2.grid(
    axis="x",
    visible=False
)


late_peak_index = (
    df["late_aircraft_share"]
    .idxmax()
)

late_peak = df.loc[
    late_peak_index
]

ax2.annotate(
    f"{late_peak['late_aircraft_share']:.1%}",
    (
        late_peak_index,
        late_peak["late_aircraft_share"]
    ),
    xytext=(0, 12),
    textcoords="offset points",
    ha="center",
    fontsize=9,
    fontweight="bold",
    color=NAVY
)


# =========================================================
# 7. Overall title and source
# =========================================================

fig.suptitle(
    "Delay risk rises toward evening, then falls late at night",
    fontsize=18,
    fontweight="bold",
    x=0.06,
    ha="left",
    y=1.02
)

fig.text(
    0.06,
    0.94,
    (
        "Observed patterns are consistent with network delay accumulation; "
        "these associations do not establish the cause of each delay."
    ),
    fontsize=10,
    color=GRAY
)

fig.text(
    0.06,
    -0.01,
    SOURCE_NOTE
    + " Delay = arrival >=15 minutes. "
      "Cause shares use recorded BTS delay minutes. 00:01-05:59 is a combined block.",
    fontsize=8,
    color=GRAY
)


for ax in axes:
    ax.tick_params(axis="x", labelrotation=45, labelsize=9)
    for label in ax.get_xticklabels():
        label.set_horizontalalignment("right")
    ax.set_ylim(bottom=0)

plt.tight_layout(
    rect=[0.04, 0.05, 0.98, 0.90]
)


# =========================================================
# 8. Save figure
# =========================================================

chart_output = (
    CHART_DIR
    / "03_rq1_delay_by_time_of_day.png"
)

plt.savefig(
    chart_output,
    dpi=300,
    bbox_inches="tight"
)

plt.close()


# =========================================================
# 9. Print summary
# =========================================================

print("\nChart created:")
print(chart_output)

print("\nChart data saved:")
print(data_output)

print("\nKey results:")

print(
    "Earliest block delay rate:",
    f"{df.iloc[0]['arrival_delay_rate']:.1%}"
)

print(
    "Peak delay rate:",
    f"{df['arrival_delay_rate'].max():.1%}"
)

print(
    "Peak late-aircraft share:",
    f"{df['late_aircraft_share'].max():.1%}"
)