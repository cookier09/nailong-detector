# -*- mode: python ; coding: utf-8 -*-
# PyInstaller 打包配置: 奶龙截屏识别 (CPU 版, 单 exe)
# 在项目根目录运行:  pyinstaller build_spec/nailong.spec --noconfirm
import os
from PyInstaller.utils.hooks import collect_submodules, collect_data_files, collect_dynamic_libs

# spec 里的相对路径是相对 spec 文件目录解析的, 显式拼项目根(build_spec 的上一级)
ROOT = os.path.dirname(os.path.abspath(SPECPATH))

# 打包进 exe 的数据: (源路径, exe 内目标目录) —— 目标目录要和代码里 _resource_path 解析的一致
datas = [
    (os.path.join(ROOT, 'models', 'best.pt'), 'models'),
    (os.path.join(ROOT, 'assets', '0001.png'), 'assets'),
]
# ultralytics 运行时需要其内置的配置/yaml 等数据文件
datas += collect_data_files('ultralytics')

binaries = []
# torch 的 DLL 之间有依赖, 必须完整收集, 否则 c10.dll 等加载失败
binaries += collect_dynamic_libs('torch')
binaries += collect_dynamic_libs('torchvision')
# c10.dll 依赖 VC++ 运行时(MSVCP140/VCRUNTIME140/_1), 显式打包, 不依赖目标机器是否已装
_env = r'E:\condaData\envs_dirs\nailong-cpu'
for _dll in ('msvcp140.dll', 'msvcp140_1.dll', 'vcruntime140.dll', 'vcruntime140_1.dll'):
    _p = os.path.join(_env, _dll)
    if os.path.exists(_p):
        binaries.append((_p, '.'))

hiddenimports = []
hiddenimports += collect_submodules('ultralytics')
hiddenimports += collect_submodules('torch')

a = Analysis(
    [os.path.join(ROOT, 'src', 'screen_detect.py')],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],  # 先不剔除依赖, 保证运行正确; 体积优化留待验证可跑后再做
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='奶龙识别',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    runtime_tmpdir=None,
    console=False,          # 发布版: 无控制台黑框
    disable_windowed_traceback=False,
    icon=os.path.join(ROOT, 'assets', '0001.png'),
)
