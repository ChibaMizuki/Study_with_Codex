"""Build an onedir portable app without any installer or OS registration."""
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parent


def main():
    required = ['tools/vlc/libvlc.dll', 'tools/vlc/libvlccore.dll',
                'tools/vlc/plugins', 'tools/ffmpeg.exe', 'tools/ffprobe.exe', 'tools/deno.exe']
    missing = [name for name in required if not (ROOT / name).exists()]
    if missing:
        raise SystemExit('同梱ツールが不足しています: ' + ', '.join(missing))
    # PyInstaller removes its previous output. Stage the build separately so an
    # update never removes downloaded media, settings, or custom output folders.
    staging = (ROOT / 'build' / 'portable').resolve()
    if not staging.is_relative_to(ROOT):
        raise SystemExit('ビルド先がプロジェクトの外を指しています。')
    subprocess.run([sys.executable, '-m', 'PyInstaller', '--noconfirm',
                    '--distpath', str(staging), '--workpath', str(ROOT / 'build'),
                    str(ROOT / 'MediaPlayer.spec')], cwd=ROOT, check=True)
    output = ROOT / 'dist' / 'MediaPlayer'
    shutil.copytree(staging / 'MediaPlayer', output, dirs_exist_ok=True)
    shutil.copy2(ROOT / 'README.md', output / 'README.md')
    shutil.copytree(ROOT / 'licenses', output / 'licenses', dirs_exist_ok=True)
    print(f'作成完了: {output / "MediaPlayer.exe"}')


if __name__ == '__main__':
    main()
