import argparse
from typing import Iterable, Optional
from pathlib import Path
import cv2
from ultralytics.utils.plotting import Annotator

def show_yolo_label(img_path, label_path=None, line_width=1):
    img_path = Path(img_path)
    label_path = Path(label_path) if label_path else img_path.with_suffix(".txt")

    im = cv2.imread(str(img_path))  # BGR
    if im is None:
        raise FileNotFoundError(img_path)

    h, w = im.shape[:2]
    ann = Annotator(im, line_width=line_width)

    if label_path.exists():
        for line in label_path.read_text().splitlines():
            if not line.strip():
                continue
            _, xc, yc, bw, bh = map(float, line.split()[:5])  # YOLO format
            x1 = int((xc - bw / 2) * w)
            y1 = int((yc - bh / 2) * h)
            x2 = int((xc + bw / 2) * w)
            y2 = int((yc + bh / 2) * h)

            ann.box_label([x1, y1, x2, y2], color=(0, 255, 0))

    out = ann.result()
    cv2.imshow("Labels", out)
    cv2.waitKey(0)
    cv2.destroyAllWindows()


def _build_argparser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Wyświetla obraz z etykietami.")
    p.add_argument("-i", "--image-path", type=Path, required=True, help="Katalog źródłowy .png.")
    p.add_argument("-l", "--label-path", type=Path, required=True, help="Katalog źródłowy .txt.")
    p.add_argument("-n", "--file-name", type=Path, required=True, help="Nazwa dla obu plików.")
    return p


def main(argv: Optional[Iterable[str]] = None) -> int:
    args = _build_argparser().parse_args(argv)
    show_yolo_label(
        img_path=args.image_path / f"{args.file_name}.png",
        label_path=args.label_path / f"{args.file_name}.txt",
        line_width=1)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
