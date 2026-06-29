# 奶龙识别 (Nailong Detector)

基于 YOLOv8 的「奶龙」检测工具。训练好的模型可以在图片、视频和**实时屏幕画面**中框出奶龙并给出置信度。

核心功能是**截屏实时识别**：屏幕右下角常驻一个悬浮图标，框选任意屏幕区域后，会在该区域上叠加一层透明遮罩，实时标出画面里的奶龙——不打断你正在看的视频或网页。

> 提供开箱即用的 Windows exe，**无需安装 Python 或任何依赖，双击即用**。

---

## 效果指标

模型在测试集（1607 张）上的实测表现：

| 指标 | 数值 |
|------|------|
| mAP50 | 0.964 |
| mAP50-95 | 0.713 |

训练配置：YOLOv8s，50 epochs，单类 `nailong`，训练集 7417 / 验证集 1538 / 测试集 1607 张。

---

## 快速开始

### 方式一：直接用 exe（推荐，给普通用户）

1. 到 [Releases](../../releases) 下载 `奶龙识别.exe`
2. 双击运行（首次启动需解压，约 10~20 秒）
3. 屏幕右下角出现奶龙图标后即可使用

> exe 为 CPU 版，任何 Windows 电脑都能跑，无需显卡。

### 方式二：从源码运行（给开发者）

```bash
# 1. 安装依赖（GPU 版）
pip install -r requirements.txt

# 1'. 或 CPU 版 torch
pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
pip install ultralytics mss keyboard pillow "numpy<2"

# 2. 运行截屏识别
python src/screen_detect.py
```

Windows 用户也可以直接双击 `scripts/启动截屏识别.bat`（需先把脚本里的 Python 路径改成你自己的环境）。

---

## 操作说明

启动后，屏幕右下角的悬浮图标即为入口。鼠标悬停图标可随时查看下表：

| 操作 | 功能 |
|------|------|
| 左键点击图标 | 框选一块区域，单次识别 |
| F8 | 单次识别 |
| F9 | 实时识别（再按一次 F9 停止） |
| ESC | 退出程序 |
| 右键图标 / 拖动 | 退出 / 移动图标位置 |

实时识别时，框选区域会显示橙色边框和提示，区域内用绿色框标出识别到的奶龙并附置信度数字。

---

## 命令行工具

```bash
# 识别单张图片或视频
python src/detect_nailong.py --source 路径/到/图片或视频

# 在测试集上评估模型指标
python src/eval_test.py

# 重新训练（需准备数据集，见 src/nailong.yaml）
python src/train_formal.py
```

---

## 项目结构

```
nailong-detector/
├─ README.md
├─ LICENSE                  # MIT
├─ requirements.txt         # 依赖
├─ models/
│  └─ best.pt               # 训练好的模型权重 (YOLOv8s, mAP50=0.964)
├─ src/
│  ├─ screen_detect.py      # 截屏实时识别（主功能）
│  ├─ detect_nailong.py     # 命令行图片/视频识别
│  ├─ eval_test.py          # 测试集评估
│  ├─ train_formal.py       # 训练脚本
│  └─ nailong.yaml          # 数据集配置
├─ assets/
│  └─ 0001.png              # 悬浮图标
├─ scripts/
│  └─ 启动截屏识别.bat       # 开发者快捷启动
└─ build_spec/
   └─ nailong.spec          # PyInstaller 打包配置
```

---

## 自行打包 exe

```bash
# 在干净的 CPU 环境里（避免把 GB 级 CUDA 库打进去）
pip install pyinstaller
# 在项目根目录运行
pyinstaller build_spec/nailong.spec --noconfirm
# 产物: dist/奶龙识别.exe
```

模型权重和图标会一起打进 exe，对方无需额外文件。

---

## 技术说明

- **检测框架**：[Ultralytics YOLOv8](https://github.com/ultralytics/ultralytics)
- **截屏**：[mss](https://github.com/BoboTiG/python-mss)，全局热键用 [keyboard](https://github.com/boppreh/keyboard)
- **透明遮罩**：Tk 颜色键透明 + Windows `SetWindowDisplayAffinity` 把遮罩排除出截屏，避免实时窗口被自己截进画面造成的画中画递归
- **打包**：PyInstaller 单文件 exe，CPU 版 torch，显式打包 VC++ 运行时 DLL 保证在未装运行时的机器上也能跑

---

## 已知限制

- 全局热键（F8/F9/ESC）在部分系统需**以管理员身份运行**才能被拦截
- exe 为 CPU 推理，实时识别帧率较低（每秒数帧）；需要高帧率请用 GPU 环境跑源码
- 透明遮罩功能依赖 Windows，非 Windows 平台会退化

---

## License

[MIT](LICENSE)

