# 🖐️ HandNavigator — Virtual 3D Mouse

> Replace your expensive 3Dconnexion SpaceMouse with hand tracking via webcam.

HandNavigator uses **MediaPipe** hand tracking to detect gestures and simulate
3D camera navigation (**Pan**, **Orbit**, **Zoom**) in any 3D software — no
extra hardware needed.

## 🎯 Supported Gestures

| Gesture             | Action    | Description                            |
| ------------------- | --------- | -------------------------------------- |
| ✋ Open Hand + Drag | **Pan**   | Move camera left/right/up/down         |
| 🤏 Pinch + Move     | **Zoom**  | Zoom in/out                            |
| ✊ Fist + Rotate    | **Orbit** | Rotate camera around target            |
| 🖐️ Idle             | —         | No action (hand still or out of frame) |

## 🎬 Supported Apps

| App       | Profile    | Status             |
| --------- | ---------- | ------------------ |
| Cinema 4D | `cinema4d` | ✅ Tested + Plugin |
| Maya      | `cinema4d` | ✅ Same shortcuts  |
| Blender   | `blender`  | ✅ Ready           |

## 🌐 Languages

The UI is available in:

- 🇺🇸 **English** (default)
- 🇧🇷 **Português (Brasil)**
- 🇪🇸 **Español**

Auto-detected from your OS locale.

## 🚀 Quick Start

### Prerequisites

- Python 3.10+
- Webcam
- Windows 10/11

### Install

```bash
cd HandNavigator
pip install -r requirements.txt
```

### Run (Desktop App)

```bash
python -m ui.app
```

Or double-click `run.bat`.

### Run (Headless — CLI only)

```bash
python -m tracker.main
```

### Change Profile

Edit `tracker/config.py`:

```python
ACTIVE_PROFILE = "cinema4d"  # or "blender"
```

## 🎬 Cinema 4D Plugin

A native C4D plugin with its own dashboard is included in `c4d_plugin/HandNavigator/`.

### Plugin Install

1. **C4D → Edit → Preferences → Plugins → Add Folder** → select `c4d_plugin/HandNavigator/`
2. Restart Cinema 4D
3. **Extensions → HandNavigator**

See [`c4d_plugin/HandNavigator/README.md`](c4d_plugin/HandNavigator/README.md) for full details.

## ⚙️ Configuration

All settings in `tracker/config.py`:

| Setting                 | Default | Description                            |
| ----------------------- | ------- | -------------------------------------- |
| `PAN_SENSITIVITY`       | 800     | Mouse pixels per unit of hand movement |
| `ZOOM_SENSITIVITY`      | 1200    | Zoom responsiveness                    |
| `ORBIT_SENSITIVITY`     | 600     | Orbit responsiveness                   |
| `DEAD_ZONE_TRANSLATION` | 0.003   | Ignore micro-movements                 |
| `GESTURE_SWITCH_FRAMES` | 3       | Frames needed to switch gesture        |
| `SHOW_DEBUG_WINDOW`     | True    | Show webcam overlay                    |

## 🏗️ Architecture

```
Webcam → MediaPipe → Gesture Engine → Win32 SendInput → Any 3D App
                                    ↘ UDP Socket → C4D Plugin
```

Two output modes:

- **Preview**: built-in OpenGL 3D viewport for testing
- **Live**: sends navigation to the active 3D app via Win32 or UDP

## 👤 Author

**Flávio Takemoto** — [takemoto.com.br](http://www.takemoto.com.br)

## 📄 License

[MIT License](LICENSE)
