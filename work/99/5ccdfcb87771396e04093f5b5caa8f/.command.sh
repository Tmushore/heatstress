#!/bin/bash -ue
mkdir -p out
python /app/scripts/statistical_heat_stress_characterization.py --input daily_WBGT_THI_stats.csv --outdir out
mv out/summary_exposure_statistics.csv summary_exposure_statistics.csv
mv out/categorized_daily.csv categorized_daily.csv
mkdir -p plots
mv out/plots/* plots/ || true
