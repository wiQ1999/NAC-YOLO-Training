from __future__ import annotations

from pathlib import Path
from typing import Optional, Tuple

import numpy as np
from osgeo import gdal


def _valid_bounds(
    mask_band: gdal.Band,
    xsize: int,
    ysize: int,
    chunk_h: int = 1024,
) -> Tuple[int, int, int, int]:
    x0, y0, x1, y1 = xsize, ysize, -1, -1

    for y in range(0, ysize, chunk_h):
        h = min(chunk_h, ysize - y)
        m = mask_band.ReadAsArray(0, y, xsize, h)
        if m is None:
            return 0, 0, xsize - 1, ysize - 1

        v = m != 0
        if not v.any():
            continue

        rows = np.where(v.any(axis=1))[0]
        cols = np.where(v.any(axis=0))[0]

        y0 = min(y0, y + int(rows[0]))
        y1 = max(y1, y + int(rows[-1]))
        x0 = min(x0, int(cols[0]))
        x1 = max(x1, int(cols[-1]))

    if x1 < 0 or y1 < 0:
        raise RuntimeError("Nie znaleziono pikseli z danymi (maska jest pusta).")

    return x0, y0, x1, y1


def _row_masks(
    mask_band: gdal.Band,
    x0: int,
    x_end: int,
    yoff: int,
    tile_size: int,
) -> Tuple[np.ndarray, np.ndarray]:
    w = x_end - x0
    top = mask_band.ReadAsArray(x0, yoff, w, 1)
    bottom = mask_band.ReadAsArray(x0, yoff + tile_size - 1, w, 1)
    if top is None or bottom is None:
        raise RuntimeError("Nie można odczytać maski z rastra.")
    return top[0], bottom[0]


def _corners_ok(
    top: np.ndarray,
    bottom: np.ndarray,
    x0: int,
    xoff: int,
    tile_size: int,
) -> bool:
    i = xoff - x0
    j = i + tile_size - 1
    return (top[i] != 0) and (top[j] != 0) and (bottom[i] != 0) and (bottom[j] != 0)


def _find_first_x(
    top: np.ndarray,
    bottom: np.ndarray,
    x0: int,
    x_end: int,
    tile_size: int,
) -> Optional[int]:
    last = x_end - tile_size
    for xoff in range(x0, last + 1):
        if _corners_ok(top, bottom, x0, xoff, tile_size):
            return xoff
    return None


def cut_square_tiles(
    input_tif: str | Path,
    output_dir: str | Path,
    tile_size: int,
) -> int:
    gdal.UseExceptions()

    in_path = Path(input_tif)
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    ds = gdal.Open(str(in_path), gdal.GA_ReadOnly)
    if ds is None:
        raise RuntimeError(f"Nie można otworzyć pliku: {in_path}")

    xsize, ysize = ds.RasterXSize, ds.RasterYSize
    bands = ds.RasterCount
    if tile_size <= 0:
        raise ValueError("tile_size musi być > 0")
    if bands < 1:
        raise RuntimeError("Raster nie zawiera pasm.")

    band1 = ds.GetRasterBand(1)
    mask_band = band1.GetMaskBand()

    x0, y0, x1, y1 = _valid_bounds(mask_band, xsize, ysize)
    x_end, y_end = x1 + 1, y1 + 1

    base = in_path.stem
    written = 0

    y_max = y_end - tile_size
    y_start = None
    for y in range(y0, y_max + 1):
        top, bottom = _row_masks(mask_band, x0, x_end, y, tile_size)
        if _find_first_x(top, bottom, x0, x_end, tile_size) is not None:
            y_start = y
            break

    if y_start is None:
        ds = None
        return 0

    for yoff in range(y_start, y_max + 1, tile_size):
        top, bottom = _row_masks(mask_band, x0, x_end, yoff, tile_size)
        x_start = _find_first_x(top, bottom, x0, x_end, tile_size)
        if x_start is None:
            continue

        for xoff in range(x_start, x_end - tile_size + 1, tile_size):
            if not _corners_ok(top, bottom, x0, xoff, tile_size):
                continue

            out_name = f"{base}_{tile_size}_y{yoff}_x{xoff}.tif"
            out_path = out_dir / out_name

            opts = gdal.TranslateOptions(
                format="GTiff",
                srcWin=[xoff, yoff, tile_size, tile_size],
                bandList=list(range(1, bands + 1)),
                outputType=band1.DataType,
            )
            out_ds = gdal.Translate(str(out_path), ds, options=opts)
            if out_ds is None:
                raise RuntimeError(f"GDAL Translate nie powiodło się dla: {out_path}")
            out_ds = None
            written += 1

    ds = None
    return written


def _parse_args():
    import argparse

    p = argparse.ArgumentParser()
    p.add_argument("-i", "--input", required=True, help="Plik w formacie .tif/.tiff.")
    p.add_argument("-o", "--output", required=True, help="Katalog docelowy na kafelki.")
    p.add_argument("-s", "--size", type=int, required=True, help="Rozmiar kafelka (piksele).")
    return p.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    n = cut_square_tiles(args.input, args.output, args.size)
    print(f"Zapisano {n} kafelków do: {args.output}")
