from __future__ import annotations

import argparse
from pathlib import Path
from typing import Iterable, Optional, Tuple

import geopandas as gpd
import rasterio
from shapely.geometry import Point, box
from shapely.errors import GEOSException

CLASS_ID = 0
DIAM_FIELD = "Diam_km"
DIAM_UNIT = "km"


def _ensure_dir(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)


def _clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


def _world_to_pixel(inv_transform, x: float, y: float) -> Tuple[float, float]:
    col, row = inv_transform * (x, y)
    return float(col), float(row)


def _iter_tifs(tiles_dir: Path) -> Iterable[Path]:
    yield from sorted(tiles_dir.glob("*.tif"))
    yield from sorted(tiles_dir.glob("*.tiff"))


def _coverage_ratio(geom, inter) -> float:
    a0 = float(getattr(geom, "area", 0.0) or 0.0)
    a1 = float(getattr(inter, "area", 0.0) or 0.0)
    if a0 > 1e-12:
        return a1 / a0
    e0 = geom.envelope
    e1 = inter.envelope
    a0b = float(getattr(e0, "area", 0.0) or 0.0)
    a1b = float(getattr(e1, "area", 0.0) or 0.0)
    return (a1b / a0b) if a0b > 1e-12 else 0.0


def _prepare_gdf(
    shp_path: Path,
    tiles_crs
) -> gpd.GeoDataFrame:
    gdf = gpd.read_file(shp_path)
    if gdf.empty:
        raise ValueError("Plik SHP/GPKG nie zawiera obiektów.")

    if gdf.crs is None:
        raise ValueError("Warstwa wektorowa nie ma CRS. Uzupełnij CRS przed generacją etykiet.")

    if tiles_crs is None:
        raise ValueError("Kafelki nie mają CRS. Napraw georeferencję przed generacją etykiet.")

    if gdf.crs != tiles_crs:
        raise ValueError("CRS warstwy i kafelków różni się. Wyrównaj CRS przed uruchomieniem skryptu.")

    if "x_coord" in gdf.columns and "y_coord" in gdf.columns:
        if gdf.geometry is None or gdf.geometry.is_empty.all():
            xs = gdf["x_coord"].astype(float)
            ys = gdf["y_coord"].astype(float)
            gdf = gdf.copy()
            gdf["geometry"] = [Point(x, y) for x, y in zip(xs, ys)]

    is_point = gdf.geometry.geom_type.isin(["Point", "MultiPoint"]).all()
    if is_point and DIAM_FIELD in gdf.columns:
        scale = 1000.0 if DIAM_UNIT == "km" else 1.0
        r = (gdf[DIAM_FIELD].astype(float) * scale) / 2.0
        gdf = gdf.copy()
        gdf["geometry"] = gdf.geometry.buffer(r)

    return gdf


def process_tiles(
    tiles_dir: Path,
    shp_path: Path,
    out_dir: Path,
    min_coverage: float
) -> None:
    if not (0.0 <= min_coverage <= 1.0):
        raise ValueError("min_coverage musi być w zakresie [0, 1].")

    tiles = list(_iter_tifs(tiles_dir))
    if not tiles:
        raise FileNotFoundError(f"Brak plików .tif/.tiff w: {tiles_dir}")

    _ensure_dir(out_dir)

    with rasterio.open(tiles[0]) as src0:
        tiles_crs = src0.crs

    gdf = _prepare_gdf(
        shp_path=shp_path,
        tiles_crs=tiles_crs
    )

    sindex = gdf.sindex

    for tile_path in tiles:
        with rasterio.open(tile_path) as src:
            if src.crs != tiles_crs:
                raise ValueError(f"Różne CRS kafelków: {tile_path.name}")

            w, h = src.width, src.height
            tile_poly = box(*src.bounds)
            inv = ~src.transform

            cand_idx = list(sindex.query(tile_poly, predicate="intersects"))
            subset = gdf.iloc[cand_idx]

            yolo_lines = []
            for geom in subset.geometry:
                if geom is None or geom.is_empty:
                    continue

                if not geom.is_valid:
                    try:
                        geom = geom.buffer(0)
                    except GEOSException:
                        continue

                try:
                    inter = geom.intersection(tile_poly)
                except GEOSException:
                    continue

                if inter.is_empty:
                    continue

                cov = _coverage_ratio(geom, inter)
                if cov < min_coverage:
                    continue

                minx, miny, maxx, maxy = inter.bounds
                c1, r1 = _world_to_pixel(inv, minx, maxy)
                c2, r2 = _world_to_pixel(inv, maxx, miny)

                col_min, col_max = sorted((c1, c2))
                row_min, row_max = sorted((r1, r2))

                col_min = _clamp(col_min, 0.0, float(w))
                col_max = _clamp(col_max, 0.0, float(w))
                row_min = _clamp(row_min, 0.0, float(h))
                row_max = _clamp(row_max, 0.0, float(h))

                bw = col_max - col_min
                bh = row_max - row_min
                if bw <= 1e-6 or bh <= 1e-6:
                    continue

                x_c = (col_min + col_max) / 2.0 / w
                y_c = (row_min + row_max) / 2.0 / h
                w_n = bw / w
                h_n = bh / h

                yolo_lines.append(f"{CLASS_ID} {x_c:.6f} {y_c:.6f} {w_n:.6f} {h_n:.6f}")

        out_txt = out_dir / f"{tile_path.stem}.txt"
        out_txt.write_text("\n".join(yolo_lines), encoding="utf-8")
        print(f"{tile_path.name}: {len(yolo_lines)} -> {out_txt.name}")


def _build_argparser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Generowanie etykiet YOLO dla kafelków TIF na podstawie SHP/GPKG.")
    p.add_argument("-i", "--input", type=Path, required=True, help="Folder z kafelkami .tif/.tiff.")
    p.add_argument("-o", "--output", type=Path, required=True, help="Folder wyjściowy dla plików .txt.")
    p.add_argument("-s", "--shp", type=Path, required=True, help="Ścieżka do SHP/GPKG z kraterami.")
    p.add_argument("-c", "--min-coverage", type=float, required=True, help="Minimalny udział powierzchni etykiety na kafelku [0..1].")
    return p


def main(argv: Optional[Iterable[str]] = None) -> int:
    args = _build_argparser().parse_args(argv)
    process_tiles(
        tiles_dir=args.input,
        out_dir=args.output,
        shp_path=args.shp,
        min_coverage=args.min_coverage
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
