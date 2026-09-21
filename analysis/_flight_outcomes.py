"""Shared, vectorized outcome definitions used by analysis and validation."""
import numpy as np
import pandas as pd

OUTCOMES = (
    "Completed, not delayed ≥15 min",
    "Completed, delayed ≥15 min",
    "Cancelled",
    "Diverted",
    "Unknown/inconsistent",
)
TIME_BLOCKS = ("0001-0559",) + tuple(f"{h:02d}00-{h:02d}59" for h in range(6, 24))
UNKNOWN_TIME = "Unknown departure time"
OUTCOME_COLUMNS = ["CANCELLED", "DIVERTED", "ARR_DEL15", "ARR_DELAY"]


def missing(series):
    return series.isna() | series.astype("string").str.strip().eq("").fillna(False)


def numeric(series):
    values = pd.to_numeric(series, errors="coerce").astype("float64")
    return values.where(np.isfinite(values))


def outcome_masks(frame):
    cancelled, diverted, flag, delay = (numeric(frame[c]) for c in OUTCOME_COLUMNS)
    completed = cancelled.eq(0) & diverted.eq(0)
    conflict = completed & flag.isin([0, 1]) & delay.notna() & flag.ne(delay.ge(15).astype(int))
    return cancelled, diverted, flag, delay, completed, conflict


def classify_outcomes(frame):
    cancelled, diverted, flag, _, completed, conflict = outcome_masks(frame)
    result = pd.Series(OUTCOMES[4], index=frame.index, dtype="string", name="flight_outcome")
    result.loc[cancelled.eq(1) & diverted.eq(0)] = OUTCOMES[2]
    result.loc[cancelled.eq(0) & diverted.eq(1)] = OUTCOMES[3]
    result.loc[completed & flag.eq(1) & ~conflict] = OUTCOMES[1]
    result.loc[completed & flag.eq(0) & ~conflict] = OUTCOMES[0]
    return result


def departure_blocks(frame):
    blocks = frame["DEP_TIME_BLK"].astype("string").str.strip()
    return blocks.where(blocks.isin(TIME_BLOCKS), UNKNOWN_TIME)


def state_checks(frame):
    cancelled, diverted, flag, delay, completed, conflict = outcome_masks(frame)
    checks = {
        "input_rows": len(frame),
        "cancelled_and_diverted": int((cancelled.eq(1) & diverted.eq(1)).sum()),
        "completed_without_valid_arrival_flag": int((completed & ~flag.isin([0, 1])).sum()),
        "completed_arrival_flag_delay_conflict": int(conflict.sum()),
        "completed_arr_delay_missing": int((completed & missing(frame.ARR_DELAY)).sum()),
        "completed_arr_delay_invalid": int((completed & ~missing(frame.ARR_DELAY) & delay.isna()).sum()),
        "unknown_departure_time": int(departure_blocks(frame).eq(UNKNOWN_TIME).sum()),
    }
    for column in OUTCOME_COLUMNS[:3]:
        absent = missing(frame[column])
        checks[f"{column}_missing"] = int(absent.sum())
        checks[f"{column}_invalid"] = int((~absent & ~numeric(frame[column]).isin([0, 1])).sum())
    return checks
