"""
RQ2: What actually causes flight delays?

Chart:
Monthly mix of recorded delay causes.

Purpose:
Check whether the overall delay-cause pattern is driven by only
one unusual month, or whether it persists throughout the year.

Interpretation:
The relative mix changes over time, but Late Aircraft remains
a major contributor across the full 12-month period.
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
# 1. Fields
# =========================================================

CAUSE_COLUMNS = {
    "Carrier": "CARRIER_DELAY",
    "Weather": "WEATHER_DELAY",
    "NAS": "NAS_DELAY",
    "Security": "SECURITY_DELAY",
    "Late Aircraft": "LATE_AIRCRAFT_DELAY"
}


USECOLS = [
    "YEAR",
    "MONTH",
    "CARRIER_DELAY",
    "WEATHER_DELAY",
    "NAS_DELAY",
    "SECURITY_DELAY",
    "LATE_AIRCRAFT_DELAY"
]


monthly = {}


print("Reading data for RQ2 - monthly delay cause mix...")


# =========================================================
# 2. Aggregate large CSV in chunks
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

    grouped = (
        chunk
        .groupby(["YEAR", "MONTH"])[cause_columns]
        .sum()
    )

    for (year, month), row in grouped.iterrows():

        key = (
            int(year),
            int(month)
        )

        if key not in monthly:

            monthly[key] = {
                cause: 0.0
                for cause in CAUSE_COLUMNS
            }

        for cause, column in CAUSE_COLUMNS.items():

            monthly[key][cause] += row[column]


# =========================================================
# 3. Build summary table
# =========================================================

rows = []


for (year, month), values in sorted(
    monthly.items()
):

    total_minutes = sum(
        values.values()
    )

    row = {
        "year": year,
        "month": month,
        "total_recorded_delay_minutes":
            total_minutes
    }

    for cause in CAUSE_COLUMNS:

        row[
            f"{cause}_minutes"
        ] = values[cause]

        row[
            f"{cause}_share"
        ] = (
            values[cause]
            / total_minutes
            if total_minutes > 0
            else 0
        )

    rows.append(row)


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


# =========================================================
# 4. Save chart-level data
# =========================================================

data_output = (
    CHART_DATA_DIR
    / "05_rq2_monthly_delay_cause_mix.csv"
)


df.to_csv(
    data_output,
    index=False
)


# =========================================================
# 5. Create 100% stacked bar chart
# =========================================================

fig, ax = plt.subplots(
    figsize=(13, 6.5)
)


x = np.arange(
    len(df)
)

bottom = np.zeros(
    len(df)
)


cause_order = [
    "Carrier",
    "Weather",
    "NAS",
    "Security",
    "Late Aircraft"
]


for cause in cause_order:

    values = df[
        f"{cause}_share"
    ].values

    ax.bar(
        x,
        values,
        bottom=bottom,
        color=CAUSE_COLORS[cause],
        label=cause,
        width=0.72
    )

    bottom += values


# =========================================================
# 6. Styling
# =========================================================

ax.set_title(
    "The delay mix changes by month, but Late Aircraft remains a persistent driver",
    loc="left",
    fontsize=17,
    fontweight="bold",
    pad=18
)


ax.text(
    0,
    1.01,
    (
        "Weather varies more by month, while Late Aircraft remains "
        "one of the largest sources of recorded delay minutes throughout the year."
    ),
    transform=ax.transAxes,
    fontsize=10,
    color=GRAY
)


ax.set_xticks(x)

ax.set_xticklabels(
    df["month_label"]
)


ax.set_ylabel(
    "Share of recorded delay minutes"
)

ax.set_xlabel("")


ax.yaxis.set_major_formatter(
    mtick.PercentFormatter(1.0)
)


ax.set_ylim(
    0,
    1
)


ax.legend(
    ncol=5,
    frameon=False,
    loc="upper center",
    bbox_to_anchor=(0.5, -0.13)
)


ax.grid(False)


ax.text(
    0,
    -0.25,
    SOURCE_NOTE
    + " Cause shares use recorded BTS delay minutes.",
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
    / "05_rq2_monthly_delay_cause_mix.png"
)


plt.savefig(
    chart_output,
    dpi=300,
    bbox_inches="tight"
)

plt.close()


# =========================================================
# 8. Print results
# =========================================================

late_min = (
    df["Late Aircraft_share"]
    .min()
)

late_max = (
    df["Late Aircraft_share"]
    .max()
)

weather_min = (
    df["Weather_share"]
    .min()
)

weather_max = (
    df["Weather_share"]
    .max()
)


print("\nChart created:")
print(chart_output)

print("\nChart data saved:")
print(data_output)

print(
    "\nLate Aircraft monthly share range:",
    f"{late_min:.1%} - {late_max:.1%}"
)

print(
    "Weather monthly share range:",
    f"{weather_min:.1%} - {weather_max:.1%}"
)