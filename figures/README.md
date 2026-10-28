# PaleoVeg manuscript figures

This directory is the canonical location for all manuscript figures. Each
figure is provided as PDF for manuscript use and PNG for convenient viewing.

| Figure | Description | Source |
| --- | --- | --- |
| 1 | Relationship between the Shao model and the two PaleoVeg configurations | Authored as `paleoveg_figure1_model_comparison_layout_v7.svg` and exported to PDF and PNG |
| 2 | Global spatial partition | `training/plot_publication_figures.py` |
| 3 | Matched blocked-cross-validation comparison | `training/plot_publication_figures.py` |
| 4 | Class-wise Shao goodness scores | `training/plot_publication_figures.py` |
| 5 | External-test confusion matrices | `training/plot_publication_figures.py` |
| 6 | External-tile accuracy comparison | `training/plot_publication_figures.py` |
| 7 | Random Forest feature importance | `training/plot_publication_figures.py` |
| 8 | Residual spatial autocorrelation | `training/analyze_residual_spatial_autocorrelation.py` |
| 9 | Last Glacial Maximum global area fractions | `training/run_shao_lgm_experiment.py` |
| 10 | Last Glacial Maximum dominant-class map | `training/run_shao_lgm_experiment.py` |

The scripts write directly to this directory. Numerical results used to build
the figures are stored under `training/results/`; see `training/README.md` for
the complete reproduction workflow.
