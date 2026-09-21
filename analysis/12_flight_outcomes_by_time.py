"""Do early departures still look reliable when cancellations/diversions count?

All rates in the outcome table use all scheduled records in their time block.
Unknown states and times are retained. No row-level flight copy is written.
"""
import argparse
from collections import Counter
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import PercentFormatter
import numpy as np
import pandas as pd

from _config import (
    DATA_FILE, CHART_DATA_DIR, CHART_DIR, NAVY, TERRACOTTA, STEEL,
    SKY, GRAY, LIGHT_GRAY, apply_chart_style,
)
from _flight_outcomes import (
    OUTCOMES, TIME_BLOCKS, UNKNOWN_TIME, OUTCOME_COLUMNS,
    classify_outcomes, departure_blocks, state_checks,
)

REQUIRED = OUTCOME_COLUMNS + ["DEP_TIME_BLK", "FL_DATE"]


def analyze(path, chunksize=250_000):
    if chunksize <= 0:
        raise ValueError("chunksize must be positive")
    try:
        columns = pd.read_csv(path, nrows=0).columns
    except pd.errors.EmptyDataError as error:
        raise ValueError("Input has no flight records") from error
    absent = set(REQUIRED) - set(columns)
    if absent:
        raise ValueError(f"Missing required columns: {', '.join(sorted(absent))}")
    counts, checks = Counter(), Counter()
    first_date = last_date = None
    # Fixed strings prevent chunk-dependent inference; blanks stay distinguishable.
    with pd.read_csv(path, usecols=REQUIRED, dtype="string",
                     keep_default_na=False, chunksize=chunksize) as reader:
        for frame in reader:
            checks.update(state_checks(frame))
            grouped = pd.DataFrame({"block": departure_blocks(frame),
                                    "outcome": classify_outcomes(frame)}).groupby(["block", "outcome"]).size()
            counts.update({key: int(value) for key, value in grouped.items()})
            dates = pd.to_datetime(frame.FL_DATE, errors="coerce", format="mixed").dropna()
            if not dates.empty:
                first_date = min(first_date, dates.min()) if first_date is not None else dates.min()
                last_date = max(last_date, dates.max()) if last_date is not None else dates.max()
            checks["unparseable_or_missing_dates"] += len(frame) - len(dates)
    total = checks["input_rows"]
    if not total:
        raise ValueError("Input has no flight records; rates are undefined")
    rows = []
    for block in (*TIME_BLOCKS, UNKNOWN_TIME):
        denominator = sum(counts[block, category] for category in OUTCOMES)
        # No observed flights means no rate, rather than a fabricated zero percent.
        if denominator:
            for category in OUTCOMES:
                count = counts[block, category]
                rows.append([block, category, count, denominator, count / denominator])
    by_time = pd.DataFrame(rows, columns=["departure_time_block", "flight_outcome", "count", "total_records", "share"])
    global_rows = []
    for category in OUTCOMES:
        count = sum(value for (_, outcome), value in counts.items() if outcome == category)
        global_rows.append([category, count, total, count / total])
    overall = pd.DataFrame(global_rows, columns=["flight_outcome", "count", "total_records", "share"])
    if by_time["count"].sum() != total or overall["count"].sum() != total:
        raise ValueError("Count conservation failed")
    for _, group in by_time.groupby("departure_time_block"):
        if group["count"].sum() != group.total_records.iloc[0] or not np.isclose(group.share.sum(), 1):
            raise ValueError("Within-block conservation failed")
    checks["start_date"] = first_date.date().isoformat() if first_date is not None else "unavailable"
    checks["end_date"] = last_date.date().isoformat() if last_date is not None else "unavailable"
    return by_time, overall, dict(checks)


def save_results(by_time, overall, checks, data_dir, chart_dir):
    data_dir, chart_dir = Path(data_dir), Path(chart_dir)
    data_dir.mkdir(parents=True, exist_ok=True)
    chart_dir.mkdir(parents=True, exist_ok=True)
    by_time.to_csv(data_dir / "12_flight_outcomes_by_time.csv", index=False)
    overall.to_csv(data_dir / "12_flight_outcomes_global.csv", index=False)
    pd.DataFrame(checks.items(), columns=["check", "value"]).to_csv(
        data_dir / "12_flight_outcomes_checks.csv", index=False)
    apply_chart_style()
    order = list(dict.fromkeys(by_time.departure_time_block))
    shares = by_time.pivot(index="departure_time_block", columns="flight_outcome", values="share").reindex(order)
    x = np.arange(len(order))
    labels = ["Unknown" if b == UNKNOWN_TIME else "00:01–05:59" if b == "0001-0559" else b[:2] for b in order]
    colors = [SKY, NAVY, TERRACOTTA, STEEL, GRAY]
    fig, axes = plt.subplots(3, 1, figsize=(13, 10), sharex=True,
                             gridspec_kw={"height_ratios": [2.6, 1.7, 1.6]})
    bottom = np.zeros(len(order))
    for category, color in zip(OUTCOMES, colors):
        values = shares[category].to_numpy(dtype=float)
        axes[0].bar(x, values, bottom=bottom, color=color, label=category, width=.8,
                    hatch="///" if category == OUTCOMES[4] else None)
        bottom += values
    axes[0].set_ylim(0, 1)
    axes[0].set_title("All scheduled records, including unknown outcomes", loc="left", fontweight="bold")
    disruption = shares[list(OUTCOMES[1:4])].sum(axis=1)
    axes[1].plot(x, disruption, "o-", color=NAVY, label="Delayed ≥15 min + cancelled + diverted")
    axes[1].set_ylim(0, max(.05, float(disruption.max()) * 1.2))
    axes[1].legend(loc="upper left", fontsize=9)
    axes[1].set_title("Combined disruption rate (different impacts counted together)", loc="left", fontsize=11)
    for category, color, marker in zip(OUTCOMES[2:], colors[2:], ["o", "s", "x"]):
        axes[2].plot(x, shares[category], marker=marker, color=color, label=category)
    axes[2].set_ylim(0, max(.01, float(shares[list(OUTCOMES[2:])].max().max()) * 1.3))
    axes[2].legend(loc="upper left", ncol=3, fontsize=9)
    axes[2].set_title("Smaller categories shown separately", loc="left", fontsize=11)
    for ax in axes:
        ax.yaxis.set_major_formatter(PercentFormatter(1))
        ax.set_ylabel("Share of all records")
        ax.grid(axis="y", color=LIGHT_GRAY, alpha=.5)
        ax.set_axisbelow(True)
    axes[2].set_xticks(x, labels, rotation=45, ha="right")
    axes[2].set_xlabel("Scheduled local departure time block (00:01–05:59 combines six hours)")
    fig.suptitle("When do flights arrive late, cancel or divert?", x=.08, ha="left", fontsize=19, fontweight="bold")
    axes[0].legend(loc="lower center", bbox_to_anchor=(.5, 1.1), ncol=3, fontsize=9, frameon=False)
    unknown_count = int(overall.loc[overall.flight_outcome == OUTCOMES[4], "count"].iloc[0])
    note = (
        f"Source: U.S. DOT BTS, Reporting Carrier On-Time Performance. Observed dates: {checks['start_date']} to {checks['end_date']}.\n"
        f"Denominator: all {checks['input_rows']:,} input records, grouped by scheduled departure block; unknown times are retained when present.\n"
        "Not delayed ≥15 min includes early arrivals and delays under 15 min. Invalid/missing flags and completed-arrival conflicts are unknown.\n"
        f"Unknown/inconsistent: {unknown_count:,} records. Disruption categories have different impacts. Empty time blocks have no rate and are omitted."
    )
    fig.text(.08, .015, note, fontsize=8, color=GRAY, va="bottom", linespacing=1.5)
    fig.tight_layout(rect=(0, .115, 1, .94), h_pad=1.6)
    fig.savefig(chart_dir / "12_flight_outcomes_by_time.png", dpi=200, bbox_inches="tight")
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DATA_FILE)
    parser.add_argument("--output-dir", type=Path, default=CHART_DATA_DIR)
    parser.add_argument("--chart-dir", type=Path, default=CHART_DIR)
    parser.add_argument("--chunk-size", type=int, default=250_000)
    args = parser.parse_args()
    try:
        by_time, overall, checks = analyze(args.input, args.chunk_size)
        save_results(by_time, overall, checks, args.output_dir, args.chart_dir)
    except (OSError, ValueError, pd.errors.ParserError) as error:
        parser.exit(1, f"Error: {error}\n")
    print(overall.to_string(index=False))
    print(f"Saved results to {args.output_dir} and {args.chart_dir}")


if __name__ == "__main__":
    main()
