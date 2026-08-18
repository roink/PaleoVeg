import csv
from importlib.resources import files

import pytest

from paleoveg import co2_at_time
from paleoveg.co2 import _co2_lookup_details, _co2_knots


def test_packaged_observations_are_complete_and_preserve_duplicate():
    resource = files("paleoveg").joinpath("data/co2/co2_ipcc_ar6.csv")
    with resource.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 1894
    assert rows[0] == {
        "source_age_kyr_before_2000": "-0.019",
        "age_ka_bp": "-0.069",
        "co2_ppm": "409.9",
    }
    assert sum(row["age_ka_bp"] == "0.227" for row in rows) == 2


def test_co2_at_20_ka_bp_matches_documented_interpolation():
    assert co2_at_time(20) == pytest.approx(194.03777777777773)
    details = _co2_lookup_details(20)
    assert details["source_age_kyr_before_2000"] == pytest.approx(20.05)
    assert details["interpolation"] == "linear"
    assert details["bracket"] == [
        {"age_ka_bp": 19.884, "source_age_kyr_before_2000": 19.934, "co2_ppm": 196.1},
        {"age_ka_bp": 20.019, "source_age_kyr_before_2000": 20.069, "co2_ppm": 193.7},
    ]


def test_duplicate_age_is_averaged_for_lookup_knot():
    assert co2_at_time(0.227) == pytest.approx((277 + 278.3) / 2)


def test_lookup_supports_endpoints_without_extrapolating():
    ages, concentrations = _co2_knots()
    assert co2_at_time(ages[0]) == concentrations[0]
    assert co2_at_time(ages[-1]) == concentrations[-1]
    with pytest.raises(ValueError, match="not extrapolated"):
        co2_at_time(ages[0] - 0.001)
    with pytest.raises(ValueError, match="not extrapolated"):
        co2_at_time(ages[-1] + 0.001)


@pytest.mark.parametrize("age", ["20", True, float("nan"), float("inf")])
def test_lookup_rejects_invalid_age(age):
    with pytest.raises(ValueError, match="finite numeric"):
        co2_at_time(age)
