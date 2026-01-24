#!/usr/bin/env python3
"""
Losowy podział par (PNG + TXT) z folderu test do folderu val w zadanej proporcji.

Założenia:
- Wszystkie pliki źródłowe są w katalogach *test* (osobno PNG i TXT).
- Każdy plik PNG ma odpowiadający mu plik TXT o tej samej nazwie bazowej.
- Do katalogów *val* przenoszone są wyłącznie wylosowane pary (PNG i TXT),
  reszta pozostaje w katalogach *test*.

Przykład:
python ./tools/split_data_into_test_and_val.py \
  --png-src ./datasets/HQ/images/raw/train \
  --png-dst ./datasets/HQ/images/val \
  --txt-src ./datasets/HQ/labels/raw/train \
  --txt-dst ./datasets/HQ/labels/val \
  --ratio 0.2 \
  --seed 123
"""

from __future__ import annotations

import argparse
import random
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Set, Tuple


@dataclass(frozen=True)
class Config:
    png_src: Path
    png_dst: Path
    txt_src: Path
    txt_dst: Path
    ratio: float
    seed: int | None


def _list_stems(directory: Path, suffix: str) -> Set[str]:
    print(f"{directory=}, {suffix=}")
    if not directory.exists() or not directory.is_dir():
        raise FileNotFoundError(f"Katalog nie istnieje lub nie jest katalogiem: {directory}")
    return {p.stem for p in directory.iterdir() if p.is_file() and p.suffix.lower() == suffix.lower()}


def _validate_pairs(png_src: Path, txt_src: Path) -> List[str]:
    png_stems = _list_stems(png_src, ".png")
    txt_stems = _list_stems(txt_src, ".txt")

    only_png = sorted(png_stems - txt_stems)
    only_txt = sorted(txt_stems - png_stems)

    if only_png or only_txt:
        msg_lines = ["Niezgodność par PNG/TXT:"]
        if only_png:
            msg_lines.append(f"- Brak plików TXT dla {len(only_png)} PNG (np. {only_png[:10]})")
        if only_txt:
            msg_lines.append(f"- Brak plików PNG dla {len(only_txt)} TXT (np. {only_txt[:10]})")
        raise ValueError("\n".join(msg_lines))

    if not png_stems:
        raise ValueError(f"Brak plików PNG w katalogu: {png_src}")

    return sorted(png_stems)


def _ensure_empty_collision(dst_dir: Path, filenames: Iterable[str]) -> None:
    existing = [name for name in filenames if (dst_dir / name).exists()]
    if existing:
        preview = existing[:10]
        raise FileExistsError(
            f"W katalogu docelowym istnieją już pliki ({len(existing)}), np.: {preview}. "
            "Usuń je albo wskaż inny katalog docelowy (skrypt nie nadpisuje plików)."
        )


def split_test_to_val(cfg: Config) -> Tuple[int, int]:
    stems = _validate_pairs(cfg.png_src, cfg.txt_src)

    if not (0.0 <= cfg.ratio <= 1.0):
        raise ValueError("--ratio musi być w zakresie [0, 1].")

    total = len(stems)
    to_move = int(total * cfg.ratio)  # zawsze <= total

    rng = random.Random(cfg.seed)
    selected = set(rng.sample(stems, k=to_move)) if to_move > 0 else set()

    cfg.png_dst.mkdir(parents=True, exist_ok=True)
    cfg.txt_dst.mkdir(parents=True, exist_ok=True)

    png_names = [f"{s}.png" for s in selected]
    txt_names = [f"{s}.txt" for s in selected]
    _ensure_empty_collision(cfg.png_dst, png_names)
    _ensure_empty_collision(cfg.txt_dst, txt_names)

    moved = 0
    for stem in sorted(selected):
        png_src_file = cfg.png_src / f"{stem}.png"
        txt_src_file = cfg.txt_src / f"{stem}.txt"
        png_dst_file = cfg.png_dst / f"{stem}.png"
        txt_dst_file = cfg.txt_dst / f"{stem}.txt"

        if not png_src_file.exists() or not txt_src_file.exists():
            raise FileNotFoundError(
                f"Brak pary w trakcie przenoszenia: {png_src_file.name} / {txt_src_file.name}"
            )

        shutil.move(str(png_src_file), str(png_dst_file))
        shutil.move(str(txt_src_file), str(txt_dst_file))
        moved += 1

    remaining = total - moved
    return moved, remaining


def parse_args() -> Config:
    p = argparse.ArgumentParser(description="Wydziela pliki oraz etykiety do wskazanego katalogu według proporcji.")
    p.add_argument("--png-src", required=True, type=Path, help="Katalog źródłowy PNG (test).")
    p.add_argument("--png-dst", required=True, type=Path, help="Katalog docelowy PNG (val).")
    p.add_argument("--txt-src", required=True, type=Path, help="Katalog źródłowy TXT (test).")
    p.add_argument("--txt-dst", required=True, type=Path, help="Katalog docelowy TXT (val).")
    p.add_argument("--ratio", required=True, type=float, help="Ułamek par do przeniesienia do val (0..1). N = int(total * ratio).")
    p.add_argument("--seed", type=int, default=None, help="Ziarno losowania (opcjonalne).")
    args = p.parse_args()

    return Config(
        png_src=args.png_src,
        png_dst=args.png_dst,
        txt_src=args.txt_src,
        txt_dst=args.txt_dst,
        ratio=args.ratio,
        seed=args.seed
    )


def main() -> None:
    cfg = parse_args()
    moved, remaining = split_test_to_val(cfg)

    print(f"Przeniesiono par: {moved}")
    print(f"Pozostało w test: {remaining}")
    print(f"PNG: {cfg.png_src} -> {cfg.png_dst}")
    print(f"TXT: {cfg.txt_src} -> {cfg.txt_dst}")


if __name__ == "__main__":
    raise SystemExit(main())
