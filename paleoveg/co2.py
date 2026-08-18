"""Atmospheric CO2 lookup from the IPCC AR6 Figure 2.4a observations."""

from __future__ import annotations

import csv
from functools import lru_cache
from importlib.resources import files
from numbers import Real

import numpy as np


CO2_DATASET_DOI = "10.5285/60eeb3cce51a457cb5ee1c577a0c8674"
CO2_DATASET_VERSION = "v20221219"
CO2_AGE_REFERENCE_YEAR = 1950
CO2_SOURCE_AGE_REFERENCE_YEAR = 2000


def _validate_age(age_ka_bp):
    if isinstance(age_ka_bp, (bool, np.bool_)) or not isinstance(age_ka_bp, Real):
        raise ValueError("age_ka_bp must be a finite numeric age in thousands of years before 1950.")
    age = float(age_ka_bp)
    if not np.isfinite(age):
        raise ValueError("age_ka_bp must be a finite numeric age in thousands of years before 1950.")
    return age


@lru_cache(maxsize=1)
def _co2_knots():
    grouped = {}
    resource = files("paleoveg").joinpath("data/co2/co2_ipcc_ar6.csv")
    with resource.open("r", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            age = float(row["age_ka_bp"])
            grouped.setdefault(age, []).append(float(row["co2_ppm"]))
    ages = np.array(sorted(grouped), dtype=float)
    concentrations = np.array([np.mean(grouped[age]) for age in ages], dtype=float)
    return ages, concentrations


def _co2_lookup_details(age_ka_bp):
    age = _validate_age(age_ka_bp)
    ages, concentrations = _co2_knots()
    if age < ages[0] or age > ages[-1]:
        raise ValueError(
            f"age_ka_bp must be between {ages[0]:g} and {ages[-1]:g}; "
            "the bundled CO2 record is not extrapolated."
        )
    right = int(np.searchsorted(ages, age, side="left"))
    if right < len(ages) and ages[right] == age:
        left = right
        ppm = concentrations[right]
    else:
        left = right - 1
        fraction = (age - ages[left]) / (ages[right] - ages[left])
        ppm = concentrations[left] + fraction * (concentrations[right] - concentrations[left])
    return {
        "age_ka_bp": age,
        "age_reference_year": CO2_AGE_REFERENCE_YEAR,
        "source_age_kyr_before_2000": age + 0.05,
        "source_age_reference_year": CO2_SOURCE_AGE_REFERENCE_YEAR,
        "co2_ppm": float(ppm),
        "interpolation": "exact" if left == right else "linear",
        "bracket": [
            {
                "age_ka_bp": float(ages[index]),
                "source_age_kyr_before_2000": float(ages[index] + 0.05),
                "co2_ppm": float(concentrations[index]),
            }
            for index in dict.fromkeys((left, right))
        ],
        "dataset_title": "IPCC AR6 WGI Chapter 2 Figure 2.4 data",
        "dataset_doi": CO2_DATASET_DOI,
        "dataset_version": CO2_DATASET_VERSION,
        "license": "CC BY 4.0",
    }


def co2_at_time(age_ka_bp: float) -> float:
    """Return linearly interpolated atmospheric CO2 for an age in ka BP (1950)."""
    return _co2_lookup_details(age_ka_bp)["co2_ppm"]
