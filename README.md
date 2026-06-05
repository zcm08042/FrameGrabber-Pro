# 帧捕获 v2.0

[![Download](https://img.shields.io/badge/下载-v2.0-brightgreen)](https://github.com/zcm08042/FrameGrabber-Pro/releases/tag/v2.0)

<p align="center">
  <img src="icon_preview.png" alt="帧捕获图标" width="120">
</p>

**帧捕获** 是一款现代化的视频逐帧浏览与截取工具。轻量、快速、优雅，基于 Python + tkinter + OpenCV 构建。

## ✨ 功能亮点

- 🎬 **视频帧浏览** — 打开视频文件，逐帧浏览，支持**拖拽打开**
- 🎞️ **进度条导航** — 拖动滑块快速定位，防抖优化不卡顿
- ⏭️ **时间跳转** — 输入秒数或 `mm:ss` 格式直接跳转
- 💾 **保存帧** — 支持 PNG / JPEG / BMP 格式，可设置默认保存目录
- 🎨 **莫兰迪暗色主题** — 低饱和柔和配色，护眼高级
- 📦 **单 exe 发布** — 无需 Python 环境，双击即用
- 🚀 **极致性能** — 帧缓存 + 滑块防抖 + 窗口 resize 防抖

## 🚀 快速开始

### 下载运行

从 [Releases](https://github.com/zcm08042/FrameGrabber-Pro/releases) 下载 `帧捕获.exe`，双击即可运行。

### 从源码运行

```bash
pip install opencv-python pillow pyinstaller
python frame_grabber.py
```

### 打包为 exe

```bash
pyinstaller --clean --onefile --noconsole --name=帧捕获 --icon=icon.ico --optimize=2 frame_grabber.py
```

## ⌨️ 快捷键

| 按键 | 功能 |
|------|------|
| `←` `→` | 逐帧移动 |
| `Shift + ← →` | 跳 1 秒 |
| `Ctrl + ← →` | 跳 10 秒 |
| `Ctrl + O` | 打开视频 |
| `Ctrl + S` | 保存当前帧 |
| `Enter`（输入框） | 执行时间跳转 |

## 📋 更新日志

### v2.0 (2025-06)
- 🔄 **全面性能重构** — 帧缓存、滑块防抖、resize 防抖，操作丝滑不卡
- 🎨 **新配色** — 莫兰迪暗色主题，低饱和柔和高级
- 🕒 **新增时间跳转** — 支持秒数 / mm:ss / h:mm:ss 输入
- 🖼️ **自绘图标** — 胶片播放器风格图标
- 📛 **中文名** — 更名为「帧捕获」
- ⚡ **启动优化** — PyInstaller 字节码优化，启动更快

### v1.0
- 初始版本：帧浏览、书签、批量导出、自动播放、裁剪比例、暗色主题
