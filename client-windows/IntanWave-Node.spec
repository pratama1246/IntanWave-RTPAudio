# -*- mode: python ; coding: utf-8 -*-

datas = [
    ('app_icon.png', '.'),
    ('app_icon.ico', '.'),
    ('test_chime.wav', '.'),
    ('config.json', '.')
]
binaries = [
    ('ffplay.exe', '.')
]
hiddenimports = []

a = Analysis(
    ['app.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'PySide6', 'shiboken6', 'qfluentwidgets', 
        'numpy', 'pandas', 'matplotlib', 'scipy', 
        'openai', 'azure', 'unittest', 'pydoc',
        'xmlrpc',
        'lzma', '_lzma', 'bz2', '_bz2', 'zstandard', '_zstd',
        'decimal', '_decimal'
    ],
    noarchive=False,
    optimize=2,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='IntanWave-Node',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['app_icon.ico'],
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='IntanWave-Node',
)
