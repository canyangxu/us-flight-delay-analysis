# Improve data validation and add flight outcome analysis

## Summary

Arrival-only delay rates omit cancelled and diverted flights. Add a five-category outcome analysis using every scheduled record in each departure block, plus quality checks that keep unknown states visible. The full-data result preserves the broad time pattern: combined disruption is 11.7% at 06:00–06:59, 34.3% at 19:00–19:59 and 21.2% at 23:00–23:59.

## Motivation

Strengthen the course project's preprocessing evidence, feature engineering, public interpretation and reproducibility. Test whether the existing early-departure finding survives a broader passenger-outcome definition without treating cancellations, diversions and delays as equal losses or making causal claims.

## Changes

- Preserve the original quality summary and add missingness, legal-value, date-coverage, state-consistency and disk-backed global duplicate screening reports.
- Share classification rules between validation and the new chunked outcome analysis. Export block/global counts, check totals, and generate a three-panel figure with all five categories.
- Correct the time-pattern claim to reflect the late-night decline; clarify that airport rates describe final arrivals of flights departing each origin. Regenerate the affected figures.
- Document the audience, feature definitions, denominator differences, biases, ethical limits, real schema and monthly reconstruction workflow.
- Protect existing CSV/Parquet outputs when merge inputs are absent or invalid, and preserve existing extracted files. Keep DuckDB optional.

## Validation

- Nine regression tests pass with DuckDB installed, including classification boundaries, unknown times, chunk equivalence, cross-chunk duplicates, empty inputs, undefined rates and merge safety. Fixtures use temporary directories.
- Verified Release asset size and SHA-256; ran scripts 01 and 12 on all 7,043,316 records covering July 1, 2025 through June 30, 2026.
- Global totals reconcile: 5,350,236 completed/not delayed ≥15 minutes; 1,546,047 completed/delayed ≥15 minutes; 127,324 cancelled; 19,708 diverted; one unknown. Every observed block has five categories whose counts and shares reconcile.
- No missing expected dates/months, invalid flags, completed minute/flag conflicts or duplicate hashes were detected. Original quality summary values remain unchanged.
- Reran scripts 03 and 08; visually checked all three new/regenerated figures and corrected overlapping time labels. Checked local documentation links and `git diff --check`.

## Limitations

The one record without a completed-arrival flag remains unknown. Hash screening has collision and textual-normalization limitations. Patterns are descriptive and unadjusted for route, season, carrier or network, and flights are not passenger-weighted. Combined disruption categories have different impacts. Original analyses other than 03 and 08 were not rerun. Monthly CSV/Parquet rebuild safety was tested with small fixtures; the full dataset was not independently rebuilt from new BTS monthly downloads. A separate public-facing course artifact and presentation remain separate deliverables.
