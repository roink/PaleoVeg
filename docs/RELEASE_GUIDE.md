# Release process for PaleoVeg

## Automated package release

Push a version tag such as `v0.2.0` after the release commit is on `main`.
The `Publish Python package` workflow verifies that the tag matches the version
in `setup.py`, runs the tests, builds and validates the distributions, publishes
them to PyPI, and creates a GitHub Release containing the wheel and source
distribution.

The workflow uses PyPI Trusted Publishing and therefore needs no PyPI token in
GitHub. Before the first release, configure a trusted publisher for the
`roink/PaleoVeg` repository in the PyPI project settings, with workflow filename
`.github/workflows/publish-pypi.yml` and environment name `pypi`.

The classifier is versioned separately from the Python package. When the model
has not changed, as for the planned CO₂ and geological-age features, do not
upload a new `model.pkl.bz2` asset: the existing `v0.1.2` model artifact remains
the model used by the package and web application.

## Release checklist

1. Update the package version in `setup.py` and any release notes or citation
   information that need a new version.
2. Commit the release changes to `main` and wait for the normal checks to pass.
3. Create and push the matching tag:

   ```bash
   git tag v0.2.0
   git push origin v0.2.0
   ```

4. Monitor the `Publish Python package` workflow. It publishes the package and
   creates the GitHub Release automatically.
5. Confirm the new version on [PyPI](https://pypi.org/project/PaleoVeg/) and
   install it in a clean environment:

   ```bash
   pip install PaleoVeg==0.2.0
   ```

## When the classifier changes

Create a separate model release only when the trained classifier changes. Upload
the new `model.pkl.bz2`, record its checksum, and update the model version, URL,
and checksum in `paleoveg/model_loader.py` and the browser workflows. A package
release that only changes code, such as the CO₂ correction interface, continues
to use the existing model artifact.
