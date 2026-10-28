#!/usr/bin/env python3
"""Verify the exact PMIP3/CMIP5 source files used in the LGM experiment."""

from __future__ import annotations

import argparse
import csv
import hashlib
from pathlib import Path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "pmip_root",
        type=Path,
        help="Directory containing tas/, tasmin/, tasmax/, and pr/ subdirectories.",
    )
    args = parser.parse_args()
    manifest = Path(__file__).parent / "data" / "pmip3_lgm" / "source_manifest.tsv"

    failures: list[str] = []
    with manifest.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))
    for row in rows:
        path = args.pmip_root / row["variable"] / row["filename"]
        if not path.is_file():
            failures.append(f"missing: {path}")
            continue
        actual = sha256(path)
        if actual != row["sha256"]:
            failures.append(
                f"checksum mismatch: {path}\n"
                f"  expected {row['sha256']}\n"
                f"  found    {actual}"
            )

    if failures:
        print("PMIP3 LGM input verification failed:")
        print("\n".join(failures))
        return 1
    print(f"Verified {len(rows)} PMIP3/CMIP5 LGM source files.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
