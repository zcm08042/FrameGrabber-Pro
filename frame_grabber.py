import os
import sys
import time
import math
import json
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from pathlib import Path
import cv2
from PIL import Image, ImageTk

# ============================================================
# Config
# ============================================================
CONFIG_PATH = Path.home() / ".frame_grabber_config.json"

def load_config():
    try:
        if CONFIG_PATH.exists():
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return {}

def save_config(cfg):
    try:
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

# ============================================================
# Color Scheme (GitHub Dark inspired)
# ============================================================
BG_DARK   = "#0d1117"
BG_CARD   = "#161b22"
BG_HOVER  = "#21262d"
BORDER    = "#30363d"
ACCENT    = "#58a6ff"
ACCENT2   = "#3fb950"
ACCENT3   = "#f0883e"
TEXT      = "#e6edf3"
TEXT_DIM  = "#8b949e"
HEADER_BG = "#010409"
CANVAS_BG = "#000000"

# ============================================================
# Drag & Drop (Windows)
# ============================================================
if sys.platform == "win32":
    import ctypes
    from ctypes import wintypes, create_unicode_buffer
    user32  = ctypes.windll.user32
    shell32 = ctypes.windll.shell32
    ole32   = ctypes.windll.ole32
    WS_EX_ACCEPTFILES = 16
    GWL_EXSTYLE       = -20

    def enable_drag_drop(hwnd, callback):
        exstyle = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
        user32.SetWindowLongW(hwnd, GWL_EXSTYLE, exstyle | WS_EX_ACCEPTFILES)
        ole32.DragAcceptFiles(hwnd, True)

        WNDPROC = ctypes.WINFUNCTYPE(
            ctypes.c_longlong, ctypes.c_void_p, ctypes.c_uint,
            ctypes.c_void_p, ctypes.c_void_p)

        old_proc = user32.SetWindowLongPtrW(hwnd, -4, 0)

        def wnd_proc(hwnd_inner, msg, wParam, lParam):
            if msg == 0x0233:  # WM_DROPFILES
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
        ctypes.c_longlong.restype = ctypes.c_longlong
        user32.SetWindowLongPtrW.restype = ctypes.c_longlong
        old_proc = user32.SetWindowLongPtrW(
            hwnd, -4,
            ctypes.cast(proc, ctypes.c_void_p).value)
        return old_proc, proc
else:
    def enable_drag_drop(hwnd, callback):
        return None, None

# ============================================================
# Toast Notification
# ============================================================
class Toast:
    def __init__(self, parent):
        self.parent = parent

    def show(self, text, duration=2000, fg=TEXT, bg=BG_CARD):
        w = tk.Toplevel(self.parent)
        w.overrideredirect(True)
        w.attributes("-topmost", True)
        w.configure(bg=bg)

        px = self.parent.winfo_rootx()
        py = self.parent.winfo_rooty()
        pw = self.parent.winfo_width()

        lbl = tk.Label(w, text=f"  {text}  ", fg=fg, bg=bg,
                       font=("Microsoft YaHei UI", 10),
                       padx=20, pady=10)
        lbl.pack()

        w.update_idletasks()
        x = px + (pw - w.winfo_width()) // 2
        y = py + 60
        w.geometry(f"+{x}+{y}")
        w.attributes("-alpha", 0.0)

        for a in range(1, 11):
            w.attributes("-alpha", a / 10.0)
            w.update()
            time.sleep(0.015)

        w.after(duration, lambda: self._fade(w))

    def _fade(self, w):
        try:
            for a in range(9, -1, -1):
                w.attributes("-alpha", a / 10.0)
                w.update()
                time.sleep(0.02)
            w.destroy()
        except Exception:
            pass

# ============================================================
# Settings Dialog
# ============================================================
class SettingsDialog:
    def __init__(self, parent, current_dir, on_save):
        self.result_dir = current_dir
        self.on_save = on_save
        self.top = tk.Toplevel(parent)
        self.top.title("设置")
        self.top.geometry("480x180")
        self.top.resizable(False, False)
        self.top.configure(bg=BG_CARD)
        self.top.transient(parent)
        self.top.grab_set()

        self.top.update_idletasks()
        px = parent.winfo_rootx()
        py = parent.winfo_rooty()
        pw = parent.winfo_width()
        ph = parent.winfo_height()
        tw = self.top.winfo_width()
        th = self.top.winfo_height()
        x = px + (pw - tw) // 2
        y = py + (ph - th) // 2
        self.top.geometry(f"+{x}+{y}")

        # Title
        row = tk.Frame(self.top, bg=BG_CARD)
        row.pack(fill=tk.X, padx=16, pady=(16, 8))

        tk.Label(row, text="默认保存位置:", fg=TEXT, bg=BG_CARD,
                 font=("Microsoft YaHei UI", 10)).pack(side=tk.LEFT)

        # Directory entry
        self.dir_var = tk.StringVar(value=current_dir or "未设置（每次询问）")
        self.lbl_dir = tk.Label(self.top, textvariable=self.dir_var,
                                fg=ACCENT, bg=BG_CARD,
                                font=("Microsoft YaHei UI", 9))
        self.lbl_dir.pack(fill=tk.X, padx=16, pady=(0, 12))

        # Buttons
        btn_row = tk.Frame(self.top, bg=BG_CARD)
        btn_row.pack(fill=tk.X, padx=16, pady=(8, 16))

        tk.Button(btn_row, text="选择文件夹", command=self._pick_dir,
                  bg=BG_HOVER, fg=TEXT, font=("Microsoft YaHei UI", 9),
                  relief=tk.FLAT, padx=14, pady=4, cursor="hand2",
                  activebackground=BORDER, activeforeground=TEXT, bd=0
                  ).pack(side=tk.LEFT, padx=(0, 8))

        tk.Button(btn_row, text="清除", command=self._clear,
                  bg=BG_HOVER, fg=TEXT_DIM, font=("Microsoft YaHei UI", 9),
                  relief=tk.FLAT, padx=14, pady=4, cursor="hand2",
                  activebackground=BORDER, activeforeground=TEXT, bd=0
                  ).pack(side=tk.LEFT, padx=(0, 8))

        bottom = tk.Frame(self.top, bg=BG_CARD)
        bottom.pack(side=tk.BOTTOM, fill=tk.X, padx=16, pady=(8, 16))

        tk.Button(bottom, text="取消", command=self.top.destroy,
                  bg=BG_HOVER, fg="#ffffff", font=("Microsoft YaHei UI", 10, "bold"),
                  relief=tk.FLAT, padx=8, pady=6, cursor="hand2",
                  activebackground=BORDER, activeforeground=TEXT, bd=0
                  ).pack(side=tk.RIGHT, padx=(8, 0))

        tk.Button(bottom, text="保存", command=self._save,
                  bg="#4090e0", fg="#ffffff", font=("Microsoft YaHei UI", 10, "bold"),
                  relief=tk.FLAT, padx=8, pady=6, cursor="hand2",
                  activebackground="#3070c0", activeforeground="#ffffff", bd=0
                  ).pack(side=tk.RIGHT, padx=(8, 0))

    def _pick_dir(self):
        d = filedialog.askdirectory(parent=self.top, title="选择默认保存位置")
        if d:
            self.result_dir = d
            self.dir_var.set(d)

    def _clear(self):
        self.result_dir = ""
        self.dir_var.set("未设置（每次询问）")

    def _save(self):
        self.on_save(self.result_dir)
        self.top.destroy()

# ============================================================
# Crop Ratios
# ============================================================
CROP_RATIOS = {
    "自由": None,
    "1:1 (正方形)": (1, 1),
    "4:3": (4, 3),
    "16:9": (16, 9),
    "3:2": (3, 2),
    "2:3": (2, 3),
    "9:16": (9, 16),
}
THUMB_SIZE = 80

# ============================================================
# Main Application
# ============================================================
class VideoFrameGrabberPro:
    def __init__(self):
        config = load_config()
        self.default_save_dir = config.get("save_dir", "")

        self.root = tk.Tk()
        self.root.title("视频截帧工具 Pro")
        self.root.geometry("1024x760")
        self.root.minsize(800, 600)
        self.root.configure(bg=BG_DARK)

        self.cap = None
        self.current_frame = 0
        self.total_frames = 0
        self.fps = 25.0
        self.video_path = None
        self.frame_image = None
        self.photo = None
        self.toast = Toast(self.root)
        self._drag_refs = None

        # Crop state
        self.crop_ratio = None       # (w_ratio, h_ratio) or None
        self.crop_ratio_var = tk.StringVar(value="自由")
        self.crop_box = None  # (x1, y1, x2, y2) relative coords (0-1)
        self._crop_drag_start = None
        self._crop_dragging = False
        self._crop_overlay_ids = []

        self._build_ui()
        self._resize_after_id = None
        self._slider_updating = False
        self._last_shown_idx = -1
        self._cached_photo = None
        self._frame_cache_key = None
        self._last_time_text = ''
        self._last_fnum_text = ''
        self.bookmarks = set()
        self._playing = False
        self._play_speed = 30
        self._play_after_id = None
        self._thumb_cache = {}
        self.batch_step_var = tk.StringVar(value='1')
        self._bind_keys()
        self.root.after(100, self._enable_dnd)
        self.root.after(200, self._update_canvas_size)
        self.root.bind("<Configure>", self._on_configure)

    def _enable_dnd(self):
        try:
            hwnd = int(self.root.frame(), 16)
            self._drag_refs = enable_drag_drop(hwnd, self._on_drop_file)
        except Exception:
            pass

    def _on_drop_file(self, fp):
        self.open_video(fp)

    # ============================================================
    # UI Building
    # ============================================================
    def _build_ui(self):
        # --- Header ---
        hdr = tk.Frame(self.root, bg=HEADER_BG, height=48)
        hdr.pack(fill=tk.X, side=tk.TOP)
        hdr.pack_propagate(False)

        # Left: icon + title
        tf = tk.Frame(hdr, bg=HEADER_BG)
        tf.pack(side=tk.LEFT, padx=16, pady=10)

        tk.Label(tf, text="★", fg=ACCENT, bg=HEADER_BG,
                 font=("Consolas", 18, "bold")).pack(side=tk.LEFT)

        tk.Label(tf, text=" 视频截帧工具", fg=TEXT, bg=HEADER_BG,
                 font=("Microsoft YaHei UI", 12, "bold")).pack(side=tk.LEFT)

        # Right: action buttons
        rf = tk.Frame(hdr, bg=HEADER_BG)
        rf.pack(side=tk.RIGHT, padx=12, pady=8)

        def _btn(parent, text, cmd, bg=None, fg=None, accent=False):
            b = tk.Button(parent, text=text, command=cmd,
                          bg=bg or BG_DARK, fg=fg or TEXT_DIM,
                          font=("Microsoft YaHei UI", 10),
                          relief=tk.FLAT, padx=12, pady=4, cursor="hand2",
                          activebackground=BG_HOVER, activeforeground=TEXT, bd=0)
            b.pack(side=tk.LEFT, padx=2)
            return b

        self.btn_settings = _btn(rf, "⚙ 设置", self._open_settings, fg=TEXT_DIM)
        self.btn_open = _btn(rf, "+ 打开视频", self.open_video, bg=BG_CARD, fg=TEXT)
        self.btn_save = _btn(rf, "💾 保存当前帧", self.save_frame,
                             bg="#1a3a1a", fg=ACCENT2)
        self.btn_save.config(font=("Microsoft YaHei UI", 10, "bold"))
        self.btn_save.config(state=tk.DISABLED, disabledforeground=TEXT_DIM)
        self.btn_batch = tk.Button(rf, text='📦 批量导出', command=self._batch_export, bg='#2a1a0a', fg=ACCENT3, font=('Microsoft YaHei UI', 9), relief=tk.FLAT, padx=12, pady=4, cursor='hand2', activebackground=BG_HOVER, activeforeground=TEXT, bd=0)
        self.btn_batch.pack(side=tk.LEFT, padx=2)
        self.btn_batch.config(state=tk.DISABLED)

        # --- Main area ---
        main = tk.Frame(self.root, bg=BG_DARK)
        main.pack(fill=tk.BOTH, expand=True, padx=16, pady=(12, 0))

        # Canvas card
        card = tk.Frame(main, bg=BG_CARD, highlightthickness=1,
                        highlightbackground=BORDER)
        card.pack(fill=tk.BOTH, expand=True)

        self.canvas = tk.Canvas(card, bg=CANVAS_BG, highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True, padx=1, pady=1)
        self.canvas.bind("<Button-1>", self._on_canvas_click)
        self._draw_empty_state()

        # --- Thumbnail timeline ---
        thumb_bar = tk.Frame(main, bg=BG_CARD, height=80 + 20)
        thumb_bar.pack(fill=tk.X, pady=(4, 0))
        thumb_bar.pack_propagate(False)
        thumb_nav = tk.Frame(thumb_bar, bg=BG_CARD, height=24)
        thumb_nav.pack(fill=tk.X)
        self.btn_thumb_prev = tk.Button(thumb_nav, text='◀', command=lambda: self._jump(-10), bg=BG_CARD, fg=TEXT_DIM, font=('Consolas', 9), relief=tk.FLAT, cursor='hand2', activebackground=BG_HOVER, bd=0)
        self.btn_thumb_prev.pack(side=tk.LEFT, padx=(8, 2))
        self.btn_thumb_next = tk.Button(thumb_nav, text='▶', command=lambda: self._jump(10), bg=BG_CARD, fg=TEXT_DIM, font=('Consolas', 9), relief=tk.FLAT, cursor='hand2', activebackground=BG_HOVER, bd=0)
        self.btn_thumb_next.pack(side=tk.RIGHT, padx=(2, 8))
        self.lbl_thumb_range = tk.Label(thumb_nav, text='', fg=TEXT_DIM, bg=BG_CARD, font=('Consolas', 8))
        self.lbl_thumb_range.pack(side=tk.RIGHT, padx=6)
        self.thumb_canvas = tk.Canvas(thumb_bar, bg=BG_CARD, height=80, highlightthickness=0)
        self.thumb_canvas.pack(fill=tk.X, padx=4, pady=(0, 8))
        self.thumb_canvas.bind('<Button-1>', self._on_thumb_click)

        # --- Info bar ---
        ib = tk.Frame(main, bg=BG_CARD, height=28)
        ib.pack(fill=tk.X, pady=(4, 0))
        ib.pack_propagate(False)

        self.lbl_file = tk.Label(ib, text="未加载视频", fg=TEXT_DIM, bg=BG_CARD,
                                  font=("Microsoft YaHei UI", 9), anchor="w")
        self.lbl_file.pack(side=tk.LEFT, padx=12, pady=4)

        self.lbl_res = tk.Label(ib, text="", fg=TEXT_DIM, bg=BG_CARD,
                                 font=("Consolas", 9), anchor="e")
        self.lbl_res.pack(side=tk.RIGHT, padx=12, pady=4)

        # --- Time/frame display bar ---
        tfb = tk.Frame(main, bg=BG_CARD, height=28)
        tfb.pack(fill=tk.X, pady=(1, 0))
        tfb.pack_propagate(False)

        self.lbl_current = tk.Label(tfb, text="00:00", fg=ACCENT, bg=BG_CARD,
                                     font=("Consolas", 13, "bold"))
        self.lbl_current.pack(side=tk.LEFT, padx=(12, 0), pady=2)

        self.lbl_fnum = tk.Label(tfb, text="", fg=TEXT_DIM, bg=BG_CARD,
                                  font=("Consolas", 13))
        self.lbl_fnum.pack(side=tk.LEFT, padx=(6, 0), pady=2)

        self.lbl_total = tk.Label(tfb, text="/ 00:00", fg=TEXT_DIM, bg=BG_CARD,
                                   font=("Consolas", 13))
        self.lbl_total.pack(side=tk.LEFT, padx=0, pady=2)
        self.lbl_bookmark = tk.Label(tfb, text='', fg=ACCENT3, bg=BG_CARD, font=('Microsoft YaHei UI', 9))
        self.lbl_bookmark.pack(side=tk.LEFT, padx=(12, 0), pady=2)

        # Save location
        self.lbl_save_dir = tk.Label(tfb, text="", fg=TEXT_DIM, bg=BG_CARD,
                                      font=("Microsoft YaHei UI", 8), anchor="e")
        self.lbl_save_dir.pack(side=tk.RIGHT, padx=12, pady=2)

        if self.default_save_dir:
            self.lbl_save_dir.config(text=f"保存到: {self.default_save_dir}")

        # --- Crop ratio selector ---
        crop_bar = tk.Frame(main, bg=BG_CARD, height=32)
        crop_bar.pack(fill=tk.X, pady=(1, 0))
        crop_bar.pack_propagate(False)

        tk.Label(crop_bar, text="裁剪比例:", fg=TEXT_DIM, bg=BG_CARD,
                 font=("Microsoft YaHei UI", 9)).pack(side=tk.LEFT, padx=(12, 6), pady=6)

        crop_combo = ttk.Combobox(crop_bar, textvariable=self.crop_ratio_var,
                                  values=list(CROP_RATIOS.keys()),
                                  state="readonly", width=14,
                                  font=("Microsoft YaHei UI", 9))
        crop_combo.pack(side=tk.LEFT, pady=4)
        crop_combo.bind("<<ComboboxSelected>>", self._on_crop_ratio_change)

        # Shortcut hints
        hint = tk.Frame(main, bg=BG_CARD, height=20)
        hint.pack(fill=tk.X, pady=(1, 0))
        hint.pack_propagate(False)
        tk.Label(hint, text='B=书签 | 空格=播放 | ←→=逐帧 | Shift=跳秒 | Ctrl=跳10秒', fg=TEXT_DIM, bg=BG_CARD, font=('Microsoft YaHei UI', 8)).pack(side=tk.RIGHT, padx=12)

        # --- Controls ---
        ctrl = tk.Frame(main, bg=BG_CARD)
        ctrl.pack(fill=tk.X, pady=(1, 0))

        # Slider
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("C.Horizontal.TScale",
                        background=BG_CARD,
                        troughcolor="#21262d",
                        bordercolor=BORDER,
                        lightcolor=BG_CARD,
                        darkcolor=BG_CARD,
                        sliderthickness=14,
                        troughrelief="flat")

        self.slider = ttk.Scale(ctrl, from_=0, to=100, orient=tk.HORIZONTAL,
                                command=self._on_slider, style="C.Horizontal.TScale")
        self.slider.pack(fill=tk.X, padx=4, pady=(10, 4))
        self.slider.config(state=tk.DISABLED)

        # Navigation buttons
        nav = tk.Frame(ctrl, bg=HEADER_BG)
        nav.pack(fill=tk.X, padx=12, pady=(6, 10))

        bgf = tk.Frame(nav, bg=HEADER_BG)
        bgf.pack(expand=True)

        nav_buttons = [
            ('⏪ -10s',  lambda: self._jump_seconds(-10)),
            ('◀ -1s',   lambda: self._jump_seconds(-1)),
            ('⬅ 上一帧', lambda: self._jump(-1)),
            ('▶ 播放',  self._toggle_play),
            ('下一帧 ➡', lambda: self._jump(1)),
            ('+1s ▶',   lambda: self._jump_seconds(1)),
            ('+10s ⏩',  lambda: self._jump_seconds(10)),
        ]

        for txt, cmd in nav_buttons:
            btn = tk.Button(bgf, text=txt, command=cmd,
                            bg=BG_CARD, fg=TEXT,
                            font=('Microsoft YaHei UI', 9),
                            relief=tk.FLAT, padx=8, pady=3, cursor='hand2',
                            activebackground=BG_HOVER, activeforeground=TEXT, bd=0)
            btn.pack(side=tk.LEFT, padx=3)

        # --- Bookmark bar ---
        bm_bar = tk.Frame(ctrl, bg=BG_CARD, height=28)
        bm_bar.pack(fill=tk.X, pady=(1, 10))
        bm_bar.pack_propagate(False)
        self.lbl_bm_count = tk.Label(bm_bar, text='书签: 0', fg=TEXT_DIM, bg=BG_CARD, font=('Microsoft YaHei UI', 8))
        self.lbl_bm_count.pack(side=tk.LEFT, padx=12, pady=4)
        self.btn_bm_prev = tk.Button(bm_bar, text='◀ 上一个书签', command=self._prev_bookmark, bg=BG_CARD, fg=TEXT_DIM, font=('Microsoft YaHei UI', 8), relief=tk.FLAT, cursor='hand2', activebackground=BG_HOVER, bd=0)
        self.btn_bm_prev.pack(side=tk.LEFT, padx=2)
        self.btn_bm_next = tk.Button(bm_bar, text='下一个书签 ▶', command=self._next_bookmark, bg=BG_CARD, fg=TEXT_DIM, font=('Microsoft YaHei UI', 8), relief=tk.FLAT, cursor='hand2', activebackground=BG_HOVER, bd=0)
        self.btn_bm_next.pack(side=tk.LEFT, padx=2)
        self.btn_bm_clear = tk.Button(bm_bar, text='清除全部', command=self._clear_bookmarks, bg=BG_CARD, fg=TEXT_DIM, font=('Microsoft YaHei UI', 8), relief=tk.FLAT, cursor='hand2', activebackground=BG_HOVER, bd=0)
        self.btn_bm_clear.pack(side=tk.RIGHT, padx=12)

    # ============================================================
    # Crop Feature
    # ============================================================
    # ============================================================
    # Thumbnail Timeline
    # ============================================================
    def _update_thumbs(self):
        if self.cap is None:
            self.thumb_canvas.delete('all')
            self._thumb_cache.clear()
            self.lbl_thumb_range.config(text='')
            return
        cw = self.thumb_canvas.winfo_width()
        if cw < 100:
            return
        gap = 2
        n = max(1, (cw + gap) // (THUMB_SIZE + gap))
        center = self.current_frame
        half = n // 2
        start = max(0, center - half)
        if start + n > self.total_frames:
            start = max(0, self.total_frames - n)
        self.lbl_thumb_range.config(text=f'{start + 1}-{min(start + n, self.total_frames)} / {self.total_frames}')
        self.thumb_canvas.delete('all')
        for i in range(n):
            fn = start + i
            if fn >= self.total_frames:
                break
            x = i * (THUMB_SIZE + gap) + 2
            if fn in self._thumb_cache:
                photo = self._thumb_cache[fn]
            else:
                self.cap.set(cv2.CAP_PROP_POS_FRAMES, fn)
                ret, frm = self.cap.read()
                if not ret:
                    continue
                rgb = cv2.cvtColor(frm, cv2.COLOR_BGR2RGB)
                img = Image.fromarray(rgb)
                h, w = frm.shape[:2]
                sc = THUMB_SIZE / max(w, h)
                img = img.resize((int(w * sc), int(h * sc)), Image.LANCZOS)
                photo = ImageTk.PhotoImage(img)
                self._thumb_cache[fn] = photo
            cx = x + THUMB_SIZE // 2
            cy = THUMB_SIZE // 2
            self.thumb_canvas.create_image(cx, cy, image=photo, anchor=tk.CENTER, tags=('thumb', f't{fn}'))
            if fn == self.current_frame:
                self.thumb_canvas.create_rectangle(x, 0, x + THUMB_SIZE, THUMB_SIZE, outline=ACCENT, width=2, tags='sel')
            if fn in self.bookmarks:
                self.thumb_canvas.create_rectangle(x + THUMB_SIZE - 12, 2, x + THUMB_SIZE - 2, 10, fill=ACCENT3, outline='', tags='bm')
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, self.current_frame)
        self.cap.read()

    def _on_thumb_click(self, e):
        if self.cap is None:
            return
        cw = self.thumb_canvas.winfo_width()
        gap = 2
        n = max(1, (cw + gap) // (THUMB_SIZE + gap))
        half = n // 2
        start = max(0, self.current_frame - half)
        if start + n > self.total_frames:
            start = max(0, self.total_frames - n)
        fn = start + (e.x - 2) // (THUMB_SIZE + gap)
        if 0 <= fn < self.total_frames:
            self._show_frame(fn)

    # ============================================================
    # Playback
    # ============================================================
    def _toggle_play(self):
        if self.cap is None:
            return
        self._playing = not self._playing
        if self._playing:
            self.toast.show('▶ 播放中... (空格停止)', 1500, fg=ACCENT2)
            self._play_step()
        else:
            if self._play_after_id:
                self.root.after_cancel(self._play_after_id)
                self._play_after_id = None
            self.toast.show('⏸ 已暂停', 1000, fg=ACCENT)

    def _play_step(self):
        if not self._playing or self.cap is None:
            return
        if self.current_frame < self.total_frames - 1:
            self._jump(1)
            delay = int(1000 / max(1, self._play_speed))
            self._play_after_id = self.root.after(delay, self._play_step)
        else:
            self._playing = False
            self.toast.show('⏹ 播放结束', 1500, fg=ACCENT)

    # ============================================================
    # Bookmarks
    # ============================================================
    def _toggle_bookmark(self):
        if self.cap is None:
            return
        fn = self.current_frame
        if fn in self.bookmarks:
            self.bookmarks.discard(fn)
            self.toast.show(f'🔖 书签已移除 (帧 {fn+1})', fg=TEXT_DIM)
        else:
            self.bookmarks.add(fn)
            self.toast.show(f'🔖 书签已添加 (帧 {fn+1})', fg=ACCENT3)
        self._update_bookmark_ui()

    def _prev_bookmark(self):
        if not self.bookmarks:
            return
        bm = sorted(b for b in self.bookmarks if b < self.current_frame)
        if bm:
            self._show_frame(bm[-1])
        else:
            self._show_frame(max(self.bookmarks))

    def _next_bookmark(self):
        if not self.bookmarks:
            return
        bm = sorted(b for b in self.bookmarks if b > self.current_frame)
        if bm:
            self._show_frame(bm[0])
        else:
            self._show_frame(min(self.bookmarks))

    def _clear_bookmarks(self):
        self.bookmarks.clear()
        self._update_bookmark_ui()
        self.toast.show('书签已全部清除', fg=TEXT_DIM)

    def _update_bookmark_ui(self):
        n = len(self.bookmarks)
        self.lbl_bm_count.config(text=f'书签: {n}')
        if self.cap and self.current_frame in self.bookmarks:
            self.lbl_bookmark.config(text='🔖')
        else:
            self.lbl_bookmark.config(text='')
        self._update_thumbs()

    # ============================================================
    # Batch Export
    # ============================================================
    def _batch_export(self):
        if self.cap is None:
            return
        dlg = tk.Toplevel(self.root)
        dlg.title('批量导出')
        dlg.geometry('400x220')
        dlg.resizable(False, False)
        dlg.configure(bg=BG_CARD)
        dlg.transient(self.root)
        dlg.grab_set()
        px = self.root.winfo_rootx()
        py = self.root.winfo_rooty()
        pw = self.root.winfo_width()
        ph = self.root.winfo_height()
        dlg.update_idletasks()
        dlg.geometry(f'+{px + (pw - 400) // 2}+{py + (ph - 220) // 2}')
        tk.Label(dlg, text='批量导出帧', fg=TEXT, bg=BG_CARD, font=('Microsoft YaHei UI', 12, 'bold')).pack(pady=(16, 8))
        r1 = tk.Frame(dlg, bg=BG_CARD)
        r1.pack(fill=tk.X, padx=16, pady=4)
        tk.Label(r1, text='每隔', fg=TEXT_DIM, bg=BG_CARD, font=('Microsoft YaHei UI', 9)).pack(side=tk.LEFT)
        se = ttk.Combobox(r1, textvariable=self.batch_step_var, values=['1', '5', '10', '15', '24', '30', '60'], state='readonly', width=6, font=('Microsoft YaHei UI', 10))
        se.pack(side=tk.LEFT, padx=4)
        tk.Label(r1, text='帧导出一张', fg=TEXT_DIM, bg=BG_CARD, font=('Microsoft YaHei UI', 9)).pack(side=tk.LEFT)
        ec = self.total_frames // max(1, int(self.batch_step_var.get()))
        lc = tk.Label(r1, text=f'（共约 {ec} 张）', fg=TEXT_DIM, bg=BG_CARD, font=('Microsoft YaHei UI', 8))
        lc.pack(side=tk.RIGHT)
        def osc(*_):
            e = self.total_frames // max(1, int(self.batch_step_var.get()))
            lc.config(text=f'（共约 {e} 张）')
        self.batch_step_var.trace_add('write', osc)
        r2 = tk.Frame(dlg, bg=BG_CARD)
        r2.pack(fill=tk.X, padx=16, pady=8)
        sv = tk.BooleanVar(value=True)
        tk.Checkbutton(r2, text='创建子文件夹', variable=sv, fg=TEXT_DIM, bg=BG_CARD, selectcolor=BG_CARD, font=('Microsoft YaHei UI', 9), activebackground=BG_CARD, activeforeground=TEXT).pack(side=tk.LEFT)
        br = tk.Frame(dlg, bg=BG_CARD)
        br.pack(side=tk.BOTTOM, fill=tk.X, padx=16, pady=(8, 16))
        tk.Button(br, text='取消', command=dlg.destroy, bg=BG_HOVER, fg=TEXT, font=('Microsoft YaHei UI', 10), relief=tk.FLAT, padx=16, pady=6, cursor='hand2', activebackground=BORDER, bd=0).pack(side=tk.RIGHT, padx=(8, 0))
        def do_export():
            dlg.destroy()
            step = max(1, int(self.batch_step_var.get()))
            sd = self.default_save_dir or str(Path(self.video_path).parent)
            stem = Path(self.video_path).stem if self.video_path else 'frames'
            if sv.get():
                sd = os.path.join(sd, f'{stem}_frames')
            os.makedirs(sd, exist_ok=True)
            ttl = (self.total_frames + step - 1) // step
            saved = 0
            orig = self.current_frame
            self.toast.show(f'开始导出 {ttl} 张...', 2000, fg=ACCENT)
            self.root.update()
            for fn in range(0, self.total_frames, step):
                self.cap.set(cv2.CAP_PROP_POS_FRAMES, fn)
                ret, frm = self.cap.read()
                if ret:
                    if self.crop_ratio and self.crop_box:
                        h, w = frm.shape[:2]
                        x1 = max(0, int(self.crop_box[0] * w))
                        y1 = max(0, int(self.crop_box[1] * h))
                        x2 = min(w, int(self.crop_box[2] * w))
                        y2 = min(h, int(self.crop_box[3] * h))
                        frm = frm[y1:y2, x1:x2]
                    cv2.imwrite(os.path.join(sd, f'{stem}_{fn:05d}.png'), frm)
                    saved += 1
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, orig)
            self._show_frame(orig)
            self.toast.show(f'导出完成: {saved} 张 → {sd}', 3000, fg=ACCENT2)
        tk.Button(br, text='开始导出', command=do_export, bg=ACCENT2, fg='#ffffff', font=('Microsoft YaHei UI', 10, 'bold'), relief=tk.FLAT, padx=16, pady=6, cursor='hand2', activebackground='#2da040', bd=0).pack(side=tk.RIGHT)

    def _on_crop_ratio_change(self, event=None):
        key = self.crop_ratio_var.get()
        self.crop_ratio = CROP_RATIOS.get(key, None)
        self.crop_box = None
        self.bookmarks.clear()
        self._thumb_cache.clear()
        self._crop_drag_start = None
        self._redraw_crop_overlay()

    def _redraw_crop_overlay(self):
        if self.canvas.winfo_width() < 10 or self.canvas.winfo_height() < 10:
            return
        # Remove old overlay
        for item_id in self._crop_overlay_ids:
            self.canvas.delete(item_id)
        self._crop_overlay_ids.clear()

        if not self.crop_ratio or self.frame_image is None:
            return

        cw = self.canvas.winfo_width()
        ch = self.canvas.winfo_height()
        if cw < 10 or ch < 10:
            return

        # Calculate crop box
        if self.crop_box is None:
            rw, rh = self.crop_ratio
            if cw / ch > rw / rh:
                crop_h = ch
                crop_w = int(ch * rw / rh)
            else:
                crop_w = cw
                crop_h = int(cw * rh / rw)
            x1 = (cw - crop_w) // 2
            y1 = (ch - crop_h) // 2
            x2 = x1 + crop_w
            y2 = y1 + crop_h
            self.crop_box = (x1 / cw, y1 / ch, x2 / cw, y2 / ch)
        else:
            x1 = int(self.crop_box[0] * cw)
            y1 = int(self.crop_box[1] * ch)
            x2 = int(self.crop_box[2] * cw)
            y2 = int(self.crop_box[3] * ch)

        # Draw semi-transparent overlay (darken outside crop area)
        # Top
        rid = self.canvas.create_rectangle(0, 0, cw, y1, fill="#000000", stipple="gray50", outline="")
        self._crop_overlay_ids.append(rid)
        # Bottom
        rid = self.canvas.create_rectangle(0, y2, cw, ch, fill="#000000", stipple="gray50", outline="")
        self._crop_overlay_ids.append(rid)
        # Left
        rid = self.canvas.create_rectangle(0, y1, x1, y2, fill="#000000", stipple="gray50", outline="")
        self._crop_overlay_ids.append(rid)
        # Right
        rid = self.canvas.create_rectangle(x2, y1, cw, y2, fill="#000000", stipple="gray50", outline="")
        self._crop_overlay_ids.append(rid)
        # Border
        rid = self.canvas.create_rectangle(x1, y1, x2, y2, outline=ACCENT2, width=2, dash=(6, 4))
        self._crop_overlay_ids.append(rid)
        # Rule of thirds lines
        dx = (x2 - x1) / 3
        dy = (y2 - y1) / 3
        for i in range(1, 3):
            lx = x1 + dx * i
            ly = y1 + dy * i
            rid = self.canvas.create_line(lx, y1, lx, y2, fill=ACCENT2, width=1, dash=(3, 5))
            self._crop_overlay_ids.append(rid)
            rid = self.canvas.create_line(x1, ly, x2, ly, fill=ACCENT2, width=1, dash=(3, 5))
            self._crop_overlay_ids.append(rid)

    # ============================================================
    # Canvas drawing
    # ============================================================
    def _on_configure(self, event):
        if event.widget != self.root:
            return
        if self._resize_after_id:
            self.root.after_cancel(self._resize_after_id)
        self._resize_after_id = self.root.after(150, self._update_canvas_size)

    def _draw_empty_state(self):
        self.canvas.delete("all")
        self._crop_overlay_ids.clear()
        w = self.canvas.winfo_width()
        h = self.canvas.winfo_height()
        if w > 50 and h > 50:
            self.canvas.create_text(w // 2, h // 2 - 15,
                                     text="拖放视频文件到此处或点击「+ 打开视频」",
                                     fill=TEXT_DIM, font=("Microsoft YaHei UI", 11),
                                     justify=tk.CENTER)
            self.canvas.create_text(w // 2, h // 2 + 15,
                                     text="支持 MP4 / MKV / AVI / MOV 等格式",
                                     fill=TEXT_DIM, font=("Microsoft YaHei UI", 9),
                                     justify=tk.CENTER)

    def _on_canvas_click(self, e):
        self.open_video()

    # ============================================================
    # Settings
    # ============================================================
    def _open_settings(self):
        SettingsDialog(self.root, self.default_save_dir, self._on_settings_saved)

    def _on_settings_saved(self, new_dir):
        self.default_save_dir = new_dir
        save_config({"save_dir": new_dir})
        if new_dir:
            self.lbl_save_dir.config(text=f"保存到: {new_dir}")
        else:
            self.lbl_save_dir.config(text="")

    # ============================================================
    # Video operations
    # ============================================================
    def open_video(self, path=None):
        if path is None:
            path = filedialog.askopenfilename(
                title="选择视频文件",
                filetypes=[
                    ("视频文件", "*.mp4 *.mkv *.avi *.mov *.flv *.wmv *.webm *.m4v *.ts"),
                    ("所有文件", "*.*"),
                ])

        if not path:
            return

        if self.cap is not None:
            self.cap.release()
        self._playing = False

        self.cap = cv2.VideoCapture(path)
        if not self.cap.isOpened():
            messagebox.showerror("错误", "无法打开视频文件")
            self.cap = None
            return

        self.video_path = path
        self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.fps = self.cap.get(cv2.CAP_PROP_FPS)
        if self.fps <= 0:
            self.fps = 25.0

        # Read first frame
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
        ret, frame = self.cap.read()
        if not ret:
            messagebox.showerror("错误", "无法读取视频帧")
            self.cap.release()
            self.cap = None
            return

        self.current_frame = 0
        self.frame_image = frame
        self.crop_box = None
        self.bookmarks.clear()
        self._thumb_cache.clear()

        # Enable controls
        self.slider.config(state=tk.NORMAL, from_=0, to=max(0, self.total_frames - 1))
        self.btn_save.config(state=tk.NORMAL)
        self.btn_batch.config(state=tk.NORMAL)

        # Update info
        h, w = frame.shape[:2]
        self.canvas.delete("all")
        self.lbl_file.config(text=Path(path).name)
        self.lbl_res.config(text=f"{w}×{h}  |  {self.total_frames} 帧  |  {self.fps:.0f} fps")
        self.lbl_total.config(text=f"/ {self._fmt(self.total_frames / self.fps)}")

        self._show_frame(0)
        self.toast.show(f"已加载: {Path(path).stem}", fg=ACCENT2)

    def _show_frame(self, idx):
        if self.cap is None:
            return

        idx = max(0, min(idx, self.total_frames - 1))
        cw = self.canvas.winfo_width()
        ch = self.canvas.winfo_height()
        if cw < 20 or ch < 20:
            return

        # Skip full reprocess if showing same frame at same canvas size
        cache_key = (idx, cw, ch)
        if cache_key == getattr(self, '_frame_cache_key', None):
            return
        self._frame_cache_key = cache_key

        if idx != self.current_frame or idx != self._last_shown_idx:
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
            ret, frame = self.cap.read()
            if not ret:
                return
            self.frame_image = frame
            self.current_frame = idx
            self._last_shown_idx = idx
        else:
            frame = self.frame_image

        h, w = frame.shape[:2]
        scale = min(cw / w, ch / h)
        nw = max(1, int(w * scale))
        nh = max(1, int(h * scale))

        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        img = Image.fromarray(rgb)
        if nw > 3000 or nh > 3000:
            s = min(3000 / nw, 3000 / nh)
            nw = max(1, int(nw * s))
            nh = max(1, int(nh * s))
        img = img.resize((nw, nh), Image.LANCZOS)
        self.photo = ImageTk.PhotoImage(img)

        self.canvas.delete("all")
        self._crop_overlay_ids.clear()
        self.canvas.create_image(cw // 2, ch // 2, image=self.photo,
                                 anchor=tk.CENTER, tags="preview")
        self._redraw_crop_overlay()

        # Update slider without triggering callback
        self._slider_updating = True
        self.slider.set(idx)
        self._slider_updating = False

        # Update time labels (only if changed)
        ts = idx / self.fps if self.fps > 0 else 0
        new_time = self._fmt(ts)
        new_fnum = f"第 {idx + 1} / {self.total_frames} 帧"
        if getattr(self, '_last_time_text', '') != new_time:
            self.lbl_current.config(text=new_time)
            self._last_time_text = new_time
        if getattr(self, '_last_fnum_text', '') != new_fnum:
            self.lbl_fnum.config(text=new_fnum)
            self._last_fnum_text = new_fnum

    def _on_slider(self, val):
        if self._slider_updating or self.cap is None:
            return
        idx = int(float(val))
        self._show_frame(idx)

    def _jump(self, d):
        if self.cap is None:
            return
        new_idx = self.current_frame + d
        self._show_frame(new_idx)

    def _jump_seconds(self, ds):
        if self.cap is None or self.fps <= 0:
            return
        df = int(ds * self.fps)
        new_idx = self.current_frame + df
        self._show_frame(new_idx)

    def _fmt(self, sec):
        m = int(sec // 60)
        s = int(sec % 60)
        return f"{m:02d}:{s:02d}"

    def _update_canvas_size(self):
        try:
            if self.frame_image is not None:
                self._show_frame(self.current_frame)
                self._update_thumbs()
            elif not bool(self.canvas.find_all()):
                self._draw_empty_state()
        except Exception:
            pass

    # ============================================================
    # Save frame
    # ============================================================
    def save_frame(self):
        if self.frame_image is None:
            return

        frame = self.frame_image
        h, w = frame.shape[:2]

        # Apply crop if set
        if self.crop_ratio and self.crop_box:
            x1 = int(self.crop_box[0] * w)
            y1 = int(self.crop_box[1] * h)
            x2 = int(self.crop_box[2] * w)
            y2 = int(self.crop_box[3] * h)
            x1 = max(0, x1)
            y1 = max(0, y1)
            x2 = min(w, x2)
            y2 = min(h, y2)
            if x2 > x1 and y2 > y1:
                frame = frame[y1:y2, x1:x2]

        # Generate default filename
        stem = Path(self.video_path).stem if self.video_path else "frame"
        stem = stem.replace(":", "-").replace("_", "-")
        ts = self.current_frame / self.fps if self.fps > 0 else 0
        timestamp = self._fmt(ts).replace(":", "-")
        default_name = f"{stem}_{timestamp}_f{self.current_frame}.png"

        init_dir = self.default_save_dir if self.default_save_dir else (
            str(Path(self.video_path).parent) if self.video_path else "")

        path = filedialog.asksaveasfilename(
            title="保存当前帧",
            initialdir=init_dir,
            initialfile=default_name,
            defaultextension=".png",
            filetypes=[
                ("PNG 图片", "*.png"),
                ("JPEG 图片", "*.jpg"),
                ("BMP 位图", "*.bmp"),
            ])

        if not path:
            return

        try:
            os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
            cv2.imwrite(path, frame)
            self.toast.show(f"已保存: {Path(path).name}", fg=ACCENT2)
        except Exception as e:
            messagebox.showerror("保存失败", f"保存失败：{e}")

    # ============================================================
    # Keyboard shortcuts
    # ============================================================
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
        self.root.bind("<space>", lambda e: self._toggle_play())
        self.root.bind("<b>", lambda e: self._toggle_bookmark())
        self.root.bind("<B>", lambda e: self._toggle_bookmark())

    def run(self):
        self.root.mainloop()

# ============================================================
# Entry point
# ============================================================
if __name__ == "__main__":
    app = VideoFrameGrabberPro()
    app.run()
