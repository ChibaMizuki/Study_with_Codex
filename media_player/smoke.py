"""Exercise the real GUI and libvlc in source and PyInstaller builds."""
import json
from pathlib import Path
import time
import traceback
from PySide6.QtCore import QTimer
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from paths import ROOT, inside_root


def run_smoke(application, window, argv):
    index = argv.index('--smoke-test')
    sample = Path(argv[index + 1]).resolve()
    output = inside_root(argv[index + 2])
    output.mkdir(parents=True, exist_ok=True)
    download_url = argv[index + 3] if len(argv) > index + 3 else None
    report = {'build': 'frozen' if getattr(__import__('sys'), 'frozen', False) else 'source'}
    started = time.monotonic()
    phase = [0]
    window.repeat.setChecked(False)

    def finish(error=None):
        timer.stop()
        if error:
            report['error'] = str(error)
        report['ok'] = error is None
        (output / 'smoke.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
        window.close()
        application.exit(1 if error else 0)

    def tick():
        try:
            elapsed = time.monotonic() - started
            if elapsed > 45:
                raise RuntimeError(f'Smoke test timeout at phase {phase[0]}; state={window.player.get_state()}; volume={window.player.audio_get_volume()}')
            if phase[0] == 0 and elapsed > 0.5:
                window.grab().save(str(output / 'player-empty.png'))
                window.add_files([str(sample)])
                window.play_file(str(sample), queued=True)
                phase[0] = 1
            elif phase[0] == 1 and elapsed > 2.5:
                assert window.player.is_playing(), f'Playback state: {window.player.get_state()}'
                assert window.player.get_length() > 0
                assert window.player.get_time() > 0
                report['playback'] = {'duration_ms': window.player.get_length(), 'position_ms': window.player.get_time()}
                window.volume.setValue(35)
                phase[0] = 2
            elif phase[0] == 2:
                if window.player.audio_get_volume() != 35:
                    return
                window.toggle_mute()
                phase[0] = 22
            elif phase[0] == 22:
                if not window.player.audio_get_mute():
                    return
                window.toggle_mute()
                window.player.set_pause(1)
                phase[0] = 21
            elif phase[0] == 21:
                if window.player.get_state() != window.vlc.State.Paused:
                    return
                window.player.set_position(0.4)
                window.player.set_pause(0)
                phase[0] = 3
            elif phase[0] == 3 and elapsed > 4:
                if window.player.get_position() <= 0.35:
                    return
                report['video_size'] = window.player.video_get_size(0)
                assert report['video_size'] == (640, 360)
                snapshot = output / 'decoded-frame.png'
                assert window.player.video_take_snapshot(0, str(snapshot), 640, 360) == 0
                window.shuffle.setChecked(True)
                assert window.queue.current == str(sample)
                window.shuffle.setChecked(False)
                window.screen().grabWindow(int(window.winId())).save(str(output / 'player-playing.png'))
                report['controls'] = ['pause', 'resume', 'seek', 'volume', 'mute', 'shuffle']
                report['normal_video_width'] = window.video_frame.width()
                report['video_handle'] = int(window.video_frame.winId())
                window.playlist_button.click()
                phase[0] = 31
            elif phase[0] == 31:
                assert window.playlist_panel.isHidden()
                report['expanded_video_width'] = window.video_frame.width()
                assert report['expanded_video_width'] > report['normal_video_width']
                window.grab().save(str(output / 'player-expanded.png'))
                window.playlist_action.trigger()
                QTest.keyClick(window, Qt.Key.Key_F11)
                phase[0] = 32
            elif phase[0] == 32:
                assert window.isFullScreen()
                assert all(widget.isHidden() for widget in window.fullscreen_chrome())
                assert window.playlist_panel.isHidden()
                assert window.video_frame.size() == window.centralWidget().size()
                assert window.player.is_playing()
                assert int(window.video_frame.winId()) == report['video_handle']
                report['fullscreen_size'] = [window.video_frame.width(), window.video_frame.height()]
                window.screen().grabWindow(int(window.winId())).save(str(output / 'video-fullscreen.png'))
                assert window.player.video_take_snapshot(0, str(output / 'fullscreen-frame.png'), 640, 360) == 0
                QTest.keyClick(window, Qt.Key.Key_Escape)
                phase[0] = 33
            elif phase[0] == 33:
                assert not window.isFullScreen()
                assert not window.playlist_panel.isHidden()
                assert window.player.is_playing()
                assert int(window.video_frame.winId()) == report['video_handle']
                report['controls'] += ['playlist toggle', 'video-only fullscreen', 'F11', 'Esc']
                window.show_page(1)
                window.grab().save(str(output / 'download.png'))
                if download_url:
                    window.url.setText(download_url)
                    window.destination.setText(str(output / 'downloads'))
                    window.play_after.setChecked(False)
                    window.start_download()
                    phase[0] = 4
                else:
                    phase[0] = 5
            elif phase[0] == 4 and window.worker is None:
                assert window.current_download_files, window.log.toPlainText()
                report['download'] = window.current_download_files
                window.grab().save(str(output / 'download-complete.png'))
                phase[0] = 5
            elif phase[0] == 5:
                if (output / 'decoded-frame.png').exists():
                    finish()
        except Exception as error:
            report['traceback'] = traceback.format_exc()
            finish(repr(error))

    timer = QTimer(window)
    timer.setInterval(200)
    timer.timeout.connect(tick)
    timer.start()
    return application.exec()
