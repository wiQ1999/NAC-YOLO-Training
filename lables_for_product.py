from __future__ import annotations

from pathlib import Path
import math

import pandas as pd
from osgeo import gdal


LUNAR_RADIUS_KM = 1737.4
CLASS_ID = 0  # jedna klasa: crater


def load_craters_csv(csv_path: str | Path) -> pd.DataFrame:
    df = pd.read_csv(csv_path)
    required = {"x_coord", "y_coord", "Diam_km"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"CSV missing columns: {missing}")
    return df[["x_coord", "y_coord", "Diam_km"]].copy()


def dataset_bounds_lonlat(ds: gdal.Dataset) -> tuple[float, float, float, float]:
    gt = ds.GetGeoTransform()
    w = ds.RasterXSize
    h = ds.RasterYSize

    corners_px = [(0, 0), (w, 0), (w, h), (0, h)]
    corners_xy = [gdal.ApplyGeoTransform(gt, px, py) for px, py in corners_px]

    xs = [c[0] for c in corners_xy]
    ys = [c[1] for c in corners_xy]
    return min(xs), max(xs), min(ys), max(ys)


def lonlat_diameter_to_deg(lat: float, diam_km: float) -> tuple[float, float]:
    deg_per_km_lat = 180.0 / (math.pi * LUNAR_RADIUS_KM)
    diam_lat_deg = diam_km * deg_per_km_lat

    cos_lat = math.cos(math.radians(lat))
    if cos_lat < 1e-8:
        diam_lon_deg = diam_lat_deg
    else:
        deg_per_km_lon = 180.0 / (math.pi * LUNAR_RADIUS_KM * cos_lat)
        diam_lon_deg = diam_km * deg_per_km_lon

    return diam_lon_deg, diam_lat_deg


def invert_geotransform(gt):
    """
    Return inverse geotransform as a 6-tuple.
    Compatible with both GDAL variants:
    - returns (ok, inv_gt)
    - returns inv_gt directly (6 numbers)
    """
    res = gdal.InvGeoTransform(gt)

    # Variant A: (ok, inv_gt)
    if isinstance(res, tuple) and len(res) == 2 and isinstance(res[0], (bool, int)):
        ok, inv_gt = res
        if not ok or inv_gt is None:
            raise RuntimeError("Cannot invert geotransform (GDAL returned ok=False).")
        return inv_gt

    # Variant B: inv_gt directly (6 numbers)
    if isinstance(res, tuple) and len(res) == 6:
        return res

    raise RuntimeError(f"Unexpected return from gdal.InvGeoTransform: {res!r}")


def world_to_pixel(inv_gt, x: float, y: float) -> tuple[float, float]:
    px, py = gdal.ApplyGeoTransform(inv_gt, x, y)
    return px, py


def write_yolo_labels_for_tiles(tiles_dir: str | Path, csv_path: str | Path, labels_dir: str | Path) -> None:
    gdal.UseExceptions()

    tiles_dir = Path(tiles_dir)
    labels_dir = Path(labels_dir)
    labels_dir.mkdir(parents=True, exist_ok=True)

    df = load_craters_csv(csv_path)

    tif_paths = sorted(tiles_dir.glob("*.tif"))
    if not tif_paths:
        raise FileNotFoundError(f"No .tif files found in: {tiles_dir}")

    for tif_path in tif_paths:
        ds = gdal.Open(str(tif_path), gdal.GA_ReadOnly)
        if ds is None:
            raise RuntimeError(f"Cannot open tile: {tif_path}")

        gt = ds.GetGeoTransform()
        inv_gt = invert_geotransform(gt)

        w = ds.RasterXSize
        h = ds.RasterYSize

        xmin, xmax, ymin, ymax = dataset_bounds_lonlat(ds)

        in_tile = df[
            (df["x_coord"] >= xmin) & (df["x_coord"] <= xmax) &
            (df["y_coord"] >= ymin) & (df["y_coord"] <= ymax)
        ]

        lines: list[str] = []

        for lon, lat, diam_km in in_tile.itertuples(index=False, name=None):
            lon = float(lon)
            lat = float(lat)
            diam_km = float(diam_km)

            cx, cy = world_to_pixel(inv_gt, lon, lat)
            if not (0.0 <= cx < w and 0.0 <= cy < h):
                continue

            diam_lon_deg, diam_lat_deg = lonlat_diameter_to_deg(lat, diam_km)

            left_px, _ = world_to_pixel(inv_gt, lon - diam_lon_deg / 2.0, lat)
            right_px, _ = world_to_pixel(inv_gt, lon + diam_lon_deg / 2.0, lat)
            _, top_py = world_to_pixel(inv_gt, lon, lat + diam_lat_deg / 2.0)
            _, bottom_py = world_to_pixel(inv_gt, lon, lat - diam_lat_deg / 2.0)

            bw = abs(right_px - left_px)
            bh = abs(bottom_py - top_py)

            x_min = max(0.0, cx - bw / 2.0)
            x_max = min(float(w), cx + bw / 2.0)
            y_min = max(0.0, cy - bh / 2.0)
            y_max = min(float(h), cy + bh / 2.0)

            bw2 = x_max - x_min
            bh2 = y_max - y_min
            if bw2 <= 0.0 or bh2 <= 0.0:
                continue

            x_center = (x_min + x_max) / 2.0 / float(w)
            y_center = (y_min + y_max) / 2.0 / float(h)
            w_norm = bw2 / float(w)
            h_norm = bh2 / float(h)

            lines.append(f"{CLASS_ID} {x_center:.6f} {y_center:.6f} {w_norm:.6f} {h_norm:.6f}")

        ds = None

        out_txt = labels_dir / f"{tif_path.stem}.txt"
        out_txt.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")


if __name__ == "__main__":
    write_yolo_labels_for_tiles(
        tiles_dir="E:\\WSB\\Praca_Magisterska_2\\Skrypty\\NAC YOLO Training\\dataset\\images",
        csv_path="E:\\WSB\\Praca_Magisterska_2\\Skrypty\\NAC YOLO Training\\dataset\\labels\\CE-5 Crater catalog.csv",
        labels_dir="E:\\WSB\\Praca_Magisterska_2\\Skrypty\\NAC YOLO Training\\dataset\\labels",
    )
    pass
