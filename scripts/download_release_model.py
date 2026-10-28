#!/usr/bin/env python3
"""Download or copy the classifier specified by the checked-in model metadata."""

import argparse
import hashlib
import json
import shutil
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def verify(path, metadata):
    digest = hashlib.sha256()
    with path.open('rb') as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b''):
            digest.update(chunk)
    if path.stat().st_size != metadata['size_bytes'] or digest.hexdigest() != metadata['sha256']:
        raise ValueError(f'Model size or SHA-256 mismatch: {path}')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, help='Copy a local model instead of downloading')
    parser.add_argument('--output', type=Path, default=ROOT / 'docs/assets/model.pkl.bz2')
    parser.add_argument('--verify-only', action='store_true')
    args = parser.parse_args()
    metadata = json.loads((ROOT / 'paleoveg/model_metadata.json').read_text())
    if args.verify_only or args.output.exists():
        verify(args.output, metadata)
    else:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        temporary = args.output.with_suffix(args.output.suffix + '.part')
        try:
            if args.source:
                verify(args.source, metadata)
                shutil.copyfile(args.source, temporary)
            else:
                url = f"https://github.com/roink/PaleoVeg/releases/download/{metadata['version']}/{metadata['filename']}"
                with urllib.request.urlopen(url, timeout=120) as response, temporary.open('wb') as target:
                    shutil.copyfileobj(response, target)
            verify(temporary, metadata)
            temporary.replace(args.output)
        finally:
            temporary.unlink(missing_ok=True)
    print(f"Verified {metadata['version']} classifier: {args.output}")


if __name__ == '__main__':
    main()
