"""
RQ5: When should passengers fly?

Chart:
Arrival delay rate by day of week and scheduled departure time.

Purpose:
Combine day-of-week and time-of-day effects into one practical view.

Main interpretation:
Time of day has the strongest visible pattern, but day of week
still shifts the level of risk.
"""

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
from matplotlib.colors import LinearSegmentedColormap

from _config import (
    DATA_FILE,
    CHART_DIR,
    CHART_DATA_DIR,
    NAVY,
    LIGHT_GRAY,
    DARK_TEXT,
    GRAY,
    SOURCE_NOTE,
    apply_chart_style
)

apply_chart_style()


USECOLS = [
    "DAY_OF_WEEK",
    "DEP_TIME_BLK",
    "ARR_DEL15"
]


summary = {}


print("Reading data for RQ5 - best time to fly...")


for chunk in pd.read_csv(
    DATA_FILE,
    usecols=USECOLS,
    chunksize=250_000
):

    valid = chunk[
        chunk["ARR_DEL15"].notna()
    ]

    grouped = (
        valid
        .groupby(
            [
                "DAY_OF_WEEK",
                "DEP_TIME_BLK"
            ]
        )["ARR_DEL15"]
        .agg(["sum", "count"])
    )


    for key, row in grouped.iterrows():

        if key not in summary:

            summary[key] = {
                "delayed": 0,
                "valid_flights": 0
            }

        summary[key]["delayed"] += row["sum"]
        summary[key]["valid_flights"] += row["count"]


rows = []


for (day, block), values in summary.items():

    rows.append({
        "day_of_week": int(day),
        "departure_time_block": block,
        "delayed_flights":
            int(values["delayed"]),
        "valid_arrival_flights":
            int(values["valid_flights"]),
        "delay_rate":
            values["delayed"]
            / values["valid_flights"]
    })


df = pd.DataFrame(rows)


def block_start(block):

    return int(
        str(block).split("-")[0]
    )


df["sort_time"] = (
    df["departure_time_block"]
    .apply(block_start)
)


time_order = (
    df[
        [
            "departure_time_block",
            "sort_time"
        ]
    ]
    .drop_duplicates()
    .sort_values("sort_time")[
        "departure_time_block"
    ]
    .tolist()
)


day_names = {
    1: "Monday",
    2: "Tuesday",
    3: "Wednesday",
    4: "Thursday",
    5: "Friday",
    6: "Saturday",
    7: "Sunday"
}


pivot = (
    df
    .pivot(
        index="day_of_week",
        columns="departure_time_block",
        values="delay_rate"
    )
    .reindex(
        index=range(1, 8),
        columns=time_order
    )
)


data_output = (
    CHART_DATA_DIR
    / "10_rq5_best_time_to_fly.csv"
)

df.drop(
    columns=["sort_time"]
).to_csv(
    data_output,
    index=False
)


cmap = LinearSegmentedColormap.from_list(
    "delay_heatmap",
    [
        "#F4F6F8",
        "#AFC5D8",
        NAVY
    ]
)


fig, ax = plt.subplots(
    figsize=(14, 7)
)


image = ax.imshow(
    pivot.values,
    cmap=cmap,
    aspect="auto"
)


ax.set_yticks(
    range(7)
)

ax.set_yticklabels(
    [
        day_names[i]
        for i in range(1, 8)
    ]
)


def short_label(block):

    start = int(
        str(block).split("-")[0]
    )

    if start == 1:
        return "Before 6"

    hour = start // 100

    return f"{hour:02d}:00"


ax.set_xticks(
    range(len(time_order))
)

ax.set_xticklabels(
    [
        short_label(block)
        for block in time_order
    ],
    rotation=45,
    ha="right"
)


for i in range(
    pivot.shape[0]
):

    for j in range(
        pivot.shape[1]
    ):

        value = pivot.iloc[i, j]

        if pd.notna(value):

            text_color = (
                "white"
                if value > 0.27
                else DARK_TEXT
            )

            ax.text(
                j,
                i,
                f"{value:.0%}",
                ha="center",
                va="center",
                fontsize=8,
                color=text_color
            )


ax.set_title(
    "Time of day matters most—but day of week still shifts the risk",
    loc="left",
    fontsize=17,
    fontweight="bold",
    pad=18
)


ax.text(
    0,
    1.02,
    (
        "Morning departures are consistently less likely to arrive 15+ minutes late; "
        "risk builds sharply into the evening."
    ),
    transform=ax.transAxes,
    fontsize=10,
    color=GRAY
)


ax.set_xlabel(
    "Scheduled departure time"
)

ax.set_ylabel("")


colorbar = fig.colorbar(
    image,
    ax=ax,
    fraction=0.025,
    pad=0.02
)

colorbar.ax.yaxis.set_major_formatter(
    mtick.PercentFormatter(1.0)
)

colorbar.set_label(
    "Arrival delay rate"
)


ax.text(
    0,
    -0.23,
    SOURCE_NOTE
    + " Delay = arrival >=15 minutes.",
    transform=ax.transAxes,
    fontsize=8,
    color=GRAY
)


plt.tight_layout()


chart_output = (
    CHART_DIR
    / "10_rq5_best_time_to_fly.png"
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


best = (
    df.loc[
        df["delay_rate"].idxmin()
    ]
)

worst = (
    df.loc[
        df["delay_rate"].idxmax()
    ]
)


print("\nLowest-risk combination:")

print(
    day_names[
        best["day_of_week"]
    ],
    best["departure_time_block"],
    f"{best['delay_rate']:.1%}"
)


print("\nHighest-risk combination:")

print(
    day_names[
        worst["day_of_week"]
    ],
    worst["departure_time_block"],
    f"{worst['delay_rate']:.1%}"
)