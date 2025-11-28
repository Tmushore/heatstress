nextflow.enable.dsl=2

/*
  2-step heat stress workflow:
    - STEP 1: 15min -> daily_WBGT_THI_stats.csv
    - STEP 2: characterization -> summary_exposure_statistics.csv, categorized_daily.csv, plots/*.png
*/

params.input  = params.input ?: "../data/Mt_Darwin_Weather_Aug_Sep_Oct_2025.csv"
params.outdir = params.outdir ?: "../results"

workflow {

    /*
     * INPUT CHANNEL
     */
    input_csv_ch = Channel.fromPath(params.input)


    /*
     * STEP 1 — Daily statistics
     */
    daily_stats_ch = DAILY_STATS(input_csv_ch)


    /*
     * STEP 2 — Characterize exposure
     */
    CHARACTERIZE(daily_stats_ch)

}




/*
 * PROCESS 1
 */
process DAILY_STATS {
    publishDir params.outdir, mode: 'copy'
    container 'heatstress:latest'

    input:
    path input_csv

    output:
    path "daily_WBGT_THI_stats.csv"

    script:
    """
    mkdir -p tmp_out
    python /app/scripts/15_min_to_daily_heat_stress.py --input ${input_csv} --outdir tmp_out
    mv tmp_out/daily_WBGT_THI_stats.csv daily_WBGT_THI_stats.csv
    """
}


/*
 * PROCESS 2
 */
process CHARACTERIZE {
    publishDir params.outdir, mode: 'copy'
    container 'heatstress:latest'

    input:
    path daily_csv

    output:
    path "summary_exposure_statistics.csv"
    path "categorized_daily.csv"
    path "plots/*"

    script:
    """
    mkdir -p out
    python /app/scripts/statistical_heat_stress_characterization.py --input ${daily_csv} --outdir out
    mv out/summary_exposure_statistics.csv summary_exposure_statistics.csv
    mv out/categorized_daily.csv categorized_daily.csv
    mkdir -p plots
    mv out/plots/* plots/ || true
    """
}
