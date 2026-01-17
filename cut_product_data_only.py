from __future__ import annotations

from pathlib import Path
from osgeo import gdal


def cut_tiles_skip_empty(
    input_tif: str | Path,
    output_dir: str | Path,
    tile_width: int,
    tile_height: int,
) -> None:
    """
    Cut tiles from a single GeoTIFF. Skip any tile that contains pixels outside the product
    (detected via GDAL validity mask / NoData mask).

    - No overlap
    - No padding
    - Skips tiles where mask has any invalid pixels (mask == 0)
    - Discards partial tiles at right/bottom edges
    """
    gdal.UseExceptions()

    in_path = Path(input_tif)
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    ds = gdal.Open(str(in_path), gdal.GA_ReadOnly)
    if ds is None:
        raise RuntimeError(f"Cannot open input GeoTIFF: {in_path}")

    xsize, ysize = ds.RasterXSize, ds.RasterYSize
    bands = ds.RasterCount
    base = in_path.stem

    # Use the dataset mask from band 1 (typically encodes NoData/outside-product regions)
    band1 = ds.GetRasterBand(1)
    mask_band = band1.GetMaskBand()

    tile_idx = 0
    for yoff in range(0, ysize - tile_height + 1, tile_height):
        for xoff in range(0, xsize - tile_width + 1, tile_width):
            mask = mask_band.ReadAsArray(xoff, yoff, tile_width, tile_height)

            # If ANY pixel is invalid (0), skip this tile
            # (Mask is usually 255 for valid pixels, 0 for invalid)
            if mask is not None and (mask == 0).any():
                continue

            out_name = f"{base}_x{xoff}_y{yoff}_w{tile_width}_h{tile_height}.tif"
            out_path = out_dir / out_name

            translate_opts = gdal.TranslateOptions(
                format="GTiff",
                srcWin=[xoff, yoff, tile_width, tile_height],
                bandList=list(range(1, bands + 1)),
                outputType=gdal.GDT_Byte,
            )
            out_ds = gdal.Translate(str(out_path), ds, options=translate_opts)
            if out_ds is None:
                raise RuntimeError(f"GDAL Translate failed for tile: {out_path}")
            out_ds = None
            tile_idx += 1

    ds = None
    print(f"Done. Wrote {tile_idx} tiles to: {out_dir}")


if __name__ == "__main__":
    cut_tiles_skip_empty(
        input_tif=r"E:\WSB\Praca_Magisterska_2\Maps\CE-6\processed_M166854798L_sldem2015\tif\M166854798L_lambert_sldem2015_8bit_georef_linear.tif",
        output_dir=r"E:\WSB\Praca_Magisterska_2\Skrypty\NAC YOLO Training\datasets\M166854798L\train",
        tile_width=640, 
        tile_height=640)

    pass
