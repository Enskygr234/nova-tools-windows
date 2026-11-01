"""Ortak arayüz bileşenleri ve yardımcılar."""
from __future__ import annotations

import os
import subprocess
import sys
import threading
import traceback
from typing import Any, Callable, Optional

from PySide6.QtCore import QRectF, QSize, Qt, QThread, QUrl, Signal
from PySide6.QtGui import QBrush, QColor, QConicalGradient, QDesktopServices, QFont, QPainter, QPen
from PySide6.QtWidgets import (
    QFileDialog, QFrame, QHBoxLayout, QLabel, QLineEdit, QMessageBox, QPushButton,
    QScrollArea, QSizePolicy, QVBoxLayout, QWidget,
)

from .theme import BLUE, PURPLE


class Card(QFrame):
    def __init__(self, title: Optional[str] = None, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setObjectName("Card")
        self.body = QVBoxLayout(self)
        self.body.setContentsMargins(16, 14, 16, 14)
        self.body.setSpacing(10)
        if title:
            lbl = QLabel(title)
            lbl.setObjectName("CardTitle")
            self.body.addWidget(lbl)


def page_header(title: str, subtitle: str) -> QWidget:
    w = QWidget()
    lay = QVBoxLayout(w)
    lay.setContentsMargins(0, 0, 0, 6)
    lay.setSpacing(2)
    t = QLabel(title)
    t.setObjectName("PageTitle")
    s = QLabel(subtitle)
    s.setObjectName("PageSubtitle")
    s.setWordWrap(True)
    lay.addWidget(t)
    lay.addWidget(s)
    return w


def scroll_page(content: QWidget) -> QScrollArea:
    area = QScrollArea()
    area.setWidgetResizable(True)
    area.setFrameShape(QFrame.NoFrame)
    area.setWidget(content)
    return area


def primary_button(text: str) -> QPushButton:
    b = QPushButton(text)
    b.setObjectName("Primary")
    b.setCursor(Qt.PointingHandCursor)
    return b


def muted_label(text: str = "") -> QLabel:
    lbl = QLabel(text)
    lbl.setObjectName("Muted")
    lbl.setWordWrap(True)
    return lbl


class FolderPicker(QWidget):
    """Yol seçici. file_mode=True ise dosya, değilse klasör seçtirir."""

    changed = Signal(str)

    def __init__(self, placeholder: str = "Klasör seçin…", parent: Optional[QWidget] = None,
                 file_mode: bool = False):
        super().__init__(parent)
        self.file_mode = file_mode
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        self.edit = QLineEdit()
        self.edit.setPlaceholderText(placeholder)
        self.edit.textChanged.connect(self.changed)
        self.browse_button = QPushButton("Gözat…")
        self.browse_button.clicked.connect(self._browse)
        lay.addWidget(self.edit, 1)
        lay.addWidget(self.browse_button)

    def _browse(self) -> None:
        current = self.path()
        if self.file_mode:
            start = os.path.dirname(current) if current else os.path.expanduser("~")
            path, _ = QFileDialog.getOpenFileName(self, "Dosya seç", start)
        else:
            path = QFileDialog.getExistingDirectory(self, "Klasör seç", current or os.path.expanduser("~"))
        if path:
            self.edit.setText(os.path.normpath(path))

    def path(self) -> str:
        return self.edit.text().strip().strip('"')

    def set_path(self, p: str) -> None:
        self.edit.setText(p)


def confirm(parent: QWidget, title: str, text: str, danger: bool = False) -> bool:
    box = QMessageBox(parent)
    box.setIcon(QMessageBox.Warning if danger else QMessageBox.Question)
    box.setWindowTitle(title)
    box.setText(text)
    yes = box.addButton("Evet", QMessageBox.YesRole)
    box.addButton("Vazgeç", QMessageBox.NoRole)
    box.exec()
    return box.clickedButton() is yes


def error(parent: QWidget, text: str, title: str = "Hata") -> None:
    QMessageBox.critical(parent, title, text)


def info(parent: QWidget, text: str, title: str = "Bilgi") -> None:
    QMessageBox.information(parent, title, text)


def show_in_explorer(path: str) -> None:
    """Dosyayı Gezgin'de seçili olarak gösterir."""
    path = os.path.normpath(path)
    if sys.platform.startswith("win"):
        subprocess.Popen(["explorer", "/select,", path])
    else:
        QDesktopServices.openUrl(QUrl.fromLocalFile(os.path.dirname(path)))


def open_path(path: str) -> None:
    QDesktopServices.openUrl(QUrl.fromLocalFile(path))


class Worker(QThread):
    """fn(cancel_event, progress_callback) fonksiyonunu arka planda çalıştırır."""

    progress = Signal(str)
    succeeded = Signal(object)
    failed = Signal(str)
    cancelled = Signal()

    def __init__(self, fn: Callable[[threading.Event, Callable[[str], None]], Any], parent=None):
        super().__init__(parent)
        self._fn = fn
        self.cancel_event = threading.Event()

    def run(self) -> None:  # noqa: D401
        from ..core.files import Cancelled
        try:
            result = self._fn(self.cancel_event, self.progress.emit)
        except Cancelled:
            self.cancelled.emit()
        except FileNotFoundError as e:
            self.failed.emit(str(e))
        except PermissionError as e:
            self.failed.emit(f"Erişim reddedildi: {e.filename or e}")
        except Exception as e:  # güvenli hata yönetimi: arayüz çökmez
            traceback.print_exc()
            self.failed.emit(f"Beklenmeyen hata: {e}")
        else:
            if self.cancel_event.is_set():
                self.cancelled.emit()
            else:
                self.succeeded.emit(result)

    def cancel(self) -> None:
        self.cancel_event.set()


class RingProgress(QWidget):
    """Dairesel ilerleme göstergesi (Pomodoro, geri sayım)."""

    def __init__(self, parent: Optional[QWidget] = None, size: int = 220):
        super().__init__(parent)
        self._value = 0.0
        self._text = ""
        self._sub = ""
        self.setMinimumSize(QSize(size, size))
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    def set_state(self, value: float, text: str, sub: str = "") -> None:
        self._value = max(0.0, min(1.0, value))
        self._text = text
        self._sub = sub
        self.update()

    def paintEvent(self, _event) -> None:  # noqa: N802
        side = min(self.width(), self.height()) - 16
        rect = QRectF((self.width() - side) / 2, (self.height() - side) / 2, side, side)
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        track = QPen(QColor(128, 128, 160, 60), 14)
        track.setCapStyle(Qt.RoundCap)
        p.setPen(track)
        p.drawArc(rect, 0, 360 * 16)
        grad = QConicalGradient(rect.center(), 90)
        grad.setColorAt(0.0, QColor(PURPLE))
        grad.setColorAt(0.5, QColor(BLUE))
        grad.setColorAt(1.0, QColor(PURPLE))
        pen = QPen(QBrush(grad), 14)
        pen.setCapStyle(Qt.RoundCap)
        p.setPen(pen)
        p.drawArc(rect, 90 * 16, int(-360 * 16 * self._value))
        p.setPen(self.palette().color(self.foregroundRole()))
        f = QFont(self.font())
        f.setPointSizeF(max(14.0, side / 9))
        f.setBold(True)
        p.setFont(f)
        p.drawText(rect, Qt.AlignCenter, self._text)
        if self._sub:
            f2 = QFont(self.font())
            f2.setPointSizeF(max(9.0, side / 22))
            p.setFont(f2)
            sub_rect = QRectF(rect.left(), rect.center().y() + side / 8, rect.width(), side / 6)
            p.drawText(sub_rect, Qt.AlignHCenter | Qt.AlignTop, self._sub)
        p.end()


def hline() -> QFrame:
    f = QFrame()
    f.setFrameShape(QFrame.HLine)
    f.setStyleSheet("color: rgba(128,128,160,60);")
    return f
