from ultralytics import YOLO

def main():
    print("=== formal train start: yolov8s 50ep ===", flush=True)
    model = YOLO('yolov8s.pt')
    results = model.train(
        data='nailong.yaml',
        epochs=50,
        imgsz=640,
        batch=16,
        device=0,
        workers=0,
        name='nailong_formal',
        verbose=True,
    )
    print("=== FORMAL DONE ===", flush=True)
    print(results, flush=True)

if __name__ == '__main__':
    main()
