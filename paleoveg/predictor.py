import numpy as np
import pandas as pd
from numbers import Real
from .model_loader import load_model
from .input import REQUIRED_COLUMNS, normalize_bioclim_columns
from .co2 import co2_at_time
import warnings

# Define class names in the order used by the model
CLASS_NAMES = [
    'Evergreen Needleleaf Forest', 'Evergreen Broadleaf Forest', 
    'Deciduous Needleleaf Forest', 'Deciduous Broadleaf Forest', 
    'Mixed Forest', 'Woodland', 'Wooded Grassland', 'Closed Shrubland', 
    'Open Shrubland', 'Grassland', 'Bare Ground'
]

# Class codes stored in the released classifier. Their order defines the
# mapping to CLASS_NAMES and is checked before labeling probability columns.
MODEL_CLASS_CODES = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 12]

# Define the C3/C4 competition factors
COMPETITION_FACTORS = {
    'Evergreen Needleleaf Forest': 0.28,
    'Evergreen Broadleaf Forest': 0.73,
    'Deciduous Needleleaf Forest': 0.20,
    'Deciduous Broadleaf Forest': 0.76,
    'Mixed Forest': 1.00,
    'Closed Shrubland': 1.66,
    'Open Shrubland': 1.66,
    'Woodland': 1.62,
    'Wooded Grassland': 1.62,
    'Grassland': 1.69,
    'Bare Ground': 1.15,
}

MODERN_CO2_PPM = 310.0
LEGACY_CORRECTION_CO2_PPM = 185.0


def _resolve_co2_ppm(c3_c4_correction, co2_ppm, age_ka_bp=None):
    """Resolve legacy correction settings to an explicit CO2 concentration."""
    if co2_ppm is not None and age_ka_bp is not None:
        raise ValueError("co2_ppm and age_ka_bp are mutually exclusive.")
    if age_ka_bp is not None and not c3_c4_correction:
        raise ValueError("age_ka_bp can only be provided when c3_c4_correction=True.")
    if co2_ppm is not None and not c3_c4_correction:
        raise ValueError("co2_ppm can only be provided when c3_c4_correction=True.")
    if age_ka_bp is not None:
        return co2_at_time(age_ka_bp)
    if co2_ppm is None:
        return LEGACY_CORRECTION_CO2_PPM if c3_c4_correction else MODERN_CO2_PPM
    if isinstance(co2_ppm, (bool, np.bool_)) or not isinstance(co2_ppm, Real):
        raise ValueError("co2_ppm must be a finite numeric concentration in ppm.")
    resolved = float(co2_ppm)
    if not np.isfinite(resolved):
        raise ValueError("co2_ppm must be a finite numeric concentration in ppm.")
    return resolved


def _competition_factors_for_co2(class_names, c3_c4_correction, co2_ppm, age_ka_bp=None):
    """Return resolved CO2 and class factors for interpolation or extrapolation."""
    resolved = _resolve_co2_ppm(c3_c4_correction, co2_ppm, age_ka_bp)
    if not c3_c4_correction:
        return resolved, np.ones(len(class_names), dtype=float)
    legacy_factors = np.array([COMPETITION_FACTORS[name] for name in class_names], dtype=float)
    scale = (MODERN_CO2_PPM - resolved) / (MODERN_CO2_PPM - LEGACY_CORRECTION_CO2_PPM)
    factors = 1.0 + scale * (legacy_factors - 1.0)
    if np.any(factors <= 0):
        raise ValueError(
            f"co2_ppm={resolved:g} produces a zero or negative C3/C4 competition factor; "
            "choose a concentration closer to the 185–310 ppm calibration interval."
        )
    return resolved, factors

# Min and max values for bioclimatic variables in the training set
BIOCLIM_RANGES = {
    "bio1": (-54.72659, 30.94079),
    "bio4": (0.0, 2361.791),
    "bio5": (-29.69077, 48.16399),
    "bio6": (-72.50053, 25.17328),
    "bio7": (1.0, 72.02339),
    "bio8": (-66.30019, 37.73918),
    "bio9": (-54.83078, 37.51987),
    "bio10": (-37.78683, 38.28006),
    "bio11": (-66.33826, 29.06288),
    "bio12": (0.0, 7953.816),
    "bio13": (0.0, 2561.44),
    "bio14": (0.0, 487.3488),
    "bio15": (0.0, 229.0017),
    "bio16": (0.0, 5597.44),
    "bio17": (0.0, 1526.664),
    "bio18": (0.0, 5190.888),
    "bio19": (0.0, 4756.88),
}

def validate_ranges(input_df):
    """
    Validate that input values are within reasonable ranges.

    Parameters:
        input_df (pd.DataFrame): Input DataFrame.

    Returns:
        None: Issues warnings for out-of-range values.
    """
    for col, (min_val, max_val) in BIOCLIM_RANGES.items():
        if col in input_df.columns:
            out_of_range = (input_df[col] < min_val) | (input_df[col] > max_val)
            if out_of_range.any():
                warnings.warn(f"Column '{col}' contains values outside the range ({min_val}, {max_val}).")

def validate_map_ranges(data):
    """
    Validate that map input values are within reasonable ranges.

    Parameters:
        data (np.ndarray): 3D array (m x n x 17) of predictor values.

    Returns:
        None: Issues warnings for out-of-range values.
    """
    for i, (min_val, max_val) in enumerate(BIOCLIM_RANGES.values()):
        out_of_range = (data[..., i] < min_val) | (data[..., i] > max_val)
        if out_of_range.any():
            warnings.warn(f"Layer {i} contains values outside the range ({min_val}, {max_val}).")


def validate_input(input_df):
    """
    Validate the input DataFrame for prediction.
    Ensures it is a pandas DataFrame and contains the required columns.

    Parameters:
        input_df (pd.DataFrame): Input data for prediction.

    Returns:
        None

    Raises:
        ValueError: If input is not a DataFrame or required columns are missing.
    """
    if not isinstance(input_df, pd.DataFrame):
        raise ValueError("Input must be a pandas DataFrame.")
    
    missing_columns = [col for col in REQUIRED_COLUMNS if col not in input_df.columns]
    if missing_columns:
        raise ValueError(f"Missing required columns: {missing_columns}")

    non_numeric = [
        column for column in REQUIRED_COLUMNS
        if not pd.api.types.is_numeric_dtype(input_df[column])
    ]
    if non_numeric:
        raise ValueError(f"Bioclimatic columns must be numeric: {non_numeric}")

    values = input_df[REQUIRED_COLUMNS].to_numpy(dtype=float)
    if not np.isfinite(values).all():
        raise ValueError("Bioclimatic columns contain missing or non-finite values.")


def _class_names_for_model(model):
    """Resolve probability columns without assuming an unchecked class order."""
    model_classes = list(model.classes_)
    if model_classes == MODEL_CLASS_CODES:
        return CLASS_NAMES
    if len(model_classes) == len(CLASS_NAMES) and set(model_classes) == set(CLASS_NAMES):
        return model_classes
    raise ValueError(
        "The model classes do not match PaleoVeg's expected vegetation classes: "
        f"{model_classes}"
    )

def predict(
    input_df,
    dominant="exclude",
    c3_c4_correction=False,
    model=None,
    normalize_columns=True,
    aliases=None,
    co2_ppm=None,
    age_ka_bp=None,
):
    """
    Predict vegetation based on bioclimatic features and return probabilities or dominant class.

    Parameters:
        input_df (pd.DataFrame): Bioclimatic variables for prediction.
        dominant (str): One of "exclude", "include", or "only".
            - "exclude": Return probabilities for each class.
            - "include": Include probabilities and a column with the dominant class.
            - "only": Return only the dominant class.
        c3_c4_correction (bool): If True, apply C3/C4 competition correction.
        co2_ppm (float, optional): Atmospheric CO2 concentration. Requires
            c3_c4_correction=True; defaults to 185 ppm when correction is enabled.
        age_ka_bp (float, optional): Geological age in thousands of years before
            1950. Mutually exclusive with co2_ppm and resolved from the bundled
            IPCC AR6 CO2 observations.

    Returns:
        pd.DataFrame: DataFrame containing probabilities and/or dominant vegetation class.
    """
    if normalize_columns:
        input_df, _ = normalize_bioclim_columns(input_df, aliases=aliases)

    validate_input(input_df)

    # Use only the required columns for prediction
    input_df = input_df[REQUIRED_COLUMNS]
    
    # Check for out-of-range values
    validate_ranges(input_df)

    # Predict probabilities
    active_model = model if model is not None else load_model()
    probabilities = active_model.predict_proba(input_df)

    # Create a dataframe for the probabilities
    class_names = _class_names_for_model(active_model)
    prob_df = pd.DataFrame(probabilities, columns=class_names, index=input_df.index)

    # Resolve the concentration even when correction is disabled so conflicting
    # arguments fail consistently before results are returned.
    _, correction_factors = _competition_factors_for_co2(
        class_names, c3_c4_correction, co2_ppm, age_ka_bp
    )
    if c3_c4_correction:
        prob_df = prob_df.multiply(correction_factors, axis=1)
        prob_df = prob_df.div(prob_df.sum(axis=1), axis=0)  # Normalize to sum to 1

    if dominant == "exclude":
        return prob_df
    elif dominant == "include":
        # Add a column with the dominant class
        prob_df["Dominant Class"] = prob_df.idxmax(axis=1)
        return prob_df
    elif dominant == "only":
        # Return only the dominant class
        dominant_classes = prob_df.idxmax(axis=1)
        return dominant_classes.to_frame(name="Dominant Class")
    else:
        raise ValueError("Invalid value for 'dominant'. Must be 'exclude', 'include', or 'only'.")
        
        
def predict_map(
    data, dominant="exclude", c3_c4_correction=False, model=None,
    co2_ppm=None, age_ka_bp=None,
):
    """
    Predict vegetation for a 3D map input (m x n x 17) and return probabilities or dominant types.

    Parameters:
        data (numpy.ndarray): 3D array (m x n x 17) of predictor values.
        dominant (str): One of "exclude" or "only".
            - "exclude": Return probabilities for each class (m x n x 11).
            - "only": Return the dominant type as integers (m x n x 1).
        c3_c4_correction (bool): If True, apply C3/C4 competition correction.
        co2_ppm (float, optional): Atmospheric CO2 concentration. Requires
            c3_c4_correction=True; defaults to 185 ppm when correction is enabled.
        age_ka_bp (float, optional): Geological age in thousands of years before
            1950. Mutually exclusive with co2_ppm.

    Returns:
        numpy.ndarray: m x n x 11 (probabilities) or m x n x 1 (dominant type).
    """
    if not isinstance(data, np.ndarray):
        raise ValueError("Input data must be a numpy array.")
    
    if data.ndim != 3 or data.shape[2] != 17:
        raise ValueError("Input data must have shape (m x n x 17).")

    if not np.issubdtype(data.dtype, np.number):
        raise ValueError("Input data must contain numeric values.")
    if not np.isfinite(data).all():
        raise ValueError("Input data contains missing or non-finite values.")
        
    validate_map_ranges(data)

    # Reshape the 3D array into a 2D array (flatten grid cells)
    m, n, _ = data.shape
    flat_data = data.reshape(-1, 17)

    # Predict probabilities
    active_model = model if model is not None else load_model()
    probabilities = active_model.predict_proba(flat_data)
    class_names = _class_names_for_model(active_model)

    _, correction_factors = _competition_factors_for_co2(
        class_names, c3_c4_correction, co2_ppm, age_ka_bp
    )
    if c3_c4_correction:
        probabilities *= correction_factors
        probabilities /= probabilities.sum(axis=1, keepdims=True)  # Normalize to sum to 1

    # Reshape probabilities back to m x n x 11
    probabilities_reshaped = probabilities.reshape(m, n, -1)

    if dominant == "exclude":
        # Return probabilities (m x n x 11)
        return probabilities_reshaped
    elif dominant == "only":
        # Find dominant class (integer indices)
        dominant_classes = probabilities.argmax(axis=1).reshape(m, n, 1)
        return dominant_classes
    else:
        raise ValueError("Invalid value for 'dominant'. Must be 'exclude' or 'only'.")
