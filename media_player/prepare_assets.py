"""Create the application icon and bundle third-party notices."""
import importlib.metadata
from pathlib import Path
import shutil
import urllib.request
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent


def main():
    image = Image.new('RGBA', (256, 256), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((8, 8, 248, 248), radius=54, fill='#121822')
    draw.rounded_rectangle((30, 30, 226, 226), radius=38, outline='#67d9c0', width=8)
    draw.polygon([(103, 76), (103, 180), (181, 128)], fill='#67d9c0')
    image.save(ROOT / 'assets' / 'app.ico', sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
    image.save(ROOT / 'assets' / 'app.png')
    licenses = ROOT / 'licenses'
    notices = ['# Third-party components', '', 'These components retain their original licenses.', '']
    packages = ['PySide6', 'PySide6_Essentials', 'PySide6_Addons', 'shiboken6', 'python-vlc',
                'yt-dlp', 'yt-dlp-ejs', 'certifi', 'requests', 'urllib3', 'charset-normalizer',
                'idna', 'websockets', 'brotli', 'pycryptodomex', 'mutagen', 'pyinstaller']
    for name in packages:
        distribution = importlib.metadata.distribution(name)
        notices.append(f'- {name} {distribution.version}: {distribution.metadata.get("License-Expression") or distribution.metadata.get("License") or "see license files"}')
        for file in distribution.files or []:
            if '.dist-info' in str(file) and any(word in str(file).lower() for word in ('license', 'copying', 'notice')):
                source = Path(distribution.locate_file(file))
                if source.is_file():
                    target = licenses / name / Path(*file.parts[1:])
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(source, target)
    urls = {
        'Deno-LICENSE.txt': 'https://raw.githubusercontent.com/denoland/deno/main/LICENSE.md',
        'VLC-COPYING.txt': 'https://raw.githubusercontent.com/videolan/vlc/3.0.x/COPYING',
        'libVLC-COPYING.LIB.txt': 'https://raw.githubusercontent.com/videolan/vlc/3.0.x/COPYING.LIB',
        'FFmpeg-COPYING.GPLv3.txt': 'https://raw.githubusercontent.com/FFmpeg/FFmpeg/n7.1.1/COPYING.GPLv3',
    }
    for filename, url in urls.items():
        with urllib.request.urlopen(url, timeout=30) as response:
            (licenses / filename).write_bytes(response.read())
    notices += ['', '## Native tools', '',
                '- VLC: https://www.videolan.org/vlc/ ; source https://code.videolan.org/videolan/vlc (3.0.x). The bundled runtime is a read-only copy of the original app runtime.',
                '- FFmpeg 7.1.1: https://www.gyan.dev/ffmpeg/builds/ ; source https://ffmpeg.org/releases/ffmpeg-7.1.1.tar.xz . The existing full build is copied into tools/. Build configuration is in NATIVE-VERSIONS.txt.',
                '- Deno: https://github.com/denoland/deno ; source https://github.com/denoland/deno/releases . Version is in NATIVE-VERSIONS.txt.',
                '- PySide6 / Qt: https://code.qt.io/ ; https://download.qt.io/official_releases/QtForPython/',
                '', 'The portable package keeps dynamically loaded Qt and VLC libraries replaceable.',
                'Copies of available license and notice files are included in this directory.']
    (licenses / 'THIRD-PARTY.md').write_text('\n'.join(notices), encoding='utf-8')


if __name__ == '__main__':
    main()
