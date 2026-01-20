from ultralytics import YOLO


model = YOLO("yolov8n.pt")
model.train(
    data=r"E:\WSB\Praca_Magisterska_2\Skrypty\NAC YOLO Training\datasets\prototyp_480x480_LQ_val\data.yaml",
    imgsz=480,
    epochs=10,
    batch=16,
)
