# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for macOS + ADB-only distribution."""
import os

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(SPECPATH)))

hiddenimports = collect_submodules("qfluentwidgets")
datas = collect_data_files("qfluentwidgets")
datas += [(os.path.join(ROOT, "config.json"), ".")]
datas += [(os.path.join(ROOT, "templates"), "templates")]
datas += [(os.path.join(ROOT, "assets", "app_icon.png"), ".")]

a = Analysis(
    [os.path.join(ROOT, "core", "gui", "__main__.py")],
    pathex=[ROOT],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "dxcam", "windows_capture", "winrt", "keyboard",
        "paddle", "paddleocr", "paddlex", "paddlepaddle",
    ],
    noarchive=False,
)

pyz = PYZ(a.pure)
app = BUNDLE(
    EXE(
        pyz,
        a.scripts,
        a.binaries,
        a.datas,
        [],
        name="CZN_Zero_Farm",
        debug=False,
        strip=False,
        upx=False,
        console=False,
        argv_emulation=False,
    ),
    name="CZN_Zero_Farm.app",
)
