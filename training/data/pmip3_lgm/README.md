# PMIP3 LGM climate inputs

No PMIP3/CMIP5 NetCDF data are distributed with PaleoVeg.  The matched Last
Glacial Maximum (LGM) behavioural-verification experiment uses 24 monthly
source fields: `tas`, `tasmin`, `tasmax`, and `pr` from the `lgm`, `r1i1p1`
realisation of six PMIP3 models.  Their exact identities and SHA-256 digests
are in [`source_manifest.tsv`](source_manifest.tsv); full provenance,
processing, access, and redistribution information is in
[`../../PMIP3_LGM_PROVENANCE.md`](../../PMIP3_LGM_PROVENANCE.md).

Download the exact fields from the Earth System Grid Federation (ESGF), subject
to the CMIP5 terms of use. The automated downloader retrieves the official
CMIP5 segments, verifies their ESGF checksums, and reconstructs the input
layout required by the preparation workflow:

```bash
python training/download_pmip3_lgm_data.py
```

It writes to `esgf_download/` by default. This directory is ignored by Git.
Use a larger scratch or data volume with `--destination /path/to/pmip3_lgm`.
`--dry-run` performs the ESGF discovery step without downloading. The output
contains the following layout:

```text
/path/to/pmip3_lgm/atmos/mon/
  tas/ tasmin/ tasmax/ pr/
```

Then create the common-grid ensemble climate used by the paper with:

```bash
bash training/prepare_shao_lgm_climate.sh /path/to/pmip3_lgm/atmos/mon
```

The downloader does not redistribute data: it retrieves the original model
output directly from ESGF. The original institute files were consolidated with
CDO and therefore have different file hashes from their reconstructed ESGF
equivalents; the downloader records both the official segment hashes and the
new consolidated-file hashes in `esgf_download_manifest.json`.
