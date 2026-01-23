#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat << 'EOF'
Usage:
  batch_process_nac.sh -i /input/folder -o /output/folder -dem /path/to/dem.cub -s /path/to/process_nac_edr_to_tif.sh

Required:
  -i, --input-dir    Folder containing .IMG files
  -o, --outdir       Output directory for all processed files
  -dem               Path to DEM cube
  -s, --script       Path to the single-file processing script

Example:
  ./batch_process_nac.sh -i ./data -o ./results -d moon.cub -s ./process_nac_edr_to_tif.sh
EOF
}

IN_DIR=""
OUT_DIR=""
DEM_PATH=""
SCRIPT_PATH=""

# Parsowanie argumentów
while [[ $# -gt 0 ]]; do
  case "$1" in
    -i|--input-dir) IN_DIR="$2"; shift 2 ;;
    -o|--outdir)    OUT_DIR="$2"; shift 2 ;;
    -d|--dem)       DEM_PATH="$2"; shift 2 ;;
    -s|--script)    SCRIPT_PATH="$2"; shift 2 ;;
    -h|--help)      usage; exit 0 ;;
    *) echo "Unknown argument: $1"; usage; exit 1 ;;
  esac
done

# Walidacja wymaganych argumentów
if [[ -z "$IN_DIR" || -z "$OUT_DIR" || -z "$DEM_PATH" || -z "$SCRIPT_PATH" ]]; then
  echo "Error: Missing required arguments."
  usage
  exit 1
fi

# Walidacja istnienia skryptu przetwarzającego
if [[ ! -f "$SCRIPT_PATH" ]]; then
    echo "Error: Processing script not found at: $SCRIPT_PATH"
    exit 1
fi

# Tworzenie folderu wyjściowego, jeśli nie istnieje
mkdir -p "$OUT_DIR"

echo "=========================================="
echo " Starting Batch Processing"
echo " Input Dir : $IN_DIR"
echo " Output Dir: $OUT_DIR"
echo " DEM       : $DEM_PATH"
echo " Script    : $SCRIPT_PATH"
echo "=========================================="

# Włącz obsługę braku dopasowania (nullglob), aby *.IMG nie zwracało błędu jeśli brak plików
shopt -s nullglob

# Znajdź wszystkie pliki .IMG oraz .img
files=("$IN_DIR"/*.IMG "$IN_DIR"/*.img)

# Policz pliki
num_files=${#files[@]}

if [[ "$num_files" -eq 0 ]]; then
    echo "No .IMG files found in $IN_DIR"
    exit 0
fi

echo "Found $num_files .IMG files to process."
echo "------------------------------------------"

# Pętla po plikach
current=1
for file in "${files[@]}"; do
    filename=$(basename "$file")
    
    echo ">>> [File $current of $num_files] Processing: $filename"
    
    # Wywołanie skryptu pojedyńczego przetwarzającego
    bash "$SCRIPT_PATH" -i "$file" -o "$OUT_DIR" -dem "$DEM_PATH"
    
    echo ">>> Finished: $filename"
    echo "------------------------------------------"
    
    ((current++))
done

echo "ALL DONE. Processed $num_files files."
