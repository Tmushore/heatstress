#!/bin/bash -ue
mkdir -p tmp_out
python /app/scripts/15_min_to_daily_heat_stress.py --input Mt_Darwin_Weather_Aug_Sep_Oct_2025\ TM\ 20_11_2025.csv --outdir tmp_out
mv tmp_out/daily_WBGT_THI_stats.csv daily_WBGT_THI_stats.csv
