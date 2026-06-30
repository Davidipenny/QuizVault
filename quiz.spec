# -*- mode: python ; coding: utf-8 -*-

a = Analysis(
    ['quiz.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=[
        'bank_manager',
        'parse_markdown',
        'import_questions',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='quiz',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    icon=None,
)
