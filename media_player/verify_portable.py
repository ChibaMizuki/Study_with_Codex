"""Run the EXE with no Python, VLC, FFmpeg, or Deno directories on PATH."""
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import os
import subprocess
import threading

ROOT = Path(__file__).resolve().parent


def main():
    class Handler(SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(ROOT / 'outputs'), **kwargs)

        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    env = os.environ.copy()
    env['PATH'] = str(Path(os.environ['SystemRoot']) / 'System32')
    env.pop('VLC_PLUGIN_PATH', None)
    env.pop('PYTHONPATH', None)
    output = ROOT / 'dist' / 'MediaPlayer' / 'outputs' / 'smoke'
    command = [str(ROOT / 'dist' / 'MediaPlayer' / 'MediaPlayer.exe'), '--smoke-test',
               str(ROOT / 'outputs' / 'test-video.mp4'), str(output),
               f'http://127.0.0.1:{server.server_port}/test-video.mp4']
    try:
        result = subprocess.run(command, cwd=ROOT / 'outputs', env=env, timeout=60)
        if not (output / 'smoke.json').exists():
            startup_log = ROOT / 'dist' / 'MediaPlayer' / 'data' / 'startup-error.log'
            raise RuntimeError(startup_log.read_text(encoding='utf-8') if startup_log.exists() else f'EXE exited {result.returncode}')
        report = json.loads((output / 'smoke.json').read_text(encoding='utf-8'))
        print(json.dumps(report, ensure_ascii=False, indent=2))
        if result.returncode or not report['ok']:
            raise SystemExit(1)
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


if __name__ == '__main__':
    main()
