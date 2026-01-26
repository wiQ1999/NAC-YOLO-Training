#!/usr/bin/env python3
"""
Użycie:
  python resize_tiles.py --in-dir /sciezka/wejscie --out-dir /sciezka/wyjscie --size 640

Co robi skrypt:
  - Wczytuje pliki *.png z folderu --in-dir.
  - Jeśli kafelek ma mniejszy rozmiar niż --size, wykonuje resize w górę do --size x --size.
  - Jeśli kafelek ma rozmiar równy lub większy niż --size, kopiuje go bez zmniejszania.
"""

import argparse
import shutil
from pathlib import Path

from PIL import Image


def resize_up(img: Image.Image, target: int) -> Image.Image:
    w, h = img.size
    if w == target and h == target:
        return img
    if w > target or h > target:
        return img
    if w != h:
        raise ValueError(f"Oczekiwano kafelka kwadratowego, otrzymano {w}x{h}.")
    return img.resize((target, target), resample=Image.Resampling.LANCZOS)


def main(args: argparse.Namespace) -> None:
    in_dir = Path(args.in_dir)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    png_files = sorted(in_dir.glob("*.png"))
    if not png_files:
        raise SystemExit(f"Nie znaleziono plików PNG w folderze: {in_dir}")

    for png_path in png_files:
        out_png = out_dir / png_path.name

        with Image.open(png_path) as im:
            im.load()
            new_im = resize_up(im, args.size)
            if new_im is im:
                shutil.copy2(png_path, out_png)
            else:
                new_im.save(out_png, format="PNG")

    print(f"Gotowe. Przetworzono {len(png_files)} plików PNG -> {out_dir}")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Resize kafelków PNG w górę do zadanego rozmiaru."
    )
    p.add_argument("--in-dir", required=True, help="Folder wejściowy z PNG.")
    p.add_argument("--out-dir", required=True, help="Folder wyjściowy.")
    p.add_argument("--size", type=int, required=True, help="Rozmiar docelowy (kwadrat), np. 640.")
    return p.parse_args()


if __name__ == "__main__":
    main(parse_args())
