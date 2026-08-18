import numpy as np
import pandas as pd
import pytest
from paleoveg import co2_at_time, predict, predict_map
from paleoveg.predictor import COMPETITION_FACTORS, CLASS_NAMES


class FakeModel:
    classes_ = np.array([1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 12])

    def predict_proba(self, values):
        values = np.asarray(values)
        base = np.arange(1, 12, dtype=float)
        probabilities = np.tile(base, (len(values), 1))
        return probabilities / probabilities.sum(axis=1, keepdims=True)


@pytest.fixture
def model():
    return FakeModel()

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

def test_predict_probabilities(tabular_data, model):
    # Test predict function with probabilities output
    result = predict(tabular_data, dominant="exclude", c3_c4_correction=False, model=model)
    assert isinstance(result, pd.DataFrame)
    assert result.shape == (2, 11)  # 2 rows, 11 vegetation types
    assert np.isclose(result.sum(axis=1).values, 1).all()  # Probabilities sum to 1

def test_predict_dominant_only(tabular_data, model):
    # Test predict function with dominant output
    result = predict(tabular_data, dominant="only", c3_c4_correction=False, model=model)
    assert isinstance(result, pd.DataFrame)
    assert result.shape == (2, 1)  # 2 rows, 1 dominant type
    assert result.iloc[:, 0].isin([
        'Evergreen Needleleaf Forest', 'Evergreen Broadleaf Forest',
        'Deciduous Needleleaf Forest', 'Deciduous Broadleaf Forest',
        'Mixed Forest', 'Woodland', 'Wooded Grassland',
        'Closed Shrubland', 'Open Shrubland', 'Grassland', 'Bare Ground'
    ]).all()

def test_predict_map_probabilities(map_data, model):
    # Test predict_map function with probabilities output
    result = predict_map(map_data, dominant="exclude", c3_c4_correction=False, model=model)
    assert isinstance(result, np.ndarray)
    assert result.shape == (5, 5, 11)  # m x n x 11
    assert np.isclose(result.sum(axis=2), 1).all()  # Probabilities sum to 1 for each grid cell

def test_predict_map_dominant_only(map_data, model):
    # Test predict_map function with dominant output
    result = predict_map(map_data, dominant="only", c3_c4_correction=False, model=model)
    assert isinstance(result, np.ndarray)
    assert result.shape == (5, 5, 1)  # m x n x 1
    assert np.issubdtype(result.dtype, np.integer)

def test_c3_c4_correction(tabular_data, model):
    # Test C3/C4 correction
    result_no_correction = predict(tabular_data, dominant="exclude", c3_c4_correction=False, model=model)
    result_with_correction = predict(tabular_data, dominant="exclude", c3_c4_correction=True, model=model)
    assert not result_no_correction.equals(result_with_correction)  # Results should differ
    assert np.isclose(result_with_correction.sum(axis=1).values, 1).all()  # Probabilities still sum to 1


def test_legacy_correction_equals_explicit_185_ppm(tabular_data, model):
    legacy = predict(tabular_data, c3_c4_correction=True, model=model)
    explicit = predict(tabular_data, c3_c4_correction=True, co2_ppm=185, model=model)
    pd.testing.assert_frame_equal(legacy, explicit)


def test_explicit_310_ppm_equals_uncorrected_result(tabular_data, model):
    uncorrected = predict(tabular_data, c3_c4_correction=False, model=model)
    modern = predict(tabular_data, c3_c4_correction=True, co2_ppm=310, model=model)
    pd.testing.assert_frame_equal(uncorrected, modern)


def test_interpolates_competition_factors(tabular_data, model):
    result = predict(tabular_data, c3_c4_correction=True, co2_ppm=247.5, model=model)
    base = np.arange(1, 12, dtype=float)
    base /= base.sum()
    factors = np.array([(1 + COMPETITION_FACTORS[name]) / 2 for name in CLASS_NAMES])
    expected = base * factors
    expected /= expected.sum()
    np.testing.assert_allclose(result.iloc[0].to_numpy(), expected)


@pytest.mark.parametrize("co2_ppm", [100, 600])
def test_rejects_extrapolation_with_nonpositive_factors(tabular_data, model, co2_ppm):
    with pytest.raises(ValueError, match="zero or negative"):
        predict(tabular_data, c3_c4_correction=True, co2_ppm=co2_ppm, model=model)


@pytest.mark.parametrize("co2_ppm", [np.nan, np.inf, "185", True])
def test_rejects_invalid_co2_concentrations(tabular_data, model, co2_ppm):
    with pytest.raises(ValueError, match="finite numeric"):
        predict(tabular_data, c3_c4_correction=True, co2_ppm=co2_ppm, model=model)


def test_rejects_co2_concentration_when_correction_is_disabled(tabular_data, model):
    with pytest.raises(ValueError, match="only be provided"):
        predict(tabular_data, c3_c4_correction=False, co2_ppm=310, model=model)


def test_map_correction_supports_explicit_co2(map_data, model):
    legacy = predict_map(map_data, c3_c4_correction=True, model=model)
    explicit = predict_map(map_data, c3_c4_correction=True, co2_ppm=185, model=model)
    np.testing.assert_allclose(legacy, explicit)


def test_age_lookup_equals_explicit_co2(tabular_data, model):
    by_age = predict(tabular_data, c3_c4_correction=True, age_ka_bp=20, model=model)
    by_ppm = predict(
        tabular_data,
        c3_c4_correction=True,
        co2_ppm=co2_at_time(20),
        model=model,
    )
    pd.testing.assert_frame_equal(by_age, by_ppm)


def test_map_age_lookup_equals_explicit_co2(map_data, model):
    by_age = predict_map(map_data, c3_c4_correction=True, age_ka_bp=20, model=model)
    by_ppm = predict_map(
        map_data,
        c3_c4_correction=True,
        co2_ppm=co2_at_time(20),
        model=model,
    )
    np.testing.assert_allclose(by_age, by_ppm)


def test_rejects_age_and_manual_co2_together(tabular_data, model):
    with pytest.raises(ValueError, match="mutually exclusive"):
        predict(
            tabular_data,
            c3_c4_correction=True,
            co2_ppm=200,
            age_ka_bp=20,
            model=model,
        )


def test_rejects_age_when_correction_is_disabled(tabular_data, model):
    with pytest.raises(ValueError, match="only be provided"):
        predict(tabular_data, c3_c4_correction=False, age_ka_bp=20, model=model)
    
def test_predict_out_of_range(tabular_data, model):
    tabular_data.loc[0, "bio1"] = -100.0  # Out-of-range value for bio1
    with pytest.warns(UserWarning, match="Column 'bio1' contains values outside the range"):
        predict(tabular_data, model=model)

def test_predict_map_out_of_range(map_data, model):
    map_data[0, 0, 0] = -100.0  # Out-of-range value for bio1
    with pytest.warns(UserWarning, match="Layer 0 contains values outside the range"):
        predict_map(map_data, model=model)


def test_predict_rejects_missing_values(tabular_data, model):
    tabular_data.loc[0, "bio1"] = np.nan
    with pytest.raises(ValueError, match="missing or non-finite"):
        predict(tabular_data, model=model)


def test_predict_accepts_normalized_spellings(tabular_data, model):
    renamed = tabular_data.rename(columns={"bio1": "Bioclim01", "bio4": "BIO_04"})
    result = predict(renamed, model=model)
    assert result.shape == (2, 11)
