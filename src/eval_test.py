import os
from ultralytics import YOLO

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _device():
    try:
        import torch
        return 0 if torch.cuda.is_available() else 'cpu'
    except Exception:
        return 'cpu'


def main():
    model = YOLO(os.path.join(_ROOT, 'models', 'best.pt'))
    metrics = model.val(
        data=os.path.join(_ROOT, 'src', 'nailong.yaml'),
        split='test',
        device=_device(),
    )
    print('=== TEST 集实测指标 ===')
    print(f'P(精确率)   = {metrics.box.mp:.4f}')
    print(f'R(召回率)   = {metrics.box.mr:.4f}')
    print(f'mAP50      = {metrics.box.map50:.4f}')
    print(f'mAP50-95   = {metrics.box.map:.4f}')

if __name__ == '__main__':
    main()