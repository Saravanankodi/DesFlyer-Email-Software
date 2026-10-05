# PyInstaller spec for the Windows one-file desktop build.
from PyInstaller.utils.hooks import collect_data_files

project = "."

hiddenimports = [
    "flask_sqlalchemy",
    "flask_login",
    "flask_mail",
    "openpyxl",
    "cryptography",
    "waitress",
]

datas = [
    ("templates", "templates"),
    ("static", "static"),
]

# pywebview selects a Windows GUI backend at runtime.
datas += collect_data_files("webview")


a = Analysis(
    ["desktop_launcher.py"],
    pathex=[project],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
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
    name="DesFlyer-Email-Automation",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
)
