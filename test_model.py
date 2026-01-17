from ultralytics import YOLO

model = YOLO(r"runs/detect/train4/weights/best.pt")

results = model.predict(
    source=r"E:\WSB\Praca_Magisterska_2\Skrypty\NAC YOLO Training\dataset2\train\A14-3844.jpg",
    imgsz=480,
    conf=0.25,
    iou=0.7,
    save=True,            # zapisze obraz z bboxami
    show=False,           # True jeśli chcesz okno podglądu
    show_labels=False,    # bez nazw klas
    show_conf=False,      # bez confidence
    line_width=1          # cieńsze ramki
)

r = results[0]
print("Liczba detekcji:", len(r.boxes))
print("Conf:", r.boxes.conf.cpu().numpy()[:10])
print("Klasy:", r.boxes.cls.cpu().numpy()[:10])
print("XYXY:", r.boxes.xyxy.cpu().numpy()[:3])
