# Provenance of the PaleoVeg vegetation target

## Identification

The vegetation target used by PaleoVeg is an institute-held copy of the
**University of Maryland (UMD) 8 km Global Land Cover Classification,
version 1.0**. It is the original published data product in GeoTIFF form, not
an independently reconstructed or reclassified land-cover layer. The local
GLCF product archive retains the raster together with its product metadata and
the supplier's `NOTE` on the 1 km/8 km legend discrepancy. The copy used for
PaleoVeg is byte-identical to that archived product file (SHA-256
`3574f9b960e428a7fe2fd228c736e1d8b900c9ce21cc39ce41eb3b8c9b517ad1`).

The historical public GLCF download service is no longer available, but this
does not create uncertainty about the identity of the data used here: the
institute archive preserves the published 8 km product and its accompanying
documentation. The unavailable public endpoint affects present-day access,
not the provenance of the PaleoVeg target.

The UMD product was produced by R. S. DeFries, M. Hansen, J. R. G. Townshend,
and R. Sohlberg and released through the former University of Maryland Global
Land Cover Facility (GLCF). DeFries et al. (1998) describe the classification
method. NASA/NOAA Pathfinder AVHRR Land (PAL) observations from 1981–1994 were
used to develop and test temporal metrics; the released 8 km classification
was produced by applying selected annual metrics to 1984 PAL observations with
a decision-tree classifier trained from interpreted Landsat scenes. James and
Kalluri (1994) provide the peer-reviewed description of the underlying PAL
dataset.

This is more precise than describing the target only as “AVHRR data”. AVHRR is
the sensor and PAL is the underlying satellite record; the categorical target
is the derived UMD land-cover classification.

## Preserved product file and documentation

The institute-held file has the following properties:

| Property | Value |
|---|---|
| Filename | `AVHRR_8km_LANDCOVER_1981_1994.GLOBAL.tif` |
| Size | 20,268,366 bytes |
| SHA-256 | `3574f9b960e428a7fe2fd228c736e1d8b900c9ce21cc39ce41eb3b8c9b517ad1` |
| Raster dimensions | 4500 columns × 2250 rows |
| Grid | global longitude–latitude, 0.08° pixels |
| Extent | −180° to 180°, −90° to 90° |
| CRS | WGS 84 / EPSG:4326 |
| Storage | single-band signed 16-bit GeoTIFF |
| Values present | integer codes 0–14 |
| Embedded provenance metadata | none beyond basic GeoTIFF spatial tags |

The retained codes 1–12 exactly reproduce the 8 km UMD/Shao class sequence:
evergreen needleleaf forest, evergreen broadleaf forest, deciduous needleleaf
forest, deciduous broadleaf forest, mixed forest, woodland, wooded grassland,
closed shrubland, open shrubland, grassland, cropland, and bare ground.
PaleoVeg excludes water (0), cropland (11), and the additional file codes 13
and 14, and trains on codes 1–10 and 12.

The accompanying GLCF `NOTE` resolves the two additional codes for the 8 km
product. It states that code 13 is permanent snow and ice (rather than the
generic urban-and-built label in the shared legend) and that code 14 should not
occur but is an erroneous value over bare-ground/water areas. It recommends
recoding code 14 to bare ground over Greenland, Antarctica, and similar icy
areas, and to water where it occurs along ocean image borders. PaleoVeg instead
excludes both codes, so this documented anomaly does not enter model fitting.

The GeoTIFF representation is the institute's preserved distribution of the
published UMD product. It is therefore identified directly by its accompanying
GLCF metadata and note, rather than inferred from raster properties alone. The
exact input file and its checksum should be archived with the paper if the
product licence permits redistribution.

## Verification of independently obtained copies

Until explicit redistribution permission is available, PaleoVeg does not
include the UMD raster or a coordinate-preserving derivative of it. Anyone who
independently obtains a candidate copy can verify whether it is the exact
PaleoVeg 1.0 training target without sharing it:

```bash
python training/verify_avhrr_target.py /path/to/umd_8km_landcover.tif
```

The command calculates the file's SHA-256 digest and exits successfully only
when it matches the preserved input described above.

## Publications and archived descriptions

- DeFries, R. S., Hansen, M., Townshend, J. R. G., and Sohlberg, R. (1998),
  “Global land cover classifications at 8 km spatial resolution: the use of
  training data derived from Landsat imagery in decision tree classifiers”,
  *International Journal of Remote Sensing*, 19, 3141–3168,
  <https://doi.org/10.1080/014311698214235>.
- James, M. E. and Kalluri, S. N. V. (1994), “The Pathfinder AVHRR land
  data set: an improved coarse resolution data set for terrestrial
  monitoring”, *International Journal of Remote Sensing*, 15, 3347–3363,
  <https://doi.org/10.1080/01431169408954335>.
- Hansen, M. C., DeFries, R. S., Townshend, J. R. G., and Sohlberg, R. (2000),
  “Global land cover classification at 1 km spatial resolution using a
  classification tree approach”, *International Journal of Remote Sensing*,
  21, 1331–1364, <https://doi.org/10.1080/014311600210209>. This describes the
  separate 1 km product, not the PaleoVeg target.
- Hansen, M., DeFries, R., Townshend, J. R. G., and Sohlberg, R. (1998), *UMD
  Global Land Cover Classification, 8 Kilometer, version 1.0*, Department of
  Geography, University of Maryland, product coverage 1981–1994. An archived
  copy of the former GLCF product page is available at
  <https://data.mint.isi.edu/files/raw-data/land-use/USGS_LCI/GLCF%3A%20AVHRR%20Global%20Land%20Cover%20Classification.pdf>.
- The NASA ORNL DAAC documentation for an Amazonian subset independently
  describes the parent global 8 km product and its processing:
  <https://daac.ornl.gov/LBA/guides/lba_glcf8km.html>. The DOI
  <https://doi.org/10.3334/ORNLDAAC/680> resolves to that **regional subset**,
  not to the complete global raster.

Shao et al. (2018) cite Tucker et al. (2005) for the AVHRR source. Tucker et
al. describe the extended AVHRR NDVI record, whereas DeFries et al. (1998) and
the UMD product record are the direct sources for the categorical 8 km
land-cover target.

## IRI Data Library record

The authenticated IRI Data Library endpoint
<https://iridl.ldeo.columbia.edu/SOURCES/.UMD/.GLCF/.GLCDS/.lc/> was checked
in August 2026. Despite the collection-level citation mentioning the 1 degree,
8 km, and 1 km classifications, the variable currently served at that endpoint
is explicitly the **1 km** GLCDS land-cover product. Its grid contains 43,200
longitude by 21,600 latitude cells at 0.008333334 degrees, and its legend
contains codes 0--13, with code 13 labelled urban and built-up. It is therefore
not a download source for the 8 km PaleoVeg target.

This comparison cautions against transferring the IRI endpoint's code-13
meaning to the 8 km PaleoVeg target. The retained GLCF `NOTE` is the governing
documentation for the institute-held 8 km product: code 13 denotes permanent
snow and ice, and code 14 is a documented erroneous bare-ground/water value.

## Present download status and rights

The original GLCF website and FTP service are no longer operational. The IRI
Data Library endpoint serves only the 1 km classification, and the NASA ORNL
DAAC record provides only a regional subset of the 8 km classification. No
open, authoritative current download of the complete 8 km global product was
located in August 2026. The complete published product used by PaleoVeg is,
however, preserved in the institute archive described above.

The archived GLCF product page states that use is free with acknowledgement
and that the University of Maryland retains copyright. Before depositing the
GeoTIFF with a paper archive, confirm that this archived statement is
sufficient for redistribution. If not, archive its checksum, complete
metadata, preprocessing code, and acquisition history, and provide the exact
raster as a confidential, reviewer-only asset at manuscript submission.
