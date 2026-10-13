from pathlib import Path
from PyInstaller.utils.hooks import collect_all, collect_data_files

base = Path(SPECPATH)
ejs_data, ejs_binaries, ejs_hidden = collect_all('yt_dlp_ejs')
datas = [(str(base / 'tools'), 'tools'), (str(base / 'assets'), 'assets'),
         (str(base / 'licenses'), 'licenses'), (str(base / 'README.md'), '.')]
datas += ejs_data + collect_data_files('certifi')
a = Analysis([str(base / 'main.py')], pathex=[str(base)], binaries=ejs_binaries,
             datas=datas, hiddenimports=ejs_hidden,
             excludes=['PySide6.QtWebEngineCore', 'PySide6.QtWebEngineWidgets',
                       'PySide6.QtQml', 'PySide6.QtQuick', 'PySide6.QtMultimedia',
                       'PySide6.QtPdf', 'tkinter', 'pytest', 'PIL'])
# Qt uses the Windows ICU API. A similarly named DLL from development tools on
# PATH exports versioned ICU symbols and must not shadow the OS implementation.
a.binaries = [entry for entry in a.binaries
              if Path(entry[0]).name.lower() not in {'icuuc.dll', 'icudt78.dll'}]
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name='MediaPlayer',
          console=False, icon=str(base / 'assets' / 'app.ico'), upx=False)
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name='MediaPlayer')
