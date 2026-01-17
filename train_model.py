from ultralytics import YOLO

model = YOLO("yolov8n.pt")
model.train(
    data=r"E:\WSB\Praca_Magisterska_2\Skrypty\NAC YOLO Training\datasets\M166854798L\data.yaml",
    imgsz=480,
    epochs=10,
    batch=16,
)
