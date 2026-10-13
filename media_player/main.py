import os
import sys
from pathlib import Path

from paths import DATA, prepare


def main():
    prepare()
    # Keep the directory handle alive while libvlc is in use.
    from paths import TOOLS
    dll_directory = os.add_dll_directory(str(TOOLS / 'vlc')) if os.name == 'nt' else None
    try:
        from app import PlayerWindow, create_application
        application = create_application()
        if '--smoke-test' in sys.argv:
            import app as app_module
            app_module.load_settings = lambda: {}
            app_module.save_settings = lambda _: None
        window = PlayerWindow()
    except Exception as error:
        import traceback
        (DATA / 'startup-error.log').write_text(traceback.format_exc(), encoding='utf-8')
        if '--smoke-test' in sys.argv:
            return 1
        from PySide6.QtWidgets import QMessageBox
        QMessageBox.critical(None, '起動できませんでした', str(error))
        return 1
    window.show()
    if '--smoke-test' in sys.argv:
        from smoke import run_smoke
        return run_smoke(application, window, sys.argv)
    paths = [arg for arg in sys.argv[1:] if Path(arg).is_file()]
    if paths:
        window.add_files(paths)
        window.play_file(paths[0], queued=len(paths) > 1)
    result = application.exec()
    if dll_directory:
        dll_directory.close()
    return result


if __name__ == '__main__':
    try:
        sys.exit(main())
    except Exception:
        import traceback
        DATA.mkdir(parents=True, exist_ok=True)
        (DATA / 'startup-error.log').write_text(traceback.format_exc(), encoding='utf-8')
        raise
