#!/usr/bin/env python3
"""
statistical_heat_stress_characterization.py

Reads daily_WBGT_THI_stats.csv and produces:
 - summary_exposure_statistics.csv
 - categorized_daily.csv
 - plots/*.png

CLI:
  --input  <path to daily_WBGT_THI_stats.csv>
  --outdir <directory to write outputs (flat results/ with plots/ subfolder)>
"""

import argparse
import os
import sys
import pandas as pd
import matplotlib.pyplot as plt

parser = argparse.ArgumentParser(description="Characterize daily heat-stress statistics and produce plots")
parser.add_argument("--input", required=True, help="Input daily CSV (from stage 1)")
parser.add_argument("--outdir", required=True, help="Directory to write outputs (will contain CSVs and a plots/ subfolder)")
args = parser.parse_args()

outdir = args.outdir
plots_dir = os.path.join(outdir, "plots")
os.makedirs(outdir, exist_ok=True)
os.makedirs(plots_dir, exist_ok=True)

summary_csv = os.path.join(outdir, "summary_exposure_statistics.csv")
categorized_csv = os.path.join(outdir, "categorized_daily.csv")

# --------------------------
# Load input
# --------------------------
try:
    df = pd.read_csv(args.input)
except Exception as e:
    print(f"ERROR reading input CSV: {e}", file=sys.stderr)
    sys.exit(1)

df.columns = df.columns.str.strip().str.lower()

# If there is a date column, parse it
date_col = next((c for c in df.columns if "date" in c), None)
if date_col:
    try:
        df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
    except:
        pass

# ----------------------------------------------------------------------
# Identify relevant columns
# ----------------------------------------------------------------------
wbgtout_mean = next((c for c in df.columns if c.startswith("wbgtout") and "mean" in c), None)
wbgtin_mean  = next((c for c in df.columns if c.startswith("wbgtin") and "mean" in c), None)
thi_mean     = next((c for c in df.columns if c.startswith("thi") and "mean" in c), None)

# Fallbacks
if wbgtout_mean is None and "wbgtout" in df.columns:
    wbgtout_mean = "wbgtout"
if wbgtin_mean is None and "wbgtin" in df.columns:
    wbgtin_mean = "wbgtin"
if thi_mean is None and "thi" in df.columns:
    thi_mean = "thi"

# ----------------------------------------------------------------------
# Categorization
# ----------------------------------------------------------------------
cat_df = df.copy()

def wbgt_category(v):
    try:
        v = float(v)
    except:
        return "Unknown"
    if v < 25:
        return "Safe"
    elif v < 28:
        return "Caution"
    elif v < 31:
        return "Extreme Caution"
    elif v < 33:
        return "Danger"
    else:
        return "Extreme Danger"

def thi_category(v):
    try:
        v = float(v)
    except:
        return "Unknown"
    if v < 72:
        return "Comfort"
    elif v < 79:
        return "Alert"
    elif v < 89:
        return "Danger"
    else:
        return "Emergency"

if wbgtout_mean:
    cat_df["wbgtout_category"] = cat_df[wbgtout_mean].apply(wbgt_category)
if wbgtin_mean:
    cat_df["wbgtin_category"] = cat_df[wbgtin_mean].apply(wbgt_category)
if thi_mean:
    cat_df["thi_category"] = cat_df[thi_mean].apply(thi_category)

# ----------------------------------------------------------------------
# Add ranges if min/max exist
# ----------------------------------------------------------------------
def add_range(prefix):
    max_col = f"{prefix}_max"
    min_col = f"{prefix}_min"
    if max_col in df.columns and min_col in df.columns:
        cat_df[f"{prefix}_range"] = df[max_col] - df[min_col]

for p in ("wbgtout", "wbgtin", "thi"):
    add_range(p)

# ----------------------------------------------------------------------
# Threshold exceedances (outdoor WBGT)
# ----------------------------------------------------------------------
thresholds = [25, 27, 28, 30, 32]
if wbgtout_mean:
    for t in thresholds:
        colname = f"wbgtout_above_{t}"
        cat_df[colname] = (cat_df[wbgtout_mean] > t).astype(int)

# Save categorized CSV
try:
    cat_df.to_csv(categorized_csv, index=False)
    print(f"SUCCESS: categorized CSV saved → {categorized_csv}")
except Exception as e:
    print(f"ERROR saving categorized CSV: {e}", file=sys.stderr)

# ----------------------------------------------------------------------
# SUMMARY STATISTICS
# ----------------------------------------------------------------------
summary = {}

def fill_summary(label, mean_col):
    if mean_col is None:
        summary[f"{label}_mean_overall"] = None
        summary[f"{label}_max_overall"] = None
        summary[f"{label}_min_overall"] = None
        return

    prefix = mean_col.replace("_mean", "")
    max_col = prefix + "_max"
    min_col = prefix + "_min"

    summary[f"{label}_mean_overall"] = cat_df[mean_col].mean()
    summary[f"{label}_max_overall"] = cat_df[max_col].max() if max_col in cat_df else cat_df[mean_col].max()
    summary[f"{label}_min_overall"] = cat_df[min_col].min() if min_col in cat_df else cat_df[mean_col].min()

fill_summary("WBGTout", wbgtout_mean)
fill_summary("WBGTin", wbgtin_mean)
fill_summary("THI", thi_mean)

summary["Days_in_Danger_or_Worse_WBGTout"] = int(cat_df["wbgtout_category"].isin(["Danger", "Extreme Danger"]).sum()) if "wbgtout_category" in cat_df else None
summary["Days_in_Danger_or_Worse_WBGTin"]  = int(cat_df["wbgtin_category"].isin(["Danger", "Extreme Danger"]).sum()) if "wbgtin_category" in cat_df else None

# Save summary CSV
pd.DataFrame([summary]).to_csv(summary_csv, index=False)
print(f"SUCCESS: summary saved → {summary_csv}")

# ----------------------------------------------------------------------
# PLOTTING HELPERS
# ----------------------------------------------------------------------

def save_ts_plot(col, title):
    """Save timeseries with corrected x-axis labeling."""
    if col not in cat_df.columns:
        return

    plt.figure(figsize=(10, 4.5))
    plt.plot(cat_df[col], marker='o', linestyle='-')

    # If date exists, use it for x-axis
    if date_col and date_col in cat_df.columns:
        plt.xticks(ticks=range(len(cat_df)), labels=cat_df[date_col].dt.strftime("%Y-%m-%d"), rotation=45)

    plt.title(title)
    plt.xlabel("Date" if date_col else "Index")
    plt.ylabel(col)
    plt.tight_layout()

    fname = os.path.join(plots_dir, f"{col}.png")
    plt.savefig(fname, dpi=150)
    plt.close()
    print(f"Saved plot → {fname}")

# ----------------------------------------------------------------------
# TIMESERIES PLOTS
# ----------------------------------------------------------------------
if wbgtout_mean:
    save_ts_plot(wbgtout_mean, "Daily Mean WBGT (Outdoor)")

if wbgtin_mean:
    save_ts_plot(wbgtin_mean, "Daily Mean WBGT (Indoor)")

if thi_mean:
    save_ts_plot(thi_mean, "Daily Mean THI")

# ----------------------------------------------------------------------
# ADDITIONAL IMPORTANT PLOT:
# “Number of WBGT outdoor thresholds exceeded per day”
# ----------------------------------------------------------------------
exceed_cols = [c for c in cat_df.columns if c.startswith("wbgtout_above_")]
if exceed_cols:
    cat_df["num_thresholds_exceeded"] = cat_df[exceed_cols].sum(axis=1)

    plt.figure(figsize=(10, 4.5))
    plt.plot(cat_df["num_thresholds_exceeded"], marker="o")
    if date_col:
        plt.xticks(range(len(cat_df)), cat_df[date_col].dt.strftime("%Y-%m-%d"), rotation=45)

    plt.title("Number of Outdoor WBGT Thresholds Exceeded per Day")
    plt.xlabel("Date" if date_col else "Index")
    plt.ylabel("Count of thresholds exceeded")
    plt.tight_layout()

    fname = os.path.join(plots_dir, "wbgtout_threshold_exceedance_count.png")
    plt.savefig(fname, dpi=150)
    plt.close()
    print(f"Saved plot → {fname}")

print("All outputs written to:", outdir)

