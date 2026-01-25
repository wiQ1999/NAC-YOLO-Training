#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  tif_res_mpx.sh -i <DIR>

Requirements:
  -i, --input-dir    Folder containing .IMG files

Example:
  ./tif_res_mpx.sh -i /data/nac_tiles
EOF
}

DIR=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    -i|--input-dir)
      [[ $# -ge 2 ]] || { echo "Error: missing value for $1" >&2; usage; exit 1; }
      DIR="$2"; shift 2;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown argument: $1"; usage; exit 1 ;;
  esac
done

[[ -n "$DIR" ]] || { echo "Error: input directory is required" >&2; usage; exit 1; }
[[ -d "$DIR" ]] || { echo "Error: not a directory: $DIR" >&2; exit 1; }

shopt -s nullglob

fmt_pl() { printf '%s' "$1" | sed 's/\./,/g'; }

for f in "$DIR"/*.tif "$DIR"/*.tiff "$DIR"/*.TIF "$DIR"/*.TIFF; do
  px=$(gdalinfo "$f" 2>/dev/null | awk -F'[(), ]+' '/Pixel Size/ {print $4; exit}')
  py=$(gdalinfo "$f" 2>/dev/null | awk -F'[(), ]+' '/Pixel Size/ {print $5; exit}')

  if [[ -z "${px:-}" || -z "${py:-}" ]]; then
    echo "$f | m/px: [UNKNOWN]"
    continue
  fi

  px=${px#-}
  py=${py#-}

  gmean=$(awk -v x="$px" -v y="$py" 'BEGIN { printf "%.6f", sqrt(x*y) }')

  echo "$f | m/px: x=$(fmt_pl "$px"), y=$(fmt_pl "$py"), g=$(fmt_pl "$gmean")"
done
