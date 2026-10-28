# Shao et al. (2018) LGM comparison fields

This directory holds two published 1° Last Glacial Maximum vegetation
reconstructions from Shao et al. (2018): one without and one with the authors'
CO₂ correction. They are **comparison outputs only**. PaleoVeg does not use
them as training data, predictors, or inference inputs.

They are available under CC BY 4.0 from the versioned Mendeley Data record:

- Shao, Y., Anhäuser, A., Ludwig, P., Schlüter, P., and Williams, E. (2018):
  *Vegetation Cover for Last Glacial Maximum*, version 1, Mendeley Data,
  https://doi.org/10.17632/cr269zdybh.1.

Download the exact two files used by the matched-LGM experiment and verify
their SHA-256 digests with:

```bash
bash training/download_shao_lgm_data.sh
```

The downloader refuses to overwrite existing files. If a manual download is
used instead, the expected hashes are:

| File | SHA-256 |
|---|---|
| `PMIP_1deg_no_co2_correction.nc` | `6df21bb3b2493304d99fed60b5e7e72998d24122f7f89d0eb53332dbc280a69c` |
| `PMIP_1deg_co2_correction.nc` | `489db357497dea9208da96d4d09bf9b08827c2ef055fe5cf2e2c493d7cd75c7f` |
