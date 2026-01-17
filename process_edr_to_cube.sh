#!/usr/bin/env bash
set -euo pipefail

# Stage 1: LROC NAC EDR pipeline (per IMG):
#   lronac2isis -> spiceinit (with DEM) -> lronaccal -> lronacecho -> trim
#
# Usage:
#   ./stage1_nac_pipeline.sh <input_img_dir> <output_dir> <dem_cub>
#
# Outputs:
#   <output_dir>/cubes/*.raw.cub
#   <output_dir>/cubes/*.cal.cub
#   <output_dir>/cubes/*.echo.cub
#   <output_dir>/cubes/*.tr.cub
#   <output_dir>/logs/stage1_pipeline.log
#
# Logging:
# - One shared logfile.
# - Does NOT capture command stdout/stderr into the log.
# - Writes a short "about to run" line to the log BEFORE each command.

if [ "$#" -ne 3 ]; then
  echo "Usage: $0 <input_img_dir> <output_dir> <dem_cub>" >&2
  exit 1
fi

IN_DIR="$1"
OUT_DIR="$2"
DEM_CUB="$3"

if [ ! -d "$IN_DIR" ]; then
  echo "ERROR: Input directory does not exist: $IN_DIR" >&2
  exit 1
fi

if [ ! -f "$DEM_CUB" ]; then
  echo "ERROR: DEM cube does not exist: $DEM_CUB" >&2
  exit 1
fi

mkdir -p "$OUT_DIR/cubes" "$OUT_DIR/logs"
LOGFILE="$OUT_DIR/logs/stage1_pipeline.log"

# Find IMG files (case-insensitive), sorted for determinism
mapfile -t IMG_FILES < <(find "$IN_DIR" -maxdepth 1 -type f \( -iname "*.img" \) | sort)

if [ "${#IMG_FILES[@]}" -eq 0 ]; then
  echo "ERROR: No IMG files found in: $IN_DIR" >&2
  exit 1
fi

basename_noext() {
  local p="$1"
  local b
  b="$(basename "$p")"
  echo "${b%.*}"
}

log_run() {
  echo "[RUN $(date -Is)] $*" >> "$LOGFILE"
}

# Determine NAC Left/Right from filename:
# Examples:
#   M176292983LE.IMG -> L (Left)
#   M176292983RE.IMG -> R (Right)
nac_side_from_img() {
  local img_path="$1"
  local base
  base="$(basename_noext "$img_path")"
  # base ends with "...LE" or "...RE" (E = EDR)
  # Take the second-to-last character:
  local n=${#base}
  if [ "$n" -lt 2 ]; then
    echo "UNKNOWN"
    return 0
  fi
  local side="${base: -2:1}"  # second last char
  if [ "$side" = "L" ] || [ "$side" = "R" ]; then
    echo "$side"
    return 0
  fi
  echo "UNKNOWN"
  return 0
}

# Read CROSSTRACK_SUMMING directly from the IMG label (EDR text header)
# User-provided example method.
crosstrack_summing_from_img() {
  local img_path="$1"
  local sum
  sum="$(grep -a "CROSSTRACK_SUMMING" "$img_path" | awk '{print $3}' | tr -d '\r' | head -n 1)"
  if [ -z "$sum" ]; then
    echo "UNKNOWN"
  else
    echo "$sum"
  fi
}

# Start log
{
  echo "=== Stage 1: lronac2isis + spiceinit + lronaccal + lronacecho + trim ==="
  echo "Start: $(date -Is)"
  echo "Input: $IN_DIR"
  echo "Output: $OUT_DIR"
  echo "DEM: $DEM_CUB"
  echo "Files: ${#IMG_FILES[@]}"
  echo
} >> "$LOGFILE"

for img in "${IMG_FILES[@]}"; do
  base="$(basename_noext "$img")"

  raw_cub="$OUT_DIR/cubes/${base}.raw.cub"
  cal_cub="$OUT_DIR/cubes/${base}.cal.cub"
  echo_cub="$OUT_DIR/cubes/${base}.echo.cub"
  tr_cub="$OUT_DIR/cubes/${base}.tr.cub"

  # 1) Import
  log_run "lronac2isis from=\"$img\" to=\"$raw_cub\""
  lronac2isis from="$img" to="$raw_cub"

  # 2) SPICE init (with DEM)
  log_run "spiceinit from=\"$raw_cub\" spksmithed=true spkrecon=false shape=user model=\"$DEM_CUB\" web=true"
  spiceinit from="$raw_cub" spksmithed=true spkrecon=false shape=user model="$DEM_CUB" web=true

  # 3) Radiometric calibration
  log_run "lronaccal from=\"$raw_cub\" to=\"$cal_cub\""
  lronaccal from="$raw_cub" to="$cal_cub"

  # 4) Echo correction
  log_run "lronacecho from=\"$cal_cub\" to=\"$echo_cub\""
  lronacecho from="$cal_cub" to="$echo_cub"

  # 5) Trim (depends on NAC side + summed/non-summed)
  SIDE="$(nac_side_from_img "$img")"
  SUM="$(crosstrack_summing_from_img "$img")"

  # Default (non-summed) trim pairs:
  #  NAC-L: left=46 right=26
  #  NAC-R: left=26 right=46
  # Summed (CROSSTRACK_SUMMING=2): divide by two -> 23 and 13.
  if [ "$SUM" = "2" ]; then
    A=23; B=13
  else
    # Treat UNKNOWN as non-summed unless you prefer to fail hard.
    A=46; B=26
  fi

  if [ "$SIDE" = "L" ]; then
    LEFT="$A"; RIGHT="$B"
  elif [ "$SIDE" = "R" ]; then
    LEFT="$B"; RIGHT="$A"
  else
    echo "ERROR: Cannot determine NAC side (L/R) from filename: $img" >&2
    echo "Expected filename ending with ...L.IMG or ...R.IMG (before extension)." >&2
    exit 2
  fi

  log_run "trim from=\"$echo_cub\" to=\"$tr_cub\" left=$LEFT right=$RIGHT   # SIDE=$SIDE SUM=$SUM"
  trim from="$echo_cub" to="$tr_cub" left="$LEFT" right="$RIGHT"
done

{
  echo
  echo "Done: $(date -Is)"
  echo "=== End Stage 1 ==="
} >> "$LOGFILE"

echo "OK: Processed ${#IMG_FILES[@]} file(s)"
echo "Cubes: $OUT_DIR/cubes"
echo "Log:   $LOGFILE"
