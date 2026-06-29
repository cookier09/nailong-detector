"""
奶龙识别脚本 - 用训练好的 best.pt 做推断
用法:
  python detect_nailong.py --source 图片或视频路径
  python detect_nailong.py --source nailong/test/images/某张图.jpg
  python detect_nailong.py --source 某视频.mp4
"""
import os
import sys
from ultralytics import YOLO

# 模型路径相对项目根(本文件在 src/, 模型在 models/)
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL = os.path.join(_ROOT, 'models', 'best.pt')


def _device():
    try:
        import torch
        return 0 if torch.cuda.is_available() else 'cpu'
    except Exception:
        return 'cpu'


def main():
    if '--source' not in sys.argv:
        print('用法: python detect_nailong.py --source <图片或视频路径>')
        sys.exit(1)
    source = sys.argv[sys.argv.index('--source') + 1]

    model = YOLO(MODEL)
    results = model.predict(
        source=source,
        conf=0.25,        # 置信度阈值，奶龙偏低也认
        save=True,        # 自动保存结果到 runs/detect/predict/
        device=_device(), # 自动选 GPU/CPU
    )

    # 图片: 打印每张图里识别到的奶龙数量和置信度
    for r in results:
        boxes = r.boxes
        n = len(boxes)
        if n == 0:
            print(f'[{r.path}] 未识别到奶龙')
        else:
            confs = [round(float(c), 3) for c in boxes.conf]
            print(f'[{r.path}] 识别到 {n} 个奶龙, 置信度: {confs}')
    print(f'\n结果已保存到 runs/detect/predict/')

if __name__ == '__main__':
    main()