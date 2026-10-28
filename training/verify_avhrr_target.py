#!/usr/bin/env python3
"""Verify whether a supplied UMD raster is PaleoVeg 1.0's training target.

Usage
-----
python training/verify_avhrr_target.py /path/to/umd_8km_landcover.tif

The command deliberately reads only the file bytes. It can therefore verify an
independently obtained copy without redistributing the restricted raster.
"""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path


EXPECTED_SHA256 = "3574f9b960e428a7fe2fd228c736e1d8b900c9ce21cc39ce41eb3b8c9b517ad1"
CHUNK_SIZE = 1024 * 1024


def sha256(path: Path) -> str:
    """Return the SHA-256 digest of *path* without loading it into memory."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(CHUNK_SIZE), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("raster", type=Path, help="candidate UMD 8 km GeoTIFF")
    args = parser.parse_args()

    if not args.raster.is_file():
        parser.error(f"not a readable file: {args.raster}")

    observed = sha256(args.raster)
    print(f"SHA-256:  {observed}")
    print(f"Expected: {EXPECTED_SHA256}")
    if observed == EXPECTED_SHA256:
        print("MATCH: this is the exact UMD raster used to train PaleoVeg 1.0.")
        return 0

    print("NO MATCH: this file is not the exact PaleoVeg 1.0 training raster.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
