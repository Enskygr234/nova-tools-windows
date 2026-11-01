"""Hesaplama araçları: bilimsel hesap makinesi, birim dönüştürücü, SHA-256."""
from __future__ import annotations

import os

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication, QComboBox, QDoubleSpinBox, QGridLayout, QHBoxLayout, QLabel, QLineEdit,
    QListWidget, QPlainTextEdit, QProgressBar, QPushButton, QTabWidget, QVBoxLayout, QWidget,
)

from ...core import calc as C
from ...core import files as F
from ...core import units as U
from ..widgets import Card, FolderPicker, Worker, muted_label, page_header, primary_button

KEYS = [
    ["sin(", "cos(", "tan(", "ln(", "log(", "√("],
    ["asin(", "acos(", "atan(", "x²", "^", "!"],
    ["(", ")", "π", "e", "%", "C"],
    ["7", "8", "9", "÷", "⌫", "AC"],
    ["4", "5", "6", "×", "−", "Ans"],
    ["1", "2", "3", "+", "±", "="],
    ["0", ",", "00", "1/x", "abs(", "fact("],
]
OPS = {"÷", "×", "−", "+", "^", "%", "!", "x²", "1/x"}


class CalculatorTab(QWidget):
    def __init__(self):
        super().__init__()
        self.ans = 0.0
        self.mode = "deg"
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 10, 0, 0)
        left = QVBoxLayout()
        top = QHBoxLayout()
        self.mode_btn = QPushButton("DEG")
        self.mode_btn.setToolTip("Açı birimi: derece / radyan")
        self.mode_btn.clicked.connect(self.toggle_mode)
        top.addWidget(self.mode_btn)
        top.addStretch(1)
        self.preview = muted_label("")
        top.addWidget(self.preview)
        left.addLayout(top)
        self.expr = QLineEdit()
        self.expr.setObjectName("Display")
        self.expr.setPlaceholderText("0")
        self.expr.setAlignment(Qt.AlignRight)
        self.expr.returnPressed.connect(self.equals)
        self.expr.textChanged.connect(self._live)
        self.expr.setStyleSheet("font-size: 20pt; padding: 10px;")
        left.addWidget(self.expr)
        self.result = QLabel("0")
        self.result.setObjectName("Display")
        self.result.setAlignment(Qt.AlignRight)
        self.result.setTextInteractionFlags(Qt.TextSelectableByMouse)
        left.addWidget(self.result)
        grid = QGridLayout()
        grid.setSpacing(6)
        self.buttons: dict[str, QPushButton] = {}
        for r, row in enumerate(KEYS):
            for c, key in enumerate(row):
                b = QPushButton(key)
                b.setObjectName("CalcEq" if key == "=" else "CalcOp" if key in OPS or key in ("C", "AC", "⌫") else "CalcKey")
                b.setCursor(Qt.PointingHandCursor)
                b.clicked.connect(lambda _=False, k=key: self.press(k))
                grid.addWidget(b, r, c)
                self.buttons[key] = b
        left.addLayout(grid)
        lay.addLayout(left, 3)
        hist = Card("Geçmiş")
        self.history = QListWidget()
        self.history.itemClicked.connect(lambda it: self.expr.setText(it.data(Qt.UserRole)))
        hist.body.addWidget(self.history, 1)
        clear = QPushButton("Geçmişi temizle")
        clear.clicked.connect(self.history.clear)
        hist.body.addWidget(clear)
        hist.body.addWidget(muted_label("Klavye: Enter = hesapla. Ondalık için virgül veya nokta kullanılabilir."))
        lay.addWidget(hist, 2)

    def toggle_mode(self) -> None:
        self.mode = "rad" if self.mode == "deg" else "deg"
        self.mode_btn.setText(self.mode.upper())
        self._live()

    def press(self, key: str) -> None:
        e = self.expr
        if key == "=":
            self.equals()
        elif key == "AC":
            e.clear()
            self.result.setText("0")
        elif key == "C":
            e.clear()
        elif key == "⌫":
            e.backspace()
        elif key == "x²":
            e.insert("^2")
        elif key == "1/x":
            e.setText(f"1/({e.text()})" if e.text() else "1/")
        elif key == "±":
            t = e.text()
            e.setText(t[1:] if t.startswith("-") else "-" + t) if t else e.insert("-")
        elif key == "Ans":
            e.insert(C.format_number(self.ans).replace(",", "."))
        elif key == "π":
            e.insert("pi")
        else:
            e.insert(key)
        e.setFocus()

    def _live(self) -> None:
        txt = self.expr.text()
        if not txt.strip():
            self.preview.setText("")
            return
        try:
            self.preview.setText("= " + C.format_number(C.evaluate(txt, self.mode)))
        except C.CalcError:
            self.preview.setText("")

    def equals(self) -> None:
        txt = self.expr.text()
        if not txt.strip():
            return
        try:
            value = C.evaluate(txt, self.mode)
        except C.CalcError as err:
            self.result.setText(str(err))
            return
        self.ans = value
        shown = C.format_number(value)
        self.result.setText(shown)
        self.history.insertItem(0, f"{txt} = {shown}")
        self.history.item(0).setData(Qt.UserRole, txt)


class ConverterTab(QWidget):
    def __init__(self):
        super().__init__()
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 10, 0, 0)
        card = Card()
        self.cat = QComboBox()
        self.cat.addItems(U.CATEGORIES)
        self.value = QDoubleSpinBox()
        self.value.setRange(-1e15, 1e15)
        self.value.setDecimals(6)
        self.value.setValue(1)
        self.src = QComboBox()
        self.dst = QComboBox()
        swap = QPushButton("⇄")
        swap.setToolTip("Birimleri değiştir")
        swap.clicked.connect(self.swap)
        self.out = QLabel("")
        self.out.setObjectName("Display")
        self.out.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.formula = muted_label()
        grid = QGridLayout()
        grid.addWidget(muted_label("Kategori"), 0, 0)
        grid.addWidget(self.cat, 0, 1, 1, 3)
        grid.addWidget(muted_label("Değer"), 1, 0)
        grid.addWidget(self.value, 1, 1, 1, 3)
        grid.addWidget(muted_label("Birimler"), 2, 0)
        grid.addWidget(self.src, 2, 1)
        grid.addWidget(swap, 2, 2)
        grid.addWidget(self.dst, 2, 3)
        grid.setColumnStretch(1, 1)
        grid.setColumnStretch(3, 1)
        card.body.addLayout(grid)
        card.body.addWidget(self.out)
        card.body.addWidget(self.formula)
        lay.addWidget(card)
        lay.addStretch(1)
        self.cat.currentTextChanged.connect(self._fill_units)
        self.value.valueChanged.connect(self.update_result)
        self.src.currentTextChanged.connect(self.update_result)
        self.dst.currentTextChanged.connect(self.update_result)
        self._fill_units(self.cat.currentText())

    def _fill_units(self, cat: str) -> None:
        names = list(U.UNITS[cat])
        for combo in (self.src, self.dst):
            combo.blockSignals(True)
            combo.clear()
            combo.addItems(names)
            combo.blockSignals(False)
        self.dst.setCurrentIndex(min(1, len(names) - 1))
        self.update_result()

    def swap(self) -> None:
        a, b = self.src.currentText(), self.dst.currentText()
        self.src.setCurrentText(b)
        self.dst.setCurrentText(a)

    def update_result(self) -> None:
        try:
            r = U.convert(self.cat.currentText(), self.value.value(), self.src.currentText(), self.dst.currentText())
            self.out.setText(f"{C.format_number(r)}  {self.dst.currentText()}")
            self.formula.setText(f"{C.format_number(self.value.value())} {self.src.currentText()} = "
                                 f"{C.format_number(r)} {self.dst.currentText()}")
        except ValueError as e:
            self.out.setText(str(e))
            self.formula.setText("")


class HashTab(QWidget):
    def __init__(self):
        super().__init__()
        self.worker: Worker | None = None
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 10, 0, 0)
        tcard = Card("Metin SHA-256")
        self.text = QPlainTextEdit()
        self.text.setPlaceholderText("Metni yazın; özet anında hesaplanır (UTF-8).")
        self.text.setMaximumHeight(120)
        self.text_hash = QLineEdit()
        self.text_hash.setReadOnly(True)
        self.text.textChanged.connect(lambda: self.text_hash.setText(C.sha256_text(self.text.toPlainText())))
        self.text_hash.setText(C.sha256_text(""))
        copy = QPushButton("Kopyala")
        copy.clicked.connect(lambda: QApplication.clipboard().setText(self.text_hash.text()))
        row = QHBoxLayout()
        row.addWidget(self.text_hash, 1)
        row.addWidget(copy)
        tcard.body.addWidget(self.text)
        tcard.body.addLayout(row)
        lay.addWidget(tcard)

        fcard = Card("Dosya SHA-256")
        self.file = FolderPicker("Dosya yolu", file_mode=True)
        self.calc_btn = primary_button("Hesapla")
        self.calc_btn.clicked.connect(self.hash_file)
        self.cancel_btn = QPushButton("Durdur")
        self.cancel_btn.setEnabled(False)
        self.cancel_btn.clicked.connect(lambda: self.worker and self.worker.cancel())
        self.bar = QProgressBar()
        self.bar.setRange(0, 100)
        self.bar.setValue(0)
        self.file_hash = QLineEdit()
        self.file_hash.setReadOnly(True)
        self.expected = QLineEdit()
        self.expected.setPlaceholderText("Karşılaştırmak için beklenen özeti yapıştırın (isteğe bağlı)")
        self.expected.textChanged.connect(self._compare)
        self.match = QLabel("")
        fcard.body.addWidget(self.file)
        r2 = QHBoxLayout()
        r2.addWidget(self.calc_btn)
        r2.addWidget(self.cancel_btn)
        r2.addWidget(self.bar, 1)
        fcard.body.addLayout(r2)
        fcard.body.addWidget(self.file_hash)
        fcard.body.addWidget(self.expected)
        fcard.body.addWidget(self.match)
        lay.addWidget(fcard)
        lay.addStretch(1)

    def hash_file(self) -> None:
        path = self.file.path()
        if not os.path.isfile(path):
            self.match.setObjectName("Danger")
            self.match.setText("Geçerli bir dosya seçin.")
            self._repolish()
            return
        self.file_hash.clear()
        self.bar.setValue(0)

        def job(cancel, progress):
            return F.sha256_file(path, cancel, lambda d, t: progress(str(int(d * 100 / t) if t else 100)))

        self.worker = Worker(job, self)
        self.worker.progress.connect(lambda v: self.bar.setValue(int(v)))
        self.worker.succeeded.connect(self._hashed)
        self.worker.failed.connect(lambda m: self.match.setText(m))
        self.worker.cancelled.connect(lambda: self.match.setText("İptal edildi."))
        self.worker.finished.connect(self._finished)
        self.calc_btn.setEnabled(False)
        self.cancel_btn.setEnabled(True)
        self.worker.start()

    def _hashed(self, digest: str) -> None:
        self.bar.setValue(100)
        self.file_hash.setText(digest)
        self._compare()

    def _finished(self) -> None:
        self.calc_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)
        self.worker = None

    def _compare(self) -> None:
        exp = self.expected.text().strip().lower()
        got = self.file_hash.text().strip().lower()
        if not exp or not got:
            self.match.setText("")
            return
        if exp == got:
            self.match.setObjectName("Success")
            self.match.setText("✓ Özetler eşleşiyor — dosya doğrulandı.")
        else:
            self.match.setObjectName("Danger")
            self.match.setText("✗ Özetler eşleşmiyor!")
        self._repolish()

    def _repolish(self) -> None:
        self.match.style().unpolish(self.match)
        self.match.style().polish(self.match)

    def shutdown(self) -> None:
        if self.worker:
            self.worker.cancel()
            self.worker.wait(3000)


class CalcPage(QWidget):
    def __init__(self, main):
        super().__init__()
        lay = QVBoxLayout(self)
        lay.setContentsMargins(28, 24, 28, 20)
        lay.addWidget(page_header("Hesaplama Araçları", "Bilimsel hesap makinesi, birim dönüştürücü ve SHA-256."))
        self.tabs = QTabWidget()
        self.calculator = CalculatorTab()
        self.converter = ConverterTab()
        self.hash = HashTab()
        self.tabs.addTab(self.calculator, "Bilimsel Hesap Makinesi")
        self.tabs.addTab(self.converter, "Birim Dönüştürücü")
        self.tabs.addTab(self.hash, "SHA-256")
        lay.addWidget(self.tabs, 1)

    def open_tab(self, index: int) -> None:
        self.tabs.setCurrentIndex(index)

    def shutdown(self) -> None:
        self.hash.shutdown()
