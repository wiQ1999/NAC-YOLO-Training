"""
Simple GDAL tile cutter for GeoTIFF (Float32).
- Cuts each input .tif independently (no global grid)
- No overlap, no padding, no filtering of empty tiles
- Default tile size: 640x640
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path
from osgeo import gdal


def cut_tiles_gdal(
    input_tif: str | Path,
    output_dir: str | Path,
    tile_width: int = 640,
    tile_height: int = 640,
) -> None:
    in_path = Path(input_tif)
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    ds = gdal.Open(str(in_path), gdal.GA_ReadOnly)
    if ds is None:
        raise RuntimeError(f"Cannot open input GeoTIFF: {in_path}")

    xsize = ds.RasterXSize
    ysize = ds.RasterYSize
    bands = ds.RasterCount

    base = in_path.stem

    # Loop in pixel coordinates, no overlap, discard remainder at right/bottom edges
    tile_idx = 0
    for yoff in range(0, ysize - tile_height + 1, tile_height):
        for xoff in range(0, xsize - tile_width + 1, tile_width):
            out_name = f"{base}_x{xoff}_y{yoff}_w{tile_width}_h{tile_height}.tif"
            out_path = out_dir / out_name

            # Use GDAL Translate to window-crop the tile
            translate_opts = gdal.TranslateOptions(
                format="GTiff",
                srcWin=[xoff, yoff, tile_width, tile_height],
                bandList=list(range(1, bands + 1)),
                outputType=gdal.GDT_Float32,  # keep Float32
            )

            out_ds = gdal.Translate(destName=str(out_path), srcDS=ds, options=translate_opts)
            if out_ds is None:
                raise RuntimeError(f"GDAL Translate failed for tile: {out_path}")
            out_ds = None  # close

            tile_idx += 1

    ds = None  # close
    print(f"Done. Wrote {tile_idx} tiles to: {out_dir}")


def main() -> None:
    cut_tiles_gdal(
        input_tif="E:\\WSB\\Praca_Magisterska_2\\Maps\\CE-5\\processed-multiple-into-one\\tif\\M166222068L.map.tif",
        output_dir="E:\\WSB\\Praca_Magisterska_2\\Maps\\CE-5\\processed-multiple-into-one\\tif\\tiles",
        tile_width=640,
        tile_height=640,
    )


if __name__ == "__main__":
    gdal.UseExceptions()
    main()
