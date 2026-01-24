import argparse
from pathlib import Path
from typing import Iterable, Optional
import numpy as np
import rasterio
from PIL import Image

def _iter_tifs(tiles_dir: Path) -> Iterable[Path]:
    yield from sorted(tiles_dir.glob("*.tif"))
    yield from sorted(tiles_dir.glob("*.tiff"))

def tif8_gray_to_png(tif_path: str | Path,
                     png_path: str | Path,
                     to_rgb: bool = False,
                     fill_nodata_with: int = 0):
    """
    Konwersja 8-bit TIF (1 kanał) do PNG bez zmiany wartości pikseli.
    - to_rgb=False: zapisuje 1-kanałowy PNG (L)
    - to_rgb=True : zapisuje 3-kanałowy PNG (RGB) przez powielenie kanału
    """
    tif_path = Path(tif_path)
    png_path = Path(png_path)
    png_path.parent.mkdir(parents=True, exist_ok=True)

    with rasterio.open(tif_path) as src:
        arr = src.read(1, masked=True)

    if np.ma.isMaskedArray(arr):
        arr = arr.filled(fill_nodata_with)

    arr = np.asarray(arr, dtype=np.uint8)

    if to_rgb:
        rgb = np.stack([arr, arr, arr], axis=-1)
        Image.fromarray(rgb, mode="RGB").save(png_path)
    else:
        Image.fromarray(arr, mode="L").save(png_path)

def batch_convert(input_dir: str | Path,
                  output_dir: str | Path,
                  to_rgb: bool = False):
    input_dir = Path(input_dir)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    tiles = list(_iter_tifs(input_dir))
    if not tiles:
        raise FileNotFoundError(f"Brak plików .tif/.tiff w: {input_dir}")

    for tif in tiles:
        out = output_dir / (tif.stem + ".png")
        tif8_gray_to_png(tif, out, to_rgb=to_rgb)


def _build_argparser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Konwertowanie plików TIF do formatu PNG.")
    p.add_argument("-i", "--input", type=Path, required=True, help="Folder z kafelkami .tif/.tiff.")
    p.add_argument("-o", "--output", type=Path, required=True, help="Folder wyjściowy dla plików .png.")
    return p


def main(argv: Optional[Iterable[str]] = None) -> int:
    args = _build_argparser().parse_args(argv)
    batch_convert(
        input_dir=args.input,
        output_dir=args.output,
        to_rgb=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
