from __future__ import annotations

import argparse
from pathlib import Path


def count_yolo_labels(txt_path: Path) -> int:
    with txt_path.open("r", encoding="utf-8", errors="ignore") as f:
        return sum(1 for line in f if line.strip())


def find_png(png_root: Path, rel_txt_path: Path) -> Path | None:
    rel_png = rel_txt_path.with_suffix(".png")
    p1 = png_root / rel_png
    if p1.exists():
        return p1
    p2 = png_root / rel_txt_path.with_suffix(".PNG")
    if p2.exists():
        return p2
    return None


def remove_by_label_count(
    png_dir: str | Path,
    txt_dir: str | Path,
    label_count: int,
    dry_run: bool = False,
) -> tuple[int, int, int]:
    png_root = Path(png_dir).expanduser().resolve()
    txt_root = Path(txt_dir).expanduser().resolve()

    if not png_root.is_dir():
        raise NotADirectoryError(f"PNG folder not found: {png_root}")
    if not txt_root.is_dir():
        raise NotADirectoryError(f"TXT folder not found: {txt_root}")
    if label_count < 0:
        raise ValueError("label_count must be >= 0")

    removed_txt = 0
    removed_png = 0
    missing_png = 0

    for txt_path in txt_root.rglob("*.txt"):
        if not txt_path.is_file():
            continue
        if count_yolo_labels(txt_path) > label_count:
            continue

        rel = txt_path.relative_to(txt_root)
        png_path = find_png(png_root, rel)

        if dry_run:
            print(f"[DRY] remove TXT: {txt_path}")
        else:
            txt_path.unlink(missing_ok=True)
        removed_txt += 1

        if png_path is None:
            missing_png += 1
            if dry_run:
                print(f"[DRY] missing PNG for: {rel}")
            else:
                print(f"[WARN] missing PNG for: {rel}")
            continue

        if dry_run:
            print(f"[DRY] remove PNG: {png_path}")
        else:
            png_path.unlink(missing_ok=True)
        removed_png += 1

    return removed_txt, removed_png, missing_png


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--png_dir", required=True, help="Path to folder with PNG files")
    p.add_argument("--txt_dir", required=True, help="Path to folder with TXT files")
    p.add_argument("--label_count", required=True, type=int, help="Exact number of labels (lines) in TXT to qualify for deletion")
    p.add_argument("--dry_run", action="store_true", help="Print actions without deleting")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    a, b, c = remove_by_label_count(
        args.png_dir, args.txt_dir, args.label_count, dry_run=args.dry_run
    )
    print(f"Removed TXT: {a}, Removed PNG: {b}, Missing PNG: {c}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
