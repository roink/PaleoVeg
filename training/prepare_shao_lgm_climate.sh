#!/usr/bin/env bash
# Prepare the monthly, six-model PMIP3 LGM ensemble used by the matched
# Shao et al. (2018) behavioural-verification experiment.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PMIP_ROOT="${1:-/data/sfb806/pmip3/lgm/atmos/mon}"
OUT="$ROOT/training/results/shao_lgm_experiment/climate"
GRID="${TMPDIR:-/tmp}/paleoveg_shao_lgm_1deg.grid"
WORK="${TMPDIR:-/tmp}/paleoveg_shao_lgm_climate"
MODELS=(CNRM-CM5 FGOALS-g2 IPSL-CM5A-LR MIROC-ESM MPI-ESM-P MRI-CGCM3)
VARS=(tas tasmin tasmax pr)

mkdir -p "$OUT" "$WORK"
cdo -s griddes "$ROOT/training/data/shao_lgm/PMIP_1deg_no_co2_correction.nc" > "$GRID"

for var in "${VARS[@]}"; do
    files=()
    for model in "${MODELS[@]}"; do
        # Select only the canonical CMIP5 monthly time series.  The institute
        # archive also contains derived climatologies and regridded products,
        # which must not silently enter the matched experiment.
        mapfile -t candidates < <(find "$PMIP_ROOT/$var" -maxdepth 1 -type f \
            -name "${var}_Amon_${model}_lgm_r1i1p1_[0-9][0-9][0-9][0-9][0-9][0-9]-[0-9][0-9][0-9][0-9][0-9][0-9].nc" \
            -print | sort)
        if [[ "${#candidates[@]}" -ne 1 ]]; then
            echo "Expected one canonical PMIP3 input for $var / $model under $PMIP_ROOT; found ${#candidates[@]}" >&2
            exit 1
        fi
        input="${candidates[0]}"
        output="$WORK/${var}_${model}_1deg_monclim.nc"
        if [[ "$var" == "pr" ]]; then
            # CMIP precipitation flux (kg m-2 s-1) -> monthly water total (mm).
            # CDO's muldpm reads each NetCDF file's CF calendar and therefore
            # uses that model's own month lengths before the ensemble mean.
            cdo -L -s -O -ymonmean -remapbil,"$GRID" -muldpm -mulc,86400 "$input" "$output"
        else
            cdo -L -s -O -ymonmean -remapbil,"$GRID" "$input" "$output"
        fi
        files+=("$output")
    done
    cdo -L -s -O ensmean "${files[@]}" "$OUT/ensemble_${var}_1deg_monclim.nc"
done
