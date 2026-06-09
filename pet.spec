# -*- mode: python ; coding: utf-8 -*-
# PyInstaller 打包配置
# 用法： pyinstaller pet.spec
# 产物： dist/BichonPet.exe （单文件、无控制台、内嵌资源）

block_cipher = None

a = Analysis(
    ['app.py'],
    pathex=[],
    binaries=[],
    # 关键：把 assets 目录一起打进 exe。
    # 元组格式 (源路径, 解压后相对路径)，运行时通过 sys._MEIPASS/assets 访问
    datas=[('assets', 'assets')],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='BichonPet',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,          # 等价于 --noconsole：不弹出黑色控制台
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    # icon='icon.ico',      # 可选：想要自定义图标，放一个 icon.ico 同目录并取消本行注释
)
