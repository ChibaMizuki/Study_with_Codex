# Third-party components

These components retain their original licenses.

- PySide6 6.12.0: LGPL-3.0-only OR GPL-2.0-only OR GPL-3.0-only
- PySide6_Essentials 6.12.0: LGPL-3.0-only OR GPL-2.0-only OR GPL-3.0-only
- PySide6_Addons 6.12.0: LGPL-3.0-only OR GPL-2.0-only OR GPL-3.0-only
- shiboken6 6.12.0: LGPL-3.0-only OR GPL-2.0-only OR GPL-3.0-only
- python-vlc 3.0.21203: LGPL-2.1+
- yt-dlp 2026.8.19: Unlicense
- yt-dlp-ejs 0.8.0: Unlicense AND MIT AND ISC
- certifi 2026.7.22: MPL-2.0
- requests 2.34.2: Apache-2.0
- urllib3 2.8.0: MIT
- charset-normalizer 3.5.2: MIT
- idna 3.20: BSD-3-Clause
- websockets 17.2: BSD-3-Clause
- brotli 1.2.0: MIT
- pycryptodomex 3.24.1: BSD, Public Domain
- mutagen 1.48.1: GPL-2.0-or-later
- pyinstaller 6.22.3: GPLv2-or-later with a special exception which allows to use PyInstaller to build and distribute non-free programs (including commercial ones)

## Native tools

- VLC: https://www.videolan.org/vlc/ ; source https://code.videolan.org/videolan/vlc (3.0.x). The bundled runtime is a read-only copy of the original app runtime.
- FFmpeg 7.1.1: https://www.gyan.dev/ffmpeg/builds/ ; source https://ffmpeg.org/releases/ffmpeg-7.1.1.tar.xz . The existing full build is copied into tools/. Build configuration is in NATIVE-VERSIONS.txt.
- Deno: https://github.com/denoland/deno ; source https://github.com/denoland/deno/releases . Version is in NATIVE-VERSIONS.txt.
- PySide6 / Qt: https://code.qt.io/ ; https://download.qt.io/official_releases/QtForPython/

The portable package keeps dynamically loaded Qt and VLC libraries replaceable.
Copies of available license and notice files are included in this directory.