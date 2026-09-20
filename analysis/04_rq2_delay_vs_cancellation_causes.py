"""
RQ2: What actually causes flight disruptions?

Chart:
Recorded delay-minute causes vs cancellation causes.

Purpose:
Show that "flight disruption" is not one single problem.

Key finding:
Late Aircraft is the largest source of recorded delay minutes,
while Weather dominates cancellations.

BTS cancellation codes:
A = Carrier
B = Weather
C = National Airspace System (NAS)
D = Security
"""

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick

from _config import (
    DATA_FILE,
    CHART_DIR,
    CHART_DATA_DIR,
    CAUSE_COLORS,
    GRAY,
    LIGHT_GRAY,
    DARK_TEXT,
    SOURCE_NOTE,
    apply_chart_style
)


apply_chart_style()


# =========================================================
# 1. BTS fields
# =========================================================

CAUSE_COLUMNS = {
    "Carrier": "CARRIER_DELAY",
    "Weather": "WEATHER_DELAY",
    "NAS": "NAS_DELAY",
    "Security": "SECURITY_DELAY",
    "Late Aircraft": "LATE_AIRCRAFT_DELAY"
}


CANCELLATION_CODES = {
    "A": "Carrier",
    "B": "Weather",
    "C": "NAS",
    "D": "Security"
}


USECOLS = [
    "CANCELLED",
    "CANCELLATION_CODE",
    "CARRIER_DELAY",
    "WEATHER_DELAY",
    "NAS_DELAY",
    "SECURITY_DELAY",
    "LATE_AIRCRAFT_DELAY"
]


delay_minutes = {
    cause: 0.0
    for cause in CAUSE_COLUMNS
}


cancellation_counts = {
    cause: 0
    for cause in [
        "Carrier",
        "Weather",
        "NAS",
        "Security"
    ]
}


total_cancelled = 0
coded_cancelled = 0


# =========================================================
# 2. Read CSV in chunks
# =========================================================

print("Reading data for RQ2 - disruption causes...")


for chunk in pd.read_csv(
    DATA_FILE,
    usecols=USECOLS,
    chunksize=250_000
):

    # -----------------------------------------------------
    # Delay minutes
    # -----------------------------------------------------

    for cause, column in CAUSE_COLUMNS.items():

        delay_minutes[cause] += (
            chunk[column]
            .fillna(0)
            .sum()
        )

    # -----------------------------------------------------
    # Cancellation causes
    # -----------------------------------------------------

    cancelled = chunk[
        chunk["CANCELLED"] == 1
    ]

    total_cancelled += len(cancelled)

    valid_codes = (
        cancelled["CANCELLATION_CODE"]
        .dropna()
        .astype(str)
        .str.strip()
    )

    for code, cause in CANCELLATION_CODES.items():

        count = (
            valid_codes == code
        ).sum()

        cancellation_counts[cause] += count

        coded_cancelled += count


# =========================================================
# 3. Calculate shares
# =========================================================

total_delay_minutes = sum(
    delay_minutes.values()
)


delay_share = {
    cause:
    minutes / total_delay_minutes

    for cause, minutes
    in delay_minutes.items()
}


cancellation_share = {
    cause:
    count / coded_cancelled

    for cause, count
    in cancellation_counts.items()
}


# =========================================================
# 4. Save chart-level data
# =========================================================

all_causes = [
    "Carrier",
    "Weather",
    "NAS",
    "Security",
    "Late Aircraft"
]


rows = []


for cause in all_causes:

    rows.append({
        "cause": cause,

        "recorded_delay_minutes":
            delay_minutes.get(
                cause,
                0
            ),

        "delay_minute_share":
            delay_share.get(
                cause,
                0
            ),

        "cancellations":
            cancellation_counts.get(
                cause,
                0
            ),

        "cancellation_share":
            cancellation_share.get(
                cause,
                0
            )
    })


summary_df = pd.DataFrame(rows)


data_output = (
    CHART_DATA_DIR
    / "04_rq2_delay_vs_cancellation_causes.csv"
)


summary_df.to_csv(
    data_output,
    index=False
)


# =========================================================
# 5. Prepare chart data
# =========================================================

delay_df = (
    summary_df
    .sort_values(
        "delay_minute_share",
        ascending=True
    )
)


cancel_df = (
    summary_df[
        summary_df["cause"]
        != "Late Aircraft"
    ]
    .sort_values(
        "cancellation_share",
        ascending=True
    )
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
# Left: delay minutes
# ---------------------------------------------------------

delay_colors = [
    CAUSE_COLORS[cause]
    for cause in delay_df["cause"]
]


bars1 = ax1.barh(
    delay_df["cause"],
    delay_df["delay_minute_share"],
    color=delay_colors,
    height=0.62
)


ax1.set_title(
    "What drives recorded delay minutes?",
    loc="left",
    fontsize=14,
    fontweight="bold",
    pad=12
)


ax1.set_xlabel(
    "Share of recorded delay minutes"
)

ax1.set_ylabel("")

ax1.xaxis.set_major_formatter(
    mtick.PercentFormatter(1.0)
)

ax1.grid(
    axis="x",
    color=LIGHT_GRAY,
    linewidth=0.8
)

ax1.grid(
    axis="y",
    visible=False
)


for bar, value in zip(
    bars1,
    delay_df["delay_minute_share"]
):

    ax1.text(
        value + 0.007,
        bar.get_y()
        + bar.get_height() / 2,
        f"{value:.1%}",
        va="center",
        fontsize=10,
        color=DARK_TEXT
    )


# ---------------------------------------------------------
# Right: cancellations
# ---------------------------------------------------------

cancel_colors = [
    CAUSE_COLORS[cause]
    for cause in cancel_df["cause"]
]


bars2 = ax2.barh(
    cancel_df["cause"],
    cancel_df["cancellation_share"],
    color=cancel_colors,
    height=0.62
)


ax2.set_title(
    "What drives cancellations?",
    loc="left",
    fontsize=14,
    fontweight="bold",
    pad=12
)


ax2.set_xlabel(
    "Share of coded cancellations"
)

ax2.set_ylabel("")

ax2.xaxis.set_major_formatter(
    mtick.PercentFormatter(1.0)
)

ax2.grid(
    axis="x",
    color=LIGHT_GRAY,
    linewidth=0.8
)

ax2.grid(
    axis="y",
    visible=False
)


for bar, value in zip(
    bars2,
    cancel_df["cancellation_share"]
):

    ax2.text(
        value + 0.009,
        bar.get_y()
        + bar.get_height() / 2,
        f"{value:.1%}",
        va="center",
        fontsize=10,
        color=DARK_TEXT
    )


# =========================================================
# 7. Main title
# =========================================================

fig.suptitle(
    "A delay and a cancellation are not caused by the same things",
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
        "Weather dominates cancellations, while Late Aircraft "
        "is the largest source of recorded delay minutes."
    ),
    fontsize=10,
    color=GRAY
)


fig.text(
    0.06,
    -0.015,
    (
        SOURCE_NOTE
        + " Cancellation codes: A=Carrier, B=Weather, "
          "C=NAS, D=Security. "
          "Late Aircraft is not a BTS cancellation-code category."
    ),
    fontsize=8,
    color=GRAY
)


plt.tight_layout(
    rect=[0.04, 0.05, 0.98, 0.90]
)


# =========================================================
# 8. Save chart
# =========================================================

chart_output = (
    CHART_DIR
    / "04_rq2_delay_vs_cancellation_causes.png"
)


plt.savefig(
    chart_output,
    dpi=300,
    bbox_inches="tight"
)

plt.close()


# =========================================================
# 9. Print key findings
# =========================================================

print("\nChart created:")
print(chart_output)

print("\nChart data saved:")
print(data_output)

print("\nRecorded delay-minute shares:")

for cause in sorted(
    delay_share,
    key=delay_share.get,
    reverse=True
):

    print(
        f"{cause:<15}",
        f"{delay_share[cause]:.1%}"
    )


print("\nCancellation shares:")

for cause in sorted(
    cancellation_share,
    key=cancellation_share.get,
    reverse=True
):

    print(
        f"{cause:<15}",
        f"{cancellation_share[cause]:.1%}"
    )


print(
    "\nTotal cancelled flights:",
    f"{total_cancelled:,}"
)

print(
    "Cancelled flights with BTS cause code:",
    f"{coded_cancelled:,}"
)