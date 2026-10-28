# Residual spatial autocorrelation

This directory contains the reproducible distance-class analysis of residuals
from the full 17-predictor development model on the untouched external spatial
test. Run it with:

```bash
PYTHONPATH=training python training/analyze_residual_spatial_autocorrelation.py
```

The analysis sampled at most 1,000 observations from each of 132 external
5-degree tiles (105,102 observations) and evaluated 1,999,995 valid random
point pairs using haversine distance. Signed class residuals are predicted
probability minus binary observed class occurrence.

The practical range is the first distance-class upper edge after which
absolute binned residual correlation remains at or below 0.05 through 1,000
km. The class-specific ranges are 100--500 km (median 300 km):

| Class residual | Range (km) |
|---|---:|
| ENF | 300 |
| EBF | 400 |
| DNF | 100 |
| DBF | 150 |
| MF | 300 |
| WL | 500 |
| WGL | 300 |
| CSL | 300 |
| OSL | 500 |
| GL | 200 |
| BG | 500 |

The 5-degree choice is therefore a defensible scale for reducing dependence
among nearby signed residuals, not a guarantee of train--test independence.
Tiles narrow east--west with latitude, and no exclusion buffer separates
adjacent training and validation tiles.

Files:

- `sampled_external_residuals.parquet`: reproducible stratified sample and residuals;
- `residual_distance_correlogram.csv`: signed-residual distance-class correlations and semivariances;
- `residual_autocorrelation_range_summary.csv`: practical ranges;
- `run_metadata.json`: inputs, checksum, sampling settings, seed, and definitions.
