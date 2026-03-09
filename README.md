<p align="center">
  <img src="assets/logo.svg" alt="HandNavigator" width="420" />
</p>

<p align="center">
  <strong>Navigate 3D viewports with your hands. No hardware needed.</strong><br/>
  Open-source alternative to the 3Dconnexion SpaceMouse — powered by computer vision.
</p>

<p align="center">
  <img alt="License" src="https://img.shields.io/badge/license-MIT-blue.svg" />
  <img alt="Python" src="https://img.shields.io/badge/python-3.11+-yellow.svg" />
  <img alt="Platform" src="https://img.shields.io/badge/platform-Windows-lightgrey.svg" />
  <img alt="C4D" src="https://img.shields.io/badge/Cinema%204D-2023%20%7C%202024%20%7C%202025-0078D7.svg" />
</p>

---

## What is HandNavigator?

HandNavigator turns any standard webcam into a 3D navigation controller. Using real-time hand tracking, it recognizes natural gestures and converts them into camera movements — **Pan**, **Orbit**, and **Zoom** — that work inside Cinema 4D, Blender, Maya, and virtually any 3D application.

No dongles. No drivers. No special hardware. Just your hands and a webcam.

### How it works

1. Open HandNavigator alongside your 3D app
2. A webcam feed tracks your hand using machine learning (21-landmark detection)
3. Gestures are recognized in real time and translated to camera navigation
4. Navigation is sent to your 3D app via native input simulation or direct plugin communication

### Gesture Reference

| Gesture                    | Action    | How                         |
| -------------------------- | --------- | --------------------------- |
| Open hand + drag           | **Pan**   | Move camera laterally       |
| Pinch (thumb+index) + move | **Zoom**  | Zoom in/out                 |
| Closed fist + rotate       | **Orbit** | Rotate camera around target |
| Hand still / out of frame  | Idle      | No action                   |

---

## Getting Started

### Option A — Installer (recommended)

Download `HandNavigator_Setup_1.0.0.exe` from the [Releases](../../releases) page. The installer:

- Installs the desktop application
- Auto-detects Cinema 4D installations (2020–2030)
- Installs the C4D plugin into each selected version
- Optionally adds auto-start with Windows

### Option B — From source

**Requirements:** Python 3.11+, Windows 10/11, webcam.

```bash
git clone https://github.com/YOUR_USER/HandNavigator.git
cd HandNavigator
pip install -r requirements.txt
python -m ui.app
```

The MediaPipe hand model (~25 MB) is auto-downloaded on first run.

### Cinema 4D Plugin

The installer handles this automatically. For manual installation:

1. Copy the `c4d_plugin/HandNavigator/` folder to your C4D plugins directory
2. Or go to **Edit → Preferences → Plugins → Add Folder** and point to it
3. Restart Cinema 4D
4. Access via **Extensions → HandNavigator**

The plugin includes a dashboard with real-time status, sensitivity sliders for each axis, and connection controls. Official Maxon Plugin ID: `1067724`.

### Supported Applications

| Application | Input Mode          | Status                               |
| ----------- | ------------------- | ------------------------------------ |
| Cinema 4D   | UDP plugin (direct) | Fully tested, native plugin included |
| Blender     | Win32 SendInput     | Ready, profile included              |
| Maya        | Win32 SendInput     | Compatible (shares C4D shortcuts)    |
| Any 3D app  | Win32 SendInput     | Works via keyboard/mouse simulation  |

### Internationalization

The UI auto-detects your OS locale and supports:

- English (default)
- Português (Brasil)
- Español

---

## Technical Documentation

> This section is aimed at developers who want to understand, contribute to, or extend HandNavigator.

### Architecture

```
                         ┌─────────────────────────────────────┐
                         │         HandNavigator Desktop       │
                         │                                     │
  Webcam ──► OpenCV ──►  │  MediaPipe Hand Landmarker (TFLite) │
                         │           │                         │
                         │  Gesture Recognizer (heuristic)     │
                         │           │                         │
                         │  Navigation Solver (delta engine)   │
                         │           │                         │
                         │    ┌──────┴───────┐                 │
                         │    │              │                 │
                         │  Win32        UDP Socket            │
                         │  SendInput    (JSON packets)        │
                         │    │              │                 │
                         └────┼──────────────┼─────────────────┘
                              │              │
                              ▼              ▼
                         Any 3D App    Cinema 4D Plugin
                         (via OS)      (native GeDialog)
```

### Stack

- **Language:** Python 3.11
- **Hand Tracking:** Google MediaPipe Tasks API — 21-landmark hand model, TFLite backend, CPU inference at 30+ FPS
- **Computer Vision:** OpenCV — webcam capture, frame processing, color space conversion
- **GUI Framework:** PyQt6 — main window, system tray, PIP webcam overlay, OpenGL viewport
- **3D Rendering:** PyOpenGL — real-time Preview mode with orbit/pan/zoom on a reference grid
- **Input Simulation:** Win32 `SendInput` via ctypes — zero-dependency mouse/keyboard injection
- **Network Protocol:** UDP sockets with JSON payloads — sub-ms latency for C4D plugin communication
- **Smoothing:** One-Euro Filter implementation — adaptive low-pass filter that balances jitter suppression with responsiveness
- **C4D Integration:** Cinema 4D Python API (`c4d` module) — `CommandData` plugin, `GeDialog` UI, threaded UDP server
- **Build:** PyInstaller 6.18 (standalone EXE), Inno Setup 6 (Windows installer)
- **i18n:** Custom string-table module with auto locale detection (3 languages, 53 keys)

### Module Map

```
HandNavigator/
├── tracker/                  # Core hand-tracking engine
│   ├── config.py             # All tunable parameters (sensitivity, dead zones, etc.)
│   ├── hand_detector.py      # MediaPipe wrapper — lifecycle, landmark extraction
│   ├── gesture_recognizer.py # Heuristic classifier (IDLE/PAN/ZOOM/ORBIT) + debounce
│   ├── navigation_solver.py  # Delta computation engine — converts landmarks to camera deltas
│   ├── smoothing.py          # One-Euro Filter implementation (adaptive low-pass)
│   └── main.py               # Orchestrator — camera loop, gesture→navigation pipeline
│
├── input/                    # Output adapters
│   ├── input_simulator.py    # Profile-based dispatcher (selects Win32 or UDP)
│   ├── win32_input.py        # Native SendInput wrapper (mouse moves, button presses, key combos)
│   ├── c4d_socket_client.py  # UDP client — serializes navigation commands as JSON
│   └── profiles/             # Per-application input mappings
│       ├── base_profile.py   # Abstract profile contract
│       ├── cinema4d.py       # C4D-specific key combos (Alt+MMB orbit, etc.)
│       └── blender.py        # Blender-specific key combos (MMB orbit, Shift+MMB pan)
│
├── ui/                       # Desktop application layer
│   ├── app.py                # Main window — mode switching, status bar, tray integration
│   ├── tray_icon.py          # System tray — gesture-reactive icon, context menu
│   ├── pip_widget.py         # PIP webcam overlay — frameless, draggable, resizable
│   ├── viewport_3d.py        # OpenGL 3D viewport for Preview mode
│   ├── tracker_thread.py     # QThread wrapper — runs tracking loop off main thread
│   └── i18n.py               # Internationalization — string tables, locale detection
│
├── c4d_plugin/               # Cinema 4D native plugin
│   └── HandNavigator/
│       ├── HandNavigator.pyp # Plugin entry — GeDialog, UDP server, navigation commands
│       ├── LICENSE
│       └── README.md
│
├── assets/                   # App icons (PNG, ICO, SVG)
├── models/                   # MediaPipe model (auto-downloaded, gitignored)
├── HandNavigator.spec        # PyInstaller build configuration
├── installer.iss             # Inno Setup installer script
└── requirements.txt          # Python dependencies
```

### Gesture Recognition (Detail)

The gesture classifier in `gesture_recognizer.py` uses a **heuristic, deterministic approach** — no secondary ML model, no training data needed. Classification is based on geometric analysis of the 21 MediaPipe landmarks:

- **Pinch detection:** Euclidean distance between thumb tip (landmark 4) and index tip (landmark 8), normalized against hand scale
- **Fist detection:** Average curl ratio of all five fingers (tip-to-MCP distance vs finger length)
- **Open hand:** All fingers extended beyond curl threshold
- **Debounce:** A gesture must persist for `GESTURE_SWITCH_FRAMES` consecutive frames before becoming active, preventing erratic switching

### Smoothing Pipeline

Raw hand landmarks are inherently noisy. HandNavigator applies a **dual-layer smoothing** strategy:

1. **Landmark smoothing** (One-Euro Filter per landmark) — applied before gesture classification to stabilize the input signal
2. **Navigation delta smoothing** — applied after the Navigation Solver to smooth the output commands
3. **Dead zones** — configurable minimum thresholds (`DEAD_ZONE_TRANSLATION`, `DEAD_ZONE_ROTATION`) below which movement is ignored entirely

The One-Euro Filter is an adaptive filter that increases smoothing at low speeds (reducing jitter) and decreases it at high speeds (preserving responsiveness). Parameters `min_cutoff` and `beta` are tuned per use case.

### C4D Plugin Protocol

The desktop app and Cinema 4D communicate via UDP on `127.0.0.1:19700`. Packets are JSON-encoded with the following schema:

```json
{
  "type": "orbit",
  "dx": 0.0023,
  "dy": -0.0011
}
```

Supported command types: `orbit`, `pan`, `zoom`. The plugin applies received deltas directly to the active camera's transformation matrix using the Cinema 4D Python API.

### Configuration

All tunable parameters live in `tracker/config.py`:

```python
ACTIVE_PROFILE       = "cinema4d"   # Profile selection
PAN_SENSITIVITY      = 800          # Mouse pixels per unit of hand movement
ZOOM_SENSITIVITY     = 1200         # Zoom responsiveness multiplier
ORBIT_SENSITIVITY    = 600          # Orbit responsiveness multiplier
DEAD_ZONE_TRANSLATION = 0.003      # Minimum movement threshold
DEAD_ZONE_ROTATION   = 0.004       # Minimum rotation threshold
GESTURE_SWITCH_FRAMES = 3          # Frames needed to confirm gesture change
SHOW_DEBUG_WINDOW    = True         # Show webcam debug overlay
```

### Building from Source

**Standalone EXE:**

```bash
pip install pyinstaller
python -m PyInstaller HandNavigator.spec --noconfirm --clean
# Output: dist/HandNavigator/HandNavigator.exe
```

**Windows Installer** (requires [Inno Setup 6](https://jrsoftware.org/isinfo.php)):

```bash
# First build the EXE, then:
iscc installer.iss
# Output: installer_output/HandNavigator_Setup_1.0.0.exe
```

### Adding a New Application Profile

1. Create `input/profiles/your_app.py` implementing `BaseProfile`
2. Define the key/mouse combos for orbit, pan, and zoom
3. Register it in `input/profiles/__init__.py`
4. Set `ACTIVE_PROFILE = "your_app"` in `tracker/config.py`

See `input/profiles/cinema4d.py` for a reference implementation.

---

## Author

**Flávio Takemoto** — [takemoto.com.br](http://www.takemoto.com.br)

## License

[MIT](LICENSE) — free for personal and commercial use.
