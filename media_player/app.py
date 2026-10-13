from pathlib import Path
import sys

from PySide6.QtCore import Qt, QTimer, QUrl, Signal
from PySide6.QtGui import QAction, QCursor, QDesktopServices, QIcon, QKeySequence
from PySide6.QtWidgets import (
    QAbstractItemView, QApplication, QCheckBox, QFileDialog, QFrame, QHBoxLayout,
    QLabel, QLineEdit, QListWidget, QListWidgetItem, QMainWindow, QMessageBox,
    QPlainTextEdit, QProgressBar, QPushButton, QSizePolicy, QSlider, QSplitter,
    QStackedWidget, QStyle, QVBoxLayout, QWidget,
)

from downloader import DownloadWorker
from library import MEDIA_EXTENSIONS, PlaybackQueue, read_playlist, write_playlist
from paths import DATA, DOWNLOADS, PLAYLISTS, RESOURCES, ROOT, inside_root, load_settings, save_settings

MEDIA_FILTER = 'メディア (' + ' '.join('*' + ext for ext in sorted(MEDIA_EXTENSIONS)) + ');;すべてのファイル (*)'

STYLE = """
QWidget { background: #121822; color: #e9edf5; font-family: 'Yu Gothic UI'; font-size: 13px; }
QMainWindow { background: #121822; }
QLabel#brand { color: #ffffff; font-size: 22px; font-weight: 700; }
QLabel#heading { font-size: 26px; font-weight: 700; }
QLabel#subtle { color: #96a5ba; }
QLabel#title { font-size: 16px; font-weight: 600; }
QFrame#sidebar { background: #0d121b; border-right: 1px solid #253044; }
QFrame#sidebar QLabel { background: transparent; }
QFrame#card { background: #192230; border: 1px solid #2a364a; border-radius: 12px; }
QFrame#card QLabel, QFrame#card QCheckBox { background: transparent; }
QPushButton { background: #243147; border: 1px solid #35435b; border-radius: 7px; padding: 9px 14px; }
QPushButton:hover { background: #30415b; border-color: #5d779b; }
QPushButton:pressed { background: #182333; }
QPushButton:disabled { color: #61718a; background: #1b2535; border-color: #263246; }
QPushButton#primary { background: #67d9c0; color: #082820; border: 0; font-weight: 700; }
QPushButton#primary:hover { background: #93eed9; }
QPushButton#primary:disabled { background: #254c48; color: #819d98; }
QPushButton#nav { text-align: left; background: transparent; border: 0; padding: 13px; }
QPushButton#nav:checked { background: #233b40; color: #83e5cc; }
QLineEdit, QPlainTextEdit, QListWidget { background: #101722; border: 1px solid #304058; border-radius: 7px; padding: 7px; }
QLineEdit:focus { border-color: #67d9c0; }
QListWidget::item { padding: 11px 7px; border-radius: 5px; }
QListWidget::item:selected { background: #29484b; color: #a4f3df; }
QListWidget::item:hover { background: #253448; }
QSlider::groove:horizontal { background: #34425a; height: 5px; border-radius: 2px; }
QSlider::sub-page:horizontal { background: #67d9c0; border-radius: 2px; }
QSlider::handle:horizontal { background: #d0fff3; width: 13px; margin: -5px 0; border-radius: 6px; }
QCheckBox { spacing: 8px; }
QCheckBox::indicator { width: 15px; height: 15px; border: 1px solid #53667e; border-radius: 4px; background: #101722; }
QCheckBox::indicator:checked { background: #67d9c0; border-color: #67d9c0; image: url(__CHECK_ICON__); }
QProgressBar { border: 1px solid #304058; border-radius: 6px; text-align: center; min-height: 20px; background: #101722; }
QProgressBar::chunk { background: #347e74; border-radius: 5px; }
QMenuBar, QMenu { background: #192230; }
QMenuBar::item:selected, QMenu::item:selected { background: #30415b; }
QStatusBar { color: #9cacbf; background: #0d121b; }
QSplitter::handle { background: #253044; width: 2px; }
QToolTip { background: #243147; color: #fff; border: 1px solid #53667e; padding: 5px; }
"""


def label(text, name=None):
    widget = QLabel(text)
    if name:
        widget.setObjectName(name)
    return widget


def button(text, callback, primary=False):
    widget = QPushButton(text)
    if primary:
        widget.setObjectName('primary')
    widget.clicked.connect(callback)
    return widget


def row(*widgets):
    layout = QHBoxLayout()
    layout.setSpacing(8)
    for widget in widgets:
        layout.addWidget(widget)
    return layout


class Slider(QSlider):
    def wheelEvent(self, event):
        event.ignore()


class MediaList(QListWidget):
    files_dropped = Signal(list)
    edited = Signal()

    def __init__(self):
        super().__init__()
        self.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.setAcceptDrops(True)
        self.setToolTip('ダブルクリックで再生。ドラッグで並べ替え、枠の外へドラッグで削除。')
        self.model().rowsMoved.connect(lambda *_: self.edited.emit())

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            super().dragEnterEvent(event)

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            super().dragMoveEvent(event)

    def dropEvent(self, event):
        if event.mimeData().hasUrls():
            self.files_dropped.emit([url.toLocalFile() for url in event.mimeData().urls() if url.isLocalFile()])
            event.acceptProposedAction()
        else:
            super().dropEvent(event)

    def startDrag(self, actions):
        selected = self.selectedItems()
        super().startDrag(actions)
        if not self.rect().contains(self.mapFromGlobal(QCursor.pos())):
            for item in selected:
                index = self.row(item)
                if index >= 0:
                    self.takeItem(index)
            self.edited.emit()


class PlayerWindow(QMainWindow):
    media_ended = Signal()
    media_error = Signal()

    def __init__(self):
        super().__init__()
        import vlc
        self.vlc = vlc
        self.settings = load_settings()
        self.queue = PlaybackQueue()
        self.current_media = None
        self.in_queue = False
        self.worker = None
        self.closing = False
        self.current_download_files = []
        self._end_pending = False
        self.muted = False
        self._audio_pending = False
        self._video_fullscreen = False
        self._playlist_visible = bool(self.settings.get('playlist_visible', True))
        self._playlist_sizes = [730, 290]
        self.setWindowTitle('Media Player')
        self.setWindowIcon(QIcon(str(RESOURCES / 'assets' / 'app.ico')))
        self.resize(1280, 800)
        self.setMinimumSize(980, 660)
        self.setAcceptDrops(True)
        self.instance = vlc.Instance('--no-video-title-show', '--no-osd', '--no-media-library', '--no-plugins-cache', '--quiet', '--no-snapshot-preview')
        if self.instance is None:
            raise RuntimeError('VLCを初期化できませんでした。tools/vlcを確認してください。')
        self.player = self.instance.media_player_new()
        self.player.video_set_mouse_input(False)
        self.player.video_set_key_input(False)
        self.build_ui()
        self.build_menu()
        self.set_playlist_visible(self._playlist_visible)
        self.media_ended.connect(self.on_end)
        self.media_error.connect(self.on_playback_error)
        self.events = self.player.event_manager()
        self._end_callback = lambda _: self.media_ended.emit()
        self._error_callback = lambda _: self.media_error.emit()
        self.events.event_attach(vlc.EventType.MediaPlayerEndReached, self._end_callback)
        self.events.event_attach(vlc.EventType.MediaPlayerEncounteredError, self._error_callback)
        self.timer = QTimer(self)
        self.timer.setInterval(250)
        self.timer.timeout.connect(self.refresh_player)
        self.timer.start()
        saved = self.settings.get('playlist', [])
        if isinstance(saved, list):
            self.add_files([p for p in saved if isinstance(p, str) and Path(p).is_file()])
        self.player.audio_set_volume(self.volume.value())
        self.statusBar().showMessage('ファイルを開くか、ここへドラッグしてください')

    def build_ui(self):
        central = QWidget()
        outer = QHBoxLayout(central)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        self.setCentralWidget(central)
        sidebar = QFrame()
        self.sidebar = sidebar
        sidebar.setObjectName('sidebar')
        sidebar.setFixedWidth(190)
        nav = QVBoxLayout(sidebar)
        nav.setContentsMargins(18, 30, 18, 20)
        nav.addWidget(label('◈  MEDIA', 'brand'))
        nav.addWidget(label('PLAYER', 'subtle'))
        nav.addSpacing(35)
        self.nav_buttons = []
        for index, text in enumerate(('▷  プレイヤー', '↓  ダウンロード')):
            entry = button(text, lambda checked=False, i=index: self.show_page(i))
            entry.setObjectName('nav')
            entry.setCheckable(True)
            nav.addWidget(entry)
            self.nav_buttons.append(entry)
        nav.addStretch()
        nav.addWidget(button('保存フォルダを開く', lambda: self.open_folder(DOWNLOADS)))
        nav.addSpacing(12)
        nav.addWidget(label('PORTABLE EDITION', 'subtle'))
        outer.addWidget(sidebar)
        self.pages = QStackedWidget()
        outer.addWidget(self.pages, 1)
        self.pages.addWidget(self.build_player_page())
        self.pages.addWidget(self.build_download_page())
        self.show_page(0)

    def build_player_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        self.player_page_layout = layout
        layout.setSpacing(12)
        layout.setContentsMargins(24, 24, 24, 20)
        self.playlist_button = QPushButton('プレイリスト')
        self.playlist_button.setCheckable(True)
        self.playlist_button.setChecked(self._playlist_visible)
        self.playlist_button.setToolTip('プレイリストを表示 / 非表示（Ctrl+P）')
        self.playlist_button.toggled.connect(self.set_playlist_visible)
        self.player_header = QWidget()
        header = row(label('プレイヤー', 'heading'), self.playlist_button,
                     button('ファイルを開く', self.open_dialog, True))
        header.setContentsMargins(0, 0, 0, 0)
        header.setStretch(0, 1)
        self.player_header.setLayout(header)
        layout.addWidget(self.player_header)
        self.player_subtitle = label('動画も音楽も、ひとつの場所で。', 'subtle')
        layout.addWidget(self.player_subtitle)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        self.player_splitter = splitter
        viewer = QWidget()
        video_layout = QVBoxLayout(viewer)
        self.viewer_layout = video_layout
        video_layout.setContentsMargins(0, 0, 14, 0)
        self.video_frame = QFrame()
        self.video_frame.setStyleSheet('background: #05090e; border-radius: 9px;')
        self.video_frame.setAttribute(Qt.WidgetAttribute.WA_NativeWindow)
        self.video_frame.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.video_frame.setMinimumSize(320, 240)
        self.empty_hint = label('▷\n\nファイルを開いて再生\n\n動画・音声をドラッグして追加', 'subtle')
        self.empty_hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hint_layout = QVBoxLayout(self.video_frame)
        hint_layout.addWidget(self.empty_hint)
        video_layout.addWidget(self.video_frame, 1)
        self.now_title = label('メディアが選択されていません', 'title')
        self.now_title.setWordWrap(True)
        video_layout.addWidget(self.now_title)
        self.time_label = label('00:00 / 00:00', 'subtle')
        self.seek = Slider(Qt.Orientation.Horizontal)
        self.seek.setRange(0, 10000)
        self.seek.setEnabled(False)
        self.seek.sliderMoved.connect(self.seek_preview)
        self.seek.sliderReleased.connect(self.seek_release)
        self.seek.actionTriggered.connect(self.seek_action)
        self.seek_panel = QWidget()
        seek_layout = row(self.seek, self.time_label)
        seek_layout.setContentsMargins(0, 0, 0, 0)
        self.seek_panel.setLayout(seek_layout)
        video_layout.addWidget(self.seek_panel)
        self.play_button = button('', self.toggle_play)
        self.play_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPlay))
        self.play_button.setToolTip('再生 / 一時停止（Space）')
        previous = button('', lambda: self.step(-1))
        previous.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaSkipBackward))
        previous.setToolTip('前のメディア（Ctrl+Left）')
        following = button('', lambda: self.step(1))
        following.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaSkipForward))
        following.setToolTip('次のメディア（Ctrl+Right）')
        stop = button('停止', self.stop)
        self.mute_button = button('音量', self.toggle_mute)
        self.mute_button.setToolTip('ミュート切り替え（M）')
        self.volume = Slider(Qt.Orientation.Horizontal)
        self.volume.setRange(0, 100)
        value = self.settings.get('volume', 50)
        self.volume.setValue(value if isinstance(value, int) and 0 <= value <= 100 else 50)
        self.volume.setMaximumWidth(100)
        self.volume.valueChanged.connect(self.set_volume)
        self.volume_label = label(str(self.volume.value()), 'subtle')
        self.repeat = QCheckBox('ループ')
        self.repeat.setChecked(bool(self.settings.get('repeat', True)))
        self.repeat.setToolTip('単体は繰り返し再生。プレイリストは最後から先頭へ戻ります。')
        full = button('全画面', self.toggle_fullscreen)
        full.setToolTip('動画だけを全画面表示（F11）、解除（Esc）')
        controls = row(previous, self.play_button, following, stop, self.repeat, self.mute_button, self.volume, self.volume_label, full)
        controls.setContentsMargins(0, 0, 0, 0)
        self.controls_panel = QWidget()
        self.controls_panel.setLayout(controls)
        video_layout.addWidget(self.controls_panel)
        splitter.addWidget(viewer)
        playlist_panel = QWidget()
        self.playlist_panel = playlist_panel
        pl = QVBoxLayout(playlist_panel)
        pl.setContentsMargins(14, 0, 0, 0)
        self.playlist_heading = label('プレイリスト · 0', 'title')
        pl.addWidget(self.playlist_heading)
        pl.addWidget(label('ドラッグで追加・並べ替え', 'subtle'))
        self.media_list = MediaList()
        self.media_list.files_dropped.connect(self.add_files)
        self.media_list.edited.connect(self.sync_queue)
        self.media_list.itemDoubleClicked.connect(self.play_item)
        pl.addWidget(self.media_list, 1)
        pl.addLayout(row(button('追加', self.add_dialog), button('削除', self.remove_selected), button('新規', self.clear_playlist)))
        pl.addLayout(row(button('CSV読込', self.load_playlist_dialog), button('CSV保存', self.save_playlist_dialog)))
        self.shuffle = QCheckBox('シャッフル')
        self.shuffle.toggled.connect(self.queue.set_shuffle)
        pl.addLayout(row(self.shuffle, button('リストを再生', self.play_list, True)))
        splitter.addWidget(playlist_panel)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes(self._playlist_sizes)
        layout.addWidget(splitter, 1)
        return page

    def build_download_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(28, 26, 28, 24)
        layout.addWidget(label('ダウンロード', 'heading'))
        layout.addWidget(label('URLから保存して、そのままプレイヤーへ。', 'subtle'))
        layout.addSpacing(20)
        card = QFrame()
        card.setObjectName('card')
        form = QVBoxLayout(card)
        form.setContentsMargins(24, 22, 24, 22)
        form.setSpacing(14)
        form.addWidget(label('動画のURL', 'title'))
        self.url = QLineEdit()
        self.url.setPlaceholderText('https://…')
        self.url.setClearButtonEnabled(True)
        self.url.returnPressed.connect(self.start_download)
        form.addWidget(self.url)
        form.addWidget(label('保存先（アプリのフォルダ内）', 'subtle'))
        self.destination = QLineEdit(str(DOWNLOADS))
        self.destination.setReadOnly(True)
        self.choose_destination = button('変更', self.choose_download_folder)
        form.addLayout(row(self.destination, self.choose_destination))
        self.play_after = QCheckBox('完了後に再生する')
        self.play_after.setChecked(bool(self.settings.get('play_after', True)))
        self.download_playlist = QCheckBox('URLに含まれるプレイリスト全体を保存する')
        form.addWidget(self.play_after)
        form.addWidget(self.download_playlist)
        form.addWidget(label('最高品質を取得し、必要に応じて映像と音声を結合します。', 'subtle'))
        self.start_button = button('ダウンロード開始', self.start_download, True)
        self.cancel_button = button('キャンセル', self.cancel_download)
        self.cancel_button.setEnabled(False)
        form.addLayout(row(self.start_button, self.cancel_button))
        layout.addWidget(card)
        layout.addSpacing(18)
        self.download_status = label('準備できています', 'title')
        layout.addWidget(self.download_status)
        self.progress = QProgressBar()
        layout.addWidget(self.progress)
        self.download_details = label('保存したファイルはプレイリストへ追加されます。', 'subtle')
        layout.addWidget(self.download_details)
        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.setMaximumBlockCount(500)
        self.log.setPlaceholderText('ダウンロードの状況をここに表示します')
        layout.addWidget(self.log, 1)
        self.download_results = QListWidget()
        self.download_results.setMaximumHeight(115)
        self.download_results.setToolTip('ダブルクリックで再生')
        self.download_results.itemDoubleClicked.connect(lambda item: self.play_file(item.data(Qt.ItemDataRole.UserRole)))
        layout.addWidget(self.download_results)
        return page

    def build_menu(self):
        file_menu = self.menuBar().addMenu('ファイル')
        self.add_action(file_menu, 'メディアを開く', self.open_dialog, 'Ctrl+O')
        self.add_action(file_menu, 'プレイリストに追加', self.add_dialog, 'Ctrl+Shift+O')
        self.add_action(file_menu, 'プレイリストを読み込む', self.load_playlist_dialog, 'Ctrl+L')
        self.add_action(file_menu, 'プレイリストを保存', self.save_playlist_dialog, 'Ctrl+S')
        file_menu.addSeparator()
        self.add_action(file_menu, '終了', self.close, 'Ctrl+Q')
        playback = self.menuBar().addMenu('再生')
        self.add_action(playback, '再生 / 一時停止', self.toggle_play, 'Space')
        self.add_action(playback, '次のメディア', lambda: self.step(1), 'Ctrl+Right')
        self.add_action(playback, '前のメディア', lambda: self.step(-1), 'Ctrl+Left')
        self.add_action(playback, '5秒戻る', lambda: self.jump(-5000), 'Left')
        self.add_action(playback, '5秒進む', lambda: self.jump(5000), 'Right')
        self.add_action(playback, 'ミュート', self.toggle_mute, 'M')
        view = self.menuBar().addMenu('表示')
        self.playlist_action = self.add_action(view, 'プレイリストを表示', None, 'Ctrl+P')
        self.playlist_action.setCheckable(True)
        self.playlist_action.setChecked(self._playlist_visible)
        self.playlist_action.toggled.connect(self.set_playlist_visible)
        self.add_action(view, '動画を全画面表示', self.toggle_fullscreen, 'F11')
        self.add_action(view, '全画面を解除', self.exit_fullscreen, 'Esc')
        self.add_action(view, 'ダウンロード', lambda: self.show_page(1), 'Ctrl+D')
        self.add_action(view, 'アプリのフォルダ', lambda: self.open_folder(ROOT))
        help_menu = self.menuBar().addMenu('ヘルプ')
        self.add_action(help_menu, '使い方', lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(str(RESOURCES / 'README.md'))))
        self.add_action(help_menu, 'バージョン情報', self.about)

    def add_action(self, menu, text, callback, shortcut=None):
        action = QAction(text, self)
        if shortcut:
            action.setShortcut(QKeySequence(shortcut))
        if callback is not None:
            action.triggered.connect(callback)
        menu.addAction(action)
        self.addAction(action)  # Keep shortcuts active while the menu bar is hidden.
        return action

    def about(self):
        import yt_dlp.version
        QMessageBox.information(self, 'Media Player', f'Media Player 1.0\n\nPySide6 / VLC / yt-dlp {yt_dlp.version.__version__}\n\n設定・保存データ: {ROOT}\nライセンス: licenses フォルダ')

    def show_page(self, index):
        if self._video_fullscreen and index != 0:
            self.exit_fullscreen()
        self.pages.setCurrentIndex(index)
        for i, entry in enumerate(self.nav_buttons):
            entry.setChecked(i == index)

    def notify(self, error):
        self.statusBar().showMessage(str(error))
        QMessageBox.warning(self, '確認してください', str(error))

    def open_folder(self, path):
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))

    def open_dialog(self):
        path, _ = QFileDialog.getOpenFileName(self, 'メディアを開く', str(DOWNLOADS), MEDIA_FILTER)
        if path:
            self.play_file(path)

    def add_dialog(self):
        paths, _ = QFileDialog.getOpenFileNames(self, 'プレイリストへ追加', str(DOWNLOADS), MEDIA_FILTER)
        self.add_files(paths)

    def list_paths(self):
        return [self.media_list.item(i).data(Qt.ItemDataRole.UserRole) for i in range(self.media_list.count())]

    def add_files(self, paths):
        existing = self.list_paths()
        for filename in paths:
            path = Path(filename).resolve()
            if not path.is_file() or path.suffix.lower() not in MEDIA_EXTENSIONS:
                continue
            if str(path) in existing:
                continue
            item = QListWidgetItem(path.name)
            item.setData(Qt.ItemDataRole.UserRole, str(path))
            item.setToolTip(str(path))
            self.media_list.addItem(item)
            existing.append(str(path))
        self.sync_queue()

    def sync_queue(self):
        self.queue.replace(self.list_paths(), self.current_media)
        if self.current_media not in self.queue.paths:
            self.in_queue = False
        self.playlist_heading.setText(f'プレイリスト · {len(self.queue.paths)}')

    def remove_selected(self):
        for item in self.media_list.selectedItems():
            self.media_list.takeItem(self.media_list.row(item))
        self.sync_queue()

    def clear_playlist(self):
        self.media_list.clear()
        self.sync_queue()

    def load_playlist_dialog(self):
        path, _ = QFileDialog.getOpenFileName(self, 'プレイリストを読み込む', str(PLAYLISTS), 'CSV (*.csv)')
        if not path:
            return
        try:
            paths, missing = read_playlist(path)
            self.clear_playlist()
            self.add_files(paths)
            if missing:
                self.notify(f'見つからない {len(missing)} 件をスキップしました。\n' + '\n'.join(missing[:5]))
            if not self.queue.paths:
                self.statusBar().showMessage('再生できるファイルが含まれていません')
        except (OSError, ValueError) as error:
            self.notify(error)

    def save_playlist_dialog(self):
        if not self.queue.paths:
            self.notify('プレイリストにメディアを追加してください。')
            return
        filename, _ = QFileDialog.getSaveFileName(self, 'プレイリストを保存', str(PLAYLISTS / 'playlist.csv'), 'CSV (*.csv)')
        if not filename:
            return
        try:
            path = inside_root(filename)
            if path.suffix.lower() != '.csv':
                path = path.with_suffix('.csv')
            write_playlist(path, self.list_paths())
            self.statusBar().showMessage(f'保存しました: {path.name}')
        except (OSError, ValueError) as error:
            self.notify(error)

    def play_item(self, item):
        self.play_file(item.data(Qt.ItemDataRole.UserRole), queued=True)

    def play_list(self):
        if not self.queue.paths:
            self.notify('プレイリストにメディアを追加してください。')
            return
        selected = self.media_list.currentItem()
        path = selected.data(Qt.ItemDataRole.UserRole) if selected else self.queue.paths[0]
        self.play_file(path, queued=True)

    def play_file(self, filename, queued=False):
        if not Path(filename).is_file():
            self.notify(f'ファイルが見つかりません:\n{filename}')
            return
        self.player.stop()
        self._end_pending = False
        self.current_media = str(Path(filename).resolve())
        self.in_queue = queued
        if queued:
            self.queue.current = self.current_media
        media = self.instance.media_new(self.current_media)
        self.player.set_media(media)
        media.release()
        self.player.set_hwnd(int(self.video_frame.winId()))
        self.empty_hint.hide()
        self.now_title.setText(Path(filename).name)
        self.now_title.setToolTip(self.current_media)
        self.setWindowTitle(f'{Path(filename).name} — Media Player')
        self.seek.setValue(0)
        self.time_label.setText('00:00 / 00:00')
        self.player.play()
        self.player.audio_set_volume(self.volume.value())
        self._audio_pending = True
        self.show_page(0)
        for i in range(self.media_list.count()):
            item = self.media_list.item(i)
            item.setForeground(Qt.GlobalColor.white)
            if item.data(Qt.ItemDataRole.UserRole) == self.current_media:
                from PySide6.QtGui import QColor
                item.setForeground(QColor('#83e5cc'))
        self.statusBar().showMessage('再生中: ' + Path(filename).name)

    def toggle_play(self):
        if not self.current_media:
            self.open_dialog()
        elif self.player.is_playing():
            self.player.set_pause(1)
        else:
            self._end_pending = False
            self.player.play()

    def stop(self):
        self.player.stop()
        self._end_pending = False
        self.seek.setValue(0)
        self.statusBar().showMessage('停止しました')

    def step(self, direction):
        if not self.in_queue:
            return
        path = self.queue.step(direction)
        if path:
            self.play_file(path, queued=True)

    def on_end(self):
        if self.closing or self._end_pending:
            return
        self._end_pending = True
        if self.in_queue:
            path = self.queue.step(1, self.repeat.isChecked())
            if path:
                QTimer.singleShot(0, lambda: self.play_file(path, queued=True))
        elif self.repeat.isChecked() and self.current_media:
            QTimer.singleShot(0, lambda: self.play_file(self.current_media))

    def on_playback_error(self):
        if not self.closing:
            self.statusBar().showMessage('再生できませんでした。ファイルの形式・破損・読み取り権限を確認してください。')

    @staticmethod
    def clock(milliseconds):
        seconds = max(0, int(milliseconds // 1000))
        minutes, seconds = divmod(seconds, 60)
        hours, minutes = divmod(minutes, 60)
        return f'{hours:02}:{minutes:02}:{seconds:02}' if hours else f'{minutes:02}:{seconds:02}'

    def refresh_player(self):
        if self.closing:
            return
        length = max(0, self.player.get_length())
        current = max(0, self.player.get_time())
        if self._audio_pending and self.player.is_playing():
            self.player.audio_set_volume(self.volume.value())
            self.player.audio_set_mute(self.muted)
            self._audio_pending = False
        self.seek.setEnabled(length > 0 and self.player.is_seekable())
        if not self.seek.isSliderDown():
            self.seek.setValue(int(current * 10000 / length) if length else 0)
            self.time_label.setText(f'{self.clock(current)} / {self.clock(length)}')
        icon = QStyle.StandardPixmap.SP_MediaPause if self.player.is_playing() else QStyle.StandardPixmap.SP_MediaPlay
        self.play_button.setIcon(self.style().standardIcon(icon))

    def seek_preview(self, value):
        length = max(0, self.player.get_length())
        self.time_label.setText(f'{self.clock(value * length / 10000)} / {self.clock(length)}')

    def seek_release(self):
        if self.player.is_seekable():
            self.player.set_position(min(self.seek.value() / 10000, 0.999))

    def seek_action(self, action):
        if not self.seek.isSliderDown():
            QTimer.singleShot(0, self.seek_release)

    def jump(self, amount):
        if self.player.is_seekable():
            self.player.set_time(max(0, min(self.player.get_time() + amount, self.player.get_length() - 50)))

    def set_volume(self, value):
        self.player.audio_set_volume(value)
        self.volume_label.setText(str(value))

    def toggle_mute(self):
        self.muted = not self.muted
        self.player.audio_set_mute(self.muted)
        self.mute_button.setText('消音中' if self.muted else '音量')

    def set_playlist_visible(self, visible):
        visible = bool(visible)
        if self._playlist_visible and not visible and not self._video_fullscreen:
            sizes = self.player_splitter.sizes()
            if all(size > 0 for size in sizes):
                self._playlist_sizes = sizes
        self._playlist_visible = visible
        self.playlist_button.setText('プレイリストを隠す' if visible else 'プレイリストを表示')
        self.playlist_panel.setVisible(visible and not self._video_fullscreen)
        if not self._video_fullscreen:
            self.viewer_layout.setContentsMargins(0, 0, 14 if visible else 0, 0)
            if visible:
                self.player_splitter.setSizes(self._playlist_sizes)
        for control in (self.playlist_button, getattr(self, 'playlist_action', None)):
            if control is not None:
                control.blockSignals(True)
                control.setChecked(visible)
                control.blockSignals(False)

    def fullscreen_chrome(self):
        return (self.sidebar, self.menuBar(), self.statusBar(), self.player_header,
                self.player_subtitle, self.now_title, self.seek_panel, self.controls_panel)

    def toggle_fullscreen(self):
        if self._video_fullscreen:
            self.exit_fullscreen()
            return
        self._before_fullscreen_page = self.pages.currentIndex()
        self._before_fullscreen_maximized = self.isMaximized()
        if self._playlist_visible:
            sizes = self.player_splitter.sizes()
            if all(size > 0 for size in sizes):
                self._playlist_sizes = sizes
        self.show_page(0)
        self._video_fullscreen = True
        for widget in self.fullscreen_chrome():
            widget.hide()
        self.playlist_panel.hide()
        self.player_page_layout.setContentsMargins(0, 0, 0, 0)
        self.player_page_layout.setSpacing(0)
        self.viewer_layout.setContentsMargins(0, 0, 0, 0)
        self.viewer_layout.setSpacing(0)
        self.video_frame.setStyleSheet('background: black; border-radius: 0;')
        # Resize the original native video surface; changing its HWND can break VLC.
        self.showFullScreen()

    def exit_fullscreen(self):
        if not self._video_fullscreen:
            return
        self._video_fullscreen = False
        for widget in self.fullscreen_chrome():
            widget.show()
        self.player_page_layout.setContentsMargins(24, 24, 24, 20)
        self.player_page_layout.setSpacing(12)
        self.viewer_layout.setSpacing(6)
        self.video_frame.setStyleSheet('background: #05090e; border-radius: 9px;')
        if self._before_fullscreen_maximized:
            self.showMaximized()
        else:
            self.showNormal()
        self.set_playlist_visible(self._playlist_visible)
        self.show_page(self._before_fullscreen_page)

    def choose_download_folder(self):
        folder = QFileDialog.getExistingDirectory(self, 'アプリ内の保存先を選択', self.destination.text())
        if folder:
            try:
                self.destination.setText(str(inside_root(folder)))
            except ValueError as error:
                self.notify(error)

    def start_download(self):
        if self.worker is not None:
            return
        try:
            worker = DownloadWorker(self.url.text(), self.destination.text(), self.download_playlist.isChecked(), self)
        except ValueError as error:
            self.notify(error)
            return
        self.worker = worker
        self.auto_play_job = self.play_after.isChecked()
        self.current_download_files = []
        self.log.clear()
        self.download_results.clear()
        self.progress.setRange(0, 0)
        self.download_status.setText('動画情報を取得しています…')
        self.set_download_busy(True)
        worker.progress.connect(self.update_download_progress)
        worker.message.connect(self.log.appendPlainText)
        worker.file_ready.connect(self.download_file_ready)
        worker.succeeded.connect(self.download_succeeded)
        worker.failed.connect(self.download_failed)
        worker.cancelled.connect(self.download_cancelled)
        worker.finished.connect(self.download_finished)
        worker.start()

    def set_download_busy(self, busy):
        self.start_button.setEnabled(not busy)
        self.cancel_button.setEnabled(busy)
        for widget in (self.url, self.choose_destination, self.play_after, self.download_playlist):
            widget.setEnabled(not busy)

    def update_download_progress(self, percent, text):
        self.progress.setRange(0, 0 if percent < 0 else 100)
        if percent >= 0:
            self.progress.setValue(percent)
        self.download_status.setText('ダウンロード中' if percent < 100 else 'ファイルを仕上げています…')
        self.download_details.setText(text)

    def download_file_ready(self, path):
        self.current_download_files.append(path)
        item = QListWidgetItem(Path(path).name)
        item.setData(Qt.ItemDataRole.UserRole, path)
        item.setToolTip(path)
        self.download_results.addItem(item)
        self.add_files([path])

    def download_succeeded(self, paths):
        self.progress.setRange(0, 100)
        self.progress.setValue(100)
        self.download_status.setText(f'完了 · {len(paths)} 件保存しました')
        self.download_details.setText('下のファイルをダブルクリックすると再生できます。')
        self.log.appendPlainText('完了しました。')
        if self.auto_play_job and paths and not self.closing:
            self.play_file(paths[0], queued=len(paths) > 1)

    def download_failed(self, message):
        self.progress.setRange(0, 100)
        self.download_status.setText('ダウンロードできませんでした')
        self.log.appendPlainText(message)
        self.download_details.setText('URL・通信環境・サイトの制限を確認してください。詳しくは下のログをご覧ください。')

    def download_cancelled(self):
        self.progress.setRange(0, 100)
        self.download_status.setText('キャンセルしました')
        self.download_details.setText('途中の .part ファイルは、同じURLで再開すると続きから取得できます。')

    def cancel_download(self):
        if self.worker:
            self.worker.requestInterruption()
            self.cancel_button.setEnabled(False)
            self.download_status.setText('キャンセル処理中…')
            self.download_details.setText('通信やファイルの結合が終了するまでお待ちください。')

    def download_finished(self):
        worker = self.worker
        self.worker = None
        self.set_download_busy(False)
        if worker:
            worker.deleteLater()
        if self.closing:
            QTimer.singleShot(0, self.close)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        paths = [url.toLocalFile() for url in event.mimeData().urls() if url.isLocalFile()]
        self.add_files(paths)
        valid = [str(Path(p).resolve()) for p in paths if str(Path(p).resolve()) in self.queue.paths]
        if valid:
            self.play_file(valid[0], queued=True)
        event.acceptProposedAction()

    def closeEvent(self, event):
        if self.worker is not None:
            self.closing = True
            self.cancel_download()
            self.player.stop()
            self.statusBar().showMessage('処理の終了を待ってからアプリを閉じます…')
            event.ignore()
            return
        try:
            save_settings({'volume': self.volume.value(), 'repeat': self.repeat.isChecked(),
                           'play_after': self.play_after.isChecked(), 'playlist': self.list_paths(),
                           'playlist_visible': self._playlist_visible})
        except OSError as error:
            self.notify(f'設定の保存に失敗しました: {error}')
        self.closing = True
        self.timer.stop()
        self.events.event_detach(self.vlc.EventType.MediaPlayerEndReached)
        self.events.event_detach(self.vlc.EventType.MediaPlayerEncounteredError)
        self.player.stop()
        self.player.release()
        self.instance.release()
        event.accept()


def create_application():
    application = QApplication(sys.argv[:1])
    application.setApplicationName('Media Player')
    application.setStyle('Fusion')
    check = (RESOURCES / 'assets' / 'check.svg').as_posix()
    application.setStyleSheet(STYLE.replace('__CHECK_ICON__', check))
    return application
