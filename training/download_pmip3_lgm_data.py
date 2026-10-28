#!/usr/bin/env python3
"""Download and reconstruct the PMIP3/CMIP5 inputs for the LGM experiment.

The institute copy used for the original run contains CDO-consolidated monthly
time series.  ESGF commonly serves the same CMIP5 output in shorter files. This
script downloads the official segments, verifies the ESGF-advertised SHA-256
checksums, and uses ``cdo mergetime`` to rebuild the layout accepted by
``prepare_shao_lgm_climate.sh``.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import shutil
import subprocess
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen


DEFAULT_INDEX = "https://esgf-node.llnl.gov/esg-search/search/"
FILENAME_RE = re.compile(
    r"^(?P<variable>[A-Za-z0-9]+)_Amon_(?P<model>.+?)_lgm_r1i1p1_"
    r"(?P<start>\d{6})-(?P<end>\d{6})\.nc$"
)


def month_index(value: str) -> int:
    year, month = int(value[:4]), int(value[4:])
    return year * 12 + month - 1


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def search(index: str, model: str, variable: str) -> list[dict]:
    params = {
        "type": "File",
        "format": "application/solr+json",
        "project": "CMIP5",
        "model": model,
        "experiment": "lgm",
        "ensemble": "r1i1p1",
        "time_frequency": "mon",
        "realm": "atmos",
        "cmor_table": "Amon",
        "variable": variable,
        "limit": "1000",
    }
    request = Request(f"{index}?{urlencode(params)}", headers={"User-Agent": "PaleoVeg/1.0"})
    with urlopen(request, timeout=180) as response:  # nosec B310: ESGF URL is user-controlled
        return json.load(response)["response"]["docs"]


def urls(record: dict) -> list[str]:
    candidates = [
        value.split("|", 1)[0]
        for value in record.get("url", [])
        if value.endswith("|HTTPServer")
    ]
    return sorted(
        set(candidates),
        key=lambda value: (
            not value.startswith("https://"),
            "data.globus.org" not in value,
            value,
        ),
    )


def expected_segments(records: list[dict], model: str, variable: str, start: str, end: str) -> list[dict]:
    """Choose one replica per official filename and require complete coverage."""
    by_title: dict[str, list[dict]] = defaultdict(list)
    target_start, target_end = month_index(start), month_index(end)
    for record in records:
        title = record.get("title", "")
        match = FILENAME_RE.match(title)
        if not match or match["model"] != model or match["variable"] != variable:
            continue
        record_start, record_end = month_index(match["start"]), month_index(match["end"])
        if target_start <= record_start and record_end <= target_end:
            by_title[title].append(record)

    selected: list[dict] = []
    cursor = target_start
    for title in sorted(by_title, key=lambda value: month_index(FILENAME_RE.match(value)["start"])):
        match = FILENAME_RE.match(title)
        assert match is not None
        record_start, record_end = month_index(match["start"]), month_index(match["end"])
        if record_start != cursor:
            continue
        record = next((item for item in by_title[title] if urls(item)), None)
        if record is None:
            continue
        selected.append(record)
        cursor = record_end + 1
        if cursor > target_end:
            break
    if cursor != target_end + 1:
        raise RuntimeError(
            f"ESGF does not provide a complete contiguous {start}-{end} monthly "
            f"series for {model} / {variable}."
        )
    return selected


def download(record: dict, destination: Path) -> dict:
    expected = record.get("checksum", [None])[0]
    checksum_type = record.get("checksum_type", [None])[0]
    if checksum_type != "SHA256" or not expected:
        raise RuntimeError(f"No SHA-256 checksum advertised by ESGF for {record.get('title')}")
    partial = destination.with_suffix(destination.suffix + ".part")
    if destination.exists() and sha256(destination) == expected:
        return {"title": record["title"], "url": "cached", "sha256": expected}
    destination.unlink(missing_ok=True)
    for url in urls(record):
        command = [
            "curl", "--location", "--fail", "--retry", "3", "--retry-delay", "2",
            "--continue-at", "-", "--output", str(partial), url,
        ]
        result = subprocess.run(command, check=False)
        if result.returncode == 0 and partial.is_file() and sha256(partial) == expected:
            partial.replace(destination)
            return {"title": record["title"], "url": url, "sha256": expected}
        partial.unlink(missing_ok=True)
    raise RuntimeError(f"Unable to download a checksum-valid copy of {record['title']}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--destination", type=Path,
        default=Path("training/data/pmip3_lgm/esgf_download"),
        help="Directory for official segments and reconstructed source files.",
    )
    parser.add_argument("--index", default=DEFAULT_INDEX, help="ESGF search endpoint.")
    parser.add_argument("--dry-run", action="store_true", help="Search and report files without downloading.")
    args = parser.parse_args()

    if not args.dry_run:
        for executable in ("curl", "cdo"):
            if shutil.which(executable) is None:
                parser.error(f"Required executable not found: {executable}")

    root = Path(__file__).parent
    manifest_path = root / "data" / "pmip3_lgm" / "source_manifest.tsv"
    with manifest_path.open(newline="", encoding="utf-8") as handle:
        entries = list(csv.DictReader(handle, delimiter="\t"))

    grouped: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for entry in entries:
        grouped[(entry["model"], entry["variable"])].append(entry)
    if any(len(items) != 1 for items in grouped.values()):
        raise RuntimeError("The source manifest must contain one canonical output per model and variable.")

    provenance: list[dict] = []
    for (model, variable), (entry,) in sorted(grouped.items()):
        match = FILENAME_RE.match(entry["filename"])
        if not match:
            raise RuntimeError(f"Unexpected manifest filename: {entry['filename']}")
        records = search(args.index, model, variable)
        segments = expected_segments(records, model, variable, match["start"], match["end"])
        print(f"{model:12s} {variable:6s} {len(segments)} ESGF segment(s)")
        if args.dry_run:
            provenance.append({"model": model, "variable": variable, "segments": [item["title"] for item in segments]})
            continue

        segment_paths: list[Path] = []
        downloaded: list[dict] = []
        for record in segments:
            path = args.destination / "segments" / variable / model / record["title"]
            path.parent.mkdir(parents=True, exist_ok=True)
            downloaded.append(download(record, path))
            segment_paths.append(path)

        output = args.destination / "atmos" / "mon" / variable / entry["filename"]
        output.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(["cdo", "-L", "-O", "mergetime", *(str(path) for path in segment_paths), str(output)], check=True)
        provenance.append(
            {
                "model": model,
                "variable": variable,
                "canonical_filename": entry["filename"],
                "canonical_sha256_from_institute_copy": entry["sha256"],
                "segments": downloaded,
                "reconstructed_sha256": sha256(output),
            }
        )

    if args.dry_run:
        return 0
    output_manifest = args.destination / "esgf_download_manifest.json"
    output_manifest.write_text(
        json.dumps(
            {
                "created_utc": datetime.now(timezone.utc).isoformat(),
                "esgf_index": args.index,
                "source_manifest": str(manifest_path),
                "entries": provenance,
            },
            indent=2,
        ) + "\n",
        encoding="utf-8",
    )
    print(f"Downloaded and reconstructed {len(provenance)} PMIP3/CMIP5 inputs under {args.destination}.")
    print("Use its atmos/mon directory as the argument to prepare_shao_lgm_climate.sh.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RuntimeError as error:
        print(f"error: {error}", file=sys.stderr)
        raise SystemExit(1)
