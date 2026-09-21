"""Chunked quality audit; disk-backed hashes detect duplicates across chunks."""
from collections import Counter
from contextlib import closing
from pathlib import Path
import sqlite3
import tempfile

import pandas as pd

from _flight_outcomes import OUTCOME_COLUMNS, missing, numeric, state_checks

KEY_COLUMNS = ["FL_DATE", "OP_UNIQUE_CARRIER", "OP_CARRIER_FL_NUM", "ORIGIN", "DEST", "CRS_DEP_TIME"]
REQUIRED = list(dict.fromkeys(KEY_COLUMNS + OUTCOME_COLUMNS + ["DEP_TIME_BLK"]))
START = pd.Timestamp("2025-07-01")
END = pd.Timestamp("2026-06-30")


def audit(path, chunksize=250_000, progress=False):
    if chunksize <= 0:
        raise ValueError("chunksize must be positive")
    try:
        columns = list(pd.read_csv(path, nrows=0).columns)
    except pd.errors.EmptyDataError as error:
        raise ValueError("Input has no flight records") from error
    absent = set(REQUIRED) - set(columns)
    if absent:
        raise ValueError(f"Missing required columns: {', '.join(sorted(absent))}")
    checks, month_counts = Counter(), Counter()
    dates_seen = set()
    unique = {column: set() for column in ("OP_UNIQUE_CARRIER", "ORIGIN", "DEST")}
    valid_arrivals = delayed = cancelled = 0
    first_date = last_date = None
    with tempfile.TemporaryDirectory(prefix="bts-quality-") as temporary:
        with closing(sqlite3.connect(str(Path(temporary) / "hashes.sqlite"))) as db:
            # This temporary database is disposable; never alters the input CSV.
            db.execute("PRAGMA journal_mode=OFF")
            db.execute("PRAGMA synchronous=OFF")
            db.execute("PRAGMA cache_size=-32768")
            db.execute("CREATE TABLE full_rows (hash INTEGER PRIMARY KEY)")
            db.execute("CREATE TABLE flight_keys (hash INTEGER PRIMARY KEY)")
            with pd.read_csv(path, dtype="string", keep_default_na=False, chunksize=chunksize) as reader:
                for frame in reader:
                    checks.update(state_checks(frame))
                    for column in columns:
                        # Flag missing counts already come from shared state checks.
                        if column not in OUTCOME_COLUMNS[:3]:
                            checks[f"{column}_missing"] += int(missing(frame[column]).sum())
                    for column in unique:
                        unique[column].update(frame.loc[~missing(frame[column]), column].tolist())
                    dates = pd.to_datetime(frame.FL_DATE, errors="coerce", format="mixed").dt.normalize()
                    checks["date_parse_failures"] += int((dates.isna() & ~missing(frame.FL_DATE)).sum())
                    checks["date_outside_expected_range"] += int((dates.notna() & ~dates.between(START, END)).sum())
                    valid_dates = dates.dropna()
                    if not valid_dates.empty:
                        first_date = min(first_date, valid_dates.min()) if first_date is not None else valid_dates.min()
                        last_date = max(last_date, valid_dates.max()) if last_date is not None else valid_dates.max()
                    dates_seen.update(valid_dates.tolist())
                    month_counts.update(dates[dates.between(START, END)].dt.strftime("%Y-%m").value_counts().to_dict())
                    flag = numeric(frame.ARR_DEL15)
                    valid_arrivals += int(flag.isin([0, 1]).sum())
                    delayed += int(flag.eq(1).sum())
                    cancelled += int(numeric(frame.CANCELLED).eq(1).sum())
                    complete_key = pd.Series(True, index=frame.index)
                    for column in KEY_COLUMNS:
                        complete_key &= ~missing(frame[column])
                    checks["candidate_key_incomplete_rows"] += int((~complete_key).sum())
                    for table, data, check in (
                        ("full_rows", frame, "full_row_duplicate_excess"),
                        ("flight_keys", frame.loc[complete_key, KEY_COLUMNS], "candidate_key_duplicate_excess"),
                    ):
                        hashes = pd.util.hash_pandas_object(data, index=False).to_numpy().view("int64")
                        before = db.total_changes
                        db.executemany(f"INSERT OR IGNORE INTO {table} VALUES (?)", ((int(h),) for h in hashes))
                        checks[check] += len(data) - (db.total_changes - before)
                    db.commit()
                    if progress:
                        print(f"Checked {checks['input_rows']:,} records", flush=True)
    total = checks["input_rows"]
    if not total:
        raise ValueError("Input has no flight records; rates are undefined")
    expected_dates = set(pd.date_range(START, END))
    missing_dates = sorted(expected_dates - dates_seen)
    checks["missing_expected_dates"] = len(missing_dates)
    months = pd.DataFrame({"month": pd.period_range(START, END, freq="M").astype(str)})
    months["records"] = months.month.map(month_counts).fillna(0).astype(int)
    checks["missing_expected_months"] = int(months.records.eq(0).sum())
    metrics = {
        "Total flight records": total,
        "Start date": first_date.date().isoformat() if first_date is not None else None,
        "End date": last_date.date().isoformat() if last_date is not None else None,
        "Airlines": len(unique["OP_UNIQUE_CARRIER"]),
        "Origin airports": len(unique["ORIGIN"]),
        "Destination airports": len(unique["DEST"]),
        "Valid arrival records": valid_arrivals,
        "Flights delayed >=15 min": delayed,
        "Arrival delay rate": delayed / valid_arrivals if valid_arrivals else float("nan"),
        "Cancelled flights": cancelled,
        "Cancellation rate": cancelled / total,
    }
    rules = {
        "full_row_duplicate_excess": "Repeated 64-bit full-row hashes beyond first occurrence; all columns as CSV strings; collision risk exists",
        "candidate_key_duplicate_excess": "Repeated complete key hashes beyond first: " + ", ".join(KEY_COLUMNS),
        "candidate_key_incomplete_rows": "Excluded from candidate-key check only; retained in all outcome counts",
        "date_parse_failures": "Nonblank FL_DATE could not be parsed",
        "date_outside_expected_range": "Parsed date outside 2025-07-01 through 2026-06-30",
        "missing_expected_dates": "Expected calendar dates with no records; investigate before declaring invalid",
        "missing_expected_months": "Expected months with zero records",
        "completed_arrival_flag_delay_conflict": "CANCELLED=DIVERTED=0, valid ARR_DEL15 disagrees with finite ARR_DELAY >=15",
        "completed_without_valid_arrival_flag": "CANCELLED=DIVERTED=0 but ARR_DEL15 is missing or not 0/1",
        "completed_arr_delay_missing": "CANCELLED=DIVERTED=0 and ARR_DELAY blank; valid ARR_DEL15 still classifies the flight",
        "completed_arr_delay_invalid": "CANCELLED=DIVERTED=0 and nonblank ARR_DELAY is nonnumeric or nonfinite",
        "cancelled_and_diverted": "Both status flags equal 1",
        "unknown_departure_time": "DEP_TIME_BLK missing or outside the published time-block list",
        "input_rows": "All input records; no automatic row exclusions",
    }
    records = []
    for check, count in sorted(checks.items()):
        denominator = 365 if check == "missing_expected_dates" else 12 if check == "missing_expected_months" else total
        rule = rules.get(check, "Blank or missing field" if check.endswith("_missing") else "Nonblank flag is not numeric 0 or 1")
        records.append([check, int(count), denominator, count / denominator, rule])
    return (pd.DataFrame(metrics.items(), columns=["Metric", "Value"]),
            pd.DataFrame(records, columns=["check", "count", "denominator", "proportion", "rule"]),
            months, pd.DataFrame({"missing_date": [date.date().isoformat() for date in missing_dates]}))
