# BIO1+BIO12 versus full-PaleoVeg comparison

This matched experiment compares two Random Forests using identical AVHRR
targets, hyperparameters, 5° spatial tiles, folds, external holdout, and random
seeds. The only changed variable is the predictor set:

- **Shao-like RF:** BIO1 (annual mean temperature) and BIO12 (annual
  precipitation), corresponding most closely to Shao et al.'s selected model 5.
- **Full PaleoVeg RF:** BIO1 and BIO4–BIO19 (17 predictors).

The reduced RF is not numerically identical to Shao model 5. Shao et al. used
binned ERA-Interim annual-mean temperature/rainfall frequencies, whereas this
experiment uses the PaleoVeg RF and WorldClim equivalents. It isolates the
effect of expanding from the two closest climate variables to PaleoVeg's full
predictor set.

## Spatially blocked cross-validation

| Model | Accuracy | Balanced accuracy | Macro F1 | Log loss | Shao Eq. 3 score |
|---|---:|---:|---:|---:|---:|
| BIO1 + BIO12 | 0.694800 ± 0.010589 | 0.472297 ± 0.012765 | 0.467642 ± 0.010716 | 0.868508 ± 0.050899 | 0.656556 ± 0.007963 |
| Full 17 predictors | 0.789666 ± 0.010989 | 0.618667 ± 0.025168 | 0.621861 ± 0.023979 | 0.563345 ± 0.029032 | 0.744753 ± 0.010513 |

Adding the full BIOCLIM predictor set improves mean blocked-CV accuracy by
0.094867, balanced accuracy by 0.146371, macro F1 by 0.154219, and the Shao
goodness score by 0.088197. Mean log loss decreases by 0.305163.

## External spatial test

| Model | Accuracy | Balanced accuracy | Macro F1 | Log loss | Shao Eq. 3 score |
|---|---:|---:|---:|---:|---:|
| BIO1 + BIO12 | 0.738728 | 0.493138 | 0.484219 | 0.745358 | 0.669386 |
| Full 17 predictors | 0.837641 | 0.652168 | 0.652379 | 0.448912 | 0.766470 |

## Relationship to Shao et al. model 5

Shao et al. reported an ensemble Equation 3 score of 0.51 for model 5. Their
score was calculated as a whole-grid self-consistency assessment using
ERA-Interim and the same AVHRR data used to build their binned probability
model. PaleoVeg's values above are spatially held out, use WorldClim, and use a
Random Forest. They use the same published equation and class concept, but are
not a like-for-like benchmark. The most defensible direct PaleoVeg comparison
is therefore BIO1+BIO12 versus 17 predictors under the matched blocked design;
the published 0.51 provides historical context.

## Files

- `*_external_confusion_matrix.csv`: aggregate observed/predicted class counts,
  permitting Figure 5 reproduction without distributing row-level target labels.
- `metrics.csv`: fold and external classification metrics.
- `cv_summary.csv`: fold means and standard deviations.
- `shao_goodness_scores.csv`: every class/fold/external Equation 3 result.
- `shao_goodness_cv_summary.csv`: class-level blocked-CV summaries.
- `shao_model5_external_comparison.csv`: published model-5 scores alongside
  both PaleoVeg external-test configurations.
- `external_tile_accuracy_comparison.csv`: paired external-tile accuracies and
  their differences, used for Figure 6.
- `run_metadata.json`: hashes, features, model parameters, and score protocol.

Large external prediction tables and serialized models are generated locally
but excluded from Git.
