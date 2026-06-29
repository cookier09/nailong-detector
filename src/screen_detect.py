"""
奶龙截屏识别 - 悬浮按钮 + 快捷键双触发 + 屏幕原位叠加结果
- 屏幕右下角常驻一个悬浮"识"按钮, 点一下进入框选
- 按 Ctrl+Alt+N 也行 (快捷键双保险)
- 框选区域 -> 识别 -> 全屏叠加显示带绿色框的画面, 点一下消失
- 右键悬浮按钮退出程序
"""
import ctypes
import sys
import os
os.environ['YOLO_AUTOINSTALL'] = 'false'   # 打包后禁止 ultralytics 联网 pip 安装可选依赖(如 pi-heif)
os.environ['YOLO_OFFLINE'] = 'true'
import time
import threading
import queue
import tkinter as tk
import numpy as np
import mss
from PIL import Image, ImageTk
from ultralytics import YOLO
import keyboard

try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    pass

def _resource_path(rel):
    # ponytail: PyInstaller 打包后数据解压到 sys._MEIPASS; 未打包时按项目根目录(src 的上一级)解析
    base = getattr(sys, '_MEIPASS', os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    return os.path.join(base, rel)


def _pick_device():
    # 有 CUDA 用 GPU, 否则 CPU。打包到无 GPU 机器上也能跑
    try:
        import torch
        if torch.cuda.is_available():
            return 0
    except Exception:
        pass
    return 'cpu'


MODEL = _resource_path('models/best.pt')
if not os.path.exists(MODEL):
    # 兼容: 模型放在 exe 同级目录的情况
    alt = os.path.join(os.path.dirname(sys.executable), 'best.pt')
    if os.path.exists(alt):
        MODEL = alt

model = None        # 延迟加载, 启动时先弹加载窗再后台加载, 避免界面卡白
DEVICE = 'cpu'


def load_model():
    # 在后台线程调用; 失败弹窗并退出
    global model, DEVICE
    try:
        m = YOLO(MODEL)
    except Exception as e:
        ctypes.windll.user32.MessageBoxW(0, f'模型加载失败:\n{MODEL}\n\n{e}', '奶龙识别', 0x10)
        os._exit(1)
    DEVICE = _pick_device()
    model = m

CONF = 0.25
trigger = threading.Event()
_busy = False   # ponytail: 一次只允许一个识别会话, 防 wait_window 嵌套循环里 F8/F9 重复触发叠开多窗口


class RegionSelector(tk.Toplevel):
    """全屏半透明遮罩, 鼠标拖框选区域"""
    def __init__(self, master):
        super().__init__(master)
        self.overrideredirect(True)
        self.attributes('-topmost', True)
        self.attributes('-alpha', 0.35)
        self.configure(bg='black')
        self.update_idletasks()
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        self.geometry(f'{sw}x{sh}+0+0')
        self.canvas = tk.Canvas(self, cursor='cross', bg='black', highlightthickness=0)
        self.canvas.pack(fill='both', expand=True)
        self.rect = None
        self.start_x = self.start_y = 0
        self.region = None
        self.canvas.bind('<ButtonPress-1>', self.on_press)
        self.canvas.bind('<B1-Motion>', self.on_drag)
        self.canvas.bind('<ButtonRelease-1>', self.on_release)
        self.bind('<Escape>', lambda e: self.destroy())
        self.canvas.create_text(self.winfo_screenwidth()//2, 40,
                                text='拖鼠标框选识别区域  (ESC 取消)', fill='white',
                                font=('Arial', 22), tags='tip')

    def on_press(self, e):
        self.canvas.delete('tip')
        self.start_x, self.start_y = e.x, e.y
        self.rect = self.canvas.create_rectangle(e.x, e.y, e.x, e.y, outline='red', width=3)

    def on_drag(self, e):
        self.canvas.coords(self.rect, self.start_x, self.start_y, e.x, e.y)

    def on_release(self, e):
        x1, y1 = min(self.start_x, e.x), min(self.start_y, e.y)
        x2, y2 = max(self.start_x, e.x), max(self.start_y, e.y)
        self.region = (x1, y1, x2, y2)
        self.destroy()


class FloatButton(tk.Toplevel):
    """屏幕右下角悬浮按钮, 点一下=框选识别, 右键=退出"""
    CHROMA = '#00fefe'   # 色键: 图案里几乎不会出现的青色, 设为这色的像素完全透明

    def __init__(self, master, on_click):
        super().__init__(master)
        self.overrideredirect(True)
        self.attributes('-topmost', True)
        self.configure(bg=self.CHROMA)
        try:
            self.attributes('-transparentcolor', self.CHROMA)
            chroma_ok = True
        except tk.TclError:
            chroma_ok = False
        self.update_idletasks()
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        self.size = 96
        x = sw - self.size - 30
        y = sh - self.size - 60   # 右下角(留出任务栏空间)
        self.geometry(f'{self.size}x{self.size}+{x}+{y}')
        self.on_click = on_click
        self._drag_start = None
        self._moved = False
        # 用 0001.png 作按钮图; 用 _resource_path 解析, 打包成 exe 后也能找到
        try:
            img = Image.open(_resource_path('assets/0001.png')).convert('RGBA')
            img = img.resize((self.size, self.size), Image.LANCZOS)
            if chroma_ok:
                px = img.load()
                for yy in range(img.height):
                    for xx in range(img.width):
                        r, g, b, a = px[xx, yy]
                        if a < 128:                      # 透明/半透明 -> 完全透明色键
                            px[xx, yy] = (0, 254, 254, 255)
                        else:                            # 不透明 -> 贴到黑底消除残留 alpha
                            px[xx, yy] = (r, g, b, 255)
                img = img.convert('RGB')
            self._photo = ImageTk.PhotoImage(img)
            lbl = tk.Label(self, image=self._photo, cursor='hand2', bd=0,
                           bg=self.CHROMA, highlightthickness=0)
        except Exception as e:
            print('按钮图片读取失败, 回退文字:', e)
            lbl = tk.Label(self, text='识', fg='white', bg='#1e88e5',
                           font=('Arial', 30, 'bold'), cursor='hand2')
        lbl.pack(fill='both', expand=True)
        # 左键: 按下记录起点, 拖动>5px算拖动移动, 松开时没拖动则触发识别
        lbl.bind('<ButtonPress-1>', self._press)
        lbl.bind('<B1-Motion>', self._drag)
        lbl.bind('<ButtonRelease-1>', self._release)
        lbl.bind('<Button-3>', lambda e: master.destroy())
        self.bind('<Button-3>', lambda e: master.destroy())
        # 鼠标悬停显示操作说明
        self._tip = None
        lbl.bind('<Enter>', self._show_tip)
        lbl.bind('<Leave>', self._hide_tip)

    HELP_LINES = [
        ('左键拖拽', '框选区域识别'),
        ('F8', '单次识别'),
        ('F9', '实时识别 (再按 F9 停止)'),
        ('ESC', '退出程序'),
        ('右键 / 拖动', '退出 / 移动图标'),
    ]

    def _show_tip(self, e=None):
        if self._tip is not None:
            return
        tip = tk.Toplevel(self)
        tip.overrideredirect(True)
        tip.attributes('-topmost', True)
        tip.configure(bg='#222')
        frame = tk.Frame(tip, bg='#222')
        frame.pack(padx=8, pady=6)
        tk.Label(frame, text='操作说明', fg='#ffcc66', bg='#222',
                 font=('Microsoft YaHei', 10, 'bold')).grid(row=0, column=0, columnspan=2, sticky='w', pady=(0, 4))
        for i, (key, desc) in enumerate(self.HELP_LINES, start=1):
            tk.Label(frame, text=key, fg='#7ec6ff', bg='#222', anchor='w',
                     font=('Microsoft YaHei', 9, 'bold')).grid(row=i, column=0, sticky='w', padx=(0, 10))
            tk.Label(frame, text=desc, fg='white', bg='#222', anchor='w',
                     font=('Microsoft YaHei', 9)).grid(row=i, column=1, sticky='w')
        tip.update_idletasks()
        tw, th = tip.winfo_reqwidth(), tip.winfo_reqheight()
        gx = self.winfo_rootx() + self.size // 2 - tw // 2
        gy = self.winfo_rooty() - th - 8   # 显示在图标上方
        gx = max(0, gx)
        gy = max(0, gy)
        tip.geometry(f'+{gx}+{gy}')
        self._tip = tip

    def _hide_tip(self, e=None):
        if self._tip is not None:
            try: self._tip.destroy()
            except Exception: pass
            self._tip = None

    def _press(self, e):
        self._drag_start = (e.x_root, e.y_root)
        self._moved = False

    def _drag(self, e):
        if not self._drag_start:
            return
        dx, dy = e.x_root - self._drag_start[0], e.y_root - self._drag_start[1]
        if abs(dx) + abs(dy) > 5:
            self._moved = True
            self._hide_tip()   # 拖动时关掉说明框, 松手后悬停会按新位置重新弹出
            # 按住拖动 -> 移动按钮到鼠标位置 (让窗口中心跟随)
            gx = e.x_root - self.size // 2
            gy = e.y_root - self.size // 2
            self.geometry(f'+{gx}+{gy}')

    def _release(self, e):
        if not self._moved:
            self.on_click()
        self._drag_start = None
        self._moved = False


class ResultWindow(tk.Toplevel):
    """可缩放的结果窗口, 显示带绿色框的识别图"""
    def __init__(self, master, img_path, n, confs):
        super().__init__(master)
        self.title("奶龙识别结果")
        self.attributes('-topmost', True)
        self.update_idletasks()
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        self.minsize(420, 300)
        img = Image.open(img_path)
        maxw, maxh = int(sw * 0.85), int(sh * 0.85)
        init_w = min(img.width, maxw)
        init_h = min(img.height + 60, maxh)
        x = (sw - init_w) // 2
        y = (sh - init_h) // 2
        self.geometry(f'{init_w}x{init_h}+{x}+{y}')
        self.original = img
        self.bg = 'white'

        # 顶部信息栏 - 白底黑字
        bar = tk.Frame(self, bg=self.bg, height=36)
        bar.pack(fill='x')
        msg = f"识别到 {n} 个奶龙" + (f"   置信度: {confs}" if confs else "")
        tk.Label(bar, text=msg, fg='black', bg=self.bg, font=('Arial', 16, 'bold'),
                 anchor='w').pack(side='left', padx=12, pady=6)

        # 图片显示区 - 白底
        self.img_label = tk.Label(self, bg=self.bg)
        self.img_label.pack(fill='both', expand=True)
        self.img_label.bind('<Configure>', self._refit)

        hint = tk.Label(self, text='鼠标单击任意地方取消',
                        fg='#666', bg=self.bg, font=('Arial', 11))
        hint.pack(side='bottom', pady=4)

        # 点击窗口任意处 / 任意键 关闭
        self.bind('<Button-1>', lambda e: self.destroy())
        self.bind('<Escape>', lambda e: self.destroy())
        self.bind('<Return>', lambda e: self.destroy())
        self.bind('<space>', lambda e: self.destroy())
        self.bind('<Any-KeyPress>', lambda e: self.destroy())
        # 子控件也转发点击
        bar.bind('<Button-1>', lambda e: self.destroy())
        self.img_label.bind('<Button-1>', lambda e: self.destroy())
        hint.bind('<Button-1>', lambda e: self.destroy())
        self.focus_force()
        self.grab_set()  # 模态, 保证拿到键盘焦点
        self._render()

    def _render(self):
        img = self.original
        self._photo = ImageTk.PhotoImage(img)
        self.img_label.config(image=self._photo)

    def _refit(self, event):
        # 窗口尺寸变化 -> 按可用区重采样图片, 图片随之放大缩小
        maxw = max(1, event.width - 8)
        maxh = max(1, event.height - 4)
        img = self.original.copy()
        img.thumbnail((maxw, maxh), Image.LANCZOS)
        self._photo = ImageTk.PhotoImage(img)
        self.img_label.config(image=self._photo)


def detect_region(region):
    x1, y1, x2, y2 = region
    with mss.mss() as sct:
        shot = sct.grab({'left': x1, 'top': y1, 'width': x2-x1, 'height': y2-y1})
        arr = np.array(shot)[:, :, :3]
    r = model.predict(source=arr, conf=0.25, iou=0.45,
                                  agnostic_nms=False, max_det=30,
                                  device=0, verbose=False)[0]
    n = len(r.boxes)
    confs = [round(float(c), 3) for c in r.boxes.conf] if n else []
    annotated = r.plot()
    out_path = 'screenshot_result.jpg'
    Image.fromarray(annotated[:, :, ::-1]).save(out_path)
    return n, confs, out_path


def start_detect(root):
    global _busy
    if _busy:
        return
    _busy = True
    try:
        sel = RegionSelector(root)
        root.wait_window(sel)
        region = sel.region
        if not region or (region[2]-region[0] < 5 or region[3]-region[1] < 5):
            return
        n, confs, path = detect_region(region)
        print(f"识别到 {n} 个, 置信度 {confs}")
        rw = ResultWindow(root, path, n, confs)
        root.wait_window(rw)   # 占住 _busy 直到结果窗口关闭, 期间忽略新的 F8
    finally:
        _busy = False


def exclude_from_screen_capture(window):
    # ponytail: 把输出窗口排除出截屏, 否则 mss 会截到自己的实时窗口 -> 画中画递归、框越叠越多
    # 关键: Tk 的 winfo_id() 返回的是内层 client HWND, 必须用 GetAncestor(GA_ROOT)
    # 取到真正带标题栏的顶层窗口句柄, 否则 SetWindowDisplayAffinity 直接返回 0 失败
    if sys.platform != 'win32':
        return False
    window.update_idletasks()
    user32 = ctypes.windll.user32
    GA_ROOT = 2
    hwnd = user32.GetAncestor(window.winfo_id(), GA_ROOT) or window.winfo_id()
    SetAffinity = user32.SetWindowDisplayAffinity
    SetAffinity.restype = ctypes.c_bool
    SetAffinity.argtypes = [ctypes.c_void_p, ctypes.c_uint]
    WDA_EXCLUDEFROMCAPTURE = 0x11   # Win10 2004+: 截屏里直接看穿(显示背景), 最干净
    WDA_MONITOR = 0x1               # 老系统兜底: 截屏里显示为黑块
    if SetAffinity(hwnd, WDA_EXCLUDEFROMCAPTURE):
        return True
    return bool(SetAffinity(hwnd, WDA_MONITOR))


def make_click_through(window):
    # ponytail: 让透明遮罩鼠标穿透, 不挡住下面的真实程序(视频/图片照常操作)
    if sys.platform != 'win32':
        return
    window.update_idletasks()
    user32 = ctypes.windll.user32
    GA_ROOT = 2
    GWL_EXSTYLE = -20
    WS_EX_LAYERED = 0x00080000
    WS_EX_TRANSPARENT = 0x00000020
    hwnd = user32.GetAncestor(window.winfo_id(), GA_ROOT) or window.winfo_id()
    cur = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
    user32.SetWindowLongW(hwnd, GWL_EXSTYLE, cur | WS_EX_LAYERED | WS_EX_TRANSPARENT)


def place_away_from_region(region, win_w, win_h, sw, sh):
    # ponytail: 第二道防线 - 把实时窗口尽量放到框选区域之外, 避免重叠
    rx1, ry1, rx2, ry2 = region
    for x, y in (
        (rx2 + 10, max(0, ry1)),                       # 区域右侧
        (max(0, rx1 - win_w - 10), max(0, ry1)),       # 区域左侧
        (max(0, sw - win_w - 10), ry2 + 10),           # 区域下方
        (max(0, sw - win_w - 10), max(0, ry1 - win_h - 10)),  # 区域上方
    ):
        if 0 <= x and x + win_w <= sw and 0 <= y and y + win_h <= sh:
            if x >= rx2 or x + win_w <= rx1 or y >= ry2 or y + win_h <= ry1:
                return x, y
    # 区域太大无处安放, 退到右下角, 靠 display affinity 兜底
    return max(0, sw - win_w - 10), max(0, sh - win_h - 10)


class LiveMonitor(tk.Toplevel):
    """在识别区域上叠加一层透明遮罩, 只画检测框和置信度, 不显示截取的画面。
    无显眼运行框, 也从根本上消除画中画递归(没有任何窗口显示截图, 自然不会被截回去)。"""
    TRANSPARENT_KEY = 'gray1'   # 用作透明色键的纯色, 画了框/文字的地方不透明, 其余完全看穿

    PAD_TOP = 30   # 顶部额外留白, 用来在框"上方"放提示字

    def __init__(self, master, region):
        super().__init__(master)
        self.region = region
        self.stop_flag = False
        self.update_idletasks()
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        x1, y1, x2, y2 = region
        rw, rh = x2 - x1, y2 - y1

        # 窗口比识别区域高出 PAD_TOP, 多出的这条放在区域上方用来写提示字
        pad = self.PAD_TOP if y1 - self.PAD_TOP >= 0 else 0
        self._pad = pad
        win_y = y1 - pad
        win_h = rh + pad

        # 透明遮罩: 颜色键透明, 鼠标穿透
        self.overrideredirect(True)
        self.attributes('-topmost', True)
        self.geometry(f'{rw}x{win_h}+{x1}+{win_y}')
        self.configure(bg=self.TRANSPARENT_KEY)
        try:
            self.attributes('-transparentcolor', self.TRANSPARENT_KEY)
        except tk.TclError:
            pass   # 非 Windows 退化为半透明遮罩
        self.canvas = tk.Canvas(self, bg=self.TRANSPARENT_KEY, highlightthickness=0,
                                width=rw, height=win_h)
        self.canvas.pack(fill='both', expand=True)

        # 识别区域可见边框(下移 pad, 正好框住真实区域) + 上方提示文字
        self.canvas.create_rectangle(2, pad+2, rw-2, win_h-2, outline='#ff9800', width=3)
        tip = '你看见奶龙了吗?'
        tx, ty = rw // 2, max(11, pad // 2)
        for dx, dy in ((-1,-1),(1,-1),(-1,1),(1,1)):   # 黑色描边
            self.canvas.create_text(tx+dx, ty+dy, text=tip, fill='black',
                                     font=('Microsoft YaHei', 14, 'bold'))
        self.canvas.create_text(tx, ty, text=tip, fill='#ff9800',
                                font=('Microsoft YaHei', 14, 'bold'))

        # 把遮罩排除出截屏 + 鼠标穿透; 必须等窗口 map 后作用在顶层句柄上
        self._exclude_done = threading.Event()
        def _setup_overlay(tries=0):
            ok = exclude_from_screen_capture(self)
            make_click_through(self)
            if ok or tries >= 5:
                self._exclude_done.set()
            else:
                self.after(60, lambda: _setup_overlay(tries+1))
        self.after(0, _setup_overlay)

        # 只保留框和框上的数字, 不显示任何信息条/文字说明。
        # 遮罩鼠标穿透且无焦点, ESC 绑定在窗口上收不到, 故用全局热键停止(在 main 里注册)。
        self._last_arr = None
        self._frame_q = queue.Queue(maxsize=2)
        self.worker = threading.Thread(target=self._loop, daemon=True)
        self.worker.start()
        self._poll_result()

    def _loop(self):
        x1, y1, x2, y2 = self.region
        self._exclude_done.wait(timeout=2.0)   # 等遮罩被排除出截屏后再抓屏, 杜绝首帧递归
        with mss.mss() as sct:
            while not self.stop_flag:
                shot = sct.grab({'left': x1, 'top': y1, 'width': x2-x1, 'height': y2-y1})
                arr = np.array(shot)[:, :, :3]   # BGR
                r = model.predict(source=arr, conf=0.5, iou=0.5,
                                  agnostic_nms=False, max_det=30,
                                  device=DEVICE, verbose=False)[0]
                n = len(r.boxes)
                confs = [round(float(c), 3) for c in r.boxes.conf] if n else []
                # 只取框坐标(相对区域左上角), 不传画面
                boxes = r.boxes.xyxy.cpu().numpy().tolist() if n else []
                self._last_arr = arr
                if self._frame_q.full():
                    try: self._frame_q.get_nowait()
                    except queue.Empty: pass
                self._frame_q.put((n, confs, boxes))
        if self._last_arr is not None:
            Image.fromarray(self._last_arr[:, :, ::-1]).save('live_last.jpg')

    def _poll_result(self):
        if self.stop_flag:
            return
        try:
            n, confs, boxes = self._frame_q.get_nowait()
            self.canvas.delete('det')
            pad = self._pad   # 画布顶部留白偏移, 框坐标相对截图区域, 需下移 pad 才对准
            for i, (bx1, by1, bx2, by2) in enumerate(boxes):
                self.canvas.create_rectangle(bx1, by1+pad, bx2, by2+pad,
                                             outline='#00ff00', width=3, tags='det')
                label = f'{confs[i]:.2f}' if i < len(confs) else ''
                if label:
                    self.canvas.create_text(bx1+2, max(pad, by1+pad-9), text=label, anchor='w',
                                            fill='#00ff00', font=('Arial', 11, 'bold'), tags='det')
        except queue.Empty:
            pass
        if not self.stop_flag:
            self.after(50, self._poll_result)

    def stop(self):
        self.stop_flag = True
        try: self.destroy()
        except Exception: pass


_live = None   # 当前实时识别窗口, 供全局热键停止


def start_live(root):
    global _busy, _live
    if _busy:
        return
    _busy = True
    try:
        sel = RegionSelector(root)
        root.wait_window(sel)
        region = sel.region
        if not region or (region[2]-region[0] < 5 or region[3]-region[1] < 5):
            return
        _live = LiveMonitor(root, region)
        root.wait_window(_live)   # 占住 _busy 直到实时窗口关闭, 期间忽略新的 F9
    finally:
        _live = None
        _busy = False


def stop_live():
    # 全局热键回调(ESC / 再按 F9)从 keyboard 线程触发, 用 after 切回主线程安全停止
    if _live is not None:
        try:
            _live.after(0, _live.stop)
        except Exception:
            pass


def _show_loading(root):
    # 小而精简的居中加载窗: 无边框, 圆点提示文字 + 一句操作提示
    win = tk.Toplevel(root)
    win.overrideredirect(True)
    win.attributes('-topmost', True)
    w, h = 300, 132
    sw, sh = win.winfo_screenwidth(), win.winfo_screenheight()
    win.geometry(f'{w}x{h}+{(sw-w)//2}+{(sh-h)//2}')
    win.configure(bg='#1e88e5')
    frame = tk.Frame(win, bg='#1e88e5')
    frame.pack(expand=True)
    tk.Label(frame, text='奶龙识别', fg='white', bg='#1e88e5',
             font=('Microsoft YaHei', 13, 'bold')).pack(pady=(0, 4))
    lbl = tk.Label(frame, text='正在加载模型', fg='#cfe3ff', bg='#1e88e5',
                   font=('Microsoft YaHei', 10))
    lbl.pack()

    tk.Label(frame, text='F8 单次识别   F9 实时识别   ESC 退出',
             fg='white', bg='#1e88e5', font=('Microsoft YaHei', 9)).pack(pady=(8, 0))
    tk.Label(frame, text='右下角图标点一下开始 · 悬停看说明',
             fg='#cfe3ff', bg='#1e88e5', font=('Microsoft YaHei', 8)).pack(pady=(2, 0))

    def animate(n=0):
        if not win.winfo_exists():
            return
        lbl.config(text='正在加载模型' + '.' * (n % 4))
        win.after(350, lambda: animate(n + 1))
    animate()
    return win


def main():
    root = tk.Tk()
    root.withdraw()
    live_trigger = threading.Event()

    def on_f9():
        # 正在实时识别时按 F9 = 停止; 否则 = 发起新的框选识别
        if _busy:
            stop_live()
        else:
            live_trigger.set()

    def on_esc():
        # ESC = 彻底退出程序(先停实时识别, 再清理热键并关闭主循环)
        stop_live()
        keyboard.unhook_all()
        root.after(0, root.destroy)

    loading = _show_loading(root)
    ready = threading.Event()
    threading.Thread(target=lambda: (load_model(), ready.set()), daemon=True).start()
    _t0 = time.monotonic()
    MIN_SHOW = 1.8   # 加载窗最短显示秒数, 保证能看清提示(否则加载太快一闪而过)

    def on_ready():
        if not ready.is_set() or (time.monotonic() - _t0) < MIN_SHOW:
            root.after(100, on_ready)
            return
        try: loading.destroy()
        except Exception: pass
        keyboard.add_hotkey('f8', lambda: trigger.set())
        keyboard.add_hotkey('f9', on_f9)
        keyboard.add_hotkey('esc', on_esc)
        FloatButton(root, lambda: trigger.set())

        def poll():
            if trigger.isSet():
                trigger.clear()
                start_detect(root)
            if live_trigger.isSet():
                live_trigger.clear()
                start_live(root)
            root.after(200, poll)
        root.after(200, poll)

    root.after(100, on_ready)
    root.mainloop()


if __name__ == '__main__':
    main()