"""Background download worker. Widgets are touched only by the GUI thread."""
from pathlib import Path
from urllib.parse import urlparse
from PySide6.QtCore import QThread, Signal
from paths import DATA, TOOLS, inside_root


class Cancelled(Exception):
    pass


def validate_url(url):
    parsed = urlparse(url.strip())
    if parsed.scheme not in ('http', 'https') or not parsed.hostname:
        raise ValueError('http:// または https:// で始まるURLを入力してください。')
    return url.strip()


class DownloadWorker(QThread):
    progress = Signal(int, str)
    message = Signal(str)
    file_ready = Signal(str)
    succeeded = Signal(list)
    failed = Signal(str)
    cancelled = Signal()

    def __init__(self, url, folder, allow_playlist=False, parent=None):
        super().__init__(parent)
        self.url = validate_url(url)
        self.folder = inside_root(folder)
        self.allow_playlist = allow_playlist
        self.files = []

    def check_cancel(self):
        if self.isInterruptionRequested():
            raise Cancelled()

    def hook(self, event):
        self.check_cancel()
        status = event.get('status')
        if status == 'downloading':
            total = event.get('total_bytes') or event.get('total_bytes_estimate')
            amount = event.get('downloaded_bytes', 0)
            percentage = min(100, int(amount * 100 / total)) if total else -1
            speed = event.get('speed')
            eta = event.get('eta')
            details = f'{amount / 1024 / 1024:.1f} MB'
            if speed:
                details += f'  ·  {speed / 1024 / 1024:.1f} MB/s'
            if eta is not None:
                details += f'  ·  残り約 {int(eta)} 秒'
            self.progress.emit(percentage, details)
        elif status == 'finished':
            self.progress.emit(100, 'ダウンロード済み · ファイルを仕上げています')

    def record(self, filename):
        self.check_cancel()
        path = inside_root(filename)
        if not path.is_file():
            raise ValueError(f'完成ファイルが見つかりません: {path.name}')
        if str(path) not in self.files:
            self.files.append(str(path))
            self.file_ready.emit(str(path))

    def options(self):
        return {
            'format': 'bv*+ba/b',
            'outtmpl': str(self.folder / '%(title).160B [%(id)s].%(ext)s'),
            'merge_output_format': 'mp4',
            'windowsfilenames': True,
            'noplaylist': not self.allow_playlist,
            'ffmpeg_location': str(TOOLS),
            'js_runtimes': {'deno': {'path': str(TOOLS / 'deno.exe')}},
            'cachedir': str(DATA / 'cache' / 'yt-dlp'),
            'progress_hooks': [self.hook],
            'postprocessor_hooks': [lambda _: self.check_cancel()],
            'socket_timeout': 15,
            'retries': 2,
            'fragment_retries': 2,
            'logger': self,
            'quiet': True,
            'no_warnings': False,
        }

    def debug(self, text):
        if not text.startswith('[debug]'):
            self.check_cancel()
            self.message.emit(text)

    def warning(self, text):
        self.message.emit('注意: ' + text)

    def error(self, text):
        self.message.emit(text)

    def run(self):
        try:
            import yt_dlp
            from yt_dlp.postprocessor.common import PostProcessor
            worker = self

            class FinalFile(PostProcessor):
                def run(self, info):
                    worker.record(info['filepath'])
                    return [], info

            self.folder.mkdir(parents=True, exist_ok=True)
            self.check_cancel()
            self.message.emit('動画情報を取得しています…')
            with yt_dlp.YoutubeDL(self.options()) as downloader:
                downloader.add_post_processor(FinalFile(downloader), when='after_move')
                downloader.extract_info(self.url, download=True)
            self.check_cancel()
            if not self.files:
                raise ValueError('ダウンロード可能な動画が見つかりませんでした。')
            self.succeeded.emit(self.files.copy())
        except Exception as error:
            if self.isInterruptionRequested() or isinstance(error, Cancelled):
                self.cancelled.emit()
            else:
                self.failed.emit(str(error))
