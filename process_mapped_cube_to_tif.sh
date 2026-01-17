#!/usr/bin/env bash
set -euo pipefail

# Stage 3: cam2map for each *.tr.cub + export to GeoTIFF (Byte) via gdal_translate
#
# Usage:
#   ./stage3_cam2map_to_tif.sh <tr_cub_dir> <map_dir> <out_dir>
#
# Inputs:
#   tr_cub_dir - directory containing *.tr.cub (may contain other files too)
#   map_dir    - directory containing the map file (*.map) to use
#   out_dir    - output directory where cubes/ (map.cub) and tif/ will be written + logs/
#
# Behavior:
# - For each <ID>.tr.cub, produces:
#     <out_dir>/cubes/<ID>.map.cub
#     <out_dir>/tif/<ID>.tif
# - Uses the map file:
#     <map_dir>/<ID>_lambert.map
#   If it doesn't exist, the script errors for that ID.
#
# Logging:
# - One shared logfile.
# - Does NOT capture command stdout/stderr into the log.
# - Writes a short "about to run" line before each command.

if [ "$#" -ne 3 ]; then
  echo "Usage: $0 <tr_cub_dir> <map_dir> <out_dir>" >&2
  exit 1
fi

TR_DIR="$1"
MAP_DIR="$2"
OUT="$3"

if [ ! -d "$TR_DIR" ]; then
  echo "ERROR: tr_cub_dir does not exist: $TR_DIR" >&2
  exit 1
fi
if [ ! -d "$MAP_DIR" ]; then
  echo "ERROR: map_dir does not exist: $MAP_DIR" >&2
  exit 1
fi

mkdir -p "$OUT"/{cubes,tif,logs}
LOGFILE="$OUT/logs/stage3_cam2map_to_tif.log"

log_run() { echo "[RUN $(date -Is)] $*" >> "$LOGFILE"; }

# Resolve absolute paths (robust across environments)
resolve_abs() {
  if command -v realpath >/dev/null 2>&1; then
    realpath "$1"
  else
    readlink -f "$1"
  fi
}

# Find *.tr.cub files (top-level), deterministic order
mapfile -d '' -t TR_FILES < <(find "$TR_DIR" -maxdepth 1 -type f -name "*.tr.cub" -print0 | sort -z)

if [ "${#TR_FILES[@]}" -eq 0 ]; then
  echo "ERROR: No *.tr.cub files found in: $TR_DIR" >&2
  exit 1
fi

{
  echo "=== Stage 3: cam2map + gdal_translate (Byte) ==="
  echo "Start: $(date -Is)"
  echo "TR_DIR: $(resolve_abs "$TR_DIR")"
  echo "MAP_DIR: $(resolve_abs "$MAP_DIR")"
  echo "OUT: $(resolve_abs "$OUT")"
  echo "Files: ${#TR_FILES[@]}"
  echo
} >> "$LOGFILE"

for tr in "${TR_FILES[@]}"; do
  # ID = basename without ".tr.cub"
  fname="$(basename "$tr")"
  ID="${fname%.tr.cub}"

  mapfile="$MAP_DIR/lambert.map"
  if [ ! -f "$mapfile" ]; then
    echo "ERROR: Map file not found for ID=$ID: $mapfile" >&2
    echo "Hint: expected <map_dir>/lambert.map" >&2
    exit 2
  fi

  map_cub="$OUT/cubes/${ID}.map.cub"
  out_tif="$OUT/tif/${ID}.tif"

  # 1) cam2map
  log_run "cam2map from=\"$tr\" to=\"$map_cub\" map=\"$mapfile\" pixres=map warpalgorithm=forwardpatch patchsize=50"
  cam2map from="$tr" \
    to="$map_cub" \
    map="$mapfile" \
    pixres=map \
    warpalgorithm=forwardpatch patchsize=50

  # 2) GeoTIFF Byte export
  log_run "gdal_translate -of GTiff -ot Byte -scale -a_nodata 0 \"$map_cub\" \"$out_tif\""
  gdal_translate -of GTiff -ot Byte \
    -scale -a_nodata 0 \
    "$map_cub" \
    "$out_tif"
done

{
  echo
  echo "Done: $(date -Is)"
  echo "=== End Stage 3 ==="
} >> "$LOGFILE"

echo "OK: Processed ${#TR_FILES[@]} file(s)"
echo "GeoTIFFs: $OUT/tif"
echo "Log:      $LOGFILE"
