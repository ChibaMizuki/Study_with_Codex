import csv
from pathlib import Path
import random
import threading
import time
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import subprocess

import pytest
from PySide6.QtWidgets import QApplication
from downloader import DownloadWorker, validate_url
from library import PlaybackQueue, read_playlist, write_playlist
from paths import ROOT, TOOLS, inside_root, prepare


@pytest.fixture(scope='session', autouse=True)
def app():
    prepare()
    application = QApplication.instance() or QApplication([])
    yield application


@pytest.fixture(autouse=True)
def isolated_window_settings(monkeypatch):
    import app as app_module
    monkeypatch.setattr(app_module, 'load_settings', lambda: {})
    monkeypatch.setattr(app_module, 'save_settings', lambda _: None)


def test_old_csv_and_missing_entries(tmp_path):
    video = tmp_path / '日本語,映像.mp4'
    video.touch()
    file = tmp_path / 'old.csv'
    with file.open('w', encoding='utf-8-sig', newline='') as stream:
        csv.writer(stream).writerows([[str(video)], ['missing.mp4'], [], [str(video)]])
    paths, missing = read_playlist(file)
    assert paths == [str(video)]
    assert missing == [str(tmp_path / 'missing.mp4')]


def test_playlist_moves_with_media_folder(tmp_path):
    original = tmp_path / 'original'
    original.mkdir()
    media = original / 'clip.mp4'
    media.touch()
    write_playlist(original / 'list.csv', [str(media)])
    moved = tmp_path / 'moved'
    original.rename(moved)
    assert read_playlist(moved / 'list.csv') == ([str(moved / 'clip.mp4')], [])


def test_shuffle_preserves_current_and_visits_each_file():
    random.seed(42)
    queue = PlaybackQueue()
    queue.replace(['a', 'b', 'c', 'd'], 'c')
    queue.set_shuffle(True)
    assert queue.current == 'c'
    assert {queue.step(1) for _ in range(4)} == {'a', 'b', 'c', 'd'}
    queue.set_shuffle(False)
    assert queue.current == 'c'
    assert queue.step(1, repeat=False) == 'd'
    assert queue.step(1, repeat=False) is None
    assert queue.step(1) == 'a'
    queue.replace([])
    assert queue.step(-1) is None


def test_output_cannot_escape_app_folder(tmp_path):
    assert inside_root(tmp_path) == tmp_path
    with pytest.raises(ValueError):
        inside_root(ROOT.parent / 'external')
    with pytest.raises(ValueError):
        inside_root(ROOT / '..' / 'external')


@pytest.mark.parametrize('url', ['', 'file:///etc/passwd', 'https://', 'ftp://host/test'])
def test_invalid_url(url):
    with pytest.raises(ValueError):
        validate_url(url)


def test_unknown_download_size(tmp_path):
    worker = DownloadWorker('http://localhost/video', tmp_path)
    result = []
    worker.progress.connect(lambda percent, text: result.append((percent, text)))
    worker.hook({'status': 'downloading', 'downloaded_bytes': 1024})
    assert result[0][0] == -1


@pytest.fixture
def media_server(tmp_path):
    ffmpeg = str(TOOLS / 'ffmpeg.exe')
    subprocess.run([ffmpeg, '-hide_banner', '-loglevel', 'error', '-f', 'lavfi', '-i',
                    'color=c=teal:s=320x180:r=24:d=2', '-f', 'lavfi', '-i',
                    'sine=frequency=440:duration=2', '-c:v', 'libx264', '-pix_fmt',
                    'yuv420p', '-c:a', 'aac', '-shortest', str(tmp_path / 'clip.mp4')],
                   check=True, creationflags=subprocess.CREATE_NO_WINDOW)

    class Handler(SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(tmp_path), **kwargs)

        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield tmp_path, f'http://127.0.0.1:{server.server_port}'
    server.shutdown()
    server.server_close()
    thread.join()


def test_real_local_download(media_server):
    directory, url = media_server
    worker = DownloadWorker(url + '/clip.mp4', directory / 'download')
    results, errors = [], []
    worker.succeeded.connect(results.append)
    worker.failed.connect(errors.append)
    worker.run()
    assert errors == []
    assert len(results[0]) == 1
    output = Path(results[0][0])
    assert output.read_bytes() == (directory / 'clip.mp4').read_bytes()


def test_real_merge_reports_final_path(media_server, monkeypatch):
    import yt_dlp
    directory, url = media_server
    ffmpeg = str(TOOLS / 'ffmpeg.exe')
    for kind, args, name in [('video', ['-an', '-c:v', 'copy'], 'video.mp4'),
                             ('audio', ['-vn', '-c:a', 'copy'], 'audio.m4a')]:
        subprocess.run([ffmpeg, '-hide_banner', '-loglevel', 'error', '-i',
                        str(directory / 'clip.mp4'), *args, str(directory / name)],
                       check=True, creationflags=subprocess.CREATE_NO_WINDOW)

    class FixtureDownloader(yt_dlp.YoutubeDL):
        def extract_info(self, *args, **kwargs):
            return self.process_ie_result({
                'id': 'merge-fixture', 'title': '日本語結合テスト', 'extractor': 'fixture',
                'webpage_url': url, 'formats': [
                    {'format_id': 'audio', 'url': url + '/audio.m4a', 'ext': 'm4a',
                     'vcodec': 'none', 'acodec': 'mp4a.40.2'},
                    {'format_id': 'video', 'url': url + '/video.mp4', 'ext': 'mp4',
                     'vcodec': 'avc1.64001e', 'acodec': 'none', 'width': 320, 'height': 180},
                ],
            }, download=True)

    monkeypatch.setattr(yt_dlp, 'YoutubeDL', FixtureDownloader)
    worker = DownloadWorker(url + '/entry', directory / 'merged')
    results, errors = [], []
    worker.succeeded.connect(results.append)
    worker.failed.connect(errors.append)
    worker.run()
    assert errors == []
    assert len(results[0]) == 1
    assert Path(results[0][0]).suffix == '.mp4'
    info = subprocess.check_output([str(TOOLS / 'ffprobe.exe'), '-v', 'error',
                                    '-show_entries', 'stream=codec_type', '-of', 'csv=p=0',
                                    results[0][0]], creationflags=subprocess.CREATE_NO_WINDOW, text=True)
    assert 'video' in info and 'audio' in info


def test_cancel_before_start_does_not_report_success(tmp_path):
    worker = DownloadWorker('http://localhost/video', tmp_path)
    outcomes = []
    worker.cancelled.connect(lambda: outcomes.append('cancelled'))
    worker.succeeded.connect(lambda _: outcomes.append('success'))
    # Interruption is only honored by Qt on a running thread. Inject a preflight cancellation.
    monkey = pytest.MonkeyPatch()
    monkey.setattr(worker, 'isInterruptionRequested', lambda: True)
    worker.run()
    monkey.undo()
    assert outcomes == ['cancelled']


def test_closing_window_cancels_active_download(tmp_path, app):
    from app import PlayerWindow

    class SlowHandler(SimpleHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_GET(self):
            self.send_response(200)
            self.send_header('Content-Type', 'video/mp4')
            self.send_header('Content-Length', '10485760')
            self.end_headers()
            try:
                for _ in range(2560):
                    self.wfile.write(b'x' * 4096)
                    self.wfile.flush()
                    time.sleep(0.02)
            except (ConnectionError, OSError):
                pass

    server = ThreadingHTTPServer(('127.0.0.1', 0), SlowHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    window = PlayerWindow()
    window.show()
    window.url.setText(f'http://127.0.0.1:{server.server_port}/slow.mp4')
    window.destination.setText(str(tmp_path / 'cancelled-download'))
    try:
        window.start_download()
        worker = window.worker
        results = []
        worker.cancelled.connect(lambda: results.append('cancelled'))
        worker.succeeded.connect(lambda _: results.append('success'))
        deadline = time.monotonic() + 8
        while time.monotonic() < deadline and window.progress.maximum() == 0:
            app.processEvents()
            time.sleep(0.02)
        assert window.worker is not None
        window.close()
        assert window.closing
        assert window.isVisible()  # Stay alive until QThread has stopped.
        while time.monotonic() < deadline and window.isVisible():
            app.processEvents()
            time.sleep(0.02)
        assert window.worker is None
        assert not window.isVisible()
        assert results == ['cancelled']
        import shiboken6
        assert not shiboken6.isValid(worker) or not worker.isRunning()
    finally:
        if window.worker:
            window.worker.requestInterruption()
            window.worker.wait(20000)
            app.processEvents()
        if window.isVisible():
            window.close()
        server.shutdown()
        server.server_close()
        thread.join()


def test_playlist_toggle_expands_video_without_changing_queue(tmp_path, app):
    from app import PlayerWindow
    video = tmp_path / 'example.mp4'
    video.touch()
    window = PlayerWindow()
    window.show()
    app.processEvents()
    try:
        window.add_files([str(video)])
        native_handle = int(window.video_frame.winId())
        original_width = window.video_frame.width()
        original_sizes = window.player_splitter.sizes()
        window.playlist_button.click()
        app.processEvents()
        assert window.playlist_panel.isHidden()
        assert window.video_frame.width() > original_width
        assert not window.playlist_action.isChecked()
        assert window.queue.paths == [str(video)]
        window.playlist_action.trigger()
        app.processEvents()
        assert not window.playlist_panel.isHidden()
        assert window.playlist_button.isChecked()
        assert window.player_splitter.sizes() == original_sizes
        assert int(window.video_frame.winId()) == native_handle
    finally:
        window.close()


def test_fullscreen_fills_window_and_escape_restores_hidden_playlist(app, monkeypatch):
    from app import PlayerWindow
    from PySide6.QtCore import Qt
    from PySide6.QtTest import QTest
    saved = []
    monkeypatch.setattr('app.save_settings', saved.append)
    monkeypatch.setattr('app.load_settings', lambda: {'playlist_visible': False})
    window = PlayerWindow()
    window.show()
    app.processEvents()
    original_size = window.size()
    native_handle = int(window.video_frame.winId())
    try:
        assert window.playlist_panel.isHidden()
        QTest.keyClick(window, Qt.Key.Key_F11)
        app.processEvents()
        assert window.isFullScreen()
        assert all(widget.isHidden() for widget in window.fullscreen_chrome())
        assert window.playlist_panel.isHidden()
        assert window.video_frame.size() == window.centralWidget().size()
        assert int(window.video_frame.winId()) == native_handle
        QTest.keyClick(window, Qt.Key.Key_Escape)
        app.processEvents()
        assert not window.isFullScreen()
        assert window.size() == original_size
        assert all(not widget.isHidden() for widget in window.fullscreen_chrome())
        assert window.playlist_panel.isHidden()
        assert not window.playlist_button.isChecked()
    finally:
        window.close()
    assert saved[0]['playlist_visible'] is False


def test_fullscreen_restores_maximized_window_and_download_page(app):
    from app import PlayerWindow
    window = PlayerWindow()
    window.showMaximized()
    app.processEvents()
    window.show_page(1)
    try:
        window.toggle_fullscreen()
        app.processEvents()
        assert window.pages.currentIndex() == 0
        window.exit_fullscreen()
        app.processEvents()
        assert window.isMaximized()
        assert window.pages.currentIndex() == 1
        assert not window.playlist_panel.isHidden()
        window.toggle_fullscreen()
        window.show_page(1)  # Ctrl+D must also restore the normal UI.
        app.processEvents()
        assert not window.isFullScreen()
        assert window.pages.currentIndex() == 1
        assert not window.sidebar.isHidden()
    finally:
        window.close()
