# -*- mode: python ; coding: utf-8 -*-
"""
HandNavigator — PyInstaller spec
Builds a single-folder distribution with all assets bundled.
"""

import os
from PyInstaller.utils.hooks import collect_submodules, collect_data_files

block_cipher = None
ROOT = os.path.abspath(".")

# Collect mediapipe submodules (but NOT torch/scipy via collect_all)
mp_hiddenimports = collect_submodules("mediapipe")

# Collect mediapipe data files (protobuf descriptors, .tflite models, etc.)
mp_datas = collect_data_files("mediapipe")

a = Analysis(
    ["ui/app.py"],
    pathex=[ROOT],
    binaries=[],
    datas=[
        ("models/hand_landmarker.task", "models"),
        ("assets", "assets"),
    ] + mp_datas,
    hiddenimports=[
        "PyQt6.QtSvg",
        "OpenGL",
        "OpenGL.GL",
        "OpenGL.GLU",
        "OpenGL.platform.win32",
        "tracker",
        "tracker.config",
        "tracker.gesture_recognizer",
        "tracker.hand_detector",
        "tracker.navigation_solver",
        "tracker.smoothing",
        "tracker.main",
        "input",
        "input.input_simulator",
        "input.c4d_socket_client",
        "input.win32_input",
        "input.profiles",
        "input.profiles.cinema4d",
        "input.profiles.blender",
        "ui",
        "ui.i18n",
        "ui.pip_widget",
        "ui.tray_icon",
        "ui.tracker_thread",
        "ui.viewport_3d",
    ] + mp_hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "torch", "torchvision", "torchaudio",
        "scipy", "pytest", "IPython", "notebook",
        "pandas", "sklearn",
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="HandNavigator",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,          # Windowed app — no console
    icon="assets/handnavigator.ico",
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="HandNavigator",
)
