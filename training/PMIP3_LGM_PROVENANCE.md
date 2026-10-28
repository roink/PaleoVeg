# PMIP3 LGM climate provenance

## Scope and exact inputs

The matched Last Glacial Maximum (LGM) behavioural-verification experiment uses
monthly climate output from the **PMIP3 contribution to CMIP5**, not a climate
dataset produced by the PaleoVeg project.  The inputs are the `lgm` experiment,
`r1i1p1` realisation, and `Amon` frequency for four variables:

- `tas` — near-surface air temperature;
- `tasmin` and `tasmax` — monthly minimum and maximum near-surface air
  temperature; and
- `pr` — precipitation flux.

The exact 24 files, modelling centres, temporal coverage, and SHA-256
digests are recorded in
[`data/pmip3_lgm/source_manifest.tsv`](data/pmip3_lgm/source_manifest.tsv).
They are the six simulations used by Shao et al. (2018): CNRM-CM5,
FGOALS-g2, IPSL-CM5A-LR, MIROC-ESM, MPI-ESM-P, and MRI-CGCM3.  The local
institute archive at `/data/sfb806/pmip3/lgm/` was used as the source copy;
its files identify themselves in their NetCDF global metadata as CMIP5,
experiment `lgm` / "last glacial maximum".

Run the checksum verifier before processing a newly downloaded or independently
preserved copy:

```bash
python training/verify_pmip3_lgm_inputs.py /path/to/atmos/mon
```

The source files are used only for the matched LGM behavioural-verification
experiment.  They are not PaleoVeg training data and are not needed to run the
released modern-climate model.

## Access and redistribution

PMIP3-CMIP5 output is distributed through the Earth System Grid Federation
(ESGF).  The PMIP3 data-access guide links to ESGF nodes and describes account
and download-script access:

- https://wiki.lsce.ipsl.fr/pmip3/doku.php/pmip3%3Adatabase%3Aaccess

The CMIP5 terms of use require acknowledgement of CMIP and the contributing
modelling groups, allow sharing with close collaborators under the terms, and
place additional obligations on wider redistribution.  We consequently do not
redistribute the raw PMIP3 NetCDF files or the first-level remapped climate
fields in this repository or its archive.  Readers should retrieve the exact
files through ESGF, subject to its terms, and confirm them against the supplied
manifest:

- https://cds.climate.copernicus.eu/licences/esgf-cmip5
- https://wcrp-cmip.org/cmip-data-citation-and-licenses/

[`download_pmip3_lgm_data.py`](download_pmip3_lgm_data.py) automates retrieval
of the necessary source segments directly from ESGF, verifies their advertised
SHA-256 digests, and reconstructs the input layout used by the workflow. It
does not redistribute data and is therefore the normal route for reviewers and
readers; a manually supplied copy of the PMIP3 fields is not needed.

## Processing into the experiment forcing

[`prepare_shao_lgm_climate.sh`](prepare_shao_lgm_climate.sh) performs the
following deterministic processing.

1. The ESGF downloader retrieves the official CMIP5 time-series segments and
   consolidates them into one input per model and variable. The preparation
   script then selects exactly one consolidated time series per model and variable using
   the canonical CMIP5 filename pattern and fails on missing or ambiguous
   inputs.
2. It computes each model's monthly climatology with CDO `ymonmean` and
   bilinearly remaps it to the 1-degree grid of the archived Shao comparison
   fields.
3. For precipitation, it converts the CMIP flux from kg m$^{-2}$ s$^{-1}$ to
   monthly water totals (mm) with `mulc,86400` and `muldpm` before averaging.
   `muldpm` uses the CF calendar in each source file, so model-specific month
   lengths are respected.
4. It calculates the arithmetic mean across the six remapped monthly
   climatologies.  BIOCLIM variables are derived only after this ensemble
   average.

This deliberately reproduces the ensemble-mean forcing treatment of Shao et
al. (2018).  It produces a mean-climate diagnostic, not a characterization of
inter-model forcing uncertainty.  The companion member-sensitivity workflow
derives predictors and PaleoVeg results member by member.

The output consists of four derived monthly ensemble climatologies beneath
`training/results/shao_lgm_experiment/climate/`.  These files are intentionally
ignored by Git because their source-data terms must be respected; their
downstream aggregate results and figure inputs can be archived with the paper.

## Required acknowledgement

The manuscript acknowledges the World Climate Research Programme's Working
Group on Coupled Modelling and the six modelling groups that produced the
output.  This follows the CMIP5 acknowledgement requested in the data-access
terms.
