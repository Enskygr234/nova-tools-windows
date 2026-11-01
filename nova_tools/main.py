"""Nova Tools giriş noktası."""
from __future__ import annotations

import os
import sys


def resource_path(*parts: str) -> str:
    """PyInstaller paketinde ve kaynak kodda çalışan varlık yolu."""
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    return os.path.join(base, *parts)


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv if argv is None else argv)
    self_test_out = None
    for arg in argv[1:]:
        if arg == "--self-test":
            self_test_out = ""
        elif arg.startswith("--self-test="):
            self_test_out = arg.split("=", 1)[1]
        elif arg in ("--version", "-v"):
            from . import __version__
            print(__version__)
            return 0

    if os.name == "nt":
        # Görev çubuğunda doğru simge için ayrı uygulama kimliği
        try:
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("NovaTools.Desktop.1")
        except Exception:  # noqa: BLE001
            pass

    from PySide6.QtGui import QIcon
    from PySide6.QtWidgets import QApplication

    from . import APP_NAME

    app = QApplication(argv)
    app.setApplicationName(APP_NAME)
    app.setOrganizationName("NovaTools")
    icon_path = resource_path("assets", "icon.ico")
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))

    if self_test_out is not None:
        from .selftest import run_self_test
        return run_self_test(app, self_test_out)

    from .core.storage import Storage
    from .ui.main_window import MainWindow

    try:
        storage = Storage()
    except Exception as e:  # noqa: BLE001
        from PySide6.QtWidgets import QMessageBox
        QMessageBox.critical(None, APP_NAME, f"Veritabanı açılamadı:\n{e}")
        return 1
    window = MainWindow(storage)
    window.show()
    code = app.exec()
    storage.close()
    return code


if __name__ == "__main__":
    sys.exit(main())
