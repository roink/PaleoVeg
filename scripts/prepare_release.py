#!/usr/bin/env python3
"""Synchronize PaleoVeg release metadata before creating a version tag.

Run ``python scripts/prepare_release.py 0.2.1 --build-browser-wheel`` before
committing a release. The resulting commit is the source that must be tagged.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WHEEL_TEMPLATE = "paleoveg-{version}-py3-none-any.whl"


def normalized_version(value: str) -> str:
    version = value.removeprefix("v")
    if not re.fullmatch(r"\d+\.\d+\.\d+(?:[a-zA-Z0-9.+-]+)?", version):
        raise ValueError("Version must look like 0.2.1 or v0.2.1.")
    return version


def replace_exactly_once(path: Path, pattern: str, replacement: str) -> bool:
    content = path.read_text(encoding="utf-8")
    updated, count = re.subn(pattern, replacement, content, flags=re.MULTILINE)
    if count != 1:
        raise ValueError(f"Expected one version reference in {path}, found {count}.")
    if updated != content:
        path.write_text(updated, encoding="utf-8")
        return True
    return False


def replace_all(path: Path, pattern: str, replacement: str, expected_count: int) -> bool:
    content = path.read_text(encoding="utf-8")
    updated, count = re.subn(pattern, replacement, content, flags=re.MULTILINE)
    if count != expected_count:
        raise ValueError(f"Expected {expected_count} version references in {path}, found {count}.")
    if updated != content:
        path.write_text(updated, encoding="utf-8")
        return True
    return False


def synchronize(version: str) -> list[Path]:
    wheel_name = WHEEL_TEMPLATE.format(version=version)
    changes = [
        (ROOT / "setup.py", r'(?<=version=")[^"]+(?=")', version, 1),
        (ROOT / "paleoveg" / "__init__.py", r'(?<=__version__ = ")[^"]+(?=")', version, 1),
        (ROOT / "CITATION.cff", r'(?<=^version: ")[^"]+(?=")', f"v{version}", 1),
        (ROOT / "README.md", r'(\*PaleoVeg\* \(v)[^)]+(\) \[Software\])', rf'\g<1>{version}\g<2>', 1),
        (ROOT / "docs" / "index.html", r'(?<=PaleoVeg \(v)[^)]+(?=\) \[Software\])', version, 1),
        (ROOT / "docs" / "app.js", r'(?<=version   = \{)[^}]+(?=\},)', version, 1),
        (ROOT / "docs" / "pyodide-worker.mjs", r'(?<=WHEEL_NAME = ")[^"]+(?=")', wheel_name, 1),
        (ROOT / "docs" / "pyodide-worker.mjs", r'(?<=paleoveg_version", "char", ")[^"]+(?=")', version, 1),
        (ROOT / "docs" / "pyodide-worker.mjs", r'(?<=paleoveg_version: ")[^"]+(?=")', version, 1),
        (ROOT / "docs" / "cache-manifest.js", r'(?<=assets/)PaleoVeg-[^"/]+(?=")', wheel_name, 1),
        (ROOT / ".gitignore", r'(?<=!docs/assets/)[^\n]+', wheel_name, 1),
    ]
    changed = []
    for path, pattern, replacement, expected_count in changes:
        updater = replace_exactly_once if expected_count == 1 else replace_all
        if updater(path, pattern, replacement) if expected_count == 1 else updater(path, pattern, replacement, expected_count):
            changed.append(path)
    return changed


def check(version: str) -> list[str]:
    wheel_name = WHEEL_TEMPLATE.format(version=version)
    expectations = {
        ROOT / "setup.py": [f'version="{version}"'],
        ROOT / "paleoveg" / "__init__.py": [f'__version__ = "{version}"'],
        ROOT / "CITATION.cff": [f'version: "v{version}"'],
        ROOT / "README.md": [f"*PaleoVeg* (v{version}) [Software]"],
        ROOT / "docs" / "index.html": [f"PaleoVeg (v{version}) [Software]"],
        ROOT / "docs" / "app.js": [f"version   = {{{version}}},"],
        ROOT / "docs" / "pyodide-worker.mjs": [wheel_name, f'paleoveg_version", "char", "{version}"', f'paleoveg_version: "{version}"'],
        ROOT / "docs" / "cache-manifest.js": [f"assets/{wheel_name}"],
        ROOT / ".gitignore": [f"!docs/assets/{wheel_name}"],
    }
    missing = []
    for path, values in expectations.items():
        content = path.read_text(encoding="utf-8")
        missing.extend(f"{path.relative_to(ROOT)}: {value}" for value in values if value not in content)
    return missing


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("version", help="Release version, with or without a leading v")
    parser.add_argument("--check", action="store_true", help="Only verify synchronized release metadata")
    parser.add_argument("--build-browser-wheel", action="store_true", help="Build the matching browser wheel in docs/assets")
    args = parser.parse_args()
    version = normalized_version(args.version)

    if args.check:
        missing = check(version)
        if missing:
            raise SystemExit("Release metadata is not synchronized:\n- " + "\n- ".join(missing))
        print(f"Release metadata is synchronized for v{version}.")
        return

    changed = synchronize(version)
    if args.build_browser_wheel:
        subprocess.run(
            [sys.executable, "setup.py", "bdist_wheel", "--dist-dir", "docs/assets"],
            cwd=ROOT,
            check=True,
        )
    missing = check(version)
    if missing:
        raise SystemExit("Release metadata is not synchronized:\n- " + "\n- ".join(missing))
    if changed:
        print("Updated release metadata:")
        print("\n".join(f"- {path.relative_to(ROOT)}" for path in changed))
    else:
        print(f"Release metadata already matches v{version}.")


if __name__ == "__main__":
    main()
