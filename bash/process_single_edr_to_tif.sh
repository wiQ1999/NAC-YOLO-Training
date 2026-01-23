#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat << 'EOF'
Usage:
  process_single_edr_to_tif.sh -i /input/NAC.IMG -o /output/folder -d /path/to/dem.cub

Required:
  -i, --input     Path to NAC EDR IMG (e.g., M166854798LE.IMG)
  -o, --outdir    Output directory (final .tif goes here)
  -d, --dem       Path to DEM cube (e.g., GLD100+LOLA .demprep.cub).

Notes:
  - Script expects ISIS + GDAL tools available in PATH (activate your conda env first).
  - Removes trailing 'E' from product ID after the first stage (e.g., ...LE -> ...L).

Example:
  ./process_single_edr_to_tif.sh -i ./data/EDR/HQ/M176299749LE.IMG -o ./data/GeoTIFF -d SLDEM.demprep.cub
EOF
}

IN=""
OUTDIR=""
DEM=""
SECONDS=0

# Parse args
while [[ $# -gt 0 ]]; do
  case "$1" in
    -i|--input)   IN="$2"; shift 2 ;;
    -o|--outdir)  OUTDIR="$2"; shift 2 ;;
    -d|--dem)     DEM="$2"; shift 2 ;;
    -h|--help)    usage; exit 0 ;;
    *) echo "Unknown argument: $1"; usage; exit 1 ;;
  esac
done

if [[ -z "$IN" || -z "$OUTDIR" || -z "$DEM" ]]; then
  usage
  exit 1
fi

echo "START: $(date '+%Y-%m-%d %H:%M:%S')"

mkdir -p "$OUTDIR"

# Check required commands
for cmd in lronac2isis spiceinit lronaccal lronacecho cam2map maptemplate trim gdal_translate; do
  command -v "$cmd" >/dev/null 2>&1 || { echo "Missing command in PATH: $cmd"; exit 1; }
done

# Product ID logic: remove extension, then remove trailing 'E' if present
base="$(basename "$IN")"
id="${base%.*}"
if [[ "${id: -1}" == "E" ]]; then
  prod="${id::-1}"
else
  prod="$id"
fi

# Temp dir inside outdir
TMP="$OUTDIR/temp_${prod}"
mkdir -p "$TMP"

RAW="$TMP/${prod}.raw.cub"
CAL="$TMP/${prod}.cal.cub"
ECHO_CUB="$TMP/${prod}.echo.cub"
TRIM_CUB="$TMP/${prod}.tr.cub"
MAP="$TMP/${prod}_lambert.map"
MAP_CUB="$TMP/${prod}.map.cub"
TIF="$OUTDIR/${prod}.tif"

echo "Input : $IN"
echo "Output: $TIF"
echo "DEM   : $DEM"
echo "Temp  : $TMP"

echo "[1/8] lronac2isis -> $RAW"
lronac2isis from="$IN" to="$RAW"

echo "[2/8] spiceinit (web=true, spksmithed=true)"
spiceinit from="$RAW" web=true spksmithed=true shape=user model="$DEM"

echo "[3/8] lronaccal (RadiometricType=IOF) -> $CAL"
lronaccal from="$RAW" to="$CAL" RadiometricType=IOF

# Echo-correction + trim
echo "[4/8] lronacecho -> $ECHO_CUB"
lronacecho from="$CAL" to="$ECHO_CUB"

# Determine L/R from prod suffix
side="${prod: -1}"

# Detect crosstrack summing from labels (default 1 if not found)
summing="$(catlab from="$RAW" 2>/dev/null | grep -m1 -oP 'CROSSTRACK_SUMMING\s*=\s*\K[0-9]+' || true)"
[[ -z "$summing" ]] && summing="1"

# Trim values from LROC NAC guide
if [[ "$side" == "L" ]]; then
left=46; right=26
elif [[ "$side" == "R" ]]; then
left=26; right=46
else
# Fallback if naming is unexpected
left=0; right=0
fi

if [[ "$summing" == "2" ]]; then
left=$(( left / 2 ))
right=$(( right / 2 ))
fi

echo "[5/8] trim (side=$side, summing=$summing, left=$left, right=$right) -> $TRIM_CUB"
trim from="$ECHO_CUB" to="$TRIM_CUB" left="$left" right="$right"

SRC_FOR_MAP="$TRIM_CUB"

echo "[6/8] maptemplate (LambertConformal) -> $MAP"
maptemplate map="$MAP" \
  projection=LAMBERTCONFORMAL \
  clon="-154" clat="-42.1" par1="-42.1" par2="-42.1" \
  targopt=USER targetname=Moon eqradius=1737400 polradius=1737400 \
  lattype=Planetocentric londir=PositiveEast londom="180" \
  rngopt=NONE resopt=NONE

echo "[7/8] cam2map -> $MAP_CUB"
cam2map from="$SRC_FOR_MAP" \
    to="$MAP_CUB" map="$MAP" \
    pixres=CAMERA \
    warpalgorithm=forwardpatch \
    patchsize=4

echo "[8/8] gdal_translate -> $TIF"
gdal_translate -of GTiff -ot Byte -scale "$MAP_CUB" "$TIF"

echo "DONE: $(date '+%Y-%m-%d %H:%M:%S')"
printf "IN TIME: %02d:%02d:%02d\n" $((SECONDS/3600)) $(((SECONDS%3600)/60)) $((SECONDS%60))
