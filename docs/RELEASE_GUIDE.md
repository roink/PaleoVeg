# **Release Process for PaleoVeg**

This document outlines the steps to create a new release for the PaleoVeg project. Follow these steps carefully to ensure a smooth release process.

---

## **1. Update Version Number**

1. **Update `setup.py`:**
   - Open `setup.py`.
   - Update the `version` field to the new version (e.g., `0.1.2`):
     ```python
     setup(
         name="PaleoVeg",
         version="0.1.2",  # Update this
         ...
     )
     ```

2. **Update the Download Path in `model_loader.py`:**
   - If the version number is part of the model download URL or path, update it in `model_loader.py`.
   - Example:
     ```python
     def download_model():
         url = "https://github.com/roink/PaleoVeg/releases/download/v0.1.2/model.pkl.bz2"
         ...
     ```

---

## **2. Clean Up the Build Directory**

1. **Remove Old Build Artifacts:**
   - Delete any existing build directories to avoid conflicts:
     ```bash
     rm -rf dist/ build/ *.egg-info
     ```

---

## **3. Commit and Push Changes to GitHub**

1. **Stage Changes:**
   - Add all changes, including the updated `setup.py` and `model_loader.py`:
     ```bash
     git add .
     ```

2. **Commit Changes:**
   - Commit the changes with a descriptive message:
     ```bash
     git commit -m "Update to version 0.1.2"
     ```

3. **Push to GitHub:**
   - Push the changes to the main branch:
     ```bash
     git push origin main
     ```

---

## **4. Tag the New Version**

1. **Create a Tag:**
   - Create a new Git tag for the release version:
     ```bash
     git tag v0.1.2
     ```

2. **Push the Tag:**
   - Push the new tag to GitHub:
     ```bash
     git push origin v0.1.2
     ```

---

## **5. Build the Package**

1. **Build the Distribution Files:**
   - Build the source distribution (`.tar.gz`) and the wheel (`.whl`):
     ```bash
     python3 setup.py sdist bdist_wheel
     ```

2. **Verify the Build:**
   - Ensure the `dist/` directory contains only the new version files:
     ```
     dist/
     ├── PaleoVeg-0.1.2-py3-none-any.whl
     ├── PaleoVeg-0.1.2.tar.gz
     ```

---

## **6. Upload to PyPI**

1. **Upload to PyPI:**
   - Upload the package to PyPI:
     ```bash
     twine upload dist/*
     ```

2. **Verify on PyPI:**
   - Visit your package page on [PyPI](https://pypi.org/) and confirm the new version is available.

---

## **7. Create a GitHub Release**

1. **Go to the Repository’s Releases Page:**
   - Navigate to the **Releases** tab in your GitHub repository.

2. **Create a New Release:**
   - Click **Draft a New Release**.
   - Select the new tag (`v0.1.2`) from the dropdown menu.
   - Add a title (e.g., `PaleoVeg v0.1.2`) and a description summarizing the changes in this release.

3. **Attach the Model File:**
   - Drag and drop the updated model file (e.g., `model.pkl.bz2`) as an asset for the release.

4. **Publish the Release:**
   - Click **Publish Release** to make the release public.

---

## **8. Final Verification**

1. **Verify GitHub Release:**
   - Ensure the new release is visible and includes the correct tag, description, and model file.

2. **Verify PyPI Package:**
   - Confirm the new version is available and correctly described on PyPI.

3. **Test Installation:**
   - Install the package from PyPI in a fresh environment:
     ```bash
     pip install PaleoVeg==0.1.2
     ```

---

## **Checklist**

- [ ] Updated `setup.py` with the new version.
- [ ] Updated paths in `model_loader.py` (if necessary).
- [ ] Cleaned up the `dist/` and `build/` directories.
- [ ] Committed and pushed changes to GitHub.
- [ ] Tagged the new version and pushed the tag.
- [ ] Built the package (`.tar.gz` and `.whl`).
- [ ] Uploaded to PyPI.
- [ ] Created a GitHub release and attached the model file.
- [ ] Verified everything on GitHub and PyPI.

