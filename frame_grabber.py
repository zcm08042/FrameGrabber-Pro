# -*- coding: utf-8 -*-
# ===== 帧捕获 · FrameGrabber — 莫兰迪暗色版 =====
import os, sys, math, json, tempfile
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from pathlib import Path
import cv2
from PIL import Image, ImageTk, ImageDraw, ImageFont

# ===== 配置 =====
CONFIG_PATH = Path.home() / ".frame_grabber_config.json"

def load_config():
    if CONFIG_PATH.exists():
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            pass
    return {}

def save_config(cfg):
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)

# ===== 配色 — 莫兰迪暗色 =====
BG_DARK       = "#161618"      # 深灰暖底
BG_TOP        = "#111113"      # 顶栏更深
BG_CARD       = "#1e1e22"      # 卡片
BG_HOVER      = "#2a2a30"      # 悬停
BORDER        = "#33333c"      # 边框

M_BLUE        = "#7a9eb3"      # 莫兰迪蓝（主色）
M_BLUE_DIM    = "#4a6a7a"      # 暗蓝
M_ROSE        = "#c4a4a4"      # 莫兰迪粉
M_SAGE        = "#9ab3a8"      # 莫兰迪绿
M_GOLD        = "#c4b08a"      # 莫兰迪金
M_LAVENDER    = "#a8a0c0"      # 莫兰迪紫

TEXT          = "#d8d8e0"      # 主文字
TEXT_DIM      = "#8a8a96"      # 次要文字
TEXT_MUTED    = "#555566"      # 极淡文字

# ===== 自绘图标 =====
def create_app_icon(size=64):
    """绘制一个胶片/播放风格的图标"""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    s = size

    # 圆角矩形背景（莫兰迪蓝）
    margin = 6
    draw.rounded_rectangle(
        [margin, margin, s - margin, s - margin],
        radius=10, fill="#7a9eb3",
    )

    # 内层深色框（取景框）
    inner_m = margin + 8
    draw.rounded_rectangle(
        [inner_m, inner_m, s - inner_m, s - inner_m],
        radius=4, fill="#2a3038",
    )

    # 播放三角
    cx, cy = s // 2 + 2, s // 2
    tri = [(cx - 7, cy - 8), (cx - 7, cy + 8), (cx + 10, cy)]
    draw.polygon(tri, fill="#7a9eb3")

    # 左上角小胶片孔
    holes = [(margin + 3, margin + 3), (s - margin - 7, margin + 3),
             (margin + 3, s - margin - 7), (s - margin - 7, s - margin - 7)]
    for hx, hy in holes:
        draw.rectangle([hx, hy, hx + 4, hy + 4], fill="#c4a4a4")

    return img

def generate_icon_file():
    """生成 .ico 文件并返回路径"""
    ico_path = os.path.join(tempfile.gettempdir(), "_fg_icon.ico")
    img = create_app_icon(64)
    # 同时生成 32x32 和 64x64
    img32 = img.resize((32, 32), Image.LANCZOS)
    # PIL 保存 .ico 时需要包含多个尺寸
    img32.save(ico_path, format="ICO", sizes=[(32, 32), (64, 64)])
    return ico_path

# ===== Windows 拖放 =====
if sys.platform == "win32":
    import ctypes
    from ctypes import wintypes, create_unicode_buffer
    user32 = ctypes.windll.user32
    shell32 = ctypes.windll.shell32
    ole32 = ctypes.windll.ole32
    WS_EX_ACCEPTFILES = 0x00000010
    GWL_EXSTYLE = -20

    def enable_drag_drop(hwnd, callback):
        exstyle = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
        user32.SetWindowLongW(hwnd, GWL_EXSTYLE, exstyle | WS_EX_ACCEPTFILES)
        ole32.DragAcceptFiles(hwnd, True)
        WNDPROC = ctypes.WINFUNCTYPE(ctypes.c_longlong, ctypes.c_void_p,
                                      ctypes.c_uint, ctypes.c_void_p, ctypes.c_void_p)
        old_proc = user32.SetWindowLongPtrW(hwnd, -4, 0)
        def wnd_proc(hwnd_inner, msg, wParam, lParam):
            if msg == 0x0233:
                hdrop = wParam
                nfiles = shell32.DragQueryFileW(hdrop, 0xFFFFFFFF, None, 0)
                files = []
                for i in range(nfiles):
                    bufsize = shell32.DragQueryFileW(hdrop, i, None, 0) + 1
                    buf = create_unicode_buffer(bufsize)
                    shell32.DragQueryFileW(hdrop, i, buf, bufsize)
                    files.append(buf.value)
                shell32.DragFinish(hdrop)
                if files:
                    callback(files[0])
                return 0
            return user32.CallWindowProcW(old_proc, hwnd_inner, msg, wParam, lParam)
        proc = WNDPROC(wnd_proc)
        ctypes.windll.user32.SetWindowLongPtrW.restype = ctypes.c_longlong
        old_proc = user32.SetWindowLongPtrW(hwnd, -4, ctypes.cast(proc, ctypes.c_void_p).value)
        return old_proc, proc
else:
    def enable_drag_drop(hwnd, callback):
        return None, None

# ===== 按钮工厂 =====
def _make_btn(parent, text, command, bg=BG_CARD, fg=TEXT, font_size=10, bold=False,
              padx=14, pady=5, cursor="hand2", hover_bg=None, hover_fg=None,
              state=tk.NORMAL):
    kw = dict(
        text=text, command=command, bg=bg, fg=fg,
        font=("Microsoft YaHei UI", font_size, "bold" if bold else "normal"),
        relief=tk.FLAT, padx=padx, pady=pady, cursor=cursor,
        activebackground=hover_bg or bg, activeforeground=hover_fg or fg,
        bd=0, state=state,
    )
    btn = tk.Button(parent, **kw)
    def on_enter(e):
        if btn.cget("state") != tk.DISABLED:
            btn.configure(bg=hover_bg or BG_HOVER)
    def on_leave(e):
        if btn.cget("state") != tk.DISABLED:
            btn.configure(bg=bg)
    btn.bind("<Enter>", on_enter)
    btn.bind("<Leave>", on_leave)
    return btn

# ===== 样式表 =====
def _apply_ttk_styles():
    style = ttk.Style()
    style.theme_use("clam")
    style.configure("Morandi.Horizontal.TScale",
                    background=BG_TOP, troughcolor="#28282e",
                    bordercolor=BG_TOP, lightcolor=BG_TOP,
                    darkcolor=BG_TOP, sliderthickness=16,
                    troughrelief="flat")
    style.map("Morandi.Horizontal.TScale",
              background=[("active", BG_TOP)])
    return style

# ===== Toast =====
class Toast:
    def __init__(self, parent):
        self.parent = parent
        self._current = None

    def _close_current(self):
        if self._current:
            try: self._current.destroy()
            except: pass
            self._current = None

    def show(self, text, kind="success"):
        colors = {
            "success": (M_SAGE, "#1a2420"),
            "info":    (M_BLUE, "#1a2228"),
            "warn":    (M_GOLD, "#24201a"),
            "dim":     (TEXT_DIM, BG_CARD),
        }
        fg, bg = colors.get(kind, colors["info"])
        self._close_current()
        w = tk.Toplevel(self.parent)
        w.overrideredirect(True)
        w.attributes("-topmost", True)
        px, py = self.parent.winfo_rootx(), self.parent.winfo_rooty()
        pw = self.parent.winfo_width()
        frame = tk.Frame(w, bg=bg, highlightthickness=1, highlightbackground=fg)
        frame.pack()
        tk.Label(frame, text="  %s  " % text, fg=fg, bg=bg,
                 font=("Microsoft YaHei UI", 10), padx=22, pady=9).pack()
        w.update_idletasks()
        w.geometry("+%d+%d" % (px + (pw - w.winfo_width()) // 2, py + 55))
        w.attributes("-alpha", 0.0)
        self._current = w
        self._fade_in(w, 0)

    def _fade_in(self, w, step):
        if not self._current or not w.winfo_exists(): return
        w.attributes("-alpha", (step + 1) / 10.0)
        if step < 9: w.after(12, lambda: self._fade_in(w, step + 1))
        else: w.after(1800, lambda: self._fade_out(w, 9))

    def _fade_out(self, w, step):
        if not w.winfo_exists(): return
        w.attributes("-alpha", step / 10.0)
        if step > 0: w.after(12, lambda: self._fade_out(w, step - 1))
        else:
            try: w.destroy()
            except: pass
            if self._current is w: self._current = None

# ===== 空状态 =====
def _draw_empty_state_canvas(canvas):
    cw, ch = canvas.winfo_width(), canvas.winfo_height()
    if cw < 50: cw, ch = 900, 450
    cx, cy = cw // 2, ch // 2
    canvas.delete("all")
    bw, bh = 280, 170
    x1, y1 = cx - bw // 2, cy - bh // 2 - 10
    x2, y2 = cx + bw // 2, cy + bh // 2 - 10

    # 柔和虚线框
    edges = [(x1, y1, x2, y1), (x2, y1, x2, y2),
             (x2, y2, x1, y2), (x1, y2, x1, y1)]
    for sx, sy, ex, ey in edges:
        length = math.hypot(ex - sx, ey - sy)
        if length == 0: continue
        dx, dy = (ex - sx) / length, (ey - sy) / length
        d = 0
        while d < length:
            lx, ly = sx + dx * d, sy + dy * d
            rem = min(6, length - d)
            rx, ry = lx + dx * rem, ly + dy * rem
            canvas.create_line(lx, ly, rx, ry, fill="#333344", width=2, tags="empty")
            d += 14

    # 播放三角
    half = 16
    canvas.create_polygon(cx - half * 0.4, cy - half - 8,
                           cx - half * 0.4, cy + half - 8,
                           cx + half * 0.7, cy - 8,
                           fill="#444455", outline="", tags="empty")

    canvas.create_text(cx, cy + 8, text="📂 拖拽视频文件到此处",
                        fill=TEXT_DIM, font=("Microsoft YaHei UI", 14), tags="empty")
    canvas.create_text(cx, cy + 36, text="或点击上方 「打开视频」 按钮",
                        fill=TEXT_MUTED, font=("Microsoft YaHei UI", 10), tags="empty")
    hints = [("⌨", "Ctrl+O 打开"), ("◀▶", "方向键逐帧"),
             ("⏪⏩", "Shift跳秒"), ("💾", "Ctrl+S 保存")]
    hy = cy + 68
    canvas.create_text(cx, hy, text="— 快捷键 —", fill=TEXT_MUTED,
                        font=("Microsoft YaHei UI", 8, "bold"), tags="empty")
    for i, (icon, txt) in enumerate(hints):
        canvas.create_text(cx - 180 + i * 120, hy + 20,
                            text="%s  %s" % (icon, txt), fill="#444466",
                            font=("Microsoft YaHei UI", 9), tags="empty")

# ===== 设置弹窗 =====
class SettingsDialog:
    def __init__(self, parent, current_dir, on_save):
        self.result_dir = current_dir
        self.on_save = on_save
        self.top = tk.Toplevel(parent)
        self.top.title("设置")
        self.top.geometry("520x210")
        self.top.resizable(False, False)
        self.top.configure(bg=BG_TOP)
        self.top.transient(parent)
        self.top.grab_set()
        self.top.update_idletasks()
        px, py = parent.winfo_rootx(), parent.winfo_rooty()
        pw, ph = parent.winfo_width(), parent.winfo_height()
        tw, th = self.top.winfo_width(), self.top.winfo_height()
        self.top.geometry("+%d+%d" % (px + (pw-tw)//2, py + (ph-th)//2))

        tframe = tk.Frame(self.top, bg=BG_TOP)
        tframe.pack(fill=tk.X, padx=24, pady=(20, 4))
        tk.Label(tframe, text="⚙ 设置", fg=M_BLUE, bg=BG_TOP,
                 font=("Microsoft YaHei UI", 14, "bold")).pack(anchor="w")
        underline = tk.Frame(tframe, bg=M_BLUE, height=2)
        underline.pack(fill=tk.X, pady=(4, 0))

        body = tk.Frame(self.top, bg=BG_TOP)
        body.pack(fill=tk.BOTH, expand=True, padx=24, pady=(16, 0))
        row = tk.Frame(body, bg=BG_TOP)
        row.pack(fill=tk.X)
        tk.Label(row, text="📁 默认保存位置", fg=TEXT_DIM, bg=BG_TOP,
                 font=("Microsoft YaHei UI", 10)).pack(side=tk.LEFT)
        self.dir_var = tk.StringVar(value=current_dir or "未设置（每次询问）")
        self.lbl_dir = tk.Label(row, textvariable=self.dir_var, fg=M_BLUE, bg=BG_TOP,
                                 font=("Microsoft YaHei UI", 9), cursor="hand2")
        self.lbl_dir.pack(side=tk.RIGHT)

        btn_row = tk.Frame(body, bg=BG_TOP)
        btn_row.pack(fill=tk.X, pady=(16, 0))
        _make_btn(btn_row, "📂 选择文件夹", self._pick_dir, bg=BG_CARD, fg=TEXT,
                  font_size=10, padx=16, pady=5, hover_bg=BG_HOVER).pack(side=tk.LEFT, padx=(0, 6))
        _make_btn(btn_row, "🗑 清除", self._clear, bg=BG_CARD, fg=TEXT_DIM,
                  font_size=10, padx=14, pady=5, hover_bg=BG_HOVER).pack(side=tk.LEFT)

        bottom = tk.Frame(self.top, bg=BG_TOP)
        bottom.pack(side=tk.BOTTOM, fill=tk.X, padx=24, pady=(12, 18))
        _make_btn(bottom, "✔ 保存", self._save, bg=M_BLUE_DIM, fg="#ffffff",
                  font_size=10, bold=True, padx=22, pady=5, hover_bg="#5a8aa0").pack(side=tk.RIGHT)
        _make_btn(bottom, "✖ 取消", self.top.destroy, bg=BG_CARD, fg=TEXT_DIM,
                  font_size=10, padx=16, pady=5, hover_bg=BG_HOVER).pack(side=tk.RIGHT, padx=(0, 8))

    def _pick_dir(self):
        d = filedialog.askdirectory(title="选择默认保存目录")
        if d: self.result_dir = d; self.dir_var.set(d)
    def _clear(self):
        self.result_dir = ""; self.dir_var.set("未设置（每次询问）")
    def _save(self):
        self.on_save(self.result_dir); self.top.destroy()


# ===== 主应用 =====
class VideoFrameGrabberPro:
    def __init__(self):
        self.config = load_config()
        self.default_save_dir = self.config.get("save_dir", "")
        self.root = tk.Tk()
        self.root.title("帧捕获")
        self.root.geometry("1100x720")
        self.root.minsize(860, 560)
        self.root.configure(bg=BG_DARK)

        # 设置图标
        try:
            ico_path = generate_icon_file()
            self.root.iconbitmap(ico_path)
        except:
            pass

        self.cap = None
        self.current_frame = 0
        self.total_frames = 0
        self.fps = 25
        self.video_path = None
        self.frame_image = None
        self.photo = None
        self.toast = Toast(self.root)
        self._drag_refs = None
        self._frame_cache = {}
        self._cache_max = 5
        self._resize_timer = None
        self._slider_timer = None
        self._slider_pending_idx = None
        _apply_ttk_styles()
        self._build_ui()
        self._bind_keys()
        self.root.after(200, self._enable_dnd)
        self.root.bind("<Configure>", self._on_window_configure)

    def _enable_dnd(self):
        try:
            hwnd = int(self.root.frame(), 16)
            self._drag_refs = enable_drag_drop(hwnd, self._on_drop_file)
        except: pass

    def _on_drop_file(self, fp):
        if os.path.isfile(fp): self.open_video(fp)

    def _build_ui(self):
        hdr = tk.Frame(self.root, bg=BG_TOP, height=52)
        hdr.pack(fill=tk.X, side=tk.TOP)
        hdr.pack_propagate(False)

        # 顶部细线
        hdr_line = tk.Frame(hdr, bg=M_BLUE, height=1)
        hdr_line.pack(side=tk.BOTTOM, fill=tk.X)

        tf = tk.Frame(hdr, bg=BG_TOP)
        tf.pack(side=tk.LEFT, padx=(18, 0), pady=12)
        # 图标占位符
        tk.Label(tf, text="▣", bg=BG_TOP, fg=M_BLUE,
                 font=("Segoe UI", 16)).pack(side=tk.LEFT)
        tk.Label(tf, text=" 帧捕获", fg=TEXT, bg=BG_TOP,
                 font=("Microsoft YaHei UI", 13, "bold")).pack(side=tk.LEFT)
        tk.Label(tf, text=" 〢 视频截帧工具", fg=M_ROSE, bg=BG_TOP,
                 font=("Microsoft YaHei UI", 9)).pack(side=tk.LEFT, padx=(6, 0))

        rf = tk.Frame(hdr, bg=BG_TOP)
        rf.pack(side=tk.RIGHT, padx=14, pady=8)
        self.btn_settings = _make_btn(rf, "⚙ 设置", self._open_settings,
                                       bg=BG_DARK, fg=TEXT_DIM, font_size=10,
                                       padx=10, pady=4, hover_bg=BG_HOVER, hover_fg=TEXT)
        self.btn_settings.pack(side=tk.LEFT, padx=2)
        self.btn_open = _make_btn(rf, "📂 打开视频", self.open_video,
                                   bg=BG_CARD, fg=M_BLUE, font_size=10,
                                   padx=14, pady=4, hover_bg=BG_HOVER)
        self.btn_open.pack(side=tk.LEFT, padx=4)
        self.btn_save = _make_btn(rf, "💾 保存帧", self.save_frame,
                                   bg="#1a2420", fg=M_SAGE, font_size=10, bold=True,
                                   padx=14, pady=4, hover_bg="#202e28", hover_fg=M_SAGE,
                                   state=tk.DISABLED)
        self.btn_save.pack(side=tk.LEFT, padx=2)

        main = tk.Frame(self.root, bg=BG_DARK)
        main.pack(fill=tk.BOTH, expand=True, padx=14, pady=(10, 0))
        card = tk.Frame(main, bg=BG_CARD, highlightthickness=1, highlightbackground=BORDER)
        card.pack(fill=tk.BOTH, expand=True)
        self.canvas = tk.Canvas(card, bg="#0e0e12", highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)
        self.canvas.bind("<Button-1>", self._on_canvas_click)
        _draw_empty_state_canvas(self.canvas)

        ib = tk.Frame(main, bg=BG_CARD, height=30)
        ib.pack(fill=tk.X, pady=(6, 0)); ib.pack_propagate(False)
        self.lbl_file = tk.Label(ib, text="▣ 未打开视频", fg=TEXT_DIM, bg=BG_CARD,
                                  font=("Microsoft YaHei UI", 9), anchor="w")
        self.lbl_file.pack(side=tk.LEFT, padx=12, pady=5)
        self.lbl_res = tk.Label(ib, text="", fg=TEXT_DIM, bg=BG_CARD,
                                 font=("Consolas", 9), anchor="e")
        self.lbl_res.pack(side=tk.RIGHT, padx=12, pady=5)
        if self.default_save_dir:
            self.lbl_save_dir = tk.Label(ib, text="📁 %s" % self.default_save_dir,
                                          fg=M_SAGE, bg=BG_CARD,
                                          font=("Microsoft YaHei UI", 8), anchor="e")
            self.lbl_save_dir.pack(side=tk.RIGHT, padx=(0, 12), pady=5)

        ctrl = tk.Frame(self.root, bg=BG_TOP, height=120)
        ctrl.pack(fill=tk.X, side=tk.BOTTOM)
        ctrl.pack_propagate(False)

        # 底部细线（顶部）
        ctrl_line = tk.Frame(ctrl, bg=M_ROSE, height=1)
        ctrl_line.pack(side=tk.TOP, fill=tk.X)

        # 时间行
        tf2 = tk.Frame(ctrl, bg=BG_TOP)
        tf2.pack(fill=tk.X, padx=20, pady=(8, 2))
        self.lbl_current = tk.Label(tf2, text="00:00", fg=M_BLUE, bg=BG_TOP,
                                     font=("Consolas", 15, "bold"))
        self.lbl_current.pack(side=tk.LEFT)
        self.lbl_fnum = tk.Label(tf2, text="", fg=TEXT_DIM, bg=BG_TOP,
                                  font=("Microsoft YaHei UI", 9))
        self.lbl_fnum.pack(side=tk.LEFT, padx=(8, 0))
        self.lbl_total = tk.Label(tf2, text="/ 00:00", fg=TEXT_MUTED, bg=BG_TOP,
                                   font=("Consolas", 13))
        self.lbl_total.pack(side=tk.RIGHT)

        # 跳转输入
        jump_frame = tk.Frame(ctrl, bg=BG_TOP)
        jump_frame.pack(side=tk.RIGHT, padx=(0, 20), pady=(4, 0))
        tk.Label(jump_frame, text="跳至", fg=TEXT_DIM, bg=BG_TOP,
                 font=("Microsoft YaHei UI", 9)).pack(side=tk.LEFT, padx=(0, 4))
        self.time_entry = tk.Entry(jump_frame, width=10, bg=BG_CARD, fg=M_BLUE,
                                    insertbackground=M_BLUE, font=("Consolas", 10),
                                    relief=tk.FLAT, bd=0,
                                    highlightthickness=1, highlightbackground=BORDER,
                                    highlightcolor=M_BLUE)
        self.time_entry.insert(0, "0")
        self.time_entry.pack(side=tk.LEFT, padx=(0, 4), ipady=3, ipadx=4)
        _make_btn(jump_frame, "▶ 跳转", self._jump_to_time,
                  bg=M_BLUE_DIM, fg="#ffffff", font_size=9, bold=True,
                  padx=10, pady=3, hover_bg="#5a8aa0").pack(side=tk.LEFT)
        tk.Label(jump_frame, text="(秒 / mm:ss)", fg=TEXT_MUTED, bg=BG_TOP,
                 font=("Microsoft YaHei UI", 8)).pack(side=tk.LEFT, padx=(4, 0))

        # 进度条
        self.slider = ttk.Scale(ctrl, from_=0, to=100, orient=tk.HORIZONTAL,
                                command=self._on_slider, style="Morandi.Horizontal.TScale")
        self.slider.pack(fill=tk.X, padx=20, pady=(4, 2))
        self.slider.config(state=tk.DISABLED)

        # 导航按钮
        nav = tk.Frame(ctrl, bg=BG_TOP)
        nav.pack(fill=tk.X, padx=12, pady=(2, 8))
        bgf = tk.Frame(nav, bg=BG_TOP)
        bgf.pack(expand=True)
        btns = [("⏪ -10s", lambda: self._jump_seconds(-10)),
                ("◀ -1s",   lambda: self._jump_seconds(-1)),
                ("◁ 上一帧", lambda: self._jump(-1)),
                ("下一帧 ▷", lambda: self._jump(1)),
                ("+1s ▶",   lambda: self._jump_seconds(1)),
                ("+10s ⏩",  lambda: self._jump_seconds(10))]
        for txt, cmd in btns:
            _make_btn(bgf, txt, cmd, bg=BG_CARD, fg=TEXT, font_size=9,
                      padx=11, pady=4, hover_bg=BG_HOVER).pack(side=tk.LEFT, padx=3)

    def _jump_to_time(self):
        text = self.time_entry.get().strip()
        if not text: return
        try:
            if ":" in text:
                parts = [int(x) for x in text.split(":")]
                if len(parts) == 2: seconds = parts[0] * 60 + parts[1]
                elif len(parts) == 3: seconds = parts[0] * 3600 + parts[1] * 60 + parts[2]
                else: raise ValueError
            else: seconds = float(text)
        except:
            self.toast.show("输入格式错误，请输入秒数或 mm:ss", kind="warn")
            return
        if not self.cap or self.fps <= 0:
            self.toast.show("请先打开视频", kind="warn"); return
        idx = max(0, min(int(seconds * self.fps), max(self.total_frames - 1, 0)))
        self._show_frame(idx)
        self.time_entry.delete(0, tk.END)
        self.time_entry.insert(0, self._fmt(idx / self.fps))

    def _bind_keys(self):
        self.root.bind("<Control-o>", lambda e: self.open_video())
        self.root.bind("<Control-s>", lambda e: self.save_frame())
        self.root.bind("<Control-S>", lambda e: self.save_frame())
        self.root.bind("<Left>", lambda e: self._jump(-1))
        self.root.bind("<Right>", lambda e: self._jump(1))
        self.root.bind("<Shift-Left>", lambda e: self._jump_seconds(-1))
        self.root.bind("<Shift-Right>", lambda e: self._jump_seconds(1))
        self.root.bind("<Control-Left>", lambda e: self._jump_seconds(-10))
        self.root.bind("<Control-Right>", lambda e: self._jump_seconds(10))
        self.time_entry.bind("<Return>", lambda e: self._jump_to_time())

    def _on_canvas_click(self, e):
        if self.cap is None: self.open_video()
    def _open_settings(self):
        SettingsDialog(self.root, self.default_save_dir, self._on_settings_saved)

    def _on_settings_saved(self, new_dir):
        self.default_save_dir = new_dir if new_dir else ""
        self.config["save_dir"] = self.default_save_dir
        save_config(self.config)
        if hasattr(self, "lbl_save_dir"): self.lbl_save_dir.destroy()
        if self.default_save_dir:
            ib = self.lbl_file.master
            self.lbl_save_dir = tk.Label(ib, text="📁 %s" % self.default_save_dir,
                                          fg=M_SAGE, bg=BG_CARD,
                                          font=("Microsoft YaHei UI", 8), anchor="e")
            self.lbl_save_dir.pack(side=tk.RIGHT, padx=(0, 12), pady=5)
        self.toast.show("默认保存位置已设置" if self.default_save_dir
                        else "已清除默认位置，保存时将询问",
                        kind="success" if self.default_save_dir else "dim")

    def _on_window_configure(self, event):
        if self._resize_timer: self.root.after_cancel(self._resize_timer)
        self._resize_timer = self.root.after(150, self._do_resize_update)
    def _do_resize_update(self):
        self._resize_timer = None
        if self.cap and self.current_frame >= 0 and self.frame_image is not None:
            self._render_frame(self.frame_image)
        elif not self.cap: _draw_empty_state_canvas(self.canvas)

    def open_video(self, path=None):
        if not path:
            path = filedialog.askopenfilename(
                title="选择视频文件",
                filetypes=[("视频文件", "*.mp4 *.mkv *.avi *.mov *.flv *.wmv *.webm *.m4v *.ts"),
                           ("所有文件", "*.*")])
        if not path: return
        if self.cap: self.cap.release()
        self.cap = cv2.VideoCapture(path)
        if not self.cap.isOpened(): messagebox.showerror("错误", "无法打开视频文件"); return
        self.video_path = path
        self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.fps = self.cap.get(cv2.CAP_PROP_FPS)
        if self.fps <= 0: self.fps = 25
        ret, frame = self.cap.read()
        h, w = frame.shape[:2] if ret else (0, 0)
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
        self.current_frame = 0
        self._frame_cache.clear()
        self.slider.config(state=tk.NORMAL, to=max(self.total_frames - 1, 0))
        self.btn_save.config(state=tk.NORMAL)
        self.canvas.delete("all")
        dur = self.total_frames / self.fps
        self.lbl_file.config(text="▣ %s" % Path(path).name)
        self.lbl_res.config(text="%dx%d  │  %d 帧  │  %.0f fps  │  %s" %
                            (w, h, self.total_frames, self.fps, self._fmt(dur)))
        self._show_frame(0)
        self.toast.show("已加载: %s" % Path(path).stem, kind="success")

    def _get_frame(self, idx):
        idx = max(0, min(idx, max(self.total_frames - 1, 0)))
        if idx in self._frame_cache: return self._frame_cache[idx]
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
        ret, frame = self.cap.read()
        if not ret: return None
        if len(self._frame_cache) >= self._cache_max:
            oldest = next(iter(self._frame_cache))
            if oldest != self.current_frame: del self._frame_cache[oldest]
        self._frame_cache[idx] = frame
        return frame

    def _render_frame(self, frame_bgr):
        if frame_bgr is None: return
        h, w = frame_bgr.shape[:2]
        cw, ch = self.canvas.winfo_width() - 4, self.canvas.winfo_height() - 4
        if cw < 50: cw, ch = 900, 450
        scale = min(cw / w, ch / h)
        nw, nh = int(w * scale), int(h * scale)
        rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        img = Image.fromarray(rgb).resize((nw, nh), Image.BILINEAR)
        self.photo = ImageTk.PhotoImage(img)
        self.canvas.delete("preview")
        self.canvas.create_image(cw // 2 + 2, ch // 2 + 2,
                                  image=self.photo, anchor=tk.CENTER, tags="preview")

    def _show_frame(self, idx):
        if not self.cap: return
        if idx == self.current_frame and self.frame_image is not None: return
        idx = max(0, min(idx, max(self.total_frames - 1, 0)))
        frame = self._get_frame(idx)
        if frame is None: return
        self.current_frame = idx
        self.frame_image = frame
        self._render_frame(frame)
        self.slider.set(idx)
        s, ts = idx / self.fps, self.total_frames / max(self.fps, 1)
        self.lbl_current.config(text=self._fmt(s))
        self.lbl_total.config(text="/ %s" % self._fmt(ts))
        self.lbl_fnum.config(text="第 %d / %d 帧" % (idx + 1, self.total_frames))

    def _on_slider(self, val):
        idx = int(float(val))
        if self._slider_timer: self.root.after_cancel(self._slider_timer); self._slider_timer = None
        if abs(idx - self.current_frame) > 5:
            self._slider_pending_idx = idx
            self._slider_timer = self.root.after(80, self._flush_slider)
        elif idx != self.current_frame:
            self._show_frame(idx)
    def _flush_slider(self):
        self._slider_timer = None
        if self._slider_pending_idx is not None:
            self._show_frame(self._slider_pending_idx)
            self._slider_pending_idx = None

    def _jump(self, d): self._show_frame(self.current_frame + d)
    def _jump_seconds(self, ds): self._show_frame(self.current_frame + int(ds * self.fps))

    @staticmethod
    def _fmt(sec):
        m, s = divmod(int(sec), 60)
        h, m = divmod(m, 60)
        return "%d:%02d:%02d" % (h, m, s) if h else "%02d:%02d" % (m, s)

    def save_frame(self):
        if self.frame_image is None: return
        dn = "%s_%s.png" % (Path(self.video_path).stem,
                            self._fmt(self.current_frame / self.fps).replace(":", "-"))
        if self.default_save_dir and os.path.isdir(self.default_save_dir):
            save_path = os.path.join(self.default_save_dir, dn)
            if cv2.imwrite(save_path, self.frame_image): self.toast.show("已保存: %s" % dn, kind="success")
            else: messagebox.showerror("错误", "保存失败")
            return
        path = filedialog.asksaveasfilename(
            title="保存当前帧", initialdir=self.default_save_dir or "", initialfile=dn,
            defaultextension=".png",
            filetypes=[("PNG 无损", "*.png"), ("JPEG 高质量", "*.jpg"), ("BMP 位图", "*.bmp")])
        if not path: return
        if cv2.imwrite(path, self.frame_image): self.toast.show("已保存: %s" % Path(path).name, kind="success")
        else: messagebox.showerror("错误", "保存失败")

    def run(self): self.root.mainloop()

if __name__ == "__main__":
    app = VideoFrameGrabberPro()
    app.run()
