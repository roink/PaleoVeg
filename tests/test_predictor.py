import numpy as np
import pandas as pd
import pytest
from paleoveg import predict, predict_map

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


# Mock input data for tabular predictions
@pytest.fixture
def tabular_data():
    data = {
        "bio1": [-10.0, 15.0],  # Within range (-54.72659, 30.94079)
        "bio4": [1000.0, 500.0],  # Within range (0.0, 2361.791)
        "bio5": [20.0, 30.0],  # Within range (-29.69077, 48.16399)
        "bio6": [-20.0, 5.0],  # Within range (-72.50053, 25.17328)
        "bio7": [10.0, 50.0],  # Within range (1.0, 72.02339)
        "bio8": [-30.0, 20.0],  # Within range (-66.30019, 37.73918)
        "bio9": [-40.0, 10.0],  # Within range (-54.83078, 37.51987)
        "bio10": [-20.0, 10.0],  # Within range (-37.78683, 38.28006)
        "bio11": [-30.0, 15.0],  # Within range (-66.33826, 29.06288)
        "bio12": [300.0, 700.0],  # Within range (0.0, 7953.816)
        "bio13": [100.0, 200.0],  # Within range (0.0, 2561.44)
        "bio14": [50.0, 100.0],  # Within range (0.0, 487.3488)
        "bio15": [10.0, 50.0],  # Within range (0.0, 229.0017)
        "bio16": [300.0, 500.0],  # Within range (0.0, 5597.44)
        "bio17": [100.0, 200.0],  # Within range (0.0, 1526.664)
        "bio18": [200.0, 400.0],  # Within range (0.0, 5190.888)
        "bio19": [100.0, 300.0],  # Within range (0.0, 4756.88)
    }
    return pd.DataFrame(data)

# Mock input data for map-like predictions
@pytest.fixture
def map_data():
    m, n = 5, 5
    data = np.random.uniform(
        low=[BIOCLIM_RANGES[var][0] for var in BIOCLIM_RANGES.keys()],
        high=[BIOCLIM_RANGES[var][1] for var in BIOCLIM_RANGES.keys()],
        size=(m, n, 17)
    )
    return data

def test_predict_probabilities(tabular_data):
    # Test predict function with probabilities output
    result = predict(tabular_data, dominant="exclude", c3_c4_correction=False)
    assert isinstance(result, pd.DataFrame)
    assert result.shape == (2, 11)  # 2 rows, 11 vegetation types
    assert np.isclose(result.sum(axis=1).values, 1).all()  # Probabilities sum to 1

def test_predict_dominant_only(tabular_data):
    # Test predict function with dominant output
    result = predict(tabular_data, dominant="only", c3_c4_correction=False)
    assert isinstance(result, pd.DataFrame)
    assert result.shape == (2, 1)  # 2 rows, 1 dominant type
    assert result.iloc[:, 0].isin([
        'Evergreen Needleleaf Forest', 'Evergreen Broadleaf Forest',
        'Deciduous Needleleaf Forest', 'Deciduous Broadleaf Forest',
        'Mixed Forest', 'Woodland', 'Wooded Grassland',
        'Closed Shrubland', 'Open Shrubland', 'Grassland', 'Bare Ground'
    ]).all()

def test_predict_map_probabilities(map_data):
    # Test predict_map function with probabilities output
    result = predict_map(map_data, dominant="exclude", c3_c4_correction=False)
    assert isinstance(result, np.ndarray)
    assert result.shape == (5, 5, 11)  # m x n x 11
    assert np.isclose(result.sum(axis=2), 1).all()  # Probabilities sum to 1 for each grid cell

def test_predict_map_dominant_only(map_data):
    # Test predict_map function with dominant output
    result = predict_map(map_data, dominant="only", c3_c4_correction=False)
    assert isinstance(result, np.ndarray)
    assert result.shape == (5, 5, 1)  # m x n x 1
    assert np.issubdtype(result.dtype, np.integer)

def test_c3_c4_correction(tabular_data):
    # Test C3/C4 correction
    result_no_correction = predict(tabular_data, dominant="exclude", c3_c4_correction=False)
    result_with_correction = predict(tabular_data, dominant="exclude", c3_c4_correction=True)
    assert not result_no_correction.equals(result_with_correction)  # Results should differ
    assert np.isclose(result_with_correction.sum(axis=1).values, 1).all()  # Probabilities still sum to 1
    
def test_predict_out_of_range(tabular_data):
    tabular_data["bio1"][0] = -100.0  # Out-of-range value
    with pytest.warns(UserWarning, match="Column 'bio1' contains values outside the range"):
        predict(tabular_data)

def test_predict_map_out_of_range(map_data):
    map_data[0, 0, 0] = -100.0  # Out-of-range value for bio1
    with pytest.warns(UserWarning, match="Layer 0 contains values outside the range"):
        predict_map(map_data)

