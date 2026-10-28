#!/usr/bin/env python3
"""Build PaleoVeg's coordinate-preserving training table from source rasters."""

from __future__ import annotations

import argparse
import platform
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import rasterio
import scipy
from scipy.interpolate import RegularGridInterpolator

from paleoveg_training import (
    EXCLUDED_CLASSES,
    FEATURES,
    TARGET,
    configure_logging,
    outer_tile_ids,
    sha256,
    write_json,
)

ROOT = Path(__file__).resolve().parents[1]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--avhrr", type=Path, default=ROOT / "training/data/raw/avhrr/AVHRR_8km_LANDCOVER_1981_1994.GLOBAL.tif")
    parser.add_argument("--worldclim-dir", type=Path, default=ROOT / "training/data/raw/worldclim")
    parser.add_argument("--output", type=Path, default=ROOT / "training/data/processed/paleoveg_training.parquet")
    parser.add_argument("--max-rows", type=int, default=None, help="Smoke tests only; takes the first eligible raster rows.")
    return parser.parse_args()


def read_worldclim(path: Path) -> tuple[np.ndarray, np.ndarray, np.ndarray, dict]:
    with rasterio.open(path) as source:
        values = source.read(1).astype(np.float64)
        if source.nodata is not None:
            values[values == source.nodata] = np.nan
        transform = source.transform
        # PaleoVeg samples WorldClim at raster grid nodes, not cell centers.
        x = transform.c + transform.a * np.arange(source.width)
        y = transform.f + transform.e * np.arange(source.height)
        metadata = {
            "path": str(path), "sha256": sha256(path), "width": source.width,
            "height": source.height, "transform": tuple(transform), "crs": str(source.crs),
        }
    return y, x, values, metadata


def main() -> None:
    args = parse_args()
    logger = configure_logging(ROOT / "training/logs/build_training_data.log")
    missing = [args.avhrr] + [args.worldclim_dir / f"wc2.1_5m_bio_{name[3:]}.tif" for name in FEATURES]
    missing = [path for path in missing if not path.exists()]
    if missing:
        raise FileNotFoundError("Missing required inputs:\n" + "\n".join(map(str, missing)))

    with rasterio.open(args.avhrr) as source:
        landuse = source.read(1)
        transform = source.transform
        rows, cols = np.where(~np.isin(landuse, EXCLUDED_CLASSES))
        labels = landuse[rows, cols].astype(np.int16)
        # Match the original notebook exactly: left edge and lower edge.
        lon = transform.c + transform.a * cols
        lat = transform.f + transform.e * (rows + 1)
        avhrr_meta = {
            "path": str(args.avhrr), "sha256": sha256(args.avhrr),
            "width": source.width, "height": source.height,
            "transform": tuple(transform), "crs": str(source.crs),
        }

    if args.max_rows is not None:
        rows, cols, labels, lon, lat = [array[: args.max_rows] for array in (rows, cols, labels, lon, lat)]
    logger.info("Eligible AVHRR observations: %s", f"{len(labels):,}")
    query = np.column_stack((lat, lon))
    output: dict[str, np.ndarray] = {"lon": lon, "lat": lat}
    sources = []
    valid = np.ones(len(labels), dtype=bool)
    for feature in FEATURES:
        path = args.worldclim_dir / f"wc2.1_5m_bio_{feature[3:]}.tif"
        y, x, values, metadata = read_worldclim(path)
        interpolator = RegularGridInterpolator((y, x), values, bounds_error=False, fill_value=np.nan)
        feature_values = interpolator(query)
        output[feature] = feature_values
        valid &= np.isfinite(feature_values)
        sources.append(metadata)
        logger.info("Interpolated %s", feature)
    output[TARGET] = labels
    frame = pd.DataFrame(output).loc[valid].reset_index(drop=True)
    frame["outer_tile_id"] = outer_tile_ids(frame["lon"].to_numpy(), frame["lat"].to_numpy())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    frame.to_parquet(args.output, index=False)
    metadata_path = args.output.with_suffix(".metadata.json")
    write_json({
        "rows": len(frame), "columns": list(frame.columns),
        "excluded_avhrr_classes": EXCLUDED_CLASSES,
        "coordinate_convention": "AVHRR left and lower pixel edges; WorldClim grid nodes (historical PaleoVeg convention)",
        "avhrr": avhrr_meta, "worldclim": sources,
        "software": {"python": platform.python_version(), "numpy": np.__version__, "pandas": pd.__version__, "rasterio": rasterio.__version__, "scipy": scipy.__version__},
        "smoke_test_max_rows": args.max_rows,
    }, metadata_path)
    logger.info("Wrote %s rows to %s", f"{len(frame):,}", args.output)


if __name__ == "__main__":
    main()
