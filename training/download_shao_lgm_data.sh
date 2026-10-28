#!/usr/bin/env bash
# Download the published Shao et al. (2018) 1° LGM reconstruction outputs.
set -euo pipefail

ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
DESTINATION="$ROOT/training/data/shao_lgm"
DATASET_URL="https://data.mendeley.com/public-api/zip/cr269zdybh/download/1"

usage() {
  cat <<'EOF'
Usage: bash training/download_shao_lgm_data.sh [--destination PATH]

Downloads the two published Shao et al. (2018) 1° LGM reconstruction fields
from Mendeley Data DOI 10.17632/cr269zdybh.1 and verifies their SHA-256 hashes.
Existing destination files are never overwritten.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --destination)
      [[ $# -ge 2 ]] || { usage >&2; exit 2; }
      DESTINATION=$2
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      usage >&2
      exit 2
      ;;
  esac
done

FILES=(PMIP_1deg_no_co2_correction.nc PMIP_1deg_co2_correction.nc)
for filename in "${FILES[@]}"; do
  if [[ -e "$DESTINATION/$filename" ]]; then
    echo "Refusing to overwrite existing file: $DESTINATION/$filename" >&2
    exit 1
  fi
done

mkdir -p "$DESTINATION"
TEMPORARY_DIRECTORY=$(mktemp -d)
trap 'rm -rf "$TEMPORARY_DIRECTORY"' EXIT

curl -L --fail --retry 3 --show-error "$DATASET_URL" -o "$TEMPORARY_DIRECTORY/shao_lgm.zip"
unzip -j "$TEMPORARY_DIRECTORY/shao_lgm.zip" "${FILES[@]}" -d "$DESTINATION"

(
  cd "$DESTINATION"
  printf '%s  %s\n' \
    '6df21bb3b2493304d99fed60b5e7e72998d24122f7f89d0eb53332dbc280a69c' 'PMIP_1deg_no_co2_correction.nc' \
    '489db357497dea9208da96d4d09bf9b08827c2ef055fe5cf2e2c493d7cd75c7f' 'PMIP_1deg_co2_correction.nc' \
    | sha256sum --check --strict
)

echo "Downloaded and verified Shao et al. (2018) LGM comparison fields in $DESTINATION"
