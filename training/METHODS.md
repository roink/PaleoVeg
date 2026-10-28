# Spatial validation design

## Scientific model held fixed

This workflow evaluates the Shao-style PaleoVeg model. The categorical AVHRR
target, seventeen BIOCLIM predictors, class exclusions, and Random Forest
hyperparameters are fixed to those used by the released PaleoVeg classifier.
No class balancing, feature scaling, hyperparameter search, elevation,
fractional targets, neural network, or ensemble is introduced.

## Training-data construction

Spatial validation starts from the archived AVHRR and WorldClim rasters and
preserves geographic coordinates. AVHRR labels are sampled at the lower-left
pixel corner and WorldClim predictors at their raster grid nodes. Rows with
non-finite predictors are excluded. The resulting canonical PaleoVeg 1.0
table contains 2,823,308 complete observations.

## Spatial partitions

The Earth is divided into fixed 5° × 5° longitude/latitude tiles. Of 1,314
tiles containing eligible observations, 132 tiles (10%, rounded upward) are
selected with seed 42 as a final external test region. They contain 294,544
observations and are not used in cross-validation or development-model fitting.

The remaining 1,182 development tiles are assigned intact to five folds. A
deterministic greedy assignment balances observation counts between folds;
tie-breaking uses seed 59. Each fold contains 236–237 tiles and 505,752–505,753
observations. Thus no tile contributes pixels to both the training and
validation side of a fold.

The 5° scale is supported by the PaleoVeg signed-residual correlogram: all
classes reach the practical $|\rho|\leq0.05$ range within 100--500 km. This
supports the block size as a reasonable global compromise, rather than proving
complete spatial independence.

## Evaluation and final fitting

For each fold, a fresh fixed-specification Random Forest is fit to the other
four development folds. Report accuracy, balanced accuracy, macro and weighted
F1, multiclass log loss, per-class precision/recall/F1, and the complete
confusion matrix. Fold means and sample standard deviations quantify spatial
transfer performance and regional variability. A development-region majority-
class predictor supplies a simple external-test baseline.

After CV, a fresh model is fit to all development observations and evaluated
once on the external tiles. Finally, a release model with the same fixed
configuration is fit to all eligible observations. The external result
estimates spatial transfer; the all-data model is the production artifact and
must not be described as having been trained without the external observations.

## Current limitations

- Degree tiles are unequal-area, especially at high latitudes.
- Random selection of complete external tiles does not guarantee environmental
  or class balance.
- Five-degree tiles vary in physical width with latitude and do not impose a
  buffer between training and validation tiles.
- AVHRR represents spatially exhaustive raster labels rather than an
  independent field-observation validation dataset.
- Spatial blocks reduce geographic leakage but do not provide temporal or
  genuinely independent observational validation.
