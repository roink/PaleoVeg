# PaleoVeg outer-tile validation results

This is the first full run of the fixed historical PaleoVeg Random Forest under
the spatial protocol in [`../../METHODS.md`](../../METHODS.md). It used
2,823,308 complete observations across 1,314 global 5° tiles.

## Five-fold development-region CV

| Metric | Mean | SD |
|---|---:|---:|
| Accuracy | 0.789666 | 0.010989 |
| Balanced accuracy | 0.618667 | 0.025168 |
| Macro F1 | 0.621861 | 0.023979 |
| Weighted F1 | 0.785670 | 0.012215 |
| Multiclass log loss | 0.563345 | 0.029032 |

Each fold held out 236–237 complete tiles containing approximately 505,753
observations. Fold accuracy ranged from 0.779878 to 0.806309.

## Untouched external spatial test

The external set comprised 132 complete tiles and 294,544 observations.

| Metric | Value |
|---|---:|
| Accuracy | 0.837641 |
| Balanced accuracy | 0.652168 |
| Macro F1 | 0.652379 |
| Weighted F1 | 0.832567 |
| Multiclass log loss | 0.448912 |

The majority-class baseline (always class 12) scores 0.507286 accuracy,
0.090909 balanced accuracy, and 0.061192 macro F1 on the same external set.

The external set happened to be easier than the average CV fold, illustrating
why fold-to-fold variation must be reported rather than relying on one spatial
holdout. Deciduous broadleaf forest (class 4) was the weakest class, with
recall 0.0491 and F1 0.0853. Bare ground (class 12) had F1 0.9831.

These numbers validate spatial transfer of this reimplementation; they do not
constitute independent validation against field observations or BIOME6000.
