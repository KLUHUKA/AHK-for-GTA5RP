# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['Port.py'],
    pathex=[],
    binaries=[],
    datas=[('cda95f6b-1f50-49be-b6b9-77d54fa40350.ico', '.'), ('cda95f6b-1f50-49be-b6b9-77d54fa40350.png', '.'), ('port.ahk', '.'), ('AutoHotkeyU64.exe', '.')],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='Port',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['cda95f6b-1f50-49be-b6b9-77d54fa40350.ico'],
)
