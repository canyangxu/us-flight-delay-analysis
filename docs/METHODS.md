# Methods, data quality and reproduction

## Input and provenance

The September 20, 2026 validation used the repository's [v1.0-data Release](https://github.com/canyangxu/us-flight-delay-analysis/releases/tag/v1.0-data), not a synthetic replacement:

- File: `data/bts_2025_07_to_2026_06.csv`
- Size: 1,608,699,934 bytes
- SHA-256: `3544dcf9815b865bee1583f4d0eeb2893fe18669ecbf9aebcc58e598378b951a` (matched the Release asset digest)
- Observed: 7,043,316 rows, 40 fields, July 1, 2025–June 30, 2026; 14 carrier codes and 358 origin/destination airports.

Raw monthly downloads, the merged CSV, analysis-specific filters/derived features, and aggregate chart outputs are distinct stages. Concatenating monthly files does not establish that the merged data are fully cleaned. The release download is the quickest reproduction path; the Git repository contains only aggregate CSVs and figures.

[BTS field definitions](https://www.transtats.bts.gov/Fields.asp?gnoyr_VQ=FGJ) identify scheduled departure times as local time, arrival-delay flags as the 15-minute threshold, and negative arrival/departure delay values as early operations. `DEP_TIME_BLK` is supplied by BTS. The release's `0001-0559` combines 00:01–05:59; other observed blocks run hourly from `0600-0659` to `2300-2359`. The first block must not be interpreted as one hour. The time plots use ordered categories, not equally spaced elapsed hours.

## Outcome feature

The two operational flags must each be numeric 0 or 1. Apply the following mutually exclusive rules:

| Outcome | Rule |
|---|---|
| Cancelled | CANCELLED=1 and DIVERTED=0 |
| Diverted | CANCELLED=0 and DIVERTED=1 |
| Completed, delayed ≥15 min | Both flags=0 and ARR_DEL15=1, with no finite-minute conflict |
| Completed, not delayed ≥15 min | Both flags=0 and ARR_DEL15=0, with no finite-minute conflict |
| Unknown/inconsistent | Missing/illegal operational flags, both flags=1, or a completed record that cannot be classified |

For completed records only, a valid arrival flag that disagrees with finite `ARR_DELAY >= 15` is a conflict and becomes unknown. Missing arrival-delay minutes do not invalidate a valid arrival flag; missing and invalid minutes are reported separately. A diverted flight with an arrival record remains diverted. These rules do not invent additional contradictions from arrival fields on cancelled/diverted records.

Blank/whitespace fields are missing. Nonblank, nonnumeric or nonfinite flags are invalid. Input strings are converted only for field-specific checks; no row is deleted or imputed. A literal nonblank token such as `NA` in a flag is invalid rather than silently treated as a blank. Negative and extreme delays are retained.

Every observed time block has five output rows, even when a category count is zero. Each category share divides by **all records in that block**. Missing/invalid blocks are grouped as `Unknown departure time`. A block with no observations has no defined rate and is omitted; an entirely empty input raises a clear error. Both within-block and global count conservation are checked before output.

The combined disruption measure adds completed delayed, cancelled and diverted flights. It is a descriptive count, not a utility/loss measure: a cancellation and a 15-minute delay do not have equal passenger costs. Unknown records remain in the denominator and outside that numerator.

## Quality audit and decisions

`01_data_quality.py` preserves the original `Metric,Value` summary format and writes three additional reports:

- `01_data_quality_checks.csv`: missing counts for all input fields, legal-value checks, state conflicts, duplicate screening and date coverage; every check has a denominator and rule.
- `01_data_quality_monthly_counts.csv`: all 12 expected months, including a zero count if a month is absent.
- `01_data_quality_missing_dates.csv`: expected dates with no observations. A missing date is a prompt to investigate, not automatic evidence that all data are invalid.

Missing arrival fields on cancelled flights can be structural. Delay-cause minute fields are absent on many flights where the reporting field is not applicable. Existing cause aggregation fills missing values with zero **only to sum recorded minutes**; it does not establish the true cause contribution for an unreported field. No extreme-delay trimming or blanket removal of negative delays is applied.

The audit and outcome analysis share their state checks. The release has 147,033 missing arrival-delay flags: 127,324 cancelled flights, 19,708 diverted flights and one other record. There are no nonmissing illegal flags or completed-flight minute/flag conflicts. The one other record is retained as unknown. All 365 dates and 12 months are present. No source records were excluded from the new analysis.

### Duplicate screening

The real CSV provides the candidate flight key:

`FL_DATE, OP_UNIQUE_CARRIER, OP_CARRIER_FL_NUM, ORIGIN, DEST, CRS_DEP_TIME`

For each chunk, pandas hashes (1) every column and (2) complete candidate keys as 64-bit values, excluding the DataFrame index. Temporary SQLite unique indexes retain hashes across **all** chunks. Counts measure occurrences beyond the first, not number of duplicate groups. Incomplete candidate keys are excluded from key screening only and counted explicitly. Full-row screening includes every row.

No full-row or candidate-key repeats were detected in the full release. This method has residual hash-collision risk and compares parsed CSV string values: alternative spellings of a date/time or numeric value can evade semantic duplicate detection. It is not byte-level file deduplication or proof that each flight key is a unique operational event. No candidate duplicate is automatically deleted. The temporary database is removed after the run and can require additional disk space during validation.

## Other feature and interpretation limits

`recovery_minutes = DEP_DELAY - ARR_DELAY` is computed for flights departing late, with CANCELLED=DIVERTED=0 and nonmissing arrival delay and distance. Distance groups are left-closed/right-open bins [0,500), [500,1000), [1000,1500), [1500,2000), [2000,infinity) miles. Neither this grouping nor schedule recovery controls for airline, route or schedule padding. `DAY_OF_WEEK` and `DEP_TIME_BLK` are source fields, not features created from scratch here.

Airport comparisons group by origin: the outcome is arrival delay for flights **from** that airport. Rankings do not isolate delays caused by airport management. Delay-cause shares describe recorded minutes, while cancellation-cause shares describe coded cancellations; neither is a probability of a cause across all flights. Late-aircraft patterns are consistent with network propagation, not causal proof for individual delays.

## Rebuild from original monthly files

1. Open the [BTS Reporting Carrier On-Time Performance download page](https://www.transtats.bts.gov/DL_SelectFields.aspx?QO_fu146_anzr=&gnoyr_VQ=FGJ). Select that reporting-carrier table, not the marketing-carrier table.
2. Download each month July–December 2025 and January–June 2026. Use the same field selection for every month. The exact 40 column names observed in the Release CSV are listed below. BTS field-description labels can differ from exported uppercase names; verify the ZIP CSV headers before merging.
3. Put the six 2025 ZIPs in `2025.7-2025.12/` and the six 2026 ZIPs in `2026.1-2026.6/`, directly below the repository root. Each ZIP should contain exactly one monthly CSV. Do not also place alternative copies of the same month in either directory.
4. Run `python merge_bts_to_csv.py`. It checks for input, nonempty CSVs and matching headers, writes a temporary file, and replaces `data/bts_2025_07_to_2026_06.csv` only when merging succeeds. A successful run deliberately replaces that path; preserve a separate copy first if comparing it with the Release.
5. Run `python analysis/01_data_quality.py` to check dates, coverage, counts and duplicates. The merge script itself does not guarantee that all 12 distinct months were selected. BTS revisions and CSV serialization can differ from the Release; byte-for-byte reconstruction is not claimed.

```text
YEAR, MONTH, DAY_OF_MONTH, DAY_OF_WEEK, FL_DATE,
OP_UNIQUE_CARRIER, TAIL_NUM, OP_CARRIER_FL_NUM,
ORIGIN_AIRPORT_ID, ORIGIN, ORIGIN_CITY_NAME, ORIGIN_STATE_ABR,
DEST_AIRPORT_ID, DEST, DEST_CITY_NAME, DEST_STATE_ABR,
CRS_DEP_TIME, DEP_TIME, DEP_DELAY, DEP_DEL15, DEP_TIME_BLK,
TAXI_OUT, TAXI_IN, CRS_ARR_TIME, ARR_TIME, ARR_DELAY, ARR_DEL15,
ARR_TIME_BLK, CANCELLED, CANCELLATION_CODE, DIVERTED,
CRS_ELAPSED_TIME, ACTUAL_ELAPSED_TIME, AIR_TIME, DISTANCE,
CARRIER_DELAY, WEATHER_DELAY, NAS_DELAY, SECURITY_DELAY,
LATE_AIRCRAFT_DELAY
```

Optional Parquet route:

```bash
python -m pip install duckdb
python merge_bts.py
```

DuckDB is only needed by the optional Parquet merge and its test. That merge extracts into a unique temporary directory, validates headers and records, and replaces its Parquet output only after a successful conversion. It does not delete an existing `data/extracted/` directory. Analysis scripts still use the CSV path.

## Environment and validation

Use a project virtual environment, as shown in the README. The local run used Python 3.13.5, pandas 3.0.6, matplotlib 3.11.2, numpy 2.5.3 and optional DuckDB 1.5.5. The dependency file lists only direct analysis dependencies; it is not an unrelated machine-wide freeze.

```bash
python -m unittest discover -s tests -v
python analysis/01_data_quality.py
python analysis/12_flight_outcomes_by_time.py
python analysis/03_rq1_delay_by_time_of_day.py
python analysis/08_rq4_airport_delay_rates.py
```

Both new/updated entry points accept `--input`, `--chunk-size` and `--output-dir`. The outcome script also accepts `--chart-dir`. Tests write only temporary fixtures and outputs. Production aggregate CSVs go to `chart_data/`, and PNG figures to `charts/`; the input data, virtual environment and caches are ignored by Git.

The full-data run confirmed 7,043,316 = 5,350,236 completed/not delayed ≥15 + 1,546,047 completed/delayed ≥15 + 127,324 cancelled + 19,708 diverted + 1 unknown. All block shares sum to one. The quality summary is unchanged from the previous committed summary. Scripts 03 and 08 were rerun after caption changes; no other original analyses were rerun. Full reconstruction from newly downloaded monthly ZIPs was not performed; safe merge behavior was verified with temporary ZIP fixtures.
