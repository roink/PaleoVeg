"""Extract the CO2 observations from the IPCC AR6 Figure 2.4a BADC-CSV file."""

from __future__ import annotations

import csv
import hashlib
import sys
from pathlib import Path


EXPECTED_SHA256 = "8d473c3b67bdd26e395bc335096a99a15630cececa738010a61c2bedeb67f859"


def main(source_name: str, output_name: str) -> None:
    source = Path(source_name)
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    if digest != EXPECTED_SHA256:
        raise SystemExit(f"Unexpected source SHA-256: {digest}")

    observations = []
    in_data = False
    with source.open(newline="", encoding="utf-8-sig") as handle:
        for row in csv.reader(handle):
            if row[:2] == ["1", "2"]:
                in_data = True
                continue
            if not in_data or len(row) < 2:
                continue
            try:
                source_age = float(row[0])
                co2_ppm = float(row[1])
            except ValueError:
                continue
            observations.append((row[0], source_age - 0.05, row[1], co2_ppm))

    if len(observations) != 1894:
        raise SystemExit(f"Expected 1,894 CO2 observations, found {len(observations)}")
    if any(left[1] > right[1] for left, right in zip(observations, observations[1:])):
        raise SystemExit("Source CO2 ages are not sorted")

    output = Path(output_name)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(["source_age_kyr_before_2000", "age_ka_bp", "co2_ppm"])
        for source_text, age_ka_bp, co2_text, _ in observations:
            writer.writerow([source_text, f"{age_ka_bp:.3f}", co2_text])


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit("Usage: prepare_co2_data.py SOURCE.csv OUTPUT.csv")
    main(sys.argv[1], sys.argv[2])
