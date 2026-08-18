"""Derive PaleoVeg's BIOCLIM predictors from 12-month climate normals."""

import numpy as np

from .input import REQUIRED_COLUMNS


def guess_temperature_unit(*values):
    """Guess Celsius or Kelvin from finite temperature values and their range."""
    finite = [np.asarray(value, dtype=float)[np.isfinite(value)] for value in values]
    finite = [value for value in finite if value.size]
    if not finite:
        return {"unit": None, "minimum": None, "maximum": None}
    combined = np.concatenate([value.ravel() for value in finite])
    minimum, maximum = float(combined.min()), float(combined.max())
    unit = "celsius" if minimum >= -100 and maximum <= 100 else None
    if minimum >= 200 and maximum <= 400:
        unit = "kelvin"
    return {"unit": unit, "minimum": minimum, "maximum": maximum}


def derive_bioclimatic_variables(tmean, tmin, tmax, precipitation, month_axis=-1):
    """Return BIO1 and BIO4--19 from monthly climate normals.

    Inputs must share a shape and contain exactly twelve ordered months along
    ``month_axis``. Temperatures are degrees Celsius and precipitation is the
    monthly total in millimetres. Any incomplete observation becomes NaN.
    """
    arrays = [np.asarray(value, dtype=float) for value in (tmean, tmin, tmax, precipitation)]
    if any(array.shape != arrays[0].shape for array in arrays[1:]):
        raise ValueError("Monthly climate arrays must have identical shapes.")
    arrays = [np.moveaxis(array, month_axis, -1) for array in arrays]
    if arrays[0].shape[-1] != 12:
        raise ValueError("Monthly climate normals must contain exactly 12 months.")
    mean_t, min_t, max_t, precip = arrays
    valid = np.logical_and.reduce([np.isfinite(array).all(axis=-1) for array in arrays])

    def quarters(array):
        return sum(np.roll(array, -offset, axis=-1) for offset in range(3))

    precip_q = quarters(precip)
    temp_q = quarters(mean_t) / 3
    wet = np.argmax(precip_q, axis=-1)
    dry = np.argmin(precip_q, axis=-1)
    warm = np.argmax(temp_q, axis=-1)
    cold = np.argmin(temp_q, axis=-1)

    def selected(array, indexes):
        return np.take_along_axis(array, indexes[..., None], axis=-1)[..., 0]

    values = [
        mean_t.mean(axis=-1),
        mean_t.std(axis=-1, ddof=1) * 100,
        max_t.max(axis=-1),
        min_t.min(axis=-1),
        max_t.max(axis=-1) - min_t.min(axis=-1),
        selected(temp_q, wet),
        selected(temp_q, dry),
        temp_q.max(axis=-1),
        temp_q.min(axis=-1),
        precip.sum(axis=-1),
        precip.max(axis=-1),
        precip.min(axis=-1),
        (precip + 1).std(axis=-1, ddof=1) / (precip + 1).mean(axis=-1) * 100,
        precip_q.max(axis=-1),
        precip_q.min(axis=-1),
        selected(precip_q, warm),
        selected(precip_q, cold),
    ]
    result = np.stack(values, axis=-1)
    result[~valid] = np.nan
    return result


def bioclimatic_variable_dict(*args, **kwargs):
    """Return derived arrays keyed by PaleoVeg's canonical predictor names."""
    values = derive_bioclimatic_variables(*args, **kwargs)
    return {name: values[..., index] for index, name in enumerate(REQUIRED_COLUMNS)}
