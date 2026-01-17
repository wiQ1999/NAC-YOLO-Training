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
    ann = Annotator(im, line_width=line_width)  # :contentReference[oaicite:1]{index=1}

    if label_path.exists():
        for line in label_path.read_text().splitlines():
            if not line.strip():
                continue
            _, xc, yc, bw, bh = map(float, line.split()[:5])  # YOLO: class x y w h (0..1)
            x1 = int((xc - bw / 2) * w)
            y1 = int((yc - bh / 2) * h)
            x2 = int((xc + bw / 2) * w)
            y2 = int((yc + bh / 2) * h)

            ann.box_label([x1, y1, x2, y2], color=(0, 255, 0))  # :contentReference[oaicite:2]{index=2}

    out = ann.result()
    cv2.imshow("GT labels", out)
    cv2.waitKey(0)
    cv2.destroyAllWindows()


dir = r"E:\\WSB\\Praca_Magisterska_2\Skrypty\\NAC YOLO Training\\datasets\\M166854798L\\"
photo_name = r"M166854798L_lambert_sldem2015_8bit_georef_linear_x3200_y22400_w640_h640"

show_yolo_label(
    img_path=dir + r"train_png\\" + photo_name + r".png", 
    label_path=dir + r"train_labels\\" + photo_name + r".txt",
    line_width=1)