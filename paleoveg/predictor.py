import numpy as np
import pandas as pd
from .model_loader import load_model
import warnings

# Load the model once when the module is imported
_model = load_model()

# Define the required column names
REQUIRED_COLUMNS = [
    "bio1", "bio4", "bio5", "bio6", "bio7", "bio8", "bio9", "bio10",
    "bio11", "bio12", "bio13", "bio14", "bio15", "bio16", "bio17", "bio18", "bio19"
]

# Define class names in the order used by the model
CLASS_NAMES = [
    'Evergreen Needleleaf Forest', 'Evergreen Broadleaf Forest', 
    'Deciduous Needleleaf Forest', 'Deciduous Broadleaf Forest', 
    'Mixed Forest', 'Woodland', 'Wooded Grassland', 'Closed Shrubland', 
    'Open Shrubland', 'Grassland', 'Bare Ground'
]

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

def predict(input_df, dominant="exclude", c3_c4_correction=False):
    """
    Predict vegetation based on bioclimatic features and return probabilities or dominant class.

    Parameters:
        input_df (pd.DataFrame): Bioclimatic variables for prediction.
        dominant (str): One of "exclude", "include", or "only".
            - "exclude": Return probabilities for each class.
            - "include": Include probabilities and a column with the dominant class.
            - "only": Return only the dominant class.
        c3_c4_correction (bool): If True, apply C3/C4 competition correction.

    Returns:
        pd.DataFrame: DataFrame containing probabilities and/or dominant vegetation class.
    """
    # Validate input (assuming validate_input has already been defined)
    validate_input(input_df)

    # Use only the required columns for prediction
    input_df = input_df[REQUIRED_COLUMNS]
    
    # Check for out-of-range values
    validate_ranges(input_df)

    # Predict probabilities
    probabilities = _model.predict_proba(input_df)

    # Create a dataframe for the probabilities
    prob_df = pd.DataFrame(probabilities, columns=CLASS_NAMES, index=input_df.index)

    # Apply C3/C4 competition correction if enabled
    if c3_c4_correction:
        correction_factors = np.array([COMPETITION_FACTORS[class_name] for class_name in CLASS_NAMES])
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
        
        
def predict_map(data, dominant="exclude", c3_c4_correction=False):
    """
    Predict vegetation for a 3D map input (m x n x 17) and return probabilities or dominant types.

    Parameters:
        data (numpy.ndarray): 3D array (m x n x 17) of predictor values.
        dominant (str): One of "exclude" or "only".
            - "exclude": Return probabilities for each class (m x n x 11).
            - "only": Return the dominant type as integers (m x n x 1).
        c3_c4_correction (bool): If True, apply C3/C4 competition correction.

    Returns:
        numpy.ndarray: m x n x 11 (probabilities) or m x n x 1 (dominant type).
    """
    if not isinstance(data, np.ndarray):
        raise ValueError("Input data must be a numpy array.")
    
    if data.ndim != 3 or data.shape[2] != 17:
        raise ValueError("Input data must have shape (m x n x 17).")
        
    validate_map_ranges(data)

    # Reshape the 3D array into a 2D array (flatten grid cells)
    m, n, _ = data.shape
    flat_data = data.reshape(-1, 17)

    # Predict probabilities
    probabilities = _model.predict_proba(flat_data)

    # Apply C3/C4 correction if enabled
    if c3_c4_correction:
        correction_factors = np.array([COMPETITION_FACTORS[class_name] for class_name in CLASS_NAMES])
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

