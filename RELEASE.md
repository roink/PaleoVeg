# Preparing and publishing PaleoVeg 1.0.0

## Source and model

The release uses the all-data classifier at
`training/models/spatial_validation_v1/model.pkl.bz2`, not a development-fit
model. Its SHA-256 is
`080fc26c53133034840e76d38eab2e2ef2444d7352766337d01f5cb60514abd5`.
The package's `paleoveg/model_metadata.json` records its size, classes, predictor
order, and training metadata. Native installations use scikit-learn 1.9.0,
the version used for training. Pickle compatibility across scikit-learn versions
is not guaranteed. Native/browser parity passed for 65 inputs and five CO₂
scenarios using native scikit-learn 1.9.0 and Pyodide scikit-learn 1.8.0. This
is an empirical compatibility check for this classifier, not a general claim
of compatibility between those versions.

Before committing:

```bash
python -m pip install -e '.[reproduction,test,browser-test]' build twine
python scripts/prepare_release.py 1.0.0 --build-browser-wheel
python scripts/prepare_release.py 1.0.0 --check
python scripts/download_release_model.py --source training/models/spatial_validation_v1/model.pkl.bz2
pytest -q
python scripts/verify_browser_parity.py
python -m build
python -m twine check dist/*.whl dist/*.tar.gz
```

Confirm the release date in `CITATION.cff` when publishing. Citations use the version-specific DOI after successful Zenodo deposition.

## Publication artifacts

After committing the source, run:

```bash
python scripts/prepare_publication_assets.py
```

The output directory `dist/release-assets/` contains:

- `model.pkl.bz2`, the classifier downloaded by native and browser applications;
- `paleoveg-v1.0.0-publication.tar.gz`, the committed source, figures, aggregate
  results, model artifacts, and aggregate figure inputs;
- `release-manifest.json`, linking the assets to their exact source commit;
- `SHA256SUMS`, checksums for these files.

The publication bundle excludes the raw AVHRR target, processed training table,
row-level prediction tables containing observed land-cover labels,
and downloaded or remapped PMIP3 climate fields. It includes PaleoVeg's derived
vegetation reconstructions. Input access and restrictions are documented in
`training/AVHRR_PROVENANCE.md` and `training/PMIP3_LGM_PROVENANCE.md`.

## Publication sequence

1. Confirm native/browser compatibility and the Zenodo connection before tagging.
   Push the prepared source commit. This does not publish to PyPI.
2. Create a **draft** GitHub release for `v1.0.0` targeting that commit and attach
   all files from `dist/release-assets/`. Use the 1.0.0 changelog for release notes.
   Keep the draft unpublished while preparing the tag and Python packages.
3. Create and push the annotated `v1.0.0` tag pointing to the same commit.
   A tag push starts the PyPI workflow. It first downloads the draft's model and
   manifest, verifies their checksum and source commit, runs tests, and builds
   the packages. After PyPI publication it attaches distributions to the draft.
   The workflow can also be dispatched for an existing tag.
4. Check the completed draft and publish it in GitHub. This should trigger the
   Zenodo webhook. Verify that Zenodo actually creates the new version record;
   an active webhook alone does not establish successful deposition.
5. Deposit the publication bundle, model, manifest, and checksums in a persistent
   data record and link it to the software DOI. **GitHub release assets are not
   included by Zenodo's automatic GitHub source archiving.**
6. Record the version-specific software and artifact DOIs in the manuscript and
   citation files, then rebuild the manuscript PDF.
7. Deploy the browser application using the Pages workflow after the model asset
   is publicly downloadable. The workflow listens for published releases and
   supports manual dispatch; it no longer deploys unreleased source on main pushes.
   A release published using the GitHub UI emits the event needed for this workflow.

## Verified Zenodo releases

After renewing GitHub authorization and recreating the repository webhook,
Zenodo automatically archived both new release events:

- v0.2.1: https://doi.org/10.5281/zenodo.23743567
- v1.0.0: https://doi.org/10.5281/zenodo.23743715

Both belong to the existing concept DOI, `10.5281/zenodo.15222519`.
The Zenodo records contain tagged source snapshots; GitHub release assets
are not included in those records.

Sources:
- https://help.zenodo.org/docs/github/archive-software/github-upload/
- https://github.com/zenodo/zenodo/issues/1235
- https://scikit-learn.org/stable/model_persistence.html
