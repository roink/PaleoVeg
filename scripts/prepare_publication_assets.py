#!/usr/bin/env python3
"""Prepare model and reproducibility assets without redistributing raw inputs.

Run after committing the release source. Upload these files to the GitHub draft
release and to a persistent data archive; GitHub/Zenodo integration archives only
the tagged source snapshot, not attached assets.
"""

import argparse
import hashlib
import json
import shutil
import subprocess
import tarfile
from pathlib import Path

from download_release_model import verify

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, default=ROOT / 'dist/release-assets')
    args = parser.parse_args()
    metadata = json.loads((ROOT / 'paleoveg/model_metadata.json').read_text())
    model = ROOT / 'training/models/spatial_validation_v1/model.pkl.bz2'
    verify(model, metadata)
    tracked = subprocess.check_output(['git', 'ls-files', '-z'], cwd=ROOT).decode().split('\0')
    status = subprocess.check_output(['git', 'status', '--porcelain'], cwd=ROOT).decode()
    if status.strip():
        raise SystemExit('Commit the release source before preparing its publication assets.')
    # Explicit allowlist: exclude the AVHRR target, training table, downloaded
    # climate fields, and other third-party inputs with redistribution limits.
    extra = sorted((ROOT / 'training/models').rglob('*.pkl.bz2'))
    extra += sorted((ROOT / 'training/results/shao_lgm_experiment').glob('paleoveg_*.nc'))
    extra += [ROOT / 'training/data/processed/paleoveg_training.metadata.json']
    missing = [str(p) for p in extra if not p.is_file()]
    if missing:
        raise SystemExit('Missing artifacts: ' + ', '.join(missing))
    args.output_dir.mkdir(parents=True, exist_ok=True)
    commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT).decode().strip()
    files = sorted(set([p for p in tracked if p] + [str(p.relative_to(ROOT)) for p in extra]))
    # Store identical models once and use tar hard links for their workflow paths.
    archive = args.output_dir / f"paleoveg-{metadata['version']}-publication.tar.gz"
    seen = {}
    with tarfile.open(archive, 'w:gz', compresslevel=1) as target:
        for name in files:
            path = ROOT / name
            if path.suffix == '.bz2':
                with path.open('rb') as source:
                    digest = hashlib.file_digest(source, 'sha256').hexdigest()
                if digest in seen:
                    info = target.gettarinfo(str(path), arcname=name)
                    info.type = tarfile.LNKTYPE
                    info.linkname = seen[digest]
                    info.size = 0
                    target.addfile(info)
                    continue
                seen[digest] = name
            target.add(path, arcname=name, recursive=False)
    model_copy = args.output_dir / metadata['filename']
    shutil.copyfile(model, model_copy)
    manifest = dict(metadata, source_commit=commit, publication_archive=archive.name,
                    included_paths=files)
    (args.output_dir / 'release-manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    outputs = [archive, model_copy, args.output_dir / 'release-manifest.json']
    lines = []
    for path in outputs:
        with path.open('rb') as source:
            digest = hashlib.file_digest(source, 'sha256').hexdigest()
        lines.append(f'{digest}  {path.name}')
    (args.output_dir / 'SHA256SUMS').write_text('\n'.join(lines) + '\n')
    print(f'Publication assets for {commit}: {args.output_dir}')


if __name__ == '__main__':
    main()
