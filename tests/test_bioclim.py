import numpy as np
import pytest

from paleoveg import derive_bioclimatic_variables, guess_temperature_unit


def test_derives_model_predictors_and_wraps_quarters():
    mean = np.arange(1, 13, dtype=float)
    minimum = mean - 2
    maximum = mean + 3
    precipitation = np.array([100, 100, 1, 1, 1, 1, 1, 1, 1, 1, 1, 100], dtype=float)
    result = derive_bioclimatic_variables(mean, minimum, maximum, precipitation)
    assert result.shape == (17,)
    assert result[0] == pytest.approx(6.5)
    assert result[2] == 15
    assert result[3] == -1
    assert result[4] == 16
    assert result[9] == 309
    assert result[13] == 300  # December-January-February


def test_rejects_non_monthly_or_mismatched_inputs():
    twelve = np.ones(12)
    with pytest.raises(ValueError, match="12 months"):
        derive_bioclimatic_variables(np.ones(11), np.ones(11), np.ones(11), np.ones(11))
    with pytest.raises(ValueError, match="identical"):
        derive_bioclimatic_variables(twelve, twelve, twelve, np.ones((1, 12)))


def test_incomplete_climate_normal_is_nan():
    values = np.ones((2, 12))
    precipitation = values.copy()
    precipitation[1, 4] = np.nan
    result = derive_bioclimatic_variables(values, values, values, precipitation)
    assert np.isfinite(result[0]).all()
    assert np.isnan(result[1]).all()


@pytest.mark.parametrize(
    "values,expected",
    [([-40, 0, 48], "celsius"), ([220, 273.15, 330], "kelvin"), ([50, 250], None)],
)
def test_guesses_temperature_unit_from_complete_range(values, expected):
    guess = guess_temperature_unit(values)
    assert guess["unit"] == expected
    assert guess["minimum"] == min(values)
    assert guess["maximum"] == max(values)
