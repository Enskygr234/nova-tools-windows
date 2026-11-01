"""Metin araçları: editör, sayaçlar, karşılaştırma, JSON, Base64."""
from __future__ import annotations

import os

from PySide6.QtCore import QTimer
from PySide6.QtGui import QFont, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QCheckBox, QFileDialog, QGridLayout, QHBoxLayout, QLabel, QPlainTextEdit, QPushButton,
    QSpinBox, QSplitter, QTabWidget, QTextBrowser, QVBoxLayout, QWidget,
)

from ...core import text as T
from ..widgets import Card, confirm, error, muted_label, page_header, primary_button

MAX_OPEN_BYTES = 20 * 1024 * 1024


def mono(widget: QPlainTextEdit) -> QPlainTextEdit:
    f = QFont("Consolas")
    f.setStyleHint(QFont.Monospace)
    f.setPointSize(10)
    widget.setFont(f)
    return widget


class EditorTab(QWidget):
    def __init__(self, main):
        super().__init__()
        self.main = main
        self.path: str | None = None
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 10, 0, 0)
        bar = QHBoxLayout()
        for text, slot, key in [("Yeni", self.new, "Ctrl+N"), ("Aç…", self.open, "Ctrl+O"),
                                ("Kaydet", self.save, "Ctrl+S"), ("Farklı kaydet…", self.save_as, "Ctrl+Shift+S")]:
            b = QPushButton(text)
            b.setToolTip(key)
            b.clicked.connect(slot)
            bar.addWidget(b)
            sc = QShortcut(QKeySequence(key), self)
            sc.activated.connect(slot)
        self.wrap = QCheckBox("Satır kaydır")
        self.wrap.setChecked(True)
        self.wrap.toggled.connect(lambda on: self.edit.setLineWrapMode(
            QPlainTextEdit.WidgetWidth if on else QPlainTextEdit.NoWrap))
        bar.addWidget(self.wrap)
        bar.addStretch(1)
        self.file_label = muted_label("Yeni belge")
        bar.addWidget(self.file_label)
        lay.addLayout(bar)
        self.edit = mono(QPlainTextEdit())
        self.edit.setPlaceholderText("Yazmaya başlayın veya bir dosya açın…")
        self.edit.textChanged.connect(self._update_stats)
        self.edit.modificationChanged.connect(lambda _m: self._update_title())
        lay.addWidget(self.edit, 1)
        self.stats = muted_label()
        lay.addWidget(self.stats)
        self._update_stats()

    def _update_stats(self) -> None:
        s = T.text_stats(self.edit.toPlainText())
        self.stats.setText(f"{s.words} kelime  •  {s.chars} karakter  •  {s.chars_no_spaces} boşluksuz  •  {s.lines} satır")

    def _update_title(self) -> None:
        name = os.path.basename(self.path) if self.path else "Yeni belge"
        self.file_label.setText(name + (" •" if self.edit.document().isModified() else ""))

    def _maybe_discard(self) -> bool:
        if not self.edit.document().isModified():
            return True
        return confirm(self, "Kaydedilmemiş değişiklikler",
                       "Kaydedilmemiş değişiklikler kaybolacak. Devam edilsin mi?", danger=True)

    def new(self) -> None:
        if self._maybe_discard():
            self.edit.clear()
            self.path = None
            self.edit.document().setModified(False)
            self._update_title()

    def open(self) -> None:
        if not self._maybe_discard():
            return
        path, _ = QFileDialog.getOpenFileName(self, "Dosya aç", "", "Metin dosyaları (*.txt *.md *.json *.csv *.log *.py *.xml *.html *.ini);;Tüm dosyalar (*)")
        if path:
            self.load(path)

    def load(self, path: str) -> bool:
        try:
            if os.path.getsize(path) > MAX_OPEN_BYTES:
                error(self, "Dosya çok büyük (en fazla 20 MB).")
                return False
            with open(path, "rb") as fh:
                raw = fh.read()
            for enc in ("utf-8-sig", "cp1254", "latin-1"):
                try:
                    content = raw.decode(enc)
                    break
                except UnicodeDecodeError:
                    continue
        except OSError as e:
            error(self, f"Dosya açılamadı:\n{e}")
            return False
        self.edit.setPlainText(content)
        self.path = path
        self.edit.document().setModified(False)
        self._update_title()
        return True

    def _write(self, path: str) -> bool:
        try:
            with open(path, "w", encoding="utf-8", newline="") as fh:
                fh.write(self.edit.toPlainText())
        except OSError as e:
            error(self, f"Kaydedilemedi:\n{e}")
            return False
        self.path = path
        self.edit.document().setModified(False)
        self._update_title()
        self.main.notify(f"Kaydedildi: {path}")
        return True

    def save(self) -> bool:
        if self.path:
            return self._write(self.path)
        return self.save_as()

    def save_as(self) -> bool:
        # Var olan dosyanın üzerine yazmadan önce sistem iletişim kutusu onay ister.
        path, _ = QFileDialog.getSaveFileName(self, "Farklı kaydet", self.path or "belge.txt",
                                              "Metin dosyası (*.txt);;Tüm dosyalar (*)")
        return self._write(path) if path else False

    def can_close(self) -> bool:
        return self._maybe_discard()


class CounterTab(QWidget):
    def __init__(self):
        super().__init__()
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 10, 0, 0)
        self.input = QPlainTextEdit()
        self.input.setPlaceholderText("Metni buraya yapıştırın; sayılar anında güncellenir.")
        self.input.textChanged.connect(self.refresh)
        lay.addWidget(self.input, 3)
        card = Card("İstatistikler")
        grid = QGridLayout()
        self.values: dict[str, QLabel] = {}
        labels = [("words", "Kelime"), ("chars", "Karakter (boşluklu)"), ("chars_no_spaces", "Karakter (boşluksuz)"),
                  ("letters", "Harf"), ("digits", "Rakam"), ("lines", "Satır"), ("sentences", "Cümle"),
                  ("paragraphs", "Paragraf"), ("unique_words", "Benzersiz kelime"), ("reading_minutes", "Okuma süresi (dk)")]
        for i, (key, text) in enumerate(labels):
            v = QLabel("0")
            v.setObjectName("CardTitle")
            grid.addWidget(muted_label(text), i, 0)
            grid.addWidget(v, i, 1)
            self.values[key] = v
        card.body.addLayout(grid)
        card.body.addWidget(QLabel("En sık kelimeler"))
        self.top = muted_label("–")
        card.body.addWidget(self.top)
        card.body.addStretch(1)
        lay.addWidget(card, 2)

    def refresh(self) -> None:
        txt = self.input.toPlainText()
        s = T.text_stats(txt)
        for key, lbl in self.values.items():
            val = getattr(s, key)
            lbl.setText(str(val).replace(".", ",") if isinstance(val, float) else str(val))
        top = T.top_words(txt, 8)
        self.top.setText(", ".join(f"{w} ({c})" for w, c in top) if top else "–")


class CompareTab(QWidget):
    def __init__(self, main):
        super().__init__()
        self.main = main
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 10, 0, 0)
        split = QSplitter()
        self.left = mono(QPlainTextEdit())
        self.left.setPlaceholderText("Orijinal metin")
        self.right = mono(QPlainTextEdit())
        self.right.setPlaceholderText("Değiştirilmiş metin")
        split.addWidget(self.left)
        split.addWidget(self.right)
        lay.addWidget(split, 2)
        row = QHBoxLayout()
        self.ignore_case = QCheckBox("Büyük/küçük harfi yok say")
        self.ignore_ws = QCheckBox("Boşlukları yok say")
        btn = primary_button("Karşılaştır")
        btn.clicked.connect(self.compare)
        row.addWidget(self.ignore_case)
        row.addWidget(self.ignore_ws)
        row.addStretch(1)
        self.summary = muted_label()
        row.addWidget(self.summary)
        row.addWidget(btn)
        lay.addLayout(row)
        self.out = QTextBrowser()
        lay.addWidget(self.out, 2)

    def compare(self) -> None:
        r = T.diff_texts(self.left.toPlainText(), self.right.toPlainText(),
                         self.ignore_case.isChecked(), self.ignore_ws.isChecked())
        self.out.setHtml(T.diff_to_html(r, dark=self.main.theme_mode == "dark"))
        self.summary.setText(f"+{r.added} eklenen  •  −{r.removed} silinen  •  benzerlik %{r.similarity * 100:.1f}".replace(".", ","))


class JsonTab(QWidget):
    def __init__(self):
        super().__init__()
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 10, 0, 0)
        row = QHBoxLayout()
        fmt = primary_button("Biçimlendir")
        mini = QPushButton("Küçült")
        val = QPushButton("Doğrula")
        self.indent = QSpinBox()
        self.indent.setRange(1, 8)
        self.indent.setValue(2)
        self.sort = QCheckBox("Anahtarları sırala")
        fmt.clicked.connect(self.format)
        mini.clicked.connect(self.minify)
        val.clicked.connect(self.validate)
        for w in (fmt, mini, val, QLabel("Girinti:"), self.indent, self.sort):
            row.addWidget(w)
        row.addStretch(1)
        self.status = muted_label()
        row.addWidget(self.status)
        lay.addLayout(row)
        split = QSplitter()
        self.input = mono(QPlainTextEdit())
        self.input.setPlaceholderText('{"ornek": [1, 2, 3]}')
        self.output = mono(QPlainTextEdit())
        self.output.setReadOnly(True)
        split.addWidget(self.input)
        split.addWidget(self.output)
        lay.addWidget(split, 1)

    def _run(self, fn) -> None:
        try:
            self.output.setPlainText(fn())
            self.status.setObjectName("Success")
            self.status.setText("✓ Geçerli JSON")
        except T.TextToolError as e:
            self.status.setObjectName("Danger")
            self.status.setText(str(e))
        self.status.style().unpolish(self.status)
        self.status.style().polish(self.status)

    def format(self) -> None:
        self._run(lambda: T.format_json(self.input.toPlainText(), self.indent.value(), self.sort.isChecked()))

    def minify(self) -> None:
        self._run(lambda: T.minify_json(self.input.toPlainText()))

    def validate(self) -> None:
        self._run(lambda: (T.format_json(self.input.toPlainText()), self.output.toPlainText())[1])


class Base64Tab(QWidget):
    def __init__(self):
        super().__init__()
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 10, 0, 0)
        self.input = mono(QPlainTextEdit())
        self.input.setPlaceholderText("Kodlanacak metin veya çözülecek Base64")
        lay.addWidget(self.input, 1)
        row = QHBoxLayout()
        enc = primary_button("Kodla ↓")
        dec = QPushButton("Çöz ↓")
        swap = QPushButton("⇅ Yer değiştir")
        self.url = QCheckBox("URL-güvenli")
        enc.clicked.connect(self.encode)
        dec.clicked.connect(self.decode)
        swap.clicked.connect(self.swap)
        for w in (enc, dec, swap, self.url):
            row.addWidget(w)
        row.addStretch(1)
        self.status = muted_label()
        row.addWidget(self.status)
        lay.addLayout(row)
        self.output = mono(QPlainTextEdit())
        self.output.setReadOnly(True)
        lay.addWidget(self.output, 1)

    def encode(self) -> None:
        self.output.setPlainText(T.b64_encode(self.input.toPlainText(), self.url.isChecked()))
        self.status.setText("Kodlandı.")

    def decode(self) -> None:
        try:
            self.output.setPlainText(T.b64_decode(self.input.toPlainText(), self.url.isChecked()))
            self.status.setText("Çözüldü.")
        except T.TextToolError as e:
            self.output.clear()
            self.status.setText(str(e))

    def swap(self) -> None:
        out = self.output.toPlainText()
        self.output.setPlainText(self.input.toPlainText())
        self.input.setPlainText(out)


class TextPage(QWidget):
    def __init__(self, main):
        super().__init__()
        lay = QVBoxLayout(self)
        lay.setContentsMargins(28, 24, 28, 20)
        lay.addWidget(page_header("Metin Araçları", "Editör, sayaçlar, karşılaştırma, JSON ve Base64 araçları."))
        self.tabs = QTabWidget()
        self.editor = EditorTab(main)
        self.counter = CounterTab()
        self.compare = CompareTab(main)
        self.json = JsonTab()
        self.b64 = Base64Tab()
        self.tabs.addTab(self.editor, "Metin Editörü")
        self.tabs.addTab(self.counter, "Kelime / Karakter Sayacı")
        self.tabs.addTab(self.compare, "Metin Karşılaştırma")
        self.tabs.addTab(self.json, "JSON Biçimlendirme")
        self.tabs.addTab(self.b64, "Base64")
        lay.addWidget(self.tabs, 1)

    def open_tab(self, index: int) -> None:
        self.tabs.setCurrentIndex(index)

    def can_close(self) -> bool:
        return self.editor.can_close()
