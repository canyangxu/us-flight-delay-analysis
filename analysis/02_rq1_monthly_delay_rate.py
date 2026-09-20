"""
RQ1: When do flight delays happen?

Chart:
Monthly arrival delay rate.

Purpose:
Show that delay risk changes throughout the year,
before moving to the stronger time-of-day pattern.

Delay definition:
Arrival delay of at least 15 minutes (ARR_DEL15 = 1).
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


# ---------------------------------------------------------
# Read and aggregate data
# ---------------------------------------------------------

monthly_data = {}


for chunk in pd.read_csv(
    DATA_FILE,
    usecols=[
        "YEAR",
        "MONTH",
        "ARR_DEL15"
    ],
    chunksize=250_000
):

    # ARR_DEL15 is missing for flights without a valid arrival record
    valid = chunk[
        chunk["ARR_DEL15"].notna()
    ].copy()

    grouped = (
        valid
        .groupby(["YEAR", "MONTH"])["ARR_DEL15"]
        .agg(["sum", "count"])
    )

    for (year, month), row in grouped.iterrows():

        key = (int(year), int(month))

        if key not in monthly_data:

            monthly_data[key] = {
                "delayed": 0,
                "valid_flights": 0
            }

        monthly_data[key]["delayed"] += row["sum"]

        monthly_data[key]["valid_flights"] += row["count"]


# ---------------------------------------------------------
# Build summary table
# ---------------------------------------------------------

rows = []

for (year, month), values in sorted(monthly_data.items()):

    delay_rate = (
        values["delayed"]
        / values["valid_flights"]
    )

    rows.append({
        "year": year,
        "month": month,
        "delayed_flights": int(values["delayed"]),
        "valid_arrival_flights": int(values["valid_flights"]),
        "delay_rate": delay_rate
    })


df = pd.DataFrame(rows)


df["date"] = pd.to_datetime(
    dict(
        year=df["year"],
        month=df["month"],
        day=1
    )
)


df["month_label"] = (
    df["date"]
    .dt.strftime("%b\n%Y")
)


overall_rate = (
    df["delayed_flights"].sum()
    / df["valid_arrival_flights"].sum()
)


# ---------------------------------------------------------
# Save chart-level data
# ---------------------------------------------------------

data_output = (
    CHART_DATA_DIR
    / "02_rq1_monthly_delay_rate.csv"
)

df.to_csv(
    data_output,
    index=False
)


# ---------------------------------------------------------
# Create chart
# ---------------------------------------------------------

fig, ax = plt.subplots(
    figsize=(12, 6.5)
)


ax.plot(
    df["month_label"],
    df["delay_rate"],
    color=NAVY,
    linewidth=2.4,
    marker="o",
    markersize=6
)


ax.axhline(
    overall_rate,
    color=GRAY,
    linewidth=1.5,
    linestyle="--"
)


ax.text(
    len(df) - 1,
    overall_rate + 0.002,
    f"Overall {overall_rate:.1%}",
    color=GRAY,
    fontsize=10,
    ha="right"
)


# Label every monthly point
for i, row in df.iterrows():

    ax.text(
        i,
        row["delay_rate"] + 0.006,
        f"{row['delay_rate']:.1%}",
        ha="center",
        va="bottom",
        fontsize=9,
        color=DARK_TEXT
    )


ax.set_title(
    "Flight delays are common—but not evenly distributed through the year",
    loc="left",
    fontsize=17,
    fontweight="bold",
    pad=18
)


ax.text(
    0,
    1.01,
    (
        "Across 7.0 million scheduled flights, "
        "arrival delay risk changes noticeably by month."
    ),
    transform=ax.transAxes,
    fontsize=10,
    color=GRAY
)


ax.set_ylabel(
    "Arrival delay rate"
)

ax.set_xlabel("")

ax.yaxis.set_major_formatter(
    mtick.PercentFormatter(1.0)
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
    -0.18,
    SOURCE_NOTE
    + " Delay = arrival >=15 minutes (ARR_DEL15).",
    transform=ax.transAxes,
    fontsize=8,
    color=GRAY
)


plt.tight_layout()


chart_output = (
    CHART_DIR
    / "02_rq1_monthly_delay_rate.png"
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

print(
    f"\nOverall delay rate: "
    f"{overall_rate:.1%}"
)