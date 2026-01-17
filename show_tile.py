from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
from osgeo import gdal


def show_tile(tile_tif: str | Path, band: int = 1) -> None:
    """
    Display a single tile GeoTIFF using matplotlib.

    Args:
        tile_tif: path to tile .tif
        band: 1-based band index to display (default: 1)
    """
    gdal.UseExceptions()

    tile_path = Path(tile_tif)
    ds = gdal.Open(str(tile_path), gdal.GA_ReadOnly)
    if ds is None:
        raise RuntimeError(f"Cannot open tile GeoTIFF: {tile_path}")

    if band < 1 or band > ds.RasterCount:
        raise ValueError(f"band must be in [1, {ds.RasterCount}], got {band}")

    arr = ds.GetRasterBand(band).ReadAsArray()
    ds = None

    if arr is None:
        raise RuntimeError("Failed to read raster data from tile")

    plt.figure()
    plt.imshow(arr)
    plt.title(f"{tile_path.name} (band {band})")
    plt.axis("off")
    plt.show()


if __name__ == "__main__":
    show_tile(
        tile_tif="E:\\WSB\\Praca_Magisterska_2\\Maps\\CE-5\\processed-multiple-into-one\\tif\\tiles\\M166222068L.map_x640_y640_w640_h640.tif", 
        band=1
    )

    pass
