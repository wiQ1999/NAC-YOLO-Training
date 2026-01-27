#!/usr/bin/env python3
"""split_png_adn_labels_data.py

Losowo dzieli pary (PNG + TXT) na 2 zbiory (test/val) lub 3 zbiory (train/val/test).

Wymagania:
- Wejście: --png-in i --txt-in zawierają pary: <nazwa>.png oraz <nazwa>.txt.
- Skrypt nie nadpisuje plików w katalogach wyjściowych.
- 2 zbiory: --ratio jako 0.2 (val=20%) albo 80/20 (test/val).
  TEST jest przenoszony tylko gdy podasz --png-test-out i --txt-test-out.
- 3 zbiory: --ratio jako 70/15/15 (train/val/test) i wtedy musisz podać wyjścia dla train/val/test.

Przykład (3 zbiory):
  python split_png_adn_labels_data.py \
    --png-in ./images/all --txt-in ./labels/all \
    --png-train-out ./images/train --txt-train-out ./labels/train \
    --png-val-out ./images/val --txt-val-out ./labels/val \
    --png-test-out ./images/test --txt-test-out ./labels/test \
    --ratio 70/15/15 --seed 123
"""

from __future__ import annotations

import argparse
import random
import shutil
from pathlib import Path


def list_stems(dir_path: Path, suffix: str) -> set[str]:
    if not dir_path.is_dir():
        raise FileNotFoundError(f"Katalog nie istnieje lub nie jest katalogiem: {dir_path}")
    return {p.stem for p in dir_path.iterdir() if p.is_file() and p.suffix.lower() == suffix}


def validate_pairs(png_in: Path, txt_in: Path) -> list[str]:
    png = list_stems(png_in, ".png")
    txt = list_stems(txt_in, ".txt")

    only_png = sorted(png - txt)
    only_txt = sorted(txt - png)
    if only_png or only_txt:
        msg = ["Niezgodność par PNG/TXT:"]
        if only_png:
            msg.append(f"- Brak TXT dla {len(only_png)} PNG (np. {only_png[:10]})")
        if only_txt:
            msg.append(f"- Brak PNG dla {len(only_txt)} TXT (np. {only_txt[:10]})")
        raise ValueError("\n".join(msg))

    if not png:
        raise ValueError(f"Brak plików PNG w katalogu: {png_in}")

    return sorted(png)


def parse_ratio(raw: str) -> tuple[float, ...]:
    s = raw.strip()
    if not s:
        raise ValueError("--ratio nie może być puste.")

    # "0.2" -> (test, val)
    if all(ch not in s for ch in ["/", ",", " "]):
        val = float(s)
        if not (0.0 <= val <= 1.0):
            raise ValueError("Dla pojedynczej wartości --ratio oczekiwano ułamka val w [0, 1].")
        return (1.0 - val, val)

    parts = [p for p in s.replace("/", ",").replace(" ", ",").split(",") if p]
    nums = [float(p) for p in parts]
    if len(nums) not in (2, 3):
        raise ValueError("--ratio musi zawierać 2 lub 3 wartości (np. 80/20 lub 70/15/15).")
    if any(x <= 0 for x in nums):
        raise ValueError("Wartości w --ratio muszą być dodatnie.")

    total = sum(nums)
    return tuple(x / total for x in nums)


def counts_from_fracs(total: int, fracs: list[float]) -> list[int]:
    raw = [total * f for f in fracs]
    base = [int(x) for x in raw]
    left = total - sum(base)
    rema = [x - int(x) for x in raw]

    for i in sorted(range(len(fracs)), key=lambda k: rema[k], reverse=True)[:left]:
        base[i] += 1

    return base


def ensure_no_collisions(dst_dir: Path, stems: list[str], suffix: str) -> None:
    existing = [f"{s}{suffix}" for s in stems if (dst_dir / f"{s}{suffix}").exists()]
    if existing:
        raise FileExistsError(
            f"W katalogu docelowym istnieją już pliki ({len(existing)}), np.: {existing[:10]}. "
            "Skrypt nie nadpisuje plików."
        )


def move_pairs(stems: list[str], png_in: Path, txt_in: Path, png_out: Path, txt_out: Path) -> int:
    png_out.mkdir(parents=True, exist_ok=True)
    txt_out.mkdir(parents=True, exist_ok=True)

    ensure_no_collisions(png_out, stems, ".png")
    ensure_no_collisions(txt_out, stems, ".txt")

    moved = 0
    for stem in stems:
        png_src = png_in / f"{stem}.png"
        txt_src = txt_in / f"{stem}.txt"
        if not png_src.exists() or not txt_src.exists():
            raise FileNotFoundError(f"Brak pary w trakcie przenoszenia: {png_src.name} / {txt_src.name}")

        shutil.move(str(png_src), str(png_out / png_src.name))
        shutil.move(str(txt_src), str(txt_out / txt_src.name))
        moved += 1

    return moved


def require_dir_pair(png: Path | None, txt: Path | None, name: str) -> tuple[Path, Path]:
    if (png is None) != (txt is None):
        raise ValueError(f"Dla {name} podaj jednocześnie ścieżki PNG i TXT.")
    if png is None or txt is None:
        raise ValueError(f"Brak ścieżek dla {name}.")
    return png, txt


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Dzieli pary PNG+TXT na 2 lub 3 zbiory zgodnie z --ratio.")
    p.add_argument("--png-in", required=True, type=Path, help="Katalog wejściowy PNG.")
    p.add_argument("--txt-in", required=True, type=Path, help="Katalog wejściowy TXT.")

    p.add_argument("--png-val-out", required=True, type=Path, help="Katalog wyjściowy PNG (val).")
    p.add_argument("--txt-val-out", required=True, type=Path, help="Katalog wyjściowy TXT (val).")

    p.add_argument("--png-test-out", type=Path, default=None, help="Katalog wyjściowy PNG (test).")
    p.add_argument("--txt-test-out", type=Path, default=None, help="Katalog wyjściowy TXT (test).")

    p.add_argument("--png-train-out", type=Path, default=None, help="Katalog wyjściowy PNG (train).")
    p.add_argument("--txt-train-out", type=Path, default=None, help="Katalog wyjściowy TXT (train).")

    p.add_argument(
        "--ratio",
        required=True,
        type=str,
        help="0.2 (val), 80/20 (test/val) lub 70/15/15 (train/val/test).",
    )
    p.add_argument("--seed", type=int, default=None, help="Ziarno losowania (opcjonalne).")
    return p.parse_args()


def main() -> None:
    args = parse_args()

    stems = validate_pairs(args.png_in, args.txt_in)
    total = len(stems)

    fracs = parse_ratio(args.ratio)

    rng = random.Random(args.seed)
    rng.shuffle(stems)

    if len(fracs) == 2:
        test_frac, val_frac = fracs
        test_n, val_n = counts_from_fracs(total, [test_frac, val_frac])

        test_stems = stems[:test_n]
        val_stems = stems[test_n:test_n + val_n]

        moved_val = move_pairs(val_stems, args.png_in, args.txt_in, args.png_val_out, args.txt_val_out)

        moved_test = 0
        if args.png_test_out is not None or args.txt_test_out is not None:
            png_test, txt_test = require_dir_pair(args.png_test_out, args.txt_test_out, "TEST")
            if png_test.resolve() == args.png_in.resolve() or txt_test.resolve() == args.txt_in.resolve():
                raise ValueError("Katalog wyjściowy TEST nie może być taki sam jak wejściowy.")
            moved_test = move_pairs(test_stems, args.png_in, args.txt_in, png_test, txt_test)

        remaining = total - moved_val - moved_test

        print(f"Łącznie par: {total}")
        print(f"VAL:  {val_n} (przeniesiono: {moved_val})")
        print(f"TEST: {test_n} (przeniesiono: {moved_test})")
        print(f"Pozostało w wejściu: {remaining}")
        return

    # 3 zbiory: train/val/test
    train_frac, val_frac, test_frac = fracs
    train_n, val_n, test_n = counts_from_fracs(total, [train_frac, val_frac, test_frac])

    png_train, txt_train = require_dir_pair(args.png_train_out, args.txt_train_out, "TRAIN")
    png_test, txt_test = require_dir_pair(args.png_test_out, args.txt_test_out, "TEST")

    for out_dir, in_dir, name in [
        (png_train, args.png_in, "TRAIN PNG"),
        (txt_train, args.txt_in, "TRAIN TXT"),
        (args.png_val_out, args.png_in, "VAL PNG"),
        (args.txt_val_out, args.txt_in, "VAL TXT"),
        (png_test, args.png_in, "TEST PNG"),
        (txt_test, args.txt_in, "TEST TXT"),
    ]:
        if out_dir.resolve() == in_dir.resolve():
            raise ValueError(f"Katalog wyjściowy {name} nie może być taki sam jak wejściowy.")

    train_stems = stems[:train_n]
    val_stems = stems[train_n:train_n + val_n]
    test_stems = stems[train_n + val_n:]

    moved_train = move_pairs(train_stems, args.png_in, args.txt_in, png_train, txt_train)
    moved_val = move_pairs(val_stems, args.png_in, args.txt_in, args.png_val_out, args.txt_val_out)
    moved_test = move_pairs(test_stems, args.png_in, args.txt_in, png_test, txt_test)

    remaining = total - moved_train - moved_val - moved_test

    print(f"Łącznie par: {total}")
    print(f"TRAIN: {train_n} (przeniesiono: {moved_train})")
    print(f"VAL:   {val_n} (przeniesiono: {moved_val})")
    print(f"TEST:  {test_n} (przeniesiono: {moved_test})")
    print(f"Pozostało w wejściu: {remaining}")


if __name__ == "__main__":
    raise SystemExit(main())
