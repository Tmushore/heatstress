#!/usr/bin/env python3
"""
15_min_to_daily_heat_stress.py

Reads a 15-minute (or otherwise sub-daily) CSV and writes daily aggregated WBGT/THI statistics.

Outputs (saved to <outdir>):
 - daily_WBGT_THI_stats.csv

CLI:
  --input  <path to input CSV>
  --outdir <directory to write outputs>
"""

import argparse
import os
import sys
import pandas as pd
from datetime import datetime

parser = argparse.ArgumentParser(description="Aggregate sub-daily heat-stress data to daily statistics")
parser.add_argument("--input", required=True, help="Input CSV file (sub-daily observations)")
parser.add_argument("--outdir", required=True, help="Output directory to write daily_WBGT_THI_stats.csv")
parser.add_argument("--dayfirst", action="store_true", help="Parse datetimes day-first (e.g., D/M/Y). Default: tries auto")
args = parser.parse_args()

os.makedirs(args.outdir, exist_ok=True)
out_csv = os.path.join(args.outdir, "daily_WBGT_THI_stats.csv")

# Read CSV (robust encoding)
try:
    df = pd.read_csv(args.input, encoding="latin1")
except Exception as e:
    print(f"ERROR reading input CSV: {e}", file=sys.stderr)
    sys.exit(1)

# Normalize column names
df.columns = df.columns.str.strip().str.replace(" ", "_").str.lower()

# Find a datetime column
dt_col = None
for c in df.columns:
    # common patterns: 'datetime', 'date_time', 'date/time', 'timestamp', or any column containing 'date' or 'time'
    if "datetime" in c or ("date" in c and "time" in c) or c in ("timestamp", "time"):
        dt_col = c
        break
if dt_col is None:
    # fallback: any column containing 'date'
    for c in df.columns:
        if "date" in c:
            dt_col = c
            break

if dt_col is None:
    print("ERROR: No datetime column found. Inspect CSV column names.", file=sys.stderr)
    print("Columns:", list(df.columns), file=sys.stderr)
    sys.exit(1)

# Parse datetime
try:
    df[dt_col] = pd.to_datetime(df[dt_col], dayfirst=args.dayfirst, errors="coerce")
except Exception:
    df[dt_col] = pd.to_datetime(df[dt_col], errors="coerce")

# Drop rows that failed to parse
n_bad = df[dt_col].isna().sum()
if n_bad > 0:
    print(f"WARNING: {n_bad} rows have invalid datetimes and will be dropped.")

df = df.dropna(subset=[dt_col])

# Create date column
df["date"] = df[dt_col].dt.date

# Candidate metric columns (flexible): look for typical names
candidates = {
    "wbgtout": ["wbgtout", "wbgt_out", "wbgt-out", "wbgt outdoor", "wbgt_outdoor"],
    "wbgtin":  ["wbgtin", "wbgt_in", "wbgt-in", "wbgt indoor", "wbgt_indoor"],
    "thi":     ["thi", "temperature_humidity_index", "temp_humidity_index"]
}

found = {}
for key, names in candidates.items():
    for name in names:
        if name in df.columns:
            found[key] = name
            break

# Additionally include any column named 'temperature' or 'humidity' if present
if "temperature" in df.columns:
    found.setdefault("temperature", "temperature")
if "humidity" in df.columns:
    found.setdefault("humidity", "humidity")

if not found:
    print("WARNING: No WBGT/THI/temperature/humidity columns detected. The output will contain only dates.", file=sys.stderr)

# Build aggregation dict
agg_dict = {}
for k, col in found.items():
    agg_dict[col] = ["min", "mean", "max"]

# If nothing to aggregate, create minimal output
if not agg_dict:
    daily = df[["date"]].drop_duplicates().sort_values("date")
else:
    daily = df.groupby("date").agg(agg_dict)

    # Flatten MultiIndex columns
    daily.columns = ["_".join(col).strip() for col in daily.columns.values]
    daily = daily.reset_index()

# Save CSV
try:
    daily.to_csv(out_csv, index=False)
    print(f"SUCCESS: daily stats written to: {out_csv}")
except Exception as e:
    print(f"ERROR writing daily CSV: {e}", file=sys.stderr)
    sys.exit(1)
