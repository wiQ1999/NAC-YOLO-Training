from pathlib import Path
import numpy as np
import rasterio
from PIL import Image

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
        # masked=True -> jeśli istnieje maska/NoData, dostaniesz masked array
        arr = src.read(1, masked=True)

    if np.ma.isMaskedArray(arr):
        arr = arr.filled(fill_nodata_with)

    # upewnij się, że to uint8
    arr = np.asarray(arr, dtype=np.uint8)

    if to_rgb:
        rgb = np.stack([arr, arr, arr], axis=-1)  # HxWx3
        Image.fromarray(rgb, mode="RGB").save(png_path)
    else:
        Image.fromarray(arr, mode="L").save(png_path)

def batch_convert(input_dir: str | Path,
                  output_dir: str | Path,
                  pattern: str = "*.tif",
                  to_rgb: bool = False):
    input_dir = Path(input_dir)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    for tif in sorted(input_dir.glob(pattern)):
        out = output_dir / (tif.stem + ".png")
        tif8_gray_to_png(tif, out, to_rgb=to_rgb)


batch_convert(
    input_dir=r"E:\WSB\Praca_Magisterska_2\Skrypty\NAC YOLO Training\datasets\M166854798L\train_tif", 
    output_dir=r"E:\WSB\Praca_Magisterska_2\Skrypty\NAC YOLO Training\datasets\M166854798L\train_png", 
    to_rgb=True)
