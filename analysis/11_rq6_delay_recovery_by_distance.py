"""
RQ6: Can flights recover lost time?

Chart:
Average schedule recovery by flight distance.

Population:
Flights that departed late and completed normally
(not cancelled or diverted).

Recovery minutes:
DEP_DELAY - ARR_DELAY

Positive values mean the flight recovered some of its departure delay.
"""

import pandas as pd
import matplotlib.pyplot as plt

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
    "DEP_DELAY",
    "ARR_DELAY",
    "DISTANCE",
    "CANCELLED",
    "DIVERTED"
]


bins = [
    0,
    500,
    1000,
    1500,
    2000,
    float("inf")
]


labels = [
    "<500",
    "500-999",
    "1000-1499",
    "1500-1999",
    "2000+"
]


summary = {
    label: {
        "recovery_sum": 0,
        "flight_count": 0
    }
    for label in labels
}


print("Reading data for RQ6 - delay recovery...")


for chunk in pd.read_csv(
    DATA_FILE,
    usecols=USECOLS,
    chunksize=250_000
):

    valid = chunk[
        (chunk["CANCELLED"] == 0)
        & (chunk["DIVERTED"] == 0)
        & (chunk["DEP_DELAY"] > 0)
        & chunk["ARR_DELAY"].notna()
        & chunk["DISTANCE"].notna()
    ].copy()


    valid["recovery_minutes"] = (
        valid["DEP_DELAY"]
        - valid["ARR_DELAY"]
    )


    valid["distance_group"] = pd.cut(
        valid["DISTANCE"],
        bins=bins,
        labels=labels,
        right=False
    )


    grouped = (
        valid
        .groupby(
            "distance_group",
            observed=True
        )["recovery_minutes"]
        .agg(["sum", "count"])
    )


    for label, row in grouped.iterrows():

        summary[str(label)][
            "recovery_sum"
        ] += row["sum"]

        summary[str(label)][
            "flight_count"
        ] += row["count"]


rows = []


for label in labels:

    values = summary[label]

    average_recovery = (
        values["recovery_sum"]
        / values["flight_count"]
        if values["flight_count"] > 0
        else 0
    )


    rows.append({
        "distance_miles": label,
        "delayed_completed_flights":
            int(values["flight_count"]),
        "average_recovery_minutes":
            average_recovery
    })


df = pd.DataFrame(rows)


data_output = (
    CHART_DATA_DIR
    / "11_rq6_delay_recovery_by_distance.csv"
)

df.to_csv(
    data_output,
    index=False
)


fig, ax = plt.subplots(
    figsize=(11, 6.5)
)


bars = ax.bar(
    df["distance_miles"],
    df["average_recovery_minutes"],
    color=NAVY,
    width=0.62
)


for bar, value in zip(
    bars,
    df["average_recovery_minutes"]
):

    ax.text(
        bar.get_x()
        + bar.get_width() / 2,
        value + 0.2,
        f"{value:.1f}",
        ha="center",
        fontsize=10,
        color=DARK_TEXT
    )


ax.set_title(
    "Longer flights recover more time—but only modestly",
    loc="left",
    fontsize=17,
    fontweight="bold",
    pad=18
)


ax.text(
    0,
    1.01,
    (
        "Among flights that departed late and still completed normally, "
        "longer routes recover more minutes before arrival."
    ),
    transform=ax.transAxes,
    fontsize=10,
    color=GRAY
)


ax.set_xlabel(
    "Flight distance (miles)"
)

ax.set_ylabel(
    "Average minutes recovered"
)


ax.grid(
    axis="y",
    color=LIGHT_GRAY,
    linewidth=0.8
)

ax.grid(
    axis="x",
    visible=False
)


ax.text(
    0,
    -0.15,
    SOURCE_NOTE
    + " Recovery = departure delay minus arrival delay; "
      "cancelled and diverted flights excluded.",
    transform=ax.transAxes,
    fontsize=8,
    color=GRAY
)


plt.tight_layout()


chart_output = (
    CHART_DIR
    / "11_rq6_delay_recovery_by_distance.png"
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

print("\nAverage recovered minutes:")

for _, row in df.iterrows():

    print(
        f"{row['distance_miles']:<10}",
        f"{row['average_recovery_minutes']:.1f} min"
    )