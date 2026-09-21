"""Validate the merged BTS CSV without deleting or changing flight records."""
import argparse
from pathlib import Path

import pandas as pd

from _config import DATA_FILE, CHART_DATA_DIR
from _quality import audit


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DATA_FILE)
    parser.add_argument("--output-dir", type=Path, default=CHART_DATA_DIR)
    parser.add_argument("--chunk-size", type=int, default=250_000)
    args = parser.parse_args()
    try:
        summary, checks, months, missing_dates = audit(args.input, args.chunk_size, progress=True)
        args.output_dir.mkdir(parents=True, exist_ok=True)
        for name, frame in (("summary", summary), ("checks", checks),
                            ("monthly_counts", months), ("missing_dates", missing_dates)):
            frame.to_csv(args.output_dir / f"01_data_quality_{name}.csv", index=False)
    except (OSError, ValueError, pd.errors.ParserError) as error:
        parser.exit(1, f"Error: {error}\n")
    print(summary.to_string(index=False))
    print(f"Saved quality reports to {args.output_dir}")


if __name__ == "__main__":
    main()
