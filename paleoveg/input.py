"""Input-column discovery and normalization for bioclim variables."""

import re
from collections import defaultdict
from typing import Iterable, Mapping, Optional

import pandas as pd


REQUIRED_COLUMNS = [
    "bio1", "bio4", "bio5", "bio6", "bio7", "bio8", "bio9", "bio10",
    "bio11", "bio12", "bio13", "bio14", "bio15", "bio16", "bio17",
    "bio18", "bio19",
]

_BIOCLIM_NAME = re.compile(r"^(?:bio|bioclim|bioclimatic)0*(\d{1,2})$")
MONTHLY_ROLES = ["tmean", "tmin", "tmax", "precipitation"]
_MONTHLY_ALIASES = {
    "tmean": {"tmp", "tmean", "temp", "temperature", "meantemperature"},
    "tmin": {"tmn", "tmin", "mintemp", "minimumtemperature"},
    "tmax": {"tmx", "tmax", "maxtemp", "maximumtemperature"},
    "precipitation": {"pre", "prec", "pr", "ppt", "precip", "precipitation"},
}


def _compact_name(value) -> str:
    """Normalize only superficial spelling differences."""
    return re.sub(r"[^a-z0-9]", "", str(value).strip().lower())


def canonical_bioclim_name(
    value, aliases: Optional[Mapping[str, str]] = None
) -> Optional[str]:
    """Return a required ``bioN`` name when *value* is an unambiguous match.

    Case, separators, the ``bioclim`` prefix, and leading zeroes are ignored.
    Semantic names are accepted only through the explicit ``aliases`` mapping;
    there is deliberately no fuzzy matching for scientific variables.
    """
    compact = _compact_name(value)
    compact_aliases = {
        _compact_name(alias): target for alias, target in (aliases or {}).items()
    }
    candidate = compact_aliases.get(compact)

    if candidate is None:
        match = _BIOCLIM_NAME.fullmatch(compact)
        if match:
            candidate = f"bio{int(match.group(1))}"

    return candidate if candidate in REQUIRED_COLUMNS else None


def match_bioclim_columns(
    columns: Iterable, aliases: Optional[Mapping[str, str]] = None
):
    """Describe how input columns map to PaleoVeg predictors.

    Each result contains ``input``, ``target``, and ``status``. Duplicate
    candidates for one target are marked ambiguous rather than silently chosen.
    """
    matches = []
    by_target = defaultdict(list)

    for index, column in enumerate(columns):
        target = canonical_bioclim_name(column, aliases=aliases)
        result = {
            "input": str(column),
            "target": target,
            "status": "matched" if target else "unmatched",
        }
        matches.append(result)
        if target:
            by_target[target].append(index)

    for indexes in by_target.values():
        if len(indexes) > 1:
            for index in indexes:
                matches[index]["status"] = "ambiguous"

    return matches


def normalize_bioclim_columns(
    input_df: pd.DataFrame, aliases: Optional[Mapping[str, str]] = None
):
    """Return a copy with recognized predictor names normalized and a report.

    Raises:
        ValueError: If multiple columns map to the same predictor, or one or
            more required predictors cannot be found.
    """
    if not isinstance(input_df, pd.DataFrame):
        raise ValueError("Input must be a pandas DataFrame.")

    report = match_bioclim_columns(input_df.columns, aliases=aliases)
    ambiguous = [item for item in report if item["status"] == "ambiguous"]
    if ambiguous:
        details = ", ".join(
            f"{item['input']} -> {item['target']}" for item in ambiguous
        )
        raise ValueError(f"Ambiguous bioclimatic columns: {details}")

    rename_map = {
        original: item["target"]
        for original, item in zip(input_df.columns, report)
        if item["status"] == "matched"
    }
    normalized = input_df.rename(columns=rename_map).copy()
    missing = [name for name in REQUIRED_COLUMNS if name not in normalized.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")
    return normalized, report


def match_monthly_column_groups(columns):
    """Find complete ``name_01`` ... ``name_12`` climate-normal groups."""
    groups = defaultdict(dict)
    labels = {}
    for column in columns:
        match = re.fullmatch(r"(.+?)[_\- ]?(0?[1-9]|1[0-2])", str(column).strip())
        if not match:
            continue
        base, month = match.group(1), int(match.group(2))
        compact = _compact_name(base)
        groups[compact][month] = str(column)
        labels.setdefault(compact, base)
    result = []
    for compact, months in groups.items():
        role = next((role for role, aliases in _MONTHLY_ALIASES.items() if compact in aliases), None)
        result.append({
            "input": labels[compact], "target": role,
            "status": "matched" if role and len(months) == 12 else "unmatched",
            "coverage": len(months),
            "columns": [months.get(month) for month in range(1, 13)],
        })
    by_role = defaultdict(list)
    for index, item in enumerate(result):
        if item["target"] and item["coverage"] == 12:
            by_role[item["target"]].append(index)
    for indexes in by_role.values():
        if len(indexes) > 1:
            for index in indexes:
                result[index]["status"] = "ambiguous"
    return result
