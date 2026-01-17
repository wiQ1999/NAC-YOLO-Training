from pathlib import Path

import geopandas as gpd
import rasterio
from shapely.geometry import box

# -----------------------------
# KONFIGURACJA
# -----------------------------
TILES_DIR = Path(r"E:\WSB\Praca_Magisterska_2\Skrypty\NAC YOLO Training\datasets\M176299749L_480x480\images\train_tif")          # katalog z kafelkami .tif
SHP_PATH  = Path(r"E:\WSB\Praca_Magisterska_2\Datasets\YOLOv8-LCNET\CE6_S1_3m_crater_larger30m — kopia.shp")# SHP już przycięty do całego TIF (krok 1)
OUT_DIR   = Path(r"E:\WSB\Praca_Magisterska_2\Skrypty\NAC YOLO Training\datasets\M176299749L_480x480\labels\train_png")        # gdzie zapisać .txt

CLASS_ID = 0                             # jedna klasa: crater

# Jeśli SHP zawiera PUNKTY + średnicę, ustaw:
DIAM_FIELD = None        # np. "Diam_km" albo "diam_m"
DIAM_UNIT  = "km"        # "km" lub "m" (istotne tylko jeśli DIAM_FIELD != None)

# -----------------------------
# POMOCNICZE
# -----------------------------
def ensure_dir(p: Path):
    p.mkdir(parents=True, exist_ok=True)

def world_to_pixel(inv_transform, x, y):
    """Zwraca (col, row) jako float."""
    col, row = inv_transform * (x, y)
    return float(col), float(row)

def clamp(v, lo, hi):
    return max(lo, min(hi, v))

# -----------------------------
# GŁÓWNY PIPELINE
# -----------------------------
def main():
    ensure_dir(OUT_DIR)

    gdf = gpd.read_file(SHP_PATH)
    if gdf.empty:
        raise ValueError("SHP jest pusty (brak obiektów).")

    # Wczytaj pierwszy kafelek tylko po to, by znać CRS kafelków (zwykle wszystkie są identyczne)
    first_tile = next(TILES_DIR.glob("*.tif"), None)
    if first_tile is None:
        raise FileNotFoundError(f"Brak .tif w {TILES_DIR}")

    with rasterio.open(first_tile) as src0:
        tiles_crs = src0.crs
        if tiles_crs is None:
            raise ValueError("Kafelek nie ma CRS. Dodaj/napraw georeferencję przed generacją labeli.")

    # Reprojekcja SHP do CRS kafelków (jeśli trzeba)
    if gdf.crs != tiles_crs:
        gdf = gdf.to_crs(tiles_crs)

    # Jeśli geometrie to PUNKTY + średnica, zamień punkty na okręgi (buffer)
    # Uwaga: bufor ma sens tylko w metrycznym CRS (nie w stopniach).
    if DIAM_FIELD is not None:
        if DIAM_FIELD not in gdf.columns:
            raise ValueError(f"Nie ma kolumny {DIAM_FIELD} w SHP.")
        scale = 1000.0 if DIAM_UNIT.lower() == "km" else 1.0
        radius = (gdf[DIAM_FIELD].astype(float) * scale) / 2.0
        gdf = gdf.copy()
        gdf["geometry"] = gdf.geometry.buffer(radius)

    # Spatial index dla szybkości
    sindex = gdf.sindex

    # Przetwarzanie kafelków
    for tile_path in sorted(TILES_DIR.glob("*.tif")):
        with rasterio.open(tile_path) as src:
            W, H = src.width, src.height
            tile_poly = box(*src.bounds)
            inv = ~src.transform

            # Kandydaci przez spatial index
            cand_idx = list(sindex.query(tile_poly, predicate="intersects"))
            subset = gdf.iloc[cand_idx]

            yolo_lines = []

            for geom in subset.geometry:
                if geom is None or geom.is_empty:
                    continue

                # Przytnij geometrię do kafelka (żeby bbox nie wychodził poza kafelek)
                gi = geom.intersection(tile_poly)
                if gi.is_empty:
                    continue

                minx, miny, maxx, maxy = gi.bounds

                # Bounds -> piksele (col/row jako float)
                c1, r1 = world_to_pixel(inv, minx, maxy)  # lewy-górny
                c2, r2 = world_to_pixel(inv, maxx, miny)  # prawy-dolny

                col_min, col_max = sorted([c1, c2])
                row_min, row_max = sorted([r1, r2])

                # Clamp do rozmiaru obrazu
                col_min = clamp(col_min, 0.0, W)
                col_max = clamp(col_max, 0.0, W)
                row_min = clamp(row_min, 0.0, H)
                row_max = clamp(row_max, 0.0, H)

                bw = col_max - col_min
                bh = row_max - row_min
                if bw <= 1e-6 or bh <= 1e-6:
                    continue

                # YOLO: znormalizowane do [0,1]
                x_c = (col_min + col_max) / 2.0 / W
                y_c = (row_min + row_max) / 2.0 / H
                w_n = bw / W
                h_n = bh / H

                yolo_lines.append(f"{CLASS_ID} {x_c:.6f} {y_c:.6f} {w_n:.6f} {h_n:.6f}")

        out_txt = OUT_DIR / (tile_path.stem + ".txt")
        out_txt.write_text("\n".join(yolo_lines), encoding="utf-8")
        print(f"{tile_path.name}: {len(yolo_lines)} bbox -> {out_txt.name}")

if __name__ == "__main__":
    main()
