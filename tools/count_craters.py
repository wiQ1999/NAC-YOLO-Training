import argparse
import csv
import json
import math
import os
from glob import glob
from typing import Dict, List


IMG = 640


def clip(v: float, lo: float = 0.0, hi: float = float(IMG)) -> float:
    return max(lo, min(hi, v))


def yolo_to_xyxy(xc: float, yc: float, w: float, h: float) -> List[float]:
    x1 = (xc - w / 2.0) * IMG
    y1 = (yc - h / 2.0) * IMG
    x2 = (xc + w / 2.0) * IMG
    y2 = (yc + h / 2.0) * IMG
    x1, x2 = clip(min(x1, x2)), clip(max(x1, x2))
    y1, y2 = clip(min(y1, y2)), clip(max(y1, y2))
    return [x1, y1, x2, y2]


def coco_to_xyxy(x: float, y: float, w: float, h: float) -> List[float]:
    x1 = clip(x)
    y1 = clip(y)
    x2 = clip(x + w)
    y2 = clip(y + h)
    x1, x2 = min(x1, x2), max(x1, x2)
    y1, y2 = min(y1, y2), max(y1, y2)
    return [x1, y1, x2, y2]


def iou(a: List[float], b: List[float]) -> float:
    ax1, ay1, ax2, ay2 = a
    bx1, by1, bx2, by2 = b

    ix1, iy1 = max(ax1, bx1), max(ay1, by1)
    ix2, iy2 = min(ax2, bx2), min(ay2, by2)

    iw, ih = max(0.0, ix2 - ix1), max(0.0, iy2 - iy1)
    inter = iw * ih
    if inter <= 0.0:
        return 0.0

    area_a = max(0.0, ax2 - ax1) * max(0.0, ay2 - ay1)
    area_b = max(0.0, bx2 - bx1) * max(0.0, by2 - by1)
    return inter / (area_a + area_b - inter + 1e-9)


def size_px(xyxy: List[float]) -> float:
    w = max(0.0, xyxy[2] - xyxy[0])
    h = max(0.0, xyxy[3] - xyxy[1])
    return math.sqrt(max(0.0, w * h))


def bucket(s: float, s_thr: float = 95.0, m_thr: float = 150.0) -> str:
    if s < s_thr:
        return "S"
    if s < m_thr:
        return "M"
    return "L"


def load_preds(pred_json: str) -> Dict[str, List[dict]]:
    with open(pred_json, "r", encoding="utf-8") as f:
        data = json.load(f)

    by_img: Dict[str, List[dict]] = {}
    for p in data:
        img_id = p.get("image_id")
        if not img_id:
            fn = p.get("file_name", "")
            img_id = os.path.splitext(os.path.basename(fn))[0]
        if not img_id:
            continue
        by_img.setdefault(img_id, []).append(p)
    return by_img


def read_gt(txt_path: str, s_thr: float, m_thr: float) -> List[dict]:
    gts = []
    with open(txt_path, "r", encoding="utf-8") as f:
        for ln in f:
            ln = ln.strip()
            if not ln:
                continue
            parts = ln.split()
            if len(parts) < 5:
                continue
            xc, yc, w, h = map(float, parts[1:5])
            bb = yolo_to_xyxy(xc, yc, w, h)
            gts.append(
                {"bbox": bb, "bucket": bucket(size_px(bb), s_thr, m_thr),
                 "matched": False}
            )
    return gts


def metrics(tp: int, fp: int, fn: int) -> Dict[str, float]:
    p = tp / (tp + fp) if (tp + fp) else 0.0
    r = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = (2 * p * r / (p + r)) if (p + r) else 0.0
    return {"precision": p, "recall": r, "f1": f1}


def eval_one(
    pred_json: str,
    gt_dir: str,
    conf: float,
    iou_thr: float,
    s_thr: float,
    m_thr: float,
) -> Dict[str, Dict[str, int]]:
    preds_by = load_preds(pred_json)
    counts = {b: {"TP": 0, "FP": 0, "FN": 0} for b in ["S", "M", "L"]}

    for gt_path in sorted(glob(os.path.join(gt_dir, "*.txt"))):
        tile_id = os.path.splitext(os.path.basename(gt_path))[0]
        gts = read_gt(gt_path, s_thr, m_thr)

        preds = preds_by.get(tile_id, [])
        preds = [p for p in preds if float(p.get("score", 0.0)) >= conf]
        preds.sort(key=lambda x: float(x.get("score", 0.0)), reverse=True)

        for p in preds:
            x, y, w, h = map(float, p["bbox"])
            pb = coco_to_xyxy(x, y, w, h)

            best_iou, best_j = 0.0, None
            for j, g in enumerate(gts):
                if g["matched"]:
                    continue
                cur = iou(pb, g["bbox"])
                if cur > best_iou:
                    best_iou, best_j = cur, j

            if best_j is not None and best_iou >= iou_thr:
                gts[best_j]["matched"] = True
                counts[gts[best_j]["bucket"]]["TP"] += 1
            else:
                counts[bucket(size_px(pb), s_thr, m_thr)]["FP"] += 1

        for g in gts:
            if not g["matched"]:
                counts[g["bucket"]]["FN"] += 1

    return counts


def write_csv(out_csv: str, rows: List[dict]) -> None:
    os.makedirs(os.path.dirname(out_csv) or ".", exist_ok=True)
    cols = ["scenario", "bucket", "TP", "FP", "FN", "precision", "recall", "f1"]
    with open(out_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(rows)


def main() -> None:
    ap = argparse.ArgumentParser(
        description="TSV do konsoli + opcjonalny zapis do CSV (S/M/L, IoU greedy)."
    )
    ap.add_argument("--gt_dir", required=True, help="Folder z GT YOLO *.txt.")
    ap.add_argument("--pred_json", required=True, help="Ścieżka do predictions.json.")
    ap.add_argument("--scenario", default="", help="Nazwa scenariusza do kolumny.")
    ap.add_argument("--conf", type=float, default=0.25, help="Próg score/conf.")
    ap.add_argument("--iou", type=float, default=0.50, help="Próg IoU dla TP.")
    ap.add_argument("--s_thr", type=float, default=95.0, help="Granica S.")
    ap.add_argument("--m_thr", type=float, default=150.0, help="Granica M.")
    ap.add_argument(
        "--out-csv",
        default="",
        help="Opcjonalnie: ścieżka do pliku CSV z wynikami.",
    )
    args = ap.parse_args()

    scenario = args.scenario.strip()
    if not scenario:
        scenario = os.path.splitext(os.path.basename(args.pred_json))[0]

    counts = eval_one(
        pred_json=args.pred_json,
        gt_dir=args.gt_dir,
        conf=args.conf,
        iou_thr=args.iou,
        s_thr=args.s_thr,
        m_thr=args.m_thr,
    )

    rows = []
    for b in ["S", "M", "L"]:
        tp, fp, fn = counts[b]["TP"], counts[b]["FP"], counts[b]["FN"]
        m = metrics(tp, fp, fn)
        rows.append(
            {
                "scenario": scenario,
                "bucket": b,
                "TP": tp,
                "FP": fp,
                "FN": fn,
                "precision": f"{m['precision']:.6f}",
                "recall": f"{m['recall']:.6f}",
                "f1": f"{m['f1']:.6f}",
            }
        )

    # TSV do konsoli (Excel-friendly przez wklejenie)
    print("scenario\tbucket\tTP\tFP\tFN\tprecision\trecall\tf1")
    for r in rows:
        print(
            f"{r['scenario']}\t{r['bucket']}\t{r['TP']}\t{r['FP']}\t{r['FN']}\t"
            f"{r['precision']}\t{r['recall']}\t{r['f1']}"
        )

    # CSV do pliku (opcjonalnie)
    if args.out_csv:
        write_csv(args.out_csv, rows)


if __name__ == "__main__":
    main()
