# Raw data

The workflow expects the following unmodified source files:

```text
training/data/raw/
├── avhrr/
│   └── AVHRR_8km_LANDCOVER_1981_1994.GLOBAL.tif
└── worldclim/
    ├── wc2.1_5m_bio_1.tif
    ├── wc2.1_5m_bio_4.tif
    └── ... wc2.1_5m_bio_19.tif
```

BIO2 and BIO3 are not predictors and are not required. Raw files are ignored
by Git pending a documented redistribution/licensing decision. Record source
URLs, versions, licences, file sizes, and SHA-256 hashes in the paper archive.
The identification, surviving-file metadata, references, download status, and
redistribution caveat for the vegetation raster are documented in
[`training/AVHRR_PROVENANCE.md`](../../AVHRR_PROVENANCE.md).
