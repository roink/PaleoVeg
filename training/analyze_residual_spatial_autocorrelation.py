#!/usr/bin/env python3
"""Estimate distance-dependent autocorrelation in held-out PaleoVeg residuals."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from paleoveg_training import CLASSES, LAND_USE_COLORS, configure_logging, sha256

ROOT = Path(__file__).resolve().parents[1]
FIGURES = ROOT / "figures"
CLASS_ABBREVIATIONS = {
    1: "ENF", 2: "EBF", 3: "DNF", 4: "DBF", 5: "MF", 6: "WL",
    7: "WGL", 8: "CSL", 9: "OSL", 10: "GL", 12: "BG",
}
DEFAULT_EDGES_KM = [
    0, 25, 50, 100, 150, 200, 300, 400, 500, 750, 1000, 1500,
    2000, 3000, 5000, 7500, 10000, 15000, 20000,
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--predictions",
        type=Path,
        default=ROOT / "training/results/predictor_set_comparison/full_bioclim_external_predictions.parquet",
    )
    parser.add_argument(
        "--results-dir",
        type=Path,
        default=ROOT / "training/results/residual_spatial_autocorrelation",
    )
    parser.add_argument("--sample-per-tile", type=int, default=1000)
    parser.add_argument("--pair-count", type=int, default=2_000_000)
    parser.add_argument("--seed", type=int, default=219)
    parser.add_argument("--distance-bin-km", type=float, nargs="+", default=DEFAULT_EDGES_KM)
    return parser.parse_args()


def haversine_km(
    lon1: np.ndarray, lat1: np.ndarray, lon2: np.ndarray, lat2: np.ndarray
) -> np.ndarray:
    radius_km = 6371.0088
    lon1, lat1, lon2, lat2 = map(np.deg2rad, (lon1, lat1, lon2, lat2))
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = np.sin(dlat / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2) ** 2
    return 2 * radius_km * np.arcsin(np.sqrt(np.minimum(1.0, a)))


def stratified_sample(frame: pd.DataFrame, per_tile: int, seed: int) -> pd.DataFrame:
    pieces = []
    for tile_index, (_, group) in enumerate(frame.groupby("outer_tile_id", sort=True)):
        n = min(per_tile, len(group))
        pieces.append(group.sample(n=n, random_state=seed + tile_index, replace=False))
    return pd.concat(pieces, ignore_index=True)


def add_residuals(frame: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    observed = frame["land_use_type"].to_numpy()
    probabilities = frame[[f"probability_{code}" for code in CLASSES]].to_numpy(dtype=np.float64)
    output = frame[["lon", "lat", "outer_tile_id", "land_use_type", "predicted_class"]].copy()
    residual_names = []
    for index, code in enumerate(CLASSES):
        name = f"residual_{CLASS_ABBREVIATIONS[code]}"
        output[name] = probabilities[:, index] - (observed == code).astype(np.float64)
        residual_names.append(name)
    return output, residual_names


def estimate(
    residuals: pd.DataFrame,
    variables: list[str],
    edges: np.ndarray,
    pair_count: int,
    seed: int,
) -> tuple[pd.DataFrame, pd.DataFrame, int]:
    rng = np.random.default_rng(seed)
    n = len(residuals)
    left = rng.integers(0, n, pair_count, dtype=np.int64)
    right = rng.integers(0, n, pair_count, dtype=np.int64)
    same = left == right
    while same.any():
        right[same] = rng.integers(0, n, int(same.sum()), dtype=np.int64)
        same = left == right

    lon = residuals["lon"].to_numpy(dtype=np.float64)
    lat = residuals["lat"].to_numpy(dtype=np.float64)
    distances = haversine_km(lon[left], lat[left], lon[right], lat[right])
    bins = np.digitize(distances, edges, right=False) - 1
    valid = (bins >= 0) & (bins < len(edges) - 1)
    left, right, distances, bins = left[valid], right[valid], distances[valid], bins[valid]
    bin_count = len(edges) - 1
    pair_counts = np.bincount(bins, minlength=bin_count)
    distance_sums = np.bincount(bins, weights=distances, minlength=bin_count)

    rows: list[dict[str, object]] = []
    ranges: list[dict[str, object]] = []
    for variable in variables:
        values = residuals[variable].to_numpy(dtype=np.float64)
        centered = values - values.mean()
        variance = float(np.mean(np.square(centered)))
        products = centered[left] * centered[right]
        semivariance_values = 0.5 * np.square(values[left] - values[right])
        covariance_sums = np.bincount(bins, weights=products, minlength=bin_count)
        semivariance_sums = np.bincount(bins, weights=semivariance_values, minlength=bin_count)
        variable_rows = []
        for index in range(bin_count):
            count = int(pair_counts[index])
            row = {
                "variable": variable,
                "distance_min_km": float(edges[index]),
                "distance_max_km": float(edges[index + 1]),
                "distance_mid_km": float((edges[index] + edges[index + 1]) / 2),
                "pair_count": count,
                "mean_distance_km": float(distance_sums[index] / count) if count else np.nan,
                "residual_correlation": float(covariance_sums[index] / count / variance) if count and variance else np.nan,
                "semivariance": float(semivariance_sums[index] / count) if count else np.nan,
                "relative_semivariance": float(semivariance_sums[index] / count / variance) if count and variance else np.nan,
            }
            rows.append(row)
            variable_rows.append(row)

        practical_range = np.nan
        range_basis = "not reached"
        local_rows = [
            row for row in variable_rows
            if row["pair_count"] >= 100 and float(row["distance_max_km"]) <= 1000
        ]
        for index, row in enumerate(local_rows):
            if all(abs(float(later["residual_correlation"])) <= 0.05 for later in local_rows[index:]):
                practical_range = float(row["distance_max_km"])
                range_basis = "first distance class after which |correlation| remains <=0.05 through 1000 km"
                break
        ranges.append(
            {
                "variable": variable,
                "sample_mean": float(values.mean()),
                "sample_variance": variance,
                "practical_range_km": practical_range,
                "range_basis": range_basis,
            }
        )
    return pd.DataFrame(rows), pd.DataFrame(ranges), int(len(left))


def make_figure(correlogram: pd.DataFrame, path: Path) -> None:
    signed = [f"residual_{CLASS_ABBREVIATIONS[code]}" for code in CLASSES]
    colors = [LAND_USE_COLORS[code] for code in CLASSES]
    fig, ax = plt.subplots(figsize=(11, 6.2))
    for variable, color in zip(signed, colors):
        group = correlogram[(correlogram.variable == variable) & (correlogram.pair_count >= 100)]
        ax.plot(group.mean_distance_km, group.residual_correlation, marker="o", markersize=3,
                linewidth=1.1, color=color, label=variable.removeprefix("residual_"))
    ax.axhline(0, color="black", linewidth=0.7)
    ax.axhline(0.05, color="0.45", linewidth=0.8, linestyle="--")
    ax.axhline(-0.05, color="0.45", linewidth=0.8, linestyle="--")
    ax.axvline(555, color="#009E73", linewidth=1.2, linestyle=":", label="5° north--south (about 555 km)")
    ax.set_xscale("log")
    ax.grid(color="0.9", linewidth=0.5)
    ax.set_ylabel("Distance-class residual correlation")
    ax.set_xlabel("Great-circle pair distance (km, logarithmic scale)")
    ax.legend(ncol=4, fontsize=8, loc="upper right")
    fig.suptitle("Spatial autocorrelation of full-model residuals on external-test tiles", fontweight="bold")
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, bbox_inches="tight")
    fig.savefig(path.with_suffix(".png"), dpi=300, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    args = parse_args()
    logger = configure_logging(ROOT / "training/logs/analyze_residual_spatial_autocorrelation.log")
    if len(args.distance_bin_km) < 2 or np.any(np.diff(args.distance_bin_km) <= 0):
        raise ValueError("Distance-bin edges must be strictly increasing.")
    frame = pd.read_parquet(args.predictions)
    required = {"lon", "lat", "outer_tile_id", "land_use_type", "predicted_class"} | {
        f"probability_{code}" for code in CLASSES
    }
    if missing := required.difference(frame.columns):
        raise ValueError(f"Prediction file is missing columns: {sorted(missing)}")
    sample = stratified_sample(frame, args.sample_per_tile, args.seed)
    residuals, signed_variables = add_residuals(sample)
    variables = signed_variables
    correlogram, ranges, valid_pairs = estimate(
        residuals, variables, np.asarray(args.distance_bin_km, dtype=float), args.pair_count, args.seed
    )
    args.results_dir.mkdir(parents=True, exist_ok=True)
    residuals.to_parquet(args.results_dir / "sampled_external_residuals.parquet", index=False)
    correlogram.to_csv(args.results_dir / "residual_distance_correlogram.csv", index=False)
    ranges.to_csv(args.results_dir / "residual_autocorrelation_range_summary.csv", index=False)
    metadata = {
        "prediction_file": str(args.predictions),
        "prediction_sha256": sha256(args.predictions),
        "source_rows": int(len(frame)),
        "source_tiles": int(frame.outer_tile_id.nunique()),
        "sample_rows": int(len(sample)),
        "sample_per_tile_maximum": args.sample_per_tile,
        "requested_pair_count": args.pair_count,
        "valid_pair_count": valid_pairs,
        "seed": args.seed,
        "distance_bin_edges_km": args.distance_bin_km,
        "residual_definition": "predicted class probability minus one-hot observed class occurrence",
        "assessment_data": "untouched external spatial-test tiles; model fitted only to development tiles",
        "range_rule": "first distance class after which absolute signed-residual correlation remains <=0.05 through 1000 km; all bins require >=100 pairs",
    }
    (args.results_dir / "run_metadata.json").write_text(json.dumps(metadata, indent=2) + "\n")
    figure_path = FIGURES / "fig08_residual_spatial_autocorrelation.pdf"
    make_figure(correlogram, figure_path)
    logger.info("Source: %s rows in %s tiles", f"{len(frame):,}", frame.outer_tile_id.nunique())
    logger.info("Sample: %s rows; valid pairs: %s", f"{len(sample):,}", f"{valid_pairs:,}")
    logger.info("Wrote results to %s and figure to %s", args.results_dir, figure_path)


if __name__ == "__main__":
    main()
