"""Not sistemi: hızlı notlar, kategoriler, arama, otomatik kaydetme."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QComboBox, QHBoxLayout, QLineEdit, QListWidget, QListWidgetItem, QPlainTextEdit, QPushButton,
    QSplitter, QVBoxLayout, QWidget,
)

from ..widgets import Card, confirm, muted_label, page_header, primary_button

DEFAULT_CATEGORIES = ["Genel", "İş", "Kişisel", "Fikirler", "Yapılacaklar"]
ALL = "Tüm kategoriler"


class NotesPage(QWidget):
    def __init__(self, main):
        super().__init__()
        self.main = main
        self.db = main.storage
        self.current_id: Optional[int] = None
        self._loading = False

        lay = QVBoxLayout(self)
        lay.setContentsMargins(28, 24, 28, 20)
        lay.addWidget(page_header("Notlar", "Yazdıklarınız otomatik olarak kaydedilir."))
        split = QSplitter()

        # ---- Sol: liste ----
        left = Card()
        self.search = QLineEdit()
        self.search.setPlaceholderText("🔍  Notlarda ara…")
        self.search.textChanged.connect(self.reload)
        self.filter = QComboBox()
        self.filter.currentTextChanged.connect(self.reload)
        self.list = QListWidget()
        self.list.currentItemChanged.connect(self._on_select)
        btns = QHBoxLayout()
        new_btn = primary_button("+ Yeni not")
        new_btn.clicked.connect(self.new_note)
        self.del_btn = QPushButton("Sil")
        self.del_btn.setObjectName("Danger")
        self.del_btn.clicked.connect(self.delete_note)
        btns.addWidget(new_btn)
        btns.addWidget(self.del_btn)
        left.body.addWidget(self.search)
        left.body.addWidget(self.filter)
        left.body.addWidget(self.list, 1)
        left.body.addLayout(btns)
        split.addWidget(left)

        # ---- Sağ: düzenleyici ----
        right = Card()
        top = QHBoxLayout()
        self.title = QLineEdit()
        self.title.setPlaceholderText("Başlık")
        self.title.setStyleSheet("font-size: 14pt; font-weight: 600;")
        self.category = QComboBox()
        self.category.setEditable(True)
        self.category.setMinimumWidth(160)
        self.category.setToolTip("Kategori seçin veya yeni bir kategori yazın")
        top.addWidget(self.title, 1)
        top.addWidget(self.category)
        self.body = QPlainTextEdit()
        self.body.setPlaceholderText("Notunuzu yazın…")
        self.saved = muted_label("")
        right.body.addLayout(top)
        right.body.addWidget(self.body, 1)
        right.body.addWidget(self.saved)
        split.addWidget(right)
        split.setSizes([320, 680])
        lay.addWidget(split, 1)

        self._autosave = QTimer(self)
        self._autosave.setSingleShot(True)
        self._autosave.setInterval(700)
        self._autosave.timeout.connect(self.save_current)
        self.title.textChanged.connect(self._changed)
        self.body.textChanged.connect(self._changed)
        self.category.currentTextChanged.connect(self._changed)

        self._fill_categories()
        self.reload()
        self._set_editor_enabled(False)

    # ---------- yardımcılar ----------
    def _fill_categories(self) -> None:
        cats = sorted(set(DEFAULT_CATEGORIES) | set(self.db.categories()))
        cur_filter = self.filter.currentText() or ALL
        self.filter.blockSignals(True)
        self.filter.clear()
        self.filter.addItems([ALL] + cats)
        self.filter.setCurrentText(cur_filter if cur_filter in [ALL] + cats else ALL)
        self.filter.blockSignals(False)
        cur = self.category.currentText()
        self.category.blockSignals(True)
        self.category.clear()
        self.category.addItems(cats)
        self.category.setCurrentText(cur or "Genel")
        self.category.blockSignals(False)

    def _set_editor_enabled(self, on: bool) -> None:
        for w in (self.title, self.body, self.category, self.del_btn):
            w.setEnabled(on)
        if not on:
            self.saved.setText("Bir not seçin veya yeni not oluşturun.")

    def reload(self, *_args, select_id: Optional[int] = None) -> None:
        target = select_id if select_id is not None else self.current_id
        cat = self.filter.currentText()
        notes = self.db.list_notes(self.search.text(), None if cat in ("", ALL) else cat)
        self.list.blockSignals(True)
        self.list.clear()
        select_row = -1
        for i, n in enumerate(notes):
            title = n.title.strip() or (n.content.strip().splitlines() or ["Başlıksız not"])[0][:40]
            when = datetime.fromtimestamp(n.updated_at).strftime("%d.%m.%Y %H:%M")
            item = QListWidgetItem(f"{title}\n{n.category} • {when}")
            item.setData(Qt.UserRole, n.id)
            self.list.addItem(item)
            if n.id == target:
                select_row = i
        if select_row >= 0:
            self.list.setCurrentRow(select_row)
        self.list.blockSignals(False)

    def _on_select(self, item: Optional[QListWidgetItem], _prev=None) -> None:
        self.save_current()
        if item is None:
            return
        note = self.db.get_note(item.data(Qt.UserRole))
        if note is None:
            return
        self._loading = True
        self.current_id = note.id
        self.title.setText(note.title)
        self.body.setPlainText(note.content)
        self.category.setCurrentText(note.category)
        self._loading = False
        self._set_editor_enabled(True)
        self.saved.setText("Kaydedildi ✓")

    def _changed(self) -> None:
        if self._loading or self.current_id is None:
            return
        self.saved.setText("Kaydediliyor…")
        self._autosave.start()

    # ---------- işlemler ----------
    def new_note(self) -> None:
        self.save_current()
        cat = self.filter.currentText()
        nid = self.db.add_note("", "", "Genel" if cat in ("", ALL) else cat)
        # Düzenleyicideki eski içerik yeni nota yazılmasın diye seçim sıfırlanır.
        self.current_id = None
        self.search.blockSignals(True)
        self.search.clear()
        self.search.blockSignals(False)
        self.reload(select_id=nid)
        self._on_select(self.list.currentItem())
        self.title.setFocus()

    def save_current(self) -> None:
        if self.current_id is None or self._loading:
            return
        self._autosave.stop()
        cat = self.category.currentText().strip() or "Genel"
        self.db.update_note(self.current_id, self.title.text(), self.body.toPlainText(), cat)
        self.saved.setText("Kaydedildi ✓  " + datetime.now().strftime("%H:%M:%S"))
        if cat not in [self.filter.itemText(i) for i in range(self.filter.count())]:
            self._fill_categories()
        # Liste metnini güncelle (seçimi koruyarak)
        item = self.list.currentItem()
        if item is not None and item.data(Qt.UserRole) == self.current_id:
            title = self.title.text().strip() or (self.body.toPlainText().strip().splitlines() or ["Başlıksız not"])[0][:40]
            item.setText(f"{title}\n{cat} • {datetime.now().strftime('%d.%m.%Y %H:%M')}")

    def delete_note(self) -> None:
        if self.current_id is None:
            return
        name = self.title.text().strip() or "Başlıksız not"
        if not confirm(self, "Notu sil", f"\"{name}\" kalıcı olarak silinsin mi?", danger=True):
            return
        self._autosave.stop()
        self.db.delete_note(self.current_id)
        self.current_id = None
        self._loading = True
        self.title.clear()
        self.body.clear()
        self._loading = False
        self._set_editor_enabled(False)
        self.reload()
        self.main.notify("Not silindi.")

    def on_show(self) -> None:
        self._fill_categories()
        self.reload()

    def shutdown(self) -> None:
        self.save_current()
