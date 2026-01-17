#!/usr/bin/env bash
set -euo pipefail

# Build a list of absolute paths to *.tr.cub files in a directory and run maptemplate on that list.
#
# Usage:
#   ./stage2_maptemplate_pair.sh <cub_dir> <out_dir_for_map>
#
# Inputs:
#   cub_dir         - directory containing *.tr.cub (and possibly other files)
#   out_dir_for_map - output directory where maps/ and logs/ will be created
#
# Outputs:
#   <out_dir_for_map>/lists/LIST.lis
#   <out_dir_for_map>/maps/<ID>_lambert.map
#   <out_dir_for_map>/logs/stage2_maptemplate.log

if [ "$#" -ne 2 ]; then
  echo "Usage: $0 <cub_dir> <out_dir_for_map>" >&2
  exit 1
fi

CUB_DIR="$1"
OUT="$2"

if [ ! -d "$CUB_DIR" ]; then
  echo "ERROR: cub_dir does not exist: $CUB_DIR" >&2
  exit 1
fi

mkdir -p "$OUT"/{lists,maps,logs}
LOGFILE="$OUT/logs/stage2_maptemplate.log"

# Generate list of absolute paths to *.tr.cub (only files in the top-level of CUB_DIR)
LISTFILE="$OUT/lists/LIST.lis"
: > "$LISTFILE"

# Use find with -print0 to be robust to spaces; then resolve absolute paths.
# Prefer realpath; fallback to readlink -f if needed.
resolve_abs() {
  if command -v realpath >/dev/null 2>&1; then
    realpath "$1"
  else
    readlink -f "$1"
  fi
}

mapfile -d '' -t TR_FILES < <(find "$CUB_DIR" -maxdepth 1 -type f -name "*.tr.cub" -print0 | sort -z)

if [ "${#TR_FILES[@]}" -eq 0 ]; then
  echo "ERROR: No *.tr.cub files found in: $CUB_DIR" >&2
  exit 1
fi

for f in "${TR_FILES[@]}"; do
  resolve_abs "$f" >> "$LISTFILE"
done

MAPFILE="$OUT/maps/lambert.map"

# Log only "about to run" (do not pipe command output into the log)
{
  echo "=== Stage 2: maptemplate ==="
  echo "Start: $(date -Is)"
  echo "CUB_DIR: $CUB_DIR"
  echo "OUT: $OUT"
  echo "LISTFILE: $LISTFILE"
  echo "MAPFILE: $MAPFILE"
  echo "Files: ${#TR_FILES[@]}"
  echo "[RUN $(date -Is)] maptemplate map=\"$MAPFILE\" projection=LAMBERTCONFORMAL clon=-154 clat=-42.1 par1=-42.1 par2=-42.1 targopt=USER targetname=Moon eqradius=1737400 polradius=1737400 lattype=Planetocentric londir=PositiveEast londom=180 rngopt=CALC fromlist=\"$LISTFILE\" resopt=CAMERA"
} >> "$LOGFILE"

maptemplate map="$MAPFILE" \
  projection=LAMBERTCONFORMAL \
  clon=-154 clat=-42.1 par1=-42.1 par2=-42.1 \
  targopt=USER targetname=Moon eqradius=1737400 polradius=1737400 \
  lattype=Planetocentric londir=PositiveEast londom=180 \
  rngopt=CALC fromlist="$LISTFILE" \
  resopt=CALC

{
  echo "Done: $(date -Is)"
  echo "=== End Stage 2 ==="
} >> "$LOGFILE"

echo "OK:"
echo "  List: $LISTFILE"
echo "  Map:  $MAPFILE"
echo "  Log:  $LOGFILE"
