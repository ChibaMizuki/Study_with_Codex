"""All persistent application files live beside the source or executable."""
import json
import os
from pathlib import Path
import sys

ROOT = Path(sys.executable).resolve().parent if getattr(sys, 'frozen', False) else Path(__file__).resolve().parent
RESOURCES = Path(getattr(sys, '_MEIPASS', ROOT))
DATA = ROOT / 'data'
DOWNLOADS = ROOT / 'downloads'
PLAYLISTS = ROOT / 'playlists'
TOOLS = RESOURCES / 'tools'


def prepare():
    for directory in (DATA, DOWNLOADS, PLAYLISTS, DATA / 'cache', DATA / 'temp'):
        directory.mkdir(parents=True, exist_ok=True)
    os.environ['DENO_DIR'] = str(DATA / 'cache' / 'deno')
    os.environ['TEMP'] = os.environ['TMP'] = str(DATA / 'temp')
    os.environ['VLC_PLUGIN_PATH'] = str(TOOLS / 'vlc' / 'plugins')
    os.environ['PYTHON_VLC_LIB_PATH'] = str(TOOLS / 'vlc' / 'libvlc.dll')
    os.environ['PYTHON_VLC_MODULE_PATH'] = str(TOOLS / 'vlc')


def inside_root(path):
    resolved = Path(path).resolve()
    if not resolved.is_relative_to(ROOT):
        raise ValueError('保存先は、このアプリのフォルダ内を選択してください。')
    return resolved


def load_settings():
    try:
        settings = json.loads((DATA / 'settings.json').read_text(encoding='utf-8'))
        return settings if isinstance(settings, dict) else {}
    except (OSError, ValueError):
        return {}


def save_settings(settings):
    pending = DATA / 'settings.tmp'
    pending.write_text(json.dumps(settings, ensure_ascii=False, indent=2), encoding='utf-8')
    pending.replace(DATA / 'settings.json')
