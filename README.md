[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.15222519.svg)](https://doi.org/10.5281/zenodo.15222519)
[![GitHub Org](https://img.shields.io/badge/GitHub-HESCOR-blue?logo=github&logoColor=white)](https://github.com/HESCOR)

---

# **PaleoVeg**

PaleoVeg is a Python package for predicting vegetation types based on bioclimatic variables. It is designed for paleovegetation reconstruction, allowing users to model vegetation based on past climate data or other environmental predictors.

## **Citation and reuse**

If you use PaleoVeg in research, please cite:

> Schlüter, P. (2025). *PaleoVeg* (v0.1.2) [Software]. Zenodo. https://doi.org/10.5281/zenodo.15222520

Machine-readable citation metadata is provided in [`CITATION.cff`](CITATION.cff).
PaleoVeg can be reused under the terms of the [MIT License](LICENSE).

---

## **Features**
- Predict vegetation types for single or multiple locations using bioclimatic variables.
- Apply a CO₂ concentration-dependent C3/C4 competition correction.
- Run CSV/TSV predictions locally in a browser through the static GitHub Pages app.
- Flexible output options:
  - Probabilities for each vegetation type.
  - Dominant vegetation type.
- Supports input as:
  - Pandas DataFrames for tabular data.
  - Numpy arrays for map-like (grid-based) data.

---

## **Predicted Vegetation/Biome Types**

PaleoVeg predicts the following vegetation/biome types:

1. Evergreen Needleleaf Forest
2. Evergreen Broadleaf Forest
3. Deciduous Needleleaf Forest
4. Deciduous Broadleaf Forest
5. Mixed Forest
6. Woodland
7. Wooded Grassland
8. Closed Shrubland
9. Open Shrubland
10. Grassland
11. Bare Ground

---

## **Installation**

1. Clone the repository:
   ```bash
   git clone https://github.com/roink/PaleoVeg.git
   cd PaleoVeg
   ```

2. Install the package:
   ```bash
   pip install .
   ```

## **Browser application**

[Open the PaleoVeg web application](https://roink.github.io/PaleoVeg/)

The web application lets researchers run PaleoVeg without installing Python.
Climate data are processed locally in the browser and are not uploaded to a
server.

It accepts CSV, TSV, and NetCDF data containing either PaleoVeg BIOCLIM
variables or 12-month temperature and precipitation normals. Variable matches,
climate units, and the choice between supplied and derived BIOCLIM variables
are shown for review before a prediction runs.

For spatial NetCDF data, the app provides a map preview and can export NetCDF,
CSV, NumPy, PNG, and reproducibility metadata. It supports dominant vegetation,
class probabilities, and C3/C4 correction using a chosen CO₂ concentration or
a geological-age lookup.

---

## **Usage**

### **1. Import the Package**
```python
from paleoveg import predict, predict_map
```

### **2. Predict Using Tabular Data**

#### **Input Data**
Provide a Pandas DataFrame with the following required columns:
```plaintext
bio1, bio4, bio5, bio6, bio7, bio8, bio9, bio10, bio11, bio12, bio13, bio14, bio15, bio16, bio17, bio18, bio19
```

#### **Example**
```python
import pandas as pd
from paleoveg import predict

# Example input DataFrame
data = {
    "bio1": [10.2, 12.5],
    "bio4": [15.6, 14.1],
    "bio5": [20.1, 18.4],
    "bio6": [5.3, 7.2],
    "bio7": [14.8, 16.5],
    "bio8": [12.4, 11.8],
    "bio9": [9.7, 8.9],
    "bio10": [8.5, 9.2],
    "bio11": [7.9, 6.5],
    "bio12": [300.5, 310.2],
    "bio13": [100.2, 102.4],
    "bio14": [150.4, 148.3],
    "bio15": [180.6, 175.9],
    "bio16": [170.3, 165.2],
    "bio17": [160.9, 155.8],
    "bio18": [140.7, 145.4],
    "bio19": [130.8, 128.7],
}

df = pd.DataFrame(data)

# Predict probabilities
probabilities = predict(df, dominant="exclude", c3_c4_correction=False)

# Predict dominant vegetation type
dominant_class = predict(df, dominant="only", c3_c4_correction=True)

# Specify another atmospheric CO2 concentration in ppm
result = predict(
    df,
    dominant="include",
    c3_c4_correction=True,
    co2_ppm=220,
)

# Derive CO2 from geological age in ka BP (before 1950)
result_at_20ka = predict(
    df,
    dominant="include",
    c3_c4_correction=True,
    age_ka_bp=20,
)
```

---

### **3. Predict Using Map-Like Data**

#### **Input Data**
Provide a Numpy array with shape `(m, n, 17)` where:
- `m` and `n` represent the grid dimensions.
- `17` represents the bioclimatic variables in the required order.

#### **Example**
```python
import numpy as np
from paleoveg import predict_map

# Example 3D data: m = 5, n = 5, 17 predictors
m, n = 5, 5
data = np.random.rand(m, n, 17)

# Predict probabilities (m x n x 11)
probabilities_map = predict_map(data, dominant="exclude", c3_c4_correction=False)

# Predict dominant type (m x n x 1)
dominant_map = predict_map(data, dominant="only", c3_c4_correction=True)
```

---

## **Functions**

### **1. `predict(input_df, dominant="exclude", c3_c4_correction=False, ..., co2_ppm=None, age_ka_bp=None)`**
Predict vegetation types for tabular data.

#### **Parameters**:
- `input_df` (pd.DataFrame): Input DataFrame with 17 bioclimatic variables.
- `dominant` (str): Specifies the output format.
  - `"exclude"`: Returns probabilities for each vegetation type.
  - `"include"`: Returns probabilities and the dominant type.
  - `"only"`: Returns only the dominant type.
- `c3_c4_correction` (bool): If `True`, applies the C3/C4 competition correction. Omitting `co2_ppm` preserves the legacy 185 ppm result. If `False`, predictions are uncorrected and represent the 310 ppm baseline.
- `co2_ppm` (float, optional): Atmospheric CO₂ concentration used for the correction. It may only be supplied when `c3_c4_correction=True`.
- `age_ka_bp` (float, optional): Geological age in thousands of years before 1950. PaleoVeg linearly interpolates atmospheric CO₂ from the bundled IPCC AR6 observations. It is mutually exclusive with `co2_ppm` and requires `c3_c4_correction=True`.

#### **Returns**:
- Pandas DataFrame: Probabilities and/or dominant type based on `dominant`.

---

### **2. `predict_map(data, dominant="exclude", c3_c4_correction=False, model=None, co2_ppm=None, age_ka_bp=None)`**
Predict vegetation types for 3D map-like data.

#### **Parameters**:
- `data` (np.ndarray): Input Numpy array with shape `(m, n, 17)`.
- `dominant` (str): Specifies the output format.
  - `"exclude"`: Returns probabilities `(m x n x 11)`.
  - `"only"`: Returns the dominant type `(m x n x 1)`.
- `c3_c4_correction` (bool): If `True`, applies the C3/C4 competition correction, defaulting to the legacy 185 ppm result.
- `co2_ppm` (float, optional): Atmospheric CO₂ concentration. Requires `c3_c4_correction=True`.
- `age_ka_bp` (float, optional): Geological age in ka BP relative to 1950. Mutually exclusive with `co2_ppm`.

#### **Returns**:
- Numpy array: Probabilities or dominant type based on `dominant`.

---

## **C3/C4 Competition Factors**
The factors below are the published correction at 185 ppm. At the uncorrected modern baseline of 310 ppm every factor is 1. For another concentration `c`, PaleoVeg calculates each class factor as:

```text
factor(c) = 1 + ((310 - c) / (310 - 185)) × (factor(185) - 1)
```

Values between 185 and 310 ppm are interpolated and values outside that interval are linearly extrapolated. PaleoVeg rejects concentrations that would make any class factor zero or negative. Corrected probabilities are renormalized to sum to one.

### CO₂ lookup by geological age

```python
from paleoveg import co2_at_time

co2_ppm = co2_at_time(20)  # approximately 194.04 ppm
```

The bundled lookup preserves all 1,894 irregular CO₂ observations from the
IPCC AR6 Figure 2.4a dataset. Source ages in kyr before 2000 are converted to
ka BP by subtracting 0.05. Duplicate ages are averaged only when constructing
the interpolation knots. PaleoVeg does not extrapolate beyond the dataset's
−0.069 to 805.669 ka BP range.

Data source: Ahn, J. (2023), *Chapter 2 of the Working Group I Contribution to
the IPCC Sixth Assessment Report – data for Figure 2.4 (v20221219)*, NERC EDS
Centre for Environmental Data Analysis,
[doi:10.5285/60eeb3cce51a457cb5ee1c577a0c8674](https://doi.org/10.5285/60eeb3cce51a457cb5ee1c577a0c8674),
licensed under CC BY 4.0. See `paleoveg/data/co2/README.md` for transformation
and attribution details.

| Vegetation Type                | Competition Factor |
|--------------------------------|--------------------|
| Evergreen Needleleaf Forest    | 0.28              |
| Evergreen Broadleaf Forest     | 0.73              |
| Deciduous Needleleaf Forest    | 0.20              |
| Deciduous Broadleaf Forest     | 0.76              |
| Mixed Forest                   | 1.00              |
| Closed Shrubland               | 1.66              |
| Open Shrubland                 | 1.66              |
| Woodland                       | 1.62              |
| Wooded Grassland               | 1.62              |
| Grassland                      | 1.69              |
| Bare Ground                    | 1.15              |

---

## **License**
This project is licensed under the MIT License.

---

## **Contributing**
Contributions are welcome! Please submit a pull request or open an issue if you have suggestions or find bugs.

---
