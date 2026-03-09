# HandNavigator — C4D Plugin

Hand-tracking viewport navigation for Cinema 4D.

## What it does

HandNavigator lets you orbit, pan, and zoom the C4D viewport using hand gestures captured by a webcam. It receives navigation commands via UDP from the HandNavigator desktop app.

| Gesture                 | Action            |
| ----------------------- | ----------------- |
| 🤏 Thumb + Index pinch  | **Pan** (full 2D) |
| ✊ Thumb + Middle pinch | **Orbit**         |
| 🤙 Thumb + Ring pinch   | **Zoom**          |

## Installation

### Option A — Plugin Search Path (recommended)

1. Open C4D → **Edit > Preferences > Plugins**
2. Click **Add Folder...** and select the `HandNavigator/` folder
3. Restart C4D

### Option B — Copy to Preferences

1. Open C4D → **Edit > Preferences** → click **Open Preferences Folder**
2. Create a `plugins/` folder if it doesn't exist
3. Copy the `HandNavigator/` folder into `plugins/`
4. Restart C4D

## Usage

1. Start the HandNavigator desktop app
2. In C4D: **Extensions > HandNavigator**
3. The plugin dialog opens with real-time status and sensitivity controls
4. Use hand gestures to navigate the viewport

## Settings

| Setting | Default | Range      | Description                 |
| ------- | ------- | ---------- | --------------------------- |
| Orbit   | 100     | 1–500      | Orbit rotation sensitivity  |
| Pan     | 500     | 1–2000     | Pan translation sensitivity |
| Zoom    | 1000    | 1–5000     | Zoom speed sensitivity      |
| Port    | 19700   | 1024–65535 | UDP listening port          |
| Poll    | 30 ms   | 10–200     | Command polling interval    |

## Supported Languages

- 🇺🇸 English
- 🇧🇷 Português (Brasil)
- 🇪🇸 Español

The plugin auto-detects C4D's interface language.

## Requirements

- Cinema 4D 2024 or later
- HandNavigator desktop app running on the same machine

## Protocol

JSON over UDP. Example commands:

```json
{"action": "orbit", "dx": 0.004, "dy": -0.002}
{"action": "pan",   "dx": 0.003, "dy": 0.001}
{"action": "zoom",  "dz": 0.005}
{"action": "reset"}
```

## License

MIT License — see [LICENSE](LICENSE)
