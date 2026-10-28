# Changelog

## 1.0.0

- Distribute the all-data 17-predictor Random Forest documented in the PaleoVeg
  manuscript, trained on 2,823,308 observations. Predictions differ from the
  classifier distributed with v0.1.2 and used by v0.2.0.
- Add reproducible training, five-fold spatial validation, a separate 132-tile
  test, and the matched BIO1+BIO12 predictor comparison.
- Include the matched LGM comparison, residual spatial-correlation analysis,
  input provenance, aggregate results, and publication figures.
- Record the classifier checksum and training specification in package metadata.
- Pin native scikit-learn to the training version (1.9.0); require Python 3.11+.
- Include training sources in the source distribution and verify model assets
  before PyPI publication. Complete the GitHub draft before publishing it.

The browser uses scikit-learn 1.8.0 supplied by Pyodide v314.0.2. Native/browser
parity was verified with the released classifier for 65 input rows and five CO₂
scenarios (absolute and relative tolerances of 1e-12). Cross-version pickle
compatibility is not guaranteed by scikit-learn; native installation uses 1.9.0.
