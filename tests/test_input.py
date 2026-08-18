import pandas as pd
import pytest

from paleoveg.input import (
    REQUIRED_COLUMNS,
    canonical_bioclim_name,
    match_bioclim_columns,
    match_monthly_column_groups,
    normalize_bioclim_columns,
)


@pytest.mark.parametrize(
    "source,target",
    [
        ("bio1", "bio1"),
        ("Bio01", "bio1"),
        ("BIO_04", "bio4"),
        ("bioclim-05", "bio5"),
        ("Bioclimatic 19", "bio19"),
    ],
)
def test_canonical_bioclim_name(source, target):
    assert canonical_bioclim_name(source) == target


def test_semantic_names_are_not_guessed_without_alias():
    assert canonical_bioclim_name("annual precipitation") is None
    assert canonical_bioclim_name(
        "annual precipitation", {"annual precipitation": "bio12"}
    ) == "bio12"


def test_match_report_marks_duplicate_targets_ambiguous():
    report = match_bioclim_columns(["bio1", "Bio01", "notes"])
    assert [item["status"] for item in report] == [
        "ambiguous",
        "ambiguous",
        "unmatched",
    ]


def test_normalize_reports_mappings_and_preserves_extra_columns():
    frame = pd.DataFrame(
        {("Bio%02d" % int(name[3:])): [1.0] for name in REQUIRED_COLUMNS}
    )
    frame["site"] = ["A"]

    normalized, report = normalize_bioclim_columns(frame)

    assert all(name in normalized.columns for name in REQUIRED_COLUMNS)
    assert normalized["site"].tolist() == ["A"]
    assert len([item for item in report if item["status"] == "matched"]) == 17


def test_normalize_rejects_ambiguity():
    frame = pd.DataFrame({"bio1": [1], "Bio01": [2]})
    with pytest.raises(ValueError, match="Ambiguous"):
        normalize_bioclim_columns(frame)


def test_normalize_lists_missing_columns():
    frame = pd.DataFrame({"bio1": [1]})
    with pytest.raises(ValueError, match="bio4"):
        normalize_bioclim_columns(frame)


def test_matches_wide_monthly_groups_and_requires_all_months():
    columns = [f"tmp_{month:02d}" for month in range(1, 13)]
    columns += [f"pre-{month}" for month in range(1, 12)]
    report = match_monthly_column_groups(columns)
    assert report[0]["target"] == "tmean"
    assert report[0]["coverage"] == 12
    assert report[0]["status"] == "matched"
    assert report[1]["target"] == "precipitation"
    assert report[1]["status"] == "unmatched"
