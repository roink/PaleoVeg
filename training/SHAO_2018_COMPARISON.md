# Relationship between Shao et al. (2018) and PaleoVeg 1.0

## Scope

Shao et al. (2018), *Statistical reconstruction of global vegetation for the
last glacial maximum*, is the published scientific predecessor of PaleoVeg.
The original implementation is no longer available. PaleoVeg must therefore be
described as an open reimplementation and methodological modernization, not as
a release, port, or numerically identical reproduction of the original code.

## Directly supported comparison

| Component | Shao et al. (2018) | PaleoVeg 1.0 |
|---|---|---|
| Modern vegetation target | AVHRR 8 km IGBP classes; cultivated/managed land excluded | Same AVHRR class lineage and eleven retained natural/bare-ground classes |
| Modern climate source | ERA-Interim, 1980–2009, 0.75° | WorldClim 2.1, 5 arc-minutes |
| Climate predictors | Nine tested pairs combining annual mean/minimum/maximum rainfall and temperature | Seventeen BIOCLIM predictors: BIO1 and BIO4–BIO19 |
| Statistical method | Empirical rainfall–temperature bin frequencies for each vegetation class | Random Forest classifier; class probabilities used as vegetation fractions |
| Selected climate model | Annual mean rainfall and annual mean temperature, `p_i(Ra, Ta)` | Fixed 17-predictor Random Forest |
| Modern evaluation | Whole-grid self-consistency score relative to randomly rearranged AVHRR | Five-fold 5° spatial-block CV plus a separate 5° external tile holdout |
| LGM climate | Six-model PMIP3 21 ka ensemble interpolated to 0.75° | Matched six-model PMIP3 ensemble mean at 1°, transformed to required BIOCLIM variables for behavioural verification |
| CO₂ correction | Diagonal transition factors from 310 to 180/185 ppm | Same published class factors, exposed explicitly and generalized by concentration |
| Palaeo comparison | Qualitative comparison with sparse BIOME 6000 pollen-derived biomes | Matched LGM global-area behavioural verification and a separate European pollen-proxy comparison reported by Kern et al. (2026) |
| Code availability | Original implementation lost/unavailable | Open training, validation, inference, and browser workflows |

The methodological differences are substantial. The manuscript should avoid
implying that the Random Forest is merely a software rewrite of the binned
vegetation–climate model. The defensible claim is that PaleoVeg preserves and
modernizes the published modeling concept: learn modern probabilistic
vegetation–climate relationships from AVHRR classes, transfer them to
paleoclimate, and apply the published low-CO₂ adjustment.

## Published results available for direct reference

For the selected annual-mean rainfall/temperature model (model 5 in Table 1),
Shao et al. reported the following class scores:

| Class | Score |
|---|---:|
| Evergreen needleleaf forest | 0.52 |
| Evergreen broadleaf forest | 0.77 |
| Deciduous needleleaf forest | 0.41 |
| Deciduous broadleaf forest | 0.17 |
| Mixed forest | 0.34 |
| Woodland | 0.48 |
| Wooded grassland | 0.48 |
| Closed shrubland | 0.29 |
| Open shrubland | 0.50 |
| Grassland | 0.53 |
| Bare ground | 0.97 |
| Ensemble | 0.51 |

These scores are not accuracy or F1 and must not be placed in a shared metric
column with PaleoVeg's classification metrics. Shao et al. defined the score as
one minus the mean squared vegetation-fraction error divided by the analogous
error of a randomly rearranged AVHRR reference. A valid numerical comparison
requires implementing that published score for PaleoVeg predictions on a
clearly matched modern grid.

Other published quantitative/qualitative targets include:

- evergreen broadleaf forest occurrence in the modern Amazon, tropical Africa,
  and Southeast Asia (Fig. 1);
- global class probability surfaces and the response to the CO₂ correction
  (Fig. 4);
- LGM grassland, open shrubland, needleleaf forest, and non-bare cover, with
  BIOME 6000 locations overlaid (Fig. 5);
- global vegetation-area changes with and without CO₂ correction (Fig. 6);
- central Amazon evergreen broadleaf cover declining from more than 80% today
  to about 40% under LGM climate and below 40% after CO₂ correction (Fig. 7);
- Sahara open shrubland and grassland reaching up to roughly 40% each, and bare
  ground declining from about 80% today to roughly 20–30% at the LGM (Fig. 8).

## Recommended verification experiments

### 1. Published-score modern verification

Shao et al.'s Eq. 3 score is now implemented. A matched experiment compares a
BIO1+BIO12 Random Forest—the closest WorldClim/PaleoVeg analogue of selected
model 5—with the full 17-predictor model using identical spatial partitions.
See [`results/predictor_set_comparison/README.md`](results/predictor_set_comparison/README.md).
Modern observed, predicted, and difference maps for the same classes as Fig. 1
remain to be produced.

### 2. CO₂ implementation verification

Verify that the eleven PaleoVeg correction factors exactly reproduce Table 2.
Generate before/after probability surfaces and class-area summaries. This is
the strongest component-level reproduction because the factors are explicitly
published and already implemented in PaleoVeg.

### 3. LGM behavioural verification

The matched six-member PMIP3 ensemble has been used to reproduce the global
class-area experiment of Fig. 6 with PaleoVeg, with and without the 185 ppm
CO₂ correction. The comparison is intentionally behavioural verification, not
independent validation. Additional regional experiments are optional rather
than prerequisites for the PaleoVeg 1.0 release.

### 4. BIOME 6000 comparison

Acquire the Harrison (2017) dataset cited by Shao et al., document the mapping
from its 24 biome classes to the nine comparison classes, and define a
quantitative site-level evaluation in addition to the original visual overlay.
