"""Ana pencere: sol navigasyon + animasyonlu sayfa geçişleri."""
from __future__ import annotations

from typing import Optional

from PySide6.QtCore import QEasingCurve, QPropertyAnimation, Qt
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import (
    QApplication, QButtonGroup, QGraphicsOpacityEffect, QHBoxLayout, QLabel, QMainWindow,
    QPushButton, QStackedWidget, QStatusBar, QVBoxLayout, QWidget,
)

from .. import APP_NAME, __version__
from ..core.storage import Storage
from .theme import build_qss

# (anahtar, menü metni)
NAV_ITEMS = [
    ("dashboard", "🏠  Ana Sayfa"),
    ("files", "📁  Dosya Araçları"),
    ("text", "📝  Metin Araçları"),
    ("calc", "🧮  Hesaplama"),
    ("time", "⏱️  Zaman Araçları"),
    ("notes", "🗒️  Notlar"),
    ("settings", "⚙️  Ayarlar"),
]
TOOL_LABELS = {k: v.split("  ", 1)[1] for k, v in NAV_ITEMS}


class MainWindow(QMainWindow):
    def __init__(self, storage: Storage):
        super().__init__()
        self.storage = storage
        self.theme_mode = storage.get("theme", "dark")
        self.setWindowTitle(f"{APP_NAME} {__version__}")
        self.resize(1200, 760)
        self.setMinimumSize(900, 600)

        # Sayfalar (geç içe aktarım: döngüsel bağımlılığı önler)
        from .pages.calc_page import CalcPage
        from .pages.dashboard import DashboardPage
        from .pages.files_page import FilesPage
        from .pages.notes_page import NotesPage
        from .pages.settings_page import SettingsPage
        from .pages.text_page import TextPage
        from .pages.time_page import TimePage

        self.pages: dict[str, QWidget] = {
            "dashboard": DashboardPage(self),
            "files": FilesPage(self),
            "text": TextPage(self),
            "calc": CalcPage(self),
            "time": TimePage(self),
            "notes": NotesPage(self),
            "settings": SettingsPage(self),
        }

        root = QWidget()
        root.setObjectName("Root")
        layout = QHBoxLayout(root)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # ---- Sol menü ----
        sidebar = QWidget()
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(220)
        side = QVBoxLayout(sidebar)
        side.setContentsMargins(12, 16, 12, 12)
        side.setSpacing(4)
        logo = QLabel("◆ Nova Tools")
        logo.setObjectName("Logo")
        sub = QLabel("Günlük araç kutunuz")
        sub.setObjectName("LogoSub")
        side.addWidget(logo)
        side.addWidget(sub)
        self.nav_group = QButtonGroup(self)
        self.nav_group.setExclusive(True)
        self.nav_buttons: dict[str, QPushButton] = {}
        for i, (key, label) in enumerate(NAV_ITEMS):
            btn = QPushButton(label)
            btn.setObjectName("NavButton")
            btn.setCheckable(True)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setToolTip(f"{TOOL_LABELS[key]} (Ctrl+{i + 1})")
            btn.clicked.connect(lambda _=False, k=key: self.navigate(k))
            self.nav_group.addButton(btn)
            self.nav_buttons[key] = btn
            side.addWidget(btn)
            act = QAction(self)
            act.setShortcut(QKeySequence(f"Ctrl+{i + 1}"))
            act.triggered.connect(lambda _=False, k=key: self.navigate(k))
            self.addAction(act)
        side.addStretch(1)
        ver = QLabel(f"Sürüm {__version__} • Çevrimdışı")
        ver.setObjectName("LogoSub")
        side.addWidget(ver)

        # ---- İçerik ----
        self.stack = QStackedWidget()
        for page in self.pages.values():
            self.stack.addWidget(page)

        layout.addWidget(sidebar)
        layout.addWidget(self.stack, 1)
        self.setCentralWidget(root)
        self.setStatusBar(QStatusBar())
        self.statusBar().showMessage("Hazır")

        self._anim: Optional[QPropertyAnimation] = None
        self.current_key = ""
        self.apply_theme(self.theme_mode, save=False)
        self.navigate("dashboard", animate=False)

    # ---------- Navigasyon ----------
    def navigate(self, key: str, tab: Optional[int] = None, animate: bool = True) -> None:
        page = self.pages.get(key)
        if page is None:
            return
        self.nav_buttons[key].setChecked(True)
        if tab is not None and hasattr(page, "open_tab"):
            page.open_tab(tab)
        if key != self.current_key:
            self.stack.setCurrentWidget(page)
            if animate:
                self._fade_in(page)
            self.current_key = key
            if key not in ("dashboard", "settings"):
                self.storage.touch_tool(key)
            if hasattr(page, "on_show"):
                page.on_show()
        self.statusBar().showMessage(TOOL_LABELS[key])

    def _fade_in(self, widget: QWidget) -> None:
        effect = QGraphicsOpacityEffect(widget)
        widget.setGraphicsEffect(effect)
        anim = QPropertyAnimation(effect, b"opacity", self)
        anim.setDuration(220)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)
        anim.setEasingCurve(QEasingCurve.OutCubic)
        # Animasyon bitince efekti kaldır (metin netliği ve performans için)
        anim.finished.connect(lambda w=widget: w.setGraphicsEffect(None))
        anim.start()
        self._anim = anim

    # ---------- Tema ----------
    def apply_theme(self, mode: str, save: bool = True) -> None:
        self.theme_mode = mode if mode in ("dark", "light") else "dark"
        app = QApplication.instance()
        if app is not None:
            app.setStyleSheet(build_qss(self.theme_mode))
        if save:
            self.storage.set("theme", self.theme_mode)
        for page in self.pages.values():
            if hasattr(page, "on_theme_changed"):
                page.on_theme_changed(self.theme_mode)

    def notify(self, text: str, ms: int = 4000) -> None:
        self.statusBar().showMessage(text, ms)

    def closeEvent(self, event) -> None:  # noqa: N802
        for page in self.pages.values():
            if hasattr(page, "can_close") and not page.can_close():
                event.ignore()
                return
        for page in self.pages.values():
            if hasattr(page, "shutdown"):
                page.shutdown()
        super().closeEvent(event)
