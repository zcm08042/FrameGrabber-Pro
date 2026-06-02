# 视频截帧工具 Pro

一款现代化的视频逐帧浏览与截取工具，基于 Python + tkinter + OpenCV 构建。

## 功能

- 🎬 **视频帧浏览** — 打开视频文件，逐帧浏览，支持拖放
- 🎞️ **缩略图时间轴** — 底部缩略图条，点击快速跳转
- 🔖 **帧书签** — 按 B 键标记关键帧，快速跳转
- ✂️ **裁剪比例** — 自由 / 1:1 / 4:3 / 16:9 / 3:2 / 2:3 / 9:16，可视化裁剪框
- 📦 **批量导出** — 每隔 N 帧自动保存，支持创建子文件夹
- ▶️ **自动播放** — 空格键启动/停止逐帧播放
- 💾 **保存当前帧** — 支持 PNG / JPEG / BMP
- 🔔 **Toast 通知** — 操作反馈优雅不打扰
- 🌙 **暗色主题** — GitHub Dark 风格，护眼现代

## 快捷键

| 按键 | 功能 |
|------|------|
| `←` `→` | 逐帧移动 |
| `Shift + ← →` | 跳 1 秒 |
| `Ctrl + ← →` | 跳 10 秒 |
| `空格` | 播放 / 暂停 |
| `B` | 添加 / 移除书签 |
| `Ctrl + O` | 打开视频 |
| `Ctrl + S` | 保存当前帧 |

## 运行

### 从源码运行

```bash
pip install opencv-python pillow
python frame_grabber.py
```

### 打包为 exe

```bash
pip install pyinstaller
pyinstaller --onefile --windowed --noconsole --icon=icon.ico --name FrameGrabber frame_grabber.py
```

## 技术栈

- **Python 3.13**
- **tkinter** — GUI
- **OpenCV** — 视频解码与帧处理
- **Pillow** — 图像缩放与格式转换

## 截图

![图标](icon_preview.png)

## License

MIT
