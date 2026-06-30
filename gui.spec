# -*- mode: python ; coding: utf-8 -*-

a = Analysis(
    ['gui/main.py'],
    pathex=['.', 'gui'],
    binaries=[],
    datas=[],
    hiddenimports=[
        'bank_manager',
        'parse_markdown',
        'pages.bank_select',
        'pages.operations',
        'pages.quiz',
        'pages.result',
        'pages.wrong_book',
        'pages.collection',
        'pages.flagged',
        'pages.batch_delete',
        'widgets.question_card',
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
    name='quiz_gui',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    icon=None,
)
