# PaleoVeg training and spatial validation

This directory contains the publication-oriented workflow for building and
evaluating the categorical PaleoVeg 1.0 model. Its locked specification is:

- target: UMD 8 km land-cover classes `1`–`10` and `12`, derived from AVHRR;
- excluded AVHRR codes: `0`, `11`, `13`, and `14`;
- predictors: WorldClim 2.1 BIO1 and BIO4–BIO19 at 5 arc-minutes;
- estimator: `RandomForestClassifier(max_depth=20, random_state=42,
  n_jobs=-1)` with all other scikit-learn defaults.

The model is evaluated with an untouched 10% holdout of complete 5° × 5° tiles
and five-fold blocked spatial cross-validation on complete 5° × 5° tiles in
the remaining development region. The final distributed model is then fit to
all eligible observations.

## Software environment

Create the environment from the repository root. The basic installation is
sufficient for applying the released model. The reproduction installation
adds the geospatial, scientific-I/O, and plotting packages required to rebuild
the training data, train and evaluate the models, and generate the manuscript
results and figures.

```bash
# Apply the released model
python -m venv venv
venv/bin/pip install -e .

# Reproduce model training, analyses, and manuscript figures
python -m venv reproduction-venv
reproduction-venv/bin/pip install -e '.[reproduction,test]'
```

The `reproduction` extra adds PyArrow, Rasterio, SciPy, Matplotlib, netCDF4,
and pyshp.

Browser/Pyodide parity testing has a separate optional installation and also
requires Chrome or Chromium:

```bash
python -m venv browser-test-venv
browser-test-venv/bin/pip install -e '.[browser-test]'
```

The climate-data reconstruction additionally requires the command-line
programs CDO, curl, unzip, and `sha256sum`. These are system packages and are
not installed by pip.

The archived analysis metadata records Python 3.13.3, NumPy 2.4.4, pandas
3.0.2, scikit-learn 1.9.0, Rasterio 1.5.0, and SciPy 1.17.1. Use these versions
when exact numerical reproduction is required; the package metadata permits a
broader range of NumPy and pandas versions. Native model application pins
scikit-learn to 1.9.0, matching the trained classifier.

## Inputs

Place the AVHRR GeoTIFF and the 17 WorldClim GeoTIFFs as described in
[`data/raw/README.md`](data/raw/README.md). PaleoVeg samples the lower-left
AVHRR pixel corner and WorldClim grid nodes; this coordinate convention is
implemented explicitly in the table-construction workflow.

The vegetation target is the institute-held original UMD 8 km Global Land
Cover Classification in GeoTIFF form. The local GLCF product archive retains
the matching product metadata and supplier note; the PaleoVeg input is
byte-identical to that archived product file. Its evidence, checksum,
literature, class-code documentation, and current download status are recorded
in [`AVHRR_PROVENANCE.md`](AVHRR_PROVENANCE.md).

Verify an independently obtained copy of this third-party raster against the
exact PaleoVeg 1.0 target:

```bash
reproduction-venv/bin/python training/verify_avhrr_target.py /path/to/umd_8km_landcover.tif
```

The matched-LGM comparison additionally uses the published Shao et al. (2018)
reconstruction outputs. They are not inputs to PaleoVeg. Download and verify
them with:

```bash
bash training/download_shao_lgm_data.sh
```

The present-day coastline shown in Figure 10 is the vendored Natural Earth
1:110 million coastline. Its version, source, licence, and checksums are recorded
in [`data/natural_earth/README.md`](data/natural_earth/README.md); no separate
download is required.

## Reproduce the analyses

Run the following commands from the repository root using the reproduction
environment created above.

Build the coordinate-preserving modeling table:

```bash
reproduction-venv/bin/python training/build_training_data.py
```

Run blocked CV, evaluate the development-fit model once on the external
holdout, and fit the production model to all observations:

```bash
reproduction-venv/bin/python training/validate_and_train.py
```

Run the matched Shao-like BIO1+BIO12 versus full 17-predictor comparison,
including Shao et al.'s Equation 3 goodness score:

```bash
reproduction-venv/bin/python training/compare_predictor_sets.py
```

To reproduce the matched-LGM behavioural-verification figures, first download
the published Shao comparison fields as above. Then retrieve the six-model
PMIP3/CMIP5 source fields directly from ESGF (subject to its terms of use).
The downloader verifies the official source-segment checksums and reconstructs
the canonical input layout; provenance is in
[`PMIP3_LGM_PROVENANCE.md`](PMIP3_LGM_PROVENANCE.md). Prepare the ensemble
climate and run the comparison:

```bash
reproduction-venv/bin/python training/download_pmip3_lgm_data.py --destination /path/to/pmip3_lgm
bash training/prepare_shao_lgm_climate.sh /path/to/pmip3_lgm/atmos/mon
PYTHONPATH=training reproduction-venv/bin/python training/run_shao_lgm_experiment.py
PYTHONPATH=training reproduction-venv/bin/python training/run_shao_lgm_member_sensitivity.py
```

Estimate distance-dependent autocorrelation in the full model's signed
class-probability residuals on the external spatial test:

```bash
PYTHONPATH=training reproduction-venv/bin/python training/analyze_residual_spatial_autocorrelation.py
```

Numerical outputs and model artifacts are placed beneath `training/results/`
and `training/models/`. Final manuscript figures are written directly to the
repository-level [`figures/`](../figures/) directory; its README identifies the
script responsible for each figure. Generated numerical and model artifacts
should be included in the versioned publication archive rather than committed
as mutable binaries.

For a quick smoke test, both scripts accept `--max-rows`. Such runs are for
software verification only and are not scientifically valid results.
