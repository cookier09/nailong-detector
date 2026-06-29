# nailong-detector

用 YOLOv8 训练的「奶龙」检测器。能识别图片、视频里的奶龙，主要用法是**截屏实时识别**——在屏幕上框一块区域，程序会实时把画面里的奶龙框出来，不影响你在看视频或刷网页。

打包成了 Windows exe，别人不用装 Python，双击就能用。

## 模型效果

YOLOv8s，单类 `nailong`，训了 50 个 epoch。测试集 1607 张：

- mAP50 = 0.964
- mAP50-95 = 0.713

训练集 7417 张，验证集 1538 张。

## 怎么用

### 用 exe（推荐）

1. 去 [Releases](../../releases) 下载 `奶龙识别.exe`
2. 双击运行，第一次启动会解压，等十几秒
3. 右下角出现奶龙图标就能用了

exe 是 CPU 版，不用显卡，普通 Windows 电脑都能跑。

### 用源码

```bash
pip install -r requirements.txt
python src/screen_detect.py
```

如果机器没显卡，把 torch 换成 CPU 版：

```bash
pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
```

Windows 下也可以双击 `scripts/启动截屏识别.bat`，不过里面的 Python 路径要改成你自己环境的。

## 快捷键

| 按键 | 作用 |
|------|------|
| F8 | 框选一块区域，识别一次 |
| F9 | 实时识别（再按一次停止） |
| ESC | 退出 |
| 左键点图标 | 同 F8 |
| 右键 / 拖动图标 | 退出 / 移动图标 |

实时识别时，框选区域会有一圈橙色边框，里面用绿框标出奶龙并带上置信度。

## 命令行

```bash
# 识别图片或视频
python src/detect_nailong.py --source 图片或视频路径

# 评估测试集指标
python src/eval_test.py

# 重新训练（需要数据集，配置在 src/nailong.yaml）
python src/train_formal.py
```

## 目录结构

```
nailong-detector/
├─ models/best.pt          # 训练好的权重
├─ src/                    # 源码
│  ├─ screen_detect.py     # 截屏实时识别（主程序）
│  ├─ detect_nailong.py    # 命令行识别
│  ├─ eval_test.py         # 评估
│  ├─ train_formal.py      # 训练
│  └─ nailong.yaml         # 数据集配置
├─ assets/0001.png         # 悬浮图标
├─ scripts/                # 启动脚本
└─ build_spec/nailong.spec # PyInstaller 打包配置
```

## 自己打包 exe

```bash
pip install pyinstaller
pyinstaller build_spec/nailong.spec --noconfirm
```

产物在 `dist/奶龙识别.exe`。权重和图标会一起打进去，发给别人不用带别的文件。

建议在干净的 CPU 环境里打包，不然会把几个 G 的 CUDA 库一起塞进去。

## 一些说明

- 全局热键在有的系统上要**管理员权限**才拦得到，按了没反应就右键以管理员身份运行
- exe 是 CPU 推理，实时识别帧率不高，每秒几帧；想要快就用源码跑 GPU
- 透明遮罩用的是 Windows 的接口，别的系统上会退化成半透明

## License

MIT，见 [LICENSE](LICENSE)。
